"""
Context processors for adding common data to all templates
Optimized with caching to reduce database queries
"""
import logging

logger = logging.getLogger(__name__)


def user_profile(request):
    """
    Add user profile and notification count to all template contexts
    Uses caching to minimize database hits
    """
    if not request.user.is_authenticated:
        return {
            'user_profile': None,
            'unread_notifications_count': 0,
        }
    
    try:
        from core.cache import CacheManager  # Import inside function
        
        # Cache key unique to this user
        cache_key = f'user_context_{request.user.id}'
        
        from django.core.cache import cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Get profile with related data
        user_profile = request.user.profile
        
        # Get unread notification count efficiently
        unread_count = request.user.notifications.filter(is_read=False).count()
        
        # Build profile data dictionary
        profile_data = {
            'id': user_profile.id,
            'user_type': user_profile.user_type,
            'email_verified': user_profile.email_verified,
            'profile_picture': user_profile.profile_picture.url if user_profile.profile_picture else None,
            'phone_number': user_profile.phone_number,
            'location': user_profile.location,
            'dietary_restrictions': user_profile.dietary_restrictions,
            'average_rating': float(user_profile.average_rating),
            'total_ratings': user_profile.total_ratings,
            'bio': user_profile.bio,
        }
        
        context_data = {
            'user_profile': profile_data,
            'unread_notifications_count': unread_count,
        }
        
        # ✅ FIX: Use Django's cache.set() directly
        cache.set(cache_key, context_data, 300)  # 5 minutes
        
        return context_data
        
    except Exception as e:
        logger.error(f"Context processor error for user {request.user.id}: {e}")
        return {
            'user_profile': None,
            'unread_notifications_count': 0,
        }


def site_settings(request):
    """
    Add site-wide settings to context
    """
    return {
        'SITE_NAME': 'FoodLoop',
        'SITE_TAGLINE': 'Fight Waste, Feed Communities',
        'SUPPORT_EMAIL': 'support@foodloop.com',
        'ENABLE_ANALYTICS': False,  # Phase 1: Analytics disabled
    }


def donation_categories(request):
    """
    Add donation categories to context for filters/dropdowns
    """
    from core.models import Donation
    
    return {
        'DONATION_CATEGORIES': Donation.FOOD_CATEGORY_CHOICES,
        'DIETARY_TAGS': [
            ('vegetarian', 'Vegetarian'),
            ('vegan', 'Vegan'),
            ('halal', 'Halal'),
            ('kosher', 'Kosher'),
            ('gluten-free', 'Gluten-Free'),
            ('dairy-free', 'Dairy-Free'),
            ('nut-free', 'Nut-Free'),
        ],
    }