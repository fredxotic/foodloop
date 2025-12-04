from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def tables_exist():
    """Check if core tables exist before running signals"""
    try:
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                # SQLite check
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='user_profiles'
                """)
                return cursor.fetchone() is not None
            else:
                # PostgreSQL check
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'user_profiles'
                    );
                """)
                return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Table check error: {e}")
        return False


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Only create profile for EXISTING users (admin-created, etc.)
    Signup form handles new user profiles
    """
    # Skip if tables don't exist yet (during migrations)
    if not tables_exist():
        logger.debug("Skipping profile creation - tables not ready")
        return
    
    if not created:  # ONLY run on UPDATE
        try:
            if not hasattr(instance, 'profile'):
                from .models import UserProfile
                
                profile, created = UserProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'user_type': UserProfile.DONOR if instance.is_staff else UserProfile.RECIPIENT,
                        'phone_number': '',
                        'location': ''
                    }
                )
                if created:
                    logger.info(f"Auto-created profile for {instance.username}")
        except Exception as e:
            logger.error(f"Error creating profile for {instance.username}: {e}", exc_info=True)