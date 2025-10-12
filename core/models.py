from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os
from geopy.geocoders import Nominatim
import geopy.exc
from django.conf import settings
import json

def user_profile_picture_path(instance, filename):
    """Ensure proper path for profile pictures"""
    if instance.user.id:
        return f'profile_pictures/user_{instance.user.id}/{filename}'
    else:
        return f'profile_pictures/temp/{filename}'

def donation_image_path(instance, filename):
    if instance.pk:
        return f'donation_images/donation_{instance.pk}/{filename}'
    else:
        return f'donation_images/temp/{filename}'

class UserProfile(models.Model):
    DONOR = 'donor'
    RECIPIENT = 'recipient'
    USER_TYPE_CHOICES = [
        (DONOR, 'Donor'),
        (RECIPIENT, 'Recipient'),
    ]
    
    # Dietary & Nutrition Goals
    DIETARY_RESTRICTION_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-Free'),
        ('dairy_free', 'Dairy-Free'),
        ('nut_free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('low_carb', 'Low-Carb'),
        ('diabetic', 'Diabetic-Friendly'),
    ]
    
    NUTRITION_GOAL_CHOICES = [
        ('balanced', 'Balanced Diet'),
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('maintenance', 'Maintenance'),
        ('health_condition', 'Specific Health Condition'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=DONOR)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True
    )
    
    # NEW: Dietary Preference Fields
    dietary_restrictions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of dietary restrictions"
    )
    allergies = models.TextField(
        blank=True,
        help_text="List any food allergies (comma separated)"
    )
    preferred_food_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Preferred food categories"
    )
    nutrition_goals = models.CharField(
        max_length=20,
        choices=NUTRITION_GOAL_CHOICES,
        default='balanced'
    )
    health_notes = models.TextField(
        blank=True,
        help_text="Any additional health or nutrition notes"
    )
    
    # Location coordinates
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"
    
    def get_profile_picture_url(self):
        """Safe method to get profile picture URL"""
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-profile.png'

    def get_average_rating(self):
        """Calculate average rating for this user based on their role"""
        if self.user_type == self.DONOR:
            ratings = Rating.objects.filter(donor=self.user)
        else:
            ratings = Rating.objects.filter(recipient=self.user)
        
        if ratings.exists():
            return round(ratings.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0.0
    
    def get_rating_count(self):
        """Get total number of ratings for this user"""
        if self.user_type == self.DONOR:
            return Rating.objects.filter(donor=self.user).count()
        else:
            return Rating.objects.filter(recipient=self.user).count()
    
    def get_recent_ratings(self, limit=5):
        """Get recent ratings for this user"""
        if self.user_type == self.DONOR:
            return Rating.objects.filter(donor=self.user).select_related('recipient', 'donation')[:limit]
        else:
            return Rating.objects.filter(recipient=self.user).select_related('donor', 'donation')[:limit]
    
    # NEW: Dietary Methods
    def get_dietary_badges(self):
        """Return dietary restrictions as list for display"""
        return self.dietary_restrictions or []
    
    def has_dietary_restrictions(self):
        """Check if user has any dietary restrictions"""
        return bool(self.dietary_restrictions)
    
    def get_allergies_list(self):
        """Return allergies as cleaned list"""
        if self.allergies:
            return [allergy.strip() for allergy in self.allergies.split(',')]
        return []
    
    def get_nutrition_match_score(self, donation):
        """Calculate how well a donation matches user's nutritional needs"""
        score = 0
        
        # Basic food type preference matching
        if donation.food_type in self.preferred_food_types:
            score += 30
        
        # Dietary restriction matching
        user_restrictions = set(self.dietary_restrictions)
        donation_tags = set(donation.dietary_tags)
        
        # Penalize if donation contains restricted items
        if user_restrictions and not donation_tags.issuperset(user_restrictions):
            score -= 50
        
        # Bonus for perfect matches
        if donation_tags.issuperset(user_restrictions):
            score += 20
            
        return min(max(score, 0), 100)


class Donation(models.Model):
    PENDING = 'pending'
    AVAILABLE = 'available'
    CLAIMED = 'claimed'
    COMPLETED = 'completed'
    EXPIRED = 'expired'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (AVAILABLE, 'Available'),
        (CLAIMED, 'Claimed'),
        (COMPLETED, 'Completed'),
        (EXPIRED, 'Expired'),
    ]
    
    FOOD_CATEGORIES = [
        ('vegetables', 'Vegetables'),
        ('fruits', 'Fruits'),
        ('dairy', 'Dairy'),
        ('bakery', 'Bakery'),
        ('cooked', 'Cooked Food'),
        ('grains', 'Grains & Cereals'),
        ('protein', 'Proteins'),
        ('beverages', 'Beverages'),
        ('other', 'Other'),
    ]
    
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    food_type = models.CharField(max_length=50, choices=FOOD_CATEGORIES)
    quantity = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(
        upload_to=donation_image_path,
        blank=True,
        null=True,
        help_text="Photo of the food donation"
    )
    expiry_date = models.DateTimeField(default=timezone.now() + timedelta(days=7))
    pickup_time = models.DateTimeField(default=timezone.now() + timedelta(days=1))
    pickup_deadline = models.DateTimeField(default=timezone.now() + timedelta(days=2))
    location = models.CharField(max_length=255)
    
    # Map integration fields
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_precision = models.CharField(max_length=20, blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_donations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # NEW: Nutrition & Dietary Fields
    dietary_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Dietary compatibility tags"
    )
    estimated_calories = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated total calories"
    )
    nutrition_score = models.IntegerField(
        default=0,
        help_text="Nutrition quality score (0-100)"
    )
    ingredients = models.TextField(
        blank=True,
        help_text="List of main ingredients"
    )
    preparation_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('raw', 'Raw'),
            ('cooked', 'Cooked'),
            ('baked', 'Baked'),
            ('fried', 'Fried'),
            ('other', 'Other')
        ],
        default='other'
    )
    
    def __str__(self):
        return f"{self.food_type} from {self.donor.username}"
    
    def is_expired(self):
        return timezone.now() > self.expiry_date
    
    def is_pickup_overdue(self):
        return timezone.now() > self.pickup_deadline
    
    def get_image_url(self):
        """Safe method to get donation image URL"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default-donation.jpg'
    
    def save(self, *args, **kwargs):
        # SIMPLIFIED: Remove complex file renaming logic
        
        # Geocoding
        if self.location and (not self.latitude or not self.longitude):
            self.geocode_location()
        
        # Auto-calculate nutrition score if not set
        if not self.nutrition_score:
            self.nutrition_score = self.calculate_nutrition_score()
        
        # Update status if expired
        if self.is_expired() and self.status != self.EXPIRED:
            self.status = self.EXPIRED
        
        super().save(*args, **kwargs)
    
    def geocode_location(self):
        """Convert address to coordinates using OpenStreetMap"""
        try:
            geolocator = Nominatim(user_agent="foodloop_app")
            location = geolocator.geocode(self.location, timeout=10)
            
            if location:
                self.latitude = location.latitude
                self.longitude = location.longitude
                self.location_precision = 'exact' if 'address' in location.raw.get('type', '') else 'approximate'
            else:
                self.latitude = None
                self.longitude = None
                self.location_precision = 'failed'
                
        except (geopy.exc.GeocoderTimedOut, geopy.exc.GeocoderServiceError) as e:
            self.latitude = None
            self.longitude = None
            self.location_precision = 'error'
    
    def get_map_marker_color(self):
        """Return color based on donation status"""
        color_map = {
            self.AVAILABLE: 'green',
            self.CLAIMED: 'orange', 
            self.COMPLETED: 'blue',
            self.EXPIRED: 'red',
            self.PENDING: 'gray'
        }
        return color_map.get(self.status, 'gray')
    
    @property
    def has_valid_coordinates(self):
        return self.latitude is not None and self.longitude is not None
    
    # NEW: Nutrition Methods
    def calculate_nutrition_score(self):
        """Calculate a basic nutrition score based on food type and tags"""
        base_scores = {
            'vegetables': 90,
            'fruits': 85,
            'grains': 70,
            'protein': 75,
            'dairy': 65,
            'bakery': 50,
            'cooked': 60,
            'beverages': 40,
            'other': 50
        }
        
        score = base_scores.get(self.food_type, 50)
        
        # Adjust based on dietary tags
        healthy_tags = ['vegetarian', 'vegan', 'gluten_free', 'low_carb']
        for tag in self.dietary_tags:
            if tag in healthy_tags:
                score += 5
                
        return min(max(score, 0), 100)
    
    def get_dietary_badges(self):
        """Return dietary tags as list for display"""
        return self.dietary_tags or []
    
    def is_dietary_compatible(self, user_profile):
        """Check if donation is compatible with user's dietary needs"""
        user_restrictions = set(user_profile.dietary_restrictions)
        donation_tags = set(self.dietary_tags)
        
        # If user has restrictions, donation must support all of them
        if user_restrictions:
            return donation_tags.issuperset(user_restrictions)
        
        return True
    
    def get_calorie_estimate(self):
        """Get calorie estimate with fallback"""
        if self.estimated_calories:
            return self.estimated_calories
        
        # Fallback estimates based on food type
        calorie_estimates = {
            'vegetables': 50,
            'fruits': 80,
            'dairy': 120,
            'bakery': 250,
            'cooked': 300,
            'grains': 150,
            'protein': 200,
            'beverages': 100,
            'other': 150
        }
        
        return calorie_estimates.get(self.food_type, 100)


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification for {self.user.username}"


