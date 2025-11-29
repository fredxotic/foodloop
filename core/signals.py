"""
Optimized Signal Handlers
Handles automatic profile creation and updates
"""
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every user has a profile.
    Only create if it doesn't exist to avoid conflicts with form-based creation.
    """
    if created:
        # Check if profile was already created by signup form
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(
                user=instance,
                user_type=UserProfile.DONOR if instance.is_staff else UserProfile.RECIPIENT
            )
    else:
        # Ensure profile exists for existing users
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'user_type': UserProfile.RECIPIENT}
        )