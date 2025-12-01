"""
Optimized Models for FoodLoop
Added database indexes for performance and validation improvements
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.templatetags.static import static
from django.core.exceptions import ValidationError
from geopy.geocoders import Nominatim 
from geopy.exc import GeocoderTimedOut
import uuid
from .validators import (
    validate_phone_number, validate_coordinates,
    validate_dietary_tags, validate_image_size
)


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class LocationAwareModel(models.Model):
    """Abstract base model for location data"""
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # If location exists but coords are missing, fetch them here.
        if self.location and (not self.latitude or not self.longitude):
            self._geocode_location()
        super().save(*args, **kwargs)

    def _geocode_location(self):
        try:
            geolocator = Nominatim(user_agent="foodloop_app")
            location = geolocator.geocode(self.location, timeout=5)
            if location:
                self.latitude = location.latitude
                self.longitude = location.longitude
        except (GeocoderTimedOut, Exception) as e:
            # Log error but don't stop the save
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Geocoding failed for {self.location}: {e}")
    
    @property
    def has_valid_coordinates(self):
        """Check if location has valid GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    def clean(self):
        """Validate coordinates"""
        super().clean()
        if self.latitude or self.longitude:
            validate_coordinates(self.latitude, self.longitude)


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


class UserProfile(TimeStampedModel, LocationAwareModel):
    """
    Extended user profile with role-based access and preferences
    Optimized with proper indexing
    """
    DONOR = 'donor'
    RECIPIENT = 'recipient'
    
    USER_TYPE_CHOICES = [
        (DONOR, 'Food Donor'),
        (RECIPIENT, 'Food Recipient'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        db_index=True
    )
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES,
        db_index=True,
        help_text="Type of user account"
    )
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        validators=[validate_phone_number],
        help_text="Contact phone number"
    )
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        help_text="Profile picture (max 5MB)"
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text="Short bio or description"
    )
    
    # Dietary preferences (for recipients)
    dietary_restrictions = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_dietary_tags],
        help_text="List of dietary restrictions"
    )
    
    # Verification status
    email_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Email verification status"
    )
    phone_verified = models.BooleanField(default=False)
    
    # Ratings and reputation
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_ratings = models.IntegerField(default=0)
    
    # Activity tracking
    last_active = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['user_type', 'email_verified']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['last_active']),
        ]
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_user_type_display()})"
    
    def get_profile_picture_url(self):
        """Get profile picture URL with fallback"""
        if self.profile_picture:
            return self.profile_picture.url
        return static('images/default-avatar.png')
    
    def is_dietary_compatible(self, donation):
        """Check if donation matches user's dietary restrictions"""
        if not self.dietary_restrictions:
            return True
        
        donation_tags = set(tag.lower() for tag in (donation.dietary_tags or []))
        user_restrictions = set(r.lower() for r in self.dietary_restrictions)
        
        # All user restrictions must be in donation tags
        return user_restrictions.issubset(donation_tags)
    
    def update_rating(self, new_rating):
        """Update average rating efficiently"""
        total = (self.average_rating * self.total_ratings) + new_rating
        self.total_ratings += 1
        self.average_rating = total / self.total_ratings
        self.save(update_fields=['average_rating', 'total_ratings'])