class Rating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donor_ratings')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipient_ratings')
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('donor', 'recipient', 'donation')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rating} stars - {self.donor.username} to {self.recipient.username}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('donation_claimed', 'Donation Claimed'),
        ('donation_completed', 'Donation Completed'),
        ('new_donation', 'New Donation Available'),
        ('rating_received', 'New Rating Received'),
        ('dietary_match', 'Dietary Match Found'),
        ('nutrition_insight', 'Nutrition Insight'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_url = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


# NEW: Nutrition Impact Analytics
class NutritionImpact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nutrition_impacts')
    date = models.DateField(default=timezone.now)
    
    # Food metrics
    donations_made = models.IntegerField(default=0)
    donations_received = models.IntegerField(default=0)
    total_calories = models.IntegerField(default=0)
    
    # Nutrition metrics
    protein_grams = models.FloatField(default=0.0)
    carbs_grams = models.FloatField(default=0.0)
    fats_grams = models.FloatField(default=0.0)
    fiber_grams = models.FloatField(default=0.0)
    
    # Environmental impact
    co2_saved_kg = models.FloatField(default=0.0)
    water_saved_liters = models.FloatField(default=0.0)
    food_waste_prevented_kg = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"Nutrition Impact - {self.user.username} - {self.date}"
    
    def calculate_environmental_impact(self):
        """Calculate environmental impact based on food saved"""
        # Rough estimates (can be refined)
        self.co2_saved_kg = self.food_waste_prevented_kg * 2.5  # kg CO2 per kg food
        self.water_saved_liters = self.food_waste_prevented_kg * 1000  # liters per kg
        self.save()