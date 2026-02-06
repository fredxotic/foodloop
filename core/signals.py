from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.utils import ProgrammingError, OperationalError
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Only create profile for EXISTING users (admin-created, etc.)
    Signup form handles new user profiles
    
    Optimized: Uses try/except to handle table existence without raw SQL
    """
    if not created:  # ONLY run on UPDATE
        try:
            # Attempt to access the profile
            _ = instance.profile
        except AttributeError:
            # Profile doesn't exist, create it
            try:
                from .models import UserProfile
                
                profile, profile_created = UserProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'user_type': UserProfile.DONOR if instance.is_staff else UserProfile.RECIPIENT,
                        'phone_number': '',
                        'location': ''
                    }
                )
                if profile_created:
                    logger.info(f"Auto-created profile for {instance.username}")
            except (ProgrammingError, OperationalError) as e:
                # Table doesn't exist yet (during migrations)
                logger.debug(f"Skipping profile creation - tables not ready: {e}")
            except Exception as e:
                logger.error(f"Error creating profile for {instance.username}: {e}", exc_info=True)
        except (ProgrammingError, OperationalError) as e:
            # Table doesn't exist yet (during migrations)
            logger.debug(f"Skipping profile check - tables not ready: {e}")
        except Exception as e:
            logger.error(f"Error checking profile for {instance.username}: {e}", exc_info=True)