"""
Practical AI Service for FoodLoop
Simplified matching and recommendations with efficient queries
"""

from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime
from typing import List, Optional
import math
import logging

from core.models import UserProfile, Donation
from core.services.base import BaseService
from core.cache import CacheManager

logger = logging.getLogger(__name__)


class AIService(BaseService):
    """
    Simplified AI service for practical recommendations
    """
    
    MAX_DISTANCE_KM = 50  # Maximum distance for recommendations
    
    @classmethod
    def get_personalized_recommendations(cls, user, limit: int = 8) -> List[Donation]:
        """
        Get practical recommendations for recipients
        Uses caching and efficient queries
        """
        try:
            # Check cache first
            cached_recommendations = CacheManager.get_recommendations(user.id)
            if cached_recommendations:
                return cached_recommendations
            
            profile = UserProfile.objects.get(user=user)
            
            # Build efficient query with prefetch
            donations = Donation.objects.filter(
                status=Donation.AVAILABLE
            ).select_related(
                'donor',
                'donor__profile'
            ).exclude(
                donor=user
            )
            
            # Filter expired in Python after fetching reasonable amount
            donations_list = list(donations[:50])
            available_donations = [d for d in donations_list if not d.is_expired()]
            
            # Score and sort donations
            scored_donations = []
            for donation in available_donations:
                score = cls._calculate_match_score(profile, donation)
                scored_donations.append((score, donation))
            
            # Sort by score descending
            scored_donations.sort(key=lambda x: x[0], reverse=True)
            
            # Get top recommendations
            recommendations = [d for _, d in scored_donations[:limit]]
            
            # Cache results
            CacheManager.set_recommendations(user.id, recommendations)
            
            return recommendations
            
        except UserProfile.DoesNotExist:
            logger.warning(f"No profile found for user {user.id}")
            return []
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return []

    @classmethod
    def _calculate_match_score(cls, profile: UserProfile, donation: Donation) -> int:
        """
        Calculate practical match score (0-100)
        Higher score = better match
        """
        score = 50  # Base score
        
        # Dietary compatibility (up to +30 points)
        if profile.is_dietary_compatible(donation):
            score += 30
        else:
            score -= 20  # Penalty for incompatibility
        
        # Nutrition score bonus (up to +15 points)
        if donation.nutrition_score:
            score += int(donation.nutrition_score * 0.15)
        
        # Distance bonus/penalty (up to ±20 points)
        if profile.has_valid_coordinates and donation.has_valid_coordinates:
            distance = cls._calculate_distance(
                profile.latitude, profile.longitude,
                donation.latitude, donation.longitude
            )
            if distance is not None:
                if distance < 5:
                    score += 20
                elif distance < 10:
                    score += 10
                elif distance < 20:
                    score += 5
                elif distance > cls.MAX_DISTANCE_KM:
                    score -= 20
        
        # Freshness bonus (up to +10 points)
        if donation.expiry_datetime:
            hours_until_expiry = (
                donation.expiry_datetime - timezone.now()
            ).total_seconds() / 3600
            
            if hours_until_expiry > 48:
                score += 10
            elif hours_until_expiry > 24:
                score += 5
        
        # Preference for certain categories
        preferred_categories = ['fruits', 'vegetables', 'protein']
        if donation.food_category in preferred_categories:
            score += 5
        
        return max(0, min(100, score))  # Clamp between 0-100

    @classmethod
    def get_donor_recommendations(cls, user) -> List[str]:
        """
        Get recommendations for donors on what to donate
        Based on demand patterns
        """
        try:
            recommendations = []
            
            # Get high demand categories
            high_demand = cls._get_high_demand_categories()
            if high_demand:
                recommendations.append(
                    f"High demand for: {', '.join(high_demand[:3])}"
                )
            
            # Seasonal recommendation
            seasonal = cls._get_seasonal_recommendation()
            if seasonal:
                recommendations.append(seasonal)
            
            # Time-based recommendation
            current_hour = timezone.now().hour
            if 6 <= current_hour < 10:
                recommendations.append("Breakfast items are popular in the morning")
            elif 11 <= current_hour < 14:
                recommendations.append("Lunch items are in high demand now")
            elif 17 <= current_hour < 20:
                recommendations.append("Dinner items are popular in the evening")
            
            return recommendations[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Donor recommendations error: {e}")
            return ["Share fresh food to help your community!"]

    @classmethod
    def get_nutrition_insights(cls, user) -> List[str]:
        """
        Get nutrition insights based on user's history
        """
        try:
            from core.models import NutritionImpact
            
            insights = []
            
            # Get recent nutrition data
            recent_impacts = NutritionImpact.objects.filter(
                user=user,
                date__gte=timezone.now().date() - timezone.timedelta(days=30)
            ).aggregate(
                total_calories=Count('total_calories'),
                avg_score=Count('avg_nutrition_score')
            )
            
            if recent_impacts['total_calories']:
                insights.append(
                    f"You've received approximately {recent_impacts['total_calories']:,} calories this month"
                )
            
            # Get user preferences
            profile = UserProfile.objects.get(user=user)
            if profile.dietary_restrictions:
                insights.append(
                    f"Filtering for: {', '.join(profile.dietary_restrictions)}"
                )
            
            if not insights:
                insights.append("Start claiming donations to see your nutrition insights!")
            
            return insights[:3]
            
        except Exception as e:
            logger.error(f"Nutrition insights error: {e}")
            return ["Track your nutrition impact by claiming donations!"]

    @classmethod
    def _get_high_demand_categories(cls) -> List[str]:
        """Get categories with high claim rates"""
        try:
            # Get categories from recently completed donations
            seven_days_ago = timezone.now() - timezone.timedelta(days=7)
            
            categories = Donation.objects.filter(
                status=Donation.COMPLETED,
                updated_at__gte=seven_days_ago
            ).values('food_category').annotate(
                count=Count('id')
            ).order_by('-count')[:3]
            
            return [cat['food_category'] for cat in categories]
            
        except Exception as e:
            logger.error(f"High demand categories error: {e}")
            return []

    @classmethod
    def _get_seasonal_recommendation(cls) -> Optional[str]:
        """Get seasonal food recommendation"""
        try:
            month = timezone.now().month
            
            seasonal_map = {
                (12, 1, 2): "Winter: Root vegetables and hearty grains are popular",
                (3, 4, 5): "Spring: Fresh greens and light proteins are in demand",
                (6, 7, 8): "Summer: Fresh fruits and vegetables are highly sought",
                (9, 10, 11): "Fall: Squashes, apples, and warming foods are popular"
            }
            
            for months, recommendation in seasonal_map.items():
                if month in months:
                    return recommendation
            
            return None
            
        except Exception as e:
            logger.error(f"Seasonal recommendation error: {e}")
            return None

    @classmethod
    def _calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
        """
        Calculate distance between two GPS coordinates using Haversine formula
        Returns distance in kilometers
        """
        try:
            # Convert to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            
            return c * r
            
        except Exception as e:
            logger.error(f"Distance calculation error: {e}")
            return None