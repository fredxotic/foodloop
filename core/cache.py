"""
Optimized Caching System - Simplified and efficient
Removes redundant hashing and consolidates cache patterns
"""
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from functools import wraps
from typing import Optional, Any, Dict, List, Callable
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Streamlined cache management with consistent naming patterns
    """
    
    # Simplified cache timeout settings (in seconds)
    TIMEOUTS = {
        'user_profile': 3600,          # 1 hour
        'user_donations': 1800,        # 30 minutes
        'search_results': 600,         # 10 minutes
        'recommendations': 1800,       # 30 minutes
        'nutrition_insights': 3600,    # 1 hour
        'donation_detail': 900,        # 15 minutes
        'map_data': 300,              # 5 minutes
        'analytics': 7200,            # 2 hours
        'notification_count': 60,     # 1 minute
    }
    
    @staticmethod
    def make_key(*parts) -> str:
        """
        Simple, readable cache key generation
        No unnecessary hashing - Redis/Memcached handle long keys efficiently
        """
        return f"foodloop:{':'.join(str(p) for p in parts)}"
    
    # =========================================================================
    # USER PROFILE CACHE
    # =========================================================================
    
    @classmethod
    def get_user_profile(cls, user_id: int) -> Optional[Dict]:
        """Get cached user profile data"""
        key = cls.make_key('user', user_id, 'profile')
        return cache.get(key)
    
    @classmethod
    def set_user_profile(cls, user_id: int, profile_data: Dict) -> None:
        """Cache user profile data"""
        key = cls.make_key('user', user_id, 'profile')
        cache.set(key, profile_data, cls.TIMEOUTS['user_profile'])
    
    @classmethod
    def invalidate_user_profile(cls, user_id: int) -> None:
        """Remove user profile from cache"""
        key = cls.make_key('user', user_id, 'profile')
        cache.delete(key)
    
    # =========================================================================
    # DONATION CACHE
    # =========================================================================
    
    @classmethod
    def get_user_donations(cls, user_id: int, donation_type: str = 'all') -> Optional[List]:
        """Get cached user donations"""
        key = cls.make_key('user', user_id, 'donations', donation_type)
        return cache.get(key)
    
    @classmethod
    def set_user_donations(cls, user_id: int, donations_data: List, donation_type: str = 'all') -> None:
        """Cache user donations"""
        key = cls.make_key('user', user_id, 'donations', donation_type)
        cache.set(key, donations_data, cls.TIMEOUTS['user_donations'])
    
    @classmethod
    def invalidate_user_donations(cls, user_id: int) -> None:
        """Remove all donation caches for user"""
        for dtype in ['all', 'active', 'completed', 'available']:
            key = cls.make_key('user', user_id, 'donations', dtype)
            cache.delete(key)
    
    @classmethod
    def get_donation_detail(cls, donation_id: int) -> Optional[Dict]:
        """Get cached donation details"""
        key = cls.make_key('donation', donation_id)
        return cache.get(key)
    
    @classmethod
    def set_donation_detail(cls, donation_id: int, donation_data: Dict) -> None:
        """Cache donation details"""
        key = cls.make_key('donation', donation_id)
        cache.set(key, donation_data, cls.TIMEOUTS['donation_detail'])
    
    @classmethod
    def invalidate_donation(cls, donation_id: int) -> None:
        """Remove donation from cache"""
        key = cls.make_key('donation', donation_id)
        cache.delete(key)
    
    # =========================================================================
    # SEARCH CACHE
    # =========================================================================
    
    @classmethod
    def get_search_results(cls, query_hash: str) -> Optional[List]:
        """Get cached search results"""
        key = cls.make_key('search', query_hash)
        return cache.get(key)
    
    @classmethod
    def set_search_results(cls, query_hash: str, results: List) -> None:
        """Cache search results"""
        key = cls.make_key('search', query_hash)
        cache.set(key, results, cls.TIMEOUTS['search_results'])
    
    # =========================================================================
    # RECOMMENDATIONS CACHE
    # =========================================================================
    
    @classmethod
    def get_recommendations(cls, user_id: int) -> Optional[List]:
        """Get cached recommendations"""
        key = cls.make_key('user', user_id, 'recommendations')
        return cache.get(key)
    
    @classmethod
    def set_recommendations(cls, user_id: int, recommendations: List) -> None:
        """Cache recommendations"""
        key = cls.make_key('user', user_id, 'recommendations')
        cache.set(key, recommendations, cls.TIMEOUTS['recommendations'])
    
    @classmethod
    def invalidate_recommendations(cls, user_id: int) -> None:
        """Remove recommendations from cache"""
        key = cls.make_key('user', user_id, 'recommendations')
        cache.delete(key)
    
    # =========================================================================
    # NOTIFICATION CACHE
    # =========================================================================
    
    @classmethod
    def get_notification_count(cls, user_id: int) -> Optional[int]:
        """Get cached unread notification count"""
        key = cls.make_key('user', user_id, 'notification_count')
        return cache.get(key)
    
    @classmethod
    def set_notification_count(cls, user_id: int, count: int) -> None:
        """Cache notification count"""
        key = cls.make_key('user', user_id, 'notification_count')
        cache.set(key, count, cls.TIMEOUTS['notification_count'])
    
    @classmethod
    def invalidate_notification_count(cls, user_id: int) -> None:
        """Remove notification count from cache"""
        key = cls.make_key('user', user_id, 'notification_count')
        cache.delete(key)
    
    # =========================================================================
    # ANALYTICS CACHE
    # =========================================================================
    
    @classmethod
    def get_analytics(cls, analytics_type: str, user_id: Optional[int] = None) -> Optional[Dict]:
        """Get cached analytics"""
        parts = ['analytics', analytics_type]
        if user_id:
            parts.append(str(user_id))
        key = cls.make_key(*parts)
        return cache.get(key)
    
    @classmethod
    def set_analytics(cls, analytics_type: str, data: Dict, user_id: Optional[int] = None) -> None:
        """Cache analytics data"""
        parts = ['analytics', analytics_type]
        if user_id:
            parts.append(str(user_id))
        key = cls.make_key(*parts)
        cache.set(key, data, cls.TIMEOUTS['analytics'])
    
    # =========================================================================
    # BULK INVALIDATION
    # =========================================================================
    
    @classmethod
    def invalidate_all_user_cache(cls, user_id: int) -> None:
        """Invalidate all cache entries for a user"""
        cls.invalidate_user_profile(user_id)
        cls.invalidate_user_donations(user_id)
        cls.invalidate_recommendations(user_id)
        cls.invalidate_notification_count(user_id)
    
    @classmethod
    def invalidate_donation_related(cls, donation_id: int, donor_id: int, recipient_id: Optional[int] = None) -> None:
        """Invalidate all caches related to a donation"""
        cls.invalidate_donation(donation_id)
        cls.invalidate_user_donations(donor_id)
        if recipient_id:
            cls.invalidate_user_donations(recipient_id)


class cached_result:
    """
    Simplified decorator for caching function results
    Replaces SmartCacheDecorator with cleaner interface
    """
    
    def __init__(self, cache_key_func: Callable, timeout: int = 300):
        """
        Args:
            cache_key_func: Function that takes the same args as decorated function and returns cache key
            timeout: Cache timeout in seconds
        """
        self.cache_key_func = cache_key_func
        self.timeout = timeout
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self.cache_key_func(*args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache.set(cache_key, result, self.timeout)
            return result
        
        return wrapper


class CacheWarmupManager:
    """
    Proactive cache warming for frequently accessed data
    """
    
    @staticmethod
    def warmup_user_data(user_id: int) -> bool:
        """Warmup all frequently accessed user data"""
        try:
            from django.db.models import Q
            from .models import UserProfile, Donation, Notification
            
            # Warmup profile
            try:
                profile = UserProfile.objects.select_related('user').get(user_id=user_id)
                profile_data = {
                    'user_type': profile.user_type,
                    'email_verified': profile.email_verified,
                    'has_location': profile.has_valid_coordinates,
                    'dietary_restrictions': profile.dietary_restrictions,
                }
                CacheManager.set_user_profile(user_id, profile_data)
            except UserProfile.DoesNotExist:
                pass
            
            # Warmup notification count
            count = Notification.objects.filter(user_id=user_id, is_read=False).count()
            CacheManager.set_notification_count(user_id, count)
            
            # Warmup active donations
            donations = list(
                Donation.objects.filter(
                    Q(donor_id=user_id) | Q(recipient_id=user_id),
                    status__in=[Donation.AVAILABLE, Donation.CLAIMED]
                ).values('id', 'title', 'status', 'expiry_datetime')[:10]
            )
            CacheManager.set_user_donations(user_id, donations, 'active')
            
            logger.info(f"Cache warmed up for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache warmup error for user {user_id}: {e}")
            return False
    
    @staticmethod
    def warmup_popular_donations(limit: int = 20) -> bool:
        """Warmup cache for popular/recent donations"""
        try:
            from .models import Donation
            
            donations = Donation.objects.filter(
                status=Donation.AVAILABLE
            ).select_related('donor').order_by('-created_at')[:limit]
            
            for donation in donations:
                donation_data = {
                    'id': donation.id,
                    'title': donation.title,
                    'food_category': donation.food_category,
                    'nutrition_score': donation.nutrition_score,
                    'donor_name': donation.donor.get_full_name(),
                }
                CacheManager.set_donation_detail(donation.id, donation_data)
            
            logger.info(f"Warmed up {donations.count()} popular donations")
            return True
            
        except Exception as e:
            logger.error(f"Popular donations warmup error: {e}")
            return False


# Convenience functions for common patterns
def cache_user_data(timeout: int = 1800):
    """Decorator for user-specific data caching"""
    def key_func(user, *args, **kwargs):
        func_name = args[0].__name__ if args else 'unknown'
        return CacheManager.make_key('user', user.id, func_name)
    return cached_result(key_func, timeout)


def cache_donation_data(timeout: int = 900):
    """Decorator for donation-specific data caching"""
    def key_func(donation_id, *args, **kwargs):
        func_name = args[0].__name__ if args else 'unknown'
        return CacheManager.make_key('donation', donation_id, func_name)
    return cached_result(key_func, timeout)