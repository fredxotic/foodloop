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
    Profile creation is now handled by signup form.
    This signal only ensures existing users have profiles (for admin users, etc.)
    """
    if not created:  # ONLY run on UPDATE, not on CREATE
        # Ensure profile exists for existing users (updates only)
        if not hasattr(instance, 'profile'):
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'user_type': UserProfile.DONOR if instance.is_staff else UserProfile.RECIPIENT,
                    'phone_number': None,  # Allow NULL for admin-created users
                    'location': ''
                }
            )