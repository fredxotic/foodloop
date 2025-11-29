"""
Context processors for adding common data to all templates
Optimized with caching to reduce database queries
"""
from core.cache import CacheManager
import logging

logger = logging.getLogger(__name__)


def user_profile(request):
    """
    Add user profile and notification count to all template contexts
    Uses caching to minimize database hits
    """
    context = {
        'user_profile': None,
        'unread_notifications': 0,
    }
    
    if request.user.is_authenticated:
        try:
            from core.models import UserProfile, Notification
            
            # Try to get profile from cache first
            cached_profile_data = CacheManager.get_user_profile(request.user.id)
            
            if cached_profile_data:
                # Reconstruct minimal profile object for template
                context['user_profile'] = type('obj', (object,), cached_profile_data)
            else:
                # Fetch from database and cache
                user_profile = UserProfile.objects.select_related('user').get(user=request.user)
                
                # Cache essential profile data
                profile_data = {
                    'user_type': user_profile.user_type,
                    'email_verified': user_profile.email_verified,
                    'profile_picture': user_profile.profile_picture.url if user_profile.profile_picture else None,
                    'phone_number': user_profile.phone_number,
                    'location': user_profile.location,
                    'has_valid_coordinates': user_profile.has_valid_coordinates,
                }
                CacheManager.set_user_profile(request.user.id, profile_data)
                
                context['user_profile'] = user_profile
            
            # Get unread notification count with caching
            unread_count = CacheManager.get_notification_count(request.user.id)
            
            if unread_count is None:
                unread_count = Notification.objects.filter(
                    user=request.user,
                    is_read=False
                ).count()
                CacheManager.set_notification_count(request.user.id, unread_count)
            
            context['unread_notifications'] = unread_count
            
        except UserProfile.DoesNotExist:
            logger.warning(f"Profile not found for user {request.user.id}")
            context['user_profile'] = None
        except Exception as e:
            logger.error(f"Context processor error for user {request.user.id}: {e}")
    
    return context


def site_settings(request):
    """
    Add global site settings to context
    Cached for performance
    """
    from django.conf import settings
    
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'FoodLoop'),
        'SITE_URL': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'DEBUG': settings.DEBUG,
    }


def donation_categories(request):
    """
    Add donation categories to context for forms/filters
    """
    from core.models import Donation
    
    return {
        'FOOD_CATEGORIES': Donation.FOOD_CATEGORY_CHOICES,
        'DONATION_STATUSES': Donation.STATUS_CHOICES,
    }