class Donation(TimeStampedModel, LocationAwareModel):
    """
    Food donation model with comprehensive tracking
    Optimized with proper indexing and validation
    """
    # Status choices
    AVAILABLE = 'available'
    CLAIMED = 'claimed'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (AVAILABLE, 'Available'),
        (CLAIMED, 'Claimed'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (EXPIRED, 'Expired'),
    ]
    
    # Food categories
    FOOD_CATEGORY_CHOICES = [
        ('fruits', 'Fruits'),
        ('vegetables', 'Vegetables'),
        ('grains', 'Grains & Bread'),
        ('protein', 'Protein (Meat/Fish)'),
        ('dairy', 'Dairy Products'),
        ('prepared', 'Prepared Meals'),
        ('pantry', 'Pantry Items'),
        ('beverages', 'Beverages'),
        ('other', 'Other'),
    ]
    
    # Core fields
    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations',
        db_index=True
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_donations',
        db_index=True
    )
    
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    food_category = models.CharField(
        max_length=50,
        choices=FOOD_CATEGORY_CHOICES,
        db_index=True
    )
    
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity of food items"
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=AVAILABLE,
        db_index=True
    )
    
    expiry_datetime = models.DateTimeField(
        db_index=True,
        help_text="When the food expires"
    )
    pickup_start = models.DateTimeField(
        db_index=True,
        help_text="Start of pickup window"
    )
    pickup_end = models.DateTimeField(
        db_index=True,
        help_text="End of pickup window"
    )
    
    # Location details
    pickup_location = models.CharField(max_length=255)
    
    # Image
    image = models.ImageField(
        upload_to=donation_image_path,
        blank=True,
        null=True,
        validators=[validate_image_size]
    )
    
    # Nutrition information
    dietary_tags = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_dietary_tags],
        help_text="Dietary tags (vegetarian, vegan, etc.)"
    )
    estimated_calories = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    nutrition_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Nutrition quality score (0-100)"
    )
    ingredients_list = models.TextField(blank=True)
    allergen_info = models.TextField(blank=True)
    
    # Timestamps for status changes
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'donations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expiry_datetime']),
            models.Index(fields=['donor', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['food_category', 'status']),
            models.Index(fields=['latitude', 'longitude', 'status']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Donation'
        verbose_name_plural = 'Donations'
    
    def __str__(self):
        return f"{self.title} by {self.donor.get_full_name()}"
    
    def is_expired(self):
        """Check if donation has expired"""
        return timezone.now() >= self.expiry_datetime
    
    def is_pickup_overdue(self):
        """Check if pickup window has passed"""
        return timezone.now() > self.pickup_end
    
    def time_until_expiry(self):
        """Get time until expiry as timedelta"""
        if self.is_expired():
            return None
        return self.expiry_datetime - timezone.now()
    
    def claim(self, user):
        """Claim this donation for a user"""
        if self.status != self.AVAILABLE:
            raise ValidationError("This donation is not available")
        
        if self.is_expired():
            self.status = self.EXPIRED
            self.save()
            raise ValidationError("This donation has expired")
        
        self.recipient = user
        self.status = self.CLAIMED
        self.claimed_at = timezone.now()
        self.save(update_fields=['recipient', 'status', 'claimed_at'])
    
    def complete(self):
        """Mark donation as completed"""
        if self.status != self.CLAIMED:
            raise ValidationError("Only claimed donations can be completed")
        
        self.status = self.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def cancel(self):
        """Cancel donation"""
        if self.status in [self.COMPLETED, self.EXPIRED]:
            raise ValidationError(f"Cannot cancel {self.status} donation")
        
        self.status = self.CANCELLED
        self.save(update_fields=['status'])
    
    def get_image_url(self):
        """Get donation image URL with fallback"""
        if self.image:
            return self.image.url
        return static('images/default-food.png')


class Rating(TimeStampedModel):
    """
    Rating system for users
    Optimized with compound indexes
    """
    rated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_ratings',
        db_index=True
    )
    rating_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        db_index=True
    )
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='ratings',
        db_index=True
    )
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(blank=True, max_length=500)
    
    class Meta:
        db_table = 'ratings'
        unique_together = ['rating_user', 'donation']
        indexes = [
            models.Index(fields=['rated_user', '-created_at']),
            models.Index(fields=['donation']),
        ]
        verbose_name = 'Rating'
        verbose_name_plural = 'Ratings'
    
    def __str__(self):
        return f"{self.rating_user.username} rated {self.rated_user.username}: {self.rating}/5"
    
    def save(self, *args, **kwargs):
        """Update user's average rating on save"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update rated user's profile
            try:
                profile = self.rated_user.profile
                profile.update_rating(self.rating)
            except Exception as e:
                import logging
                logging.error(f"Failed to update rating: {e}")


class Notification(TimeStampedModel):
    """
    Notification system
    Optimized with selective indexes
    """
    # Notification types
    DONATION_CLAIMED = 'donation_claimed'
    DONATION_COMPLETED = 'donation_completed'
    NEW_DONATION = 'new_donation'
    RATING_RECEIVED = 'rating_received'
    SYSTEM = 'system'
    
    NOTIFICATION_TYPE_CHOICES = [
        (DONATION_CLAIMED, 'Donation Claimed'),
        (DONATION_COMPLETED, 'Donation Completed'),
        (NEW_DONATION, 'New Donation'),
        (RATING_RECEIVED, 'Rating Received'),
        (SYSTEM, 'System Notification'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    related_donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_url = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class EmailVerification(TimeStampedModel):
    """
    Email verification tokens
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    expires_at = models.DateTimeField(db_index=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'email_verifications'
        ordering = ['-created_at']
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
    
    def __str__(self):
        return f"Verification for {self.user.email}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at


class NutritionImpact(TimeStampedModel):
    """
    Track nutrition impact and analytics
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='nutrition_impacts',
        db_index=True
    )
    date = models.DateField(db_index=True)
    
    donations_made = models.IntegerField(default=0)
    donations_received = models.IntegerField(default=0)
    total_calories = models.IntegerField(default=0)
    avg_nutrition_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    
    class Meta:
        db_table = 'nutrition_impacts'
        unique_together = ['user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
        verbose_name = 'Nutrition Impact'
        verbose_name_plural = 'Nutrition Impacts'
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"