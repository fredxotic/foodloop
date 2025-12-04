"""
Analytics Services for FoodLoop

Provides comprehensive analytics and reporting functionality.
Includes user stats, donation metrics, nutrition impact, and system health.
"""

from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F
from django.contrib.auth.models import User
from datetime import timedelta, datetime
from typing import Dict, List, Any, Optional
import logging

from core.models import Donation, UserProfile, Rating, Notification
from core.cache import CacheManager

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for generating analytics and reports across the FoodLoop platform.
    All methods use caching for performance.
    """
    
    @staticmethod
    def get_platform_overview() -> Dict[str, Any]:
        """
        Get high-level platform statistics with caching
        
        Returns:
            Dictionary containing platform metrics
        """
        try:
            # Check cache first
            cached_overview = CacheManager.get_analytics('platform_overview')
            if cached_overview:
                return cached_overview
            
            now = timezone.now()
            thirty_days_ago = now - timedelta(days=30)
            
            # Single efficient query for all metrics
            overview = {
                'total_users': User.objects.filter(is_active=True).count(),
                'total_donors': UserProfile.objects.filter(
                    user_type=UserProfile.DONOR,
                    email_verified=True
                ).count(),
                'total_recipients': UserProfile.objects.filter(
                    user_type=UserProfile.RECIPIENT,
                    email_verified=True
                ).count(),
            }
            
            # Donation metrics in one query
            donation_stats = Donation.objects.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status=Donation.COMPLETED)),
                active=Count('id', filter=Q(status__in=[Donation.AVAILABLE, Donation.CLAIMED])),
                recent=Count('id', filter=Q(created_at__gte=thirty_days_ago)),
                total_calories=Sum('estimated_calories', filter=Q(status=Donation.COMPLETED)),
                avg_nutrition_score=Avg('nutrition_score', filter=Q(status=Donation.COMPLETED))
            )
            
            overview.update({
                'total_donations': donation_stats['total'],
                'completed_donations': donation_stats['completed'],
                'active_donations': donation_stats['active'],
                'donations_last_30_days': donation_stats['recent'],
                'total_calories_saved': donation_stats['total_calories'] or 0,
                'avg_nutrition_score': round(donation_stats['avg_nutrition_score'] or 0, 2),
                'completion_rate': round(
                    (donation_stats['completed'] / donation_stats['total'] * 100) 
                    if donation_stats['total'] > 0 else 0,
                    2
                )
            })
            
            # Cache for 2 hours
            CacheManager.set_analytics('platform_overview', overview)
            
            return overview
            
        except Exception as e:
            logger.error(f"Platform overview error: {e}")
            return {'error': 'Failed to generate platform overview'}
    
    @staticmethod
    def get_user_analytics(user: User, date_range: str = '30d') -> Dict[str, Any]:
        """
        Get detailed analytics for a specific user with caching
        
        Args:
            user: User object
            date_range: '7d', '30d', '90d', or 'all'
        
        Returns:
            Dictionary containing user metrics
        """
        try:
            # Check cache first
            cache_key = f"user_analytics_{date_range}"
            cached_analytics = CacheManager.get_analytics(cache_key, user.id)
            if cached_analytics:
                return cached_analytics
            
            profile = UserProfile.objects.get(user=user)
            
            # Calculate date range
            now = timezone.now()
            date_filters = {
                '7d': now - timedelta(days=7),
                '30d': now - timedelta(days=30),
                '90d': now - timedelta(days=90),
                'all': None
            }
            start_date = date_filters.get(date_range, date_filters['30d'])
            
            # Build base queryset
            if profile.user_type == UserProfile.DONOR:
                base_query = Q(donor=user)
            else:
                base_query = Q(recipient=user)
            
            if start_date:
                base_query &= Q(created_at__gte=start_date)
            
            # Get donation statistics
            donation_stats = Donation.objects.filter(base_query).aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status=Donation.COMPLETED)),
                claimed=Count('id', filter=Q(status=Donation.CLAIMED)),
                available=Count('id', filter=Q(status=Donation.AVAILABLE)),
                total_calories=Sum('estimated_calories', filter=Q(status=Donation.COMPLETED)),
                avg_nutrition=Avg('nutrition_score', filter=Q(status=Donation.COMPLETED))
            )
            
            # Get rating information
            rating_stats = Rating.objects.filter(rated_user=user).aggregate(
                avg_rating=Avg('rating'),
                total_ratings=Count('id')
            )
            
            # Compile analytics
            analytics = {
                'user_type': profile.user_type,
                'date_range': date_range,
                'donation_stats': {
                    'total': donation_stats['total'],
                    'completed': donation_stats['completed'],
                    'claimed': donation_stats['claimed'],
                    'available': donation_stats['available'],
                    'completion_rate': round(
                        (donation_stats['completed'] / donation_stats['total'] * 100)
                        if donation_stats['total'] > 0 else 0,
                        2
                    )
                },
                'nutrition_impact': {
                    'total_calories': donation_stats['total_calories'] or 0,
                    'avg_nutrition_score': round(donation_stats['avg_nutrition'] or 0, 2),
                },
                'reputation': {
                    'avg_rating': round(rating_stats['avg_rating'] or 0, 2),
                    'total_ratings': rating_stats['total_ratings'],
                },
                'account_age_days': (now - user.date_joined).days
            }
            
            # Cache for 30 minutes
            CacheManager.set_analytics(cache_key, analytics, user.id)
            
            return analytics
            
        except UserProfile.DoesNotExist:
            return {'error': 'User profile not found'}
        except Exception as e:
            logger.error(f"User analytics error: {e}")
            return {'error': 'Failed to generate user analytics'}
    
    @staticmethod
    def get_donation_trends(days: int = 30, user=None) -> Dict[str, Any]:
        """
        Get donation trends over time period with caching
        
        Args:
            days: Number of days to analyze
            user: Optional user to filter by (for personal analytics)
        """
        try:
            # Generate a specific cache key if a user is provided
            cache_key = f'donation_trends_{days}'
            if user:
                cache_key += f'_user_{user.id}'
                
            # Check cache
            cached_trends = CacheManager.get_analytics(cache_key)
            if cached_trends:
                return cached_trends
            
            start_date = timezone.now() - timedelta(days=days)
            
            # Base query
            base_query = Q(created_at__gte=start_date)
            
            # Filter by user role if provided
            if user:
                from core.models import UserProfile
                try:
                    if user.profile.user_type == UserProfile.DONOR:
                        base_query &= Q(donor=user)
                    else:
                        base_query &= Q(recipient=user, status__in=['claimed', 'completed'])
                except Exception:
                    pass

            # Get donations by day
            donations = Donation.objects.filter(base_query).extra(
                select={'day': 'DATE(created_at)'}
            ).values('day').annotate(
                count=Count('id'),
                completed=Count('id', filter=Q(status=Donation.COMPLETED))
            ).order_by('day')
            
            # Get category breakdown
            categories = Donation.objects.filter(base_query).values('food_category').annotate(
                count=Count('id')
            ).order_by('-count')
            
            trends = {
                'period_days': days,
                'daily_trends': list(donations),
                'category_breakdown': list(categories),
                'peak_donation_day': max(donations, key=lambda x: x['count'])['day'] if donations else None,
                'total_period': sum(d['count'] for d in donations)
            }
            
            # Cache for 1 hour
            CacheManager.set_analytics(cache_key, trends)
            
            return trends
            
        except Exception as e:
            logger.error(f"Donation trends error: {e}")
            return {'error': 'Failed to generate donation trends'}
    
    @staticmethod
    def get_geographic_distribution() -> Dict[str, Any]:
        """
        Get geographic distribution of donations and users
        
        Returns:
            Dictionary containing geographic data (SIMPLIFIED - No GPS)
        """
        try:
            # Check cache
            cached_geo = CacheManager.get_analytics('geographic_distribution')
            if cached_geo:
                return cached_geo
            
            # SIMPLIFIED: Get location counts by city/neighborhood text
            location_counts = Donation.objects.filter(
                pickup_location__isnull=False,
                status=Donation.AVAILABLE
            ).exclude(
                pickup_location=''
            ).values('pickup_location').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Get users with location text
            users_with_location = UserProfile.objects.filter(
                location__isnull=False
            ).exclude(
                location=''
            ).count()
            
            distribution = {
                'total_locations': users_with_location,
                'top_locations': list(location_counts),
                'coverage_percentage': round(
                    (users_with_location / UserProfile.objects.count() * 100)
                    if UserProfile.objects.count() > 0 else 0,
                    2
                )
            }
            
            # Cache for 15 minutes
            CacheManager.set_analytics('geographic_distribution', distribution)
            
            return distribution
            
        except Exception as e:
            logger.error(f"Geographic distribution error: {e}")
            return {'error': 'Failed to generate geographic distribution'}
    
    @staticmethod
    def get_nutrition_insights_summary() -> Dict[str, Any]:
        """
        Get aggregated nutrition insights across platform
        
        Returns:
            Dictionary containing nutrition metrics (SIMPLIFIED - No NutritionImpact model)
        """
        try:
            # Check cache
            cached_insights = CacheManager.get_analytics('nutrition_insights')
            if cached_insights:
                return cached_insights
            
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            
            # SIMPLIFIED: Get nutrition data from Donation model directly
            nutrition_data = Donation.objects.filter(
                status=Donation.COMPLETED,
                created_at__gte=thirty_days_ago
            ).aggregate(
                total_donations=Count('id'),
                total_calories=Sum('estimated_calories'),
                avg_nutrition_score=Avg('nutrition_score')
            )
            
            # Get top categories by nutrition score
            top_categories = Donation.objects.filter(
                status=Donation.COMPLETED,
                nutrition_score__isnull=False,
                created_at__gte=thirty_days_ago
            ).values('food_category').annotate(
                avg_score=Avg('nutrition_score'),
                count=Count('id')
            ).order_by('-avg_score')[:5]
            
            insights = {
                'period': '30 days',
                'total_donations_made': nutrition_data['total_donations'] or 0,
                'total_calories_distributed': nutrition_data['total_calories'] or 0,
                'platform_avg_nutrition_score': round(nutrition_data['avg_nutrition_score'] or 0, 2),
                'top_nutrition_categories': list(top_categories),
                'estimated_meals_provided': round(
                    (nutrition_data['total_calories'] or 0) / 600,  # Assuming 600 cal per meal
                    0
                )
            }
            
            # Cache for 2 hours
            CacheManager.set_analytics('nutrition_insights', insights)
            
            return insights
            
        except Exception as e:
            logger.error(f"Nutrition insights error: {e}")
            return {'error': 'Failed to generate nutrition insights'}
    
    @staticmethod
    def generate_system_health_report() -> Dict[str, Any]:
        """
        Generate system health metrics for monitoring
        
        Returns:
            Dictionary containing system health indicators
        """
        try:
            now = timezone.now()
            one_hour_ago = now - timedelta(hours=1)
            
            health = {
                'timestamp': now.isoformat(),
                'database_connectivity': True,  # If we got here, DB is working
                'active_users_last_hour': User.objects.filter(
                    last_login__gte=one_hour_ago
                ).count(),
                'donations_last_hour': Donation.objects.filter(
                    created_at__gte=one_hour_ago
                ).count(),
                'notifications_pending': Notification.objects.filter(
                    is_read=False
                ).count(),
                'expired_donations_needing_cleanup': Donation.objects.filter(
                    status=Donation.AVAILABLE,
                    expiry_datetime__lt=now
                ).count(),
                'cache_status': 'operational',  # Could add actual cache ping
            }
            
            # Calculate health score
            health_score = 100
            if health['expired_donations_needing_cleanup'] > 10:
                health_score -= 10
            if health['notifications_pending'] > 1000:
                health_score -= 10
            
            health['overall_health_score'] = health_score
            health['status'] = 'healthy' if health_score >= 80 else 'degraded' if health_score >= 60 else 'unhealthy'
            
            return health
            
        except Exception as e:
            logger.error(f"System health report error: {e}")
            return {
                'status': 'error',
                'database_connectivity': False,
                'error': str(e)
            }