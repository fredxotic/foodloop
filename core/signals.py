from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Only create profile for EXISTING users (admin-created, etc.)
    Signup form handles new user profiles
    """
    if not created:  # ONLY run on UPDATE
        try:
            if not hasattr(instance, 'profile'):
                UserProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'user_type': UserProfile.DONOR if instance.is_staff else UserProfile.RECIPIENT,
                        'phone_number': None,
                        'location': ''
                    }
                )
        except Exception as e:
            logger.error(f"Error creating profile for {instance.username}: {e}")