"""
Optimized Models for FoodLoop
Phase 1: GPS fields removed, simple location text only
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.templatetags.static import static
from django.core.exceptions import ValidationError
from .validators import validate_phone_number, validate_dietary_tags, validate_image_size
import uuid
import logging
import re

logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


def user_profile_picture_path(instance, filename):
    """Generate upload path for user profile pictures"""
    ext = filename.split('.')[-1]
    filename = f'profile_{instance.user.id}_{uuid.uuid4().hex[:8]}.{ext}'
    return f'profiles/{filename}'


def donation_image_path(instance, filename):
    """Generate upload path for donation images"""
    ext = filename.split('.')[-1]
    filename = f'donation_{instance.id or uuid.uuid4().hex[:8]}.{ext}'
    return f'donations/{filename}'


class UserProfile(TimeStampedModel):
    """User profile with simplified location"""
    
    DONOR = 'donor'
    RECIPIENT = 'recipient'
    USER_TYPE_CHOICES = [
        (DONOR, 'Donor'),
        (RECIPIENT, 'Recipient'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES,
        db_index=True
    )
    
    # Contact & Location (SIMPLIFIED)
    phone_number = models.CharField(
        max_length=15, 
        blank=True,
        null=True,
        validators=[validate_phone_number]
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="City or neighborhood (e.g., 'Westlands, Nairobi')"
    )
    
    # Profile
    bio = models.TextField(blank=True, max_length=500)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        validators=[validate_image_size]
    )
    
    # Dietary Preferences (For Recipients)
    dietary_restrictions = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_dietary_tags],
        help_text="List of dietary restrictions (e.g., ['vegetarian', 'gluten-free'])"
    )
    
    # Verification & Reputation
    email_verified = models.BooleanField(default=False)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_ratings = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['user_type', 'email_verified']),
            models.Index(fields=['average_rating']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_user_type_display()})"
    
    def update_rating_stats(self):
        """Recalculate average rating from all ratings"""
        from django.db.models import Avg, Count
        
        stats = Rating.objects.filter(rated_user=self.user).aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )
        
        self.average_rating = round(stats['avg'] or 0, 2)
        self.total_ratings = stats['count']
        self.save(update_fields=['average_rating', 'total_ratings'])
    
    def is_dietary_compatible(self, donation):
        """Check if donation is safe for user's dietary restrictions
        
        Algorithm:
        - Donation must contain ALL lifestyle tags requested by user
        - Donation must contain ZERO allergen tags restricted by user
        
        This ensures safety: allergen exposure is prevented.
        """
        if not self.dietary_restrictions or not donation.dietary_tags:
            return True
        
        from core.validators import get_lifestyle_tags, get_allergen_tags
        
        lifestyle_tag_list = get_lifestyle_tags()
        allergen_tag_list = get_allergen_tags()
        
        # Separate user restrictions into lifestyle and allergens
        user_lifestyle = set(tag for tag in self.dietary_restrictions if tag.lower() in lifestyle_tag_list)
        user_allergens = set(tag for tag in self.dietary_restrictions if tag.lower() in allergen_tag_list)
        
        # Separate donation tags into lifestyle and allergens
        donation_lifestyle = set(tag for tag in donation.dietary_tags if tag.lower() in lifestyle_tag_list)
        donation_allergens = set(tag for tag in donation.dietary_tags if tag.lower() in allergen_tag_list)
        
        # Safety check: donation must NOT contain any allergens user is avoiding
        if user_allergens & donation_allergens:
            return False  # UNSAFE: contains allergen
        
        # Lifestyle check: donation must contain ALL lifestyle tags user wants
        if user_lifestyle and not user_lifestyle.issubset(donation_lifestyle):
            return False  # Missing required lifestyle tags
        
        return True  # SAFE and compatible


class Donation(TimeStampedModel):
    """Simplified donation model without GPS"""
    
    # Status choices
    AVAILABLE = 'available'
    CLAIMED = 'claimed'
    COMPLETED = 'completed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (AVAILABLE, 'Available'),
        (CLAIMED, 'Claimed'),
        (COMPLETED, 'Completed'),
        (EXPIRED, 'Expired'),
        (CANCELLED, 'Cancelled'),
    ]
    
    # Food categories
    FOOD_CATEGORY_CHOICES = [
        ('fruits', 'Fruits'),
        ('vegetables', 'Vegetables'),
        ('grains', 'Grains & Bread'),
        ('protein', 'Protein (Meat/Fish)'),
        ('dairy', 'Dairy'),
        ('pantry', 'Pantry Items'),
        ('prepared', 'Prepared Meals'),
        ('beverages', 'Beverages'),
        ('other', 'Other'),
    ]
    
    # Core Fields
    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations_given'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations_received'
    )
    
    title = models.CharField(max_length=200, db_index=True)
    food_category = models.CharField(
        max_length=20,
        choices=FOOD_CATEGORY_CHOICES,
        db_index=True
    )
    description = models.TextField()
    quantity = models.CharField(max_length=100)
    
    # Timing
    expiry_datetime = models.DateTimeField(db_index=True)
    pickup_start = models.DateTimeField()
    pickup_end = models.DateTimeField()
    
    # Location (SIMPLIFIED - Text only)
    pickup_location = models.CharField(
        max_length=255,
        help_text="Full address or meeting point"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=AVAILABLE,
        db_index=True
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Media
    image = models.ImageField(
        upload_to=donation_image_path,
        blank=True,
        null=True,
        validators=[validate_image_size]
    )
    
    # Nutrition Info (Optional)
    dietary_tags = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_dietary_tags]
    )
    estimated_calories = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    nutrition_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    ingredients_list = models.TextField(blank=True)
    allergen_info = models.TextField(blank=True)
    
    class Meta:
        db_table = 'donations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expiry_datetime']),
            models.Index(fields=['donor', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['food_category']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.donor.get_full_name()}"
    
    def is_expired(self) -> bool:
        """Check if donation has expired"""
        return timezone.now() > self.expiry_datetime
    
    def is_pickup_overdue(self) -> bool:
        """Check if pickup window has passed"""
        return timezone.now() > self.pickup_end
    
    def claim(self, recipient: User):
        """Claim this donation"""
        self.recipient = recipient
        self.status = self.CLAIMED
        self.claimed_at = timezone.now()
        self.save(update_fields=['recipient', 'status', 'claimed_at'])
    
    def complete(self):
        """Mark donation as completed"""
        self.status = self.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def cancel(self):
        """Cancel donation"""
        self.status = self.CANCELLED
        self.save(update_fields=['status'])
    
    def get_time_until_expiry(self) -> str:
        """Human-readable time until expiry"""
        if self.is_expired():
            return "Expired"
        
        delta = self.expiry_datetime - timezone.now()
        hours = delta.total_seconds() / 3600
        
        if hours < 1:
            return f"{int(delta.total_seconds() / 60)} minutes"
        elif hours < 24:
            return f"{int(hours)} hours"
        else:
            return f"{int(hours / 24)} days"


class Rating(TimeStampedModel):
    """Rating system for user reputation"""
    
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rating_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ratings_given',
        help_text="User who gave the rating"
    )
    rated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ratings_received',
        help_text="User being rated"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, max_length=500)
    
    class Meta:
        db_table = 'ratings'
        unique_together = ['donation', 'rating_user', 'rated_user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rated_user', 'rating']),
        ]
    
    def __str__(self):
        return f"{self.rating}★ for {self.rated_user.username} by {self.rating_user.username}"
    
    def save(self, *args, **kwargs):
        """Update user's rating stats after saving"""
        super().save(*args, **kwargs)
        
        # Update rated user's profile stats using correct method
        try:
            profile = UserProfile.objects.get(user=self.rated_user)
            profile.update_rating_stats()
        except UserProfile.DoesNotExist:
            logger.warning(f"Profile not found for user {self.rated_user.id}")
        except Exception as e:
            logger.error(f"Error updating rating stats: {e}")


class Notification(TimeStampedModel):
    """Simple notification system"""
    
    # Notification types
    DONATION_CLAIMED = 'donation_claimed'
    DONATION_COMPLETED = 'donation_completed'
    NEW_DONATION = 'new_donation'
    RATING_RECEIVED = 'rating_received'
    SYSTEM = 'system'
    
    TYPE_CHOICES = [
        (DONATION_CLAIMED, 'Donation Claimed'),
        (DONATION_COMPLETED, 'Donation Completed'),
        (NEW_DONATION, 'New Donation'),
        (RATING_RECEIVED, 'Rating Received'),
        (SYSTEM, 'System Notification'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        db_index=True
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_url = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
        default=''
    )
    is_read = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} for {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])


class EmailVerification(TimeStampedModel):
    """Email verification tokens"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'email_verifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Email verification for {self.user.email}"
    
    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return not self.is_used and timezone.now() < self.expires_at