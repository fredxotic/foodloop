# core/models.py
from django.db import models
from django.contrib.auth.models import User

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
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"

class Donation(models.Model):
    PENDING = 'pending'
    AVAILABLE = 'available'
    CLAIMED = 'claimed'
    COMPLETED = 'completed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (AVAILABLE, 'Available'),
        (CLAIMED, 'Claimed'),
        (COMPLETED, 'Completed'),
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
    pickup_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_donations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.food_type} from {self.donor.username}"