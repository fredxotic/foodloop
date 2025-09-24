from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os
from geopy.geocoders import Nominatim
import geopy.exc
from django.conf import settings

def user_profile_picture_path(instance, filename):
    """Ensure proper path for profile pictures"""
    if instance.user.id:
        return f'profile_pictures/user_{instance.user.id}/{filename}'
    else:
        return f'profile_pictures/temp/{filename}'

def donation_image_path(instance, filename):
    if instance.pk:  # Use primary key instead of id
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
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"
    
    def get_profile_picture_url(self):
        """Safe method to get profile picture URL"""
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        # Use absolute path to static file
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
        # Use absolute path to static file
        return '/static/images/default-donation.jpg'
    
    def save(self, *args, **kwargs):
        # First save to get an ID for image path
        if self.pk is None:
            # Save once to get primary key
            super().save(*args, **kwargs)
            
            # Now handle image with proper path
            if self.image and hasattr(self.image, 'name'):
                # Get the original filename
                original_path = self.image.name
                # Generate new path with correct donation ID
                new_path = donation_image_path(self, os.path.basename(original_path))
                if original_path != new_path:
                    # Rename the file
                    try:
                        os.rename(
                            os.path.join(settings.MEDIA_ROOT, original_path),
                            os.path.join(settings.MEDIA_ROOT, new_path)
                        )
                        self.image.name = new_path
                    except (OSError, FileNotFoundError):
                        # If rename fails, keep original path
                        pass
        
        # Then do the geocoding and status updates
        if self.location and (not self.latitude or not self.longitude):
            self.geocode_location()
        
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
                print(f"Geocoded {self.location} to {self.latitude}, {self.longitude}")
            else:
                self.latitude = None
                self.longitude = None
                self.location_precision = 'failed'
                print(f"Geocoding failed for: {self.location}")
                
        except (geopy.exc.GeocoderTimedOut, geopy.exc.GeocoderServiceError) as e:
            print(f"Geocoding error for {self.location}: {e}")
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

class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification for {self.user.username}"
    

# Add to core/models.py after the existing models

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
        unique_together = ('donor', 'recipient', 'donation')  # One rating per donation pair
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rating} stars - {self.donor.username} to {self.recipient.username}"
    
    def get_rating_display(self):
        return f"{'★' * self.rating}{'☆' * (5 - self.rating)}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('donation_claimed', 'Donation Claimed'),
        ('donation_completed', 'Donation Completed'),
        ('new_donation', 'New Donation Available'),
        ('rating_received', 'New Rating Received'),
        ('message_received', 'New Message'),
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


