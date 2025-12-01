"""
Optimized Donation Service - Clean, focused, and efficient
"""
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Avg, Sum, Prefetch
from datetime import timedelta
from typing import Optional, List, Dict, Any

from core.models import Donation, UserProfile, NutritionImpact, User
from core.services.notification_services import NotificationService
from core.services.email_services import EmailService
from core.services.base import BaseService, ServiceResponse


class DonationService(BaseService):
    """High-performance donation management service"""
    
    MAX_ACTIVE_CLAIMS = 5
    EXPIRY_REMINDER_HOURS = [1, 6, 24]

    @classmethod
    def create_donation(cls, donor: User, form_data: Dict, image_file=None) -> ServiceResponse:
        """Create a new donation with comprehensive validation"""
        try:
            # Validate donor eligibility
            validation_error = cls._validate_donor_eligibility(donor)
            if validation_error:
                return cls.error(validation_error)

            with transaction.atomic():
                donation = cls._build_donation_instance(donor, form_data, image_file)
                donation.nutrition_score = cls._calculate_nutrition_score(donation)
                donation.save()
                
                # Async notification to avoid blocking
                NotificationService.notify_new_donation(donation)
                
                return cls.success(
                    data=donation,
                    message="Donation created successfully!"
                )
                
        except Exception as e:
            return cls.handle_exception(e, "donation creation")

    @classmethod
    def _validate_donor_eligibility(cls, donor: User) -> Optional[str]:
        """Validate if user can create donations"""
        try:
            profile = UserProfile.objects.get(user=donor)
            
            if profile.user_type != UserProfile.DONOR:
                return "Only donors can create donations"
            
            if not profile.email_verified:
                return "Please verify your email before creating donations"
            
            return None
            
        except UserProfile.DoesNotExist:
            return "Donor profile not found"

    @classmethod
    def _build_donation_instance(cls, donor: User, form_data: Dict, image_file) -> Donation:
        """Build donation instance from form data"""
        donation = Donation(
            donor=donor,
            title=form_data['title'],
            food_category=form_data['food_category'],
            description=form_data['description'],
            quantity=form_data['quantity'],
            expiry_datetime=form_data['expiry_datetime'],
            pickup_start=form_data['pickup_start'],
            pickup_end=form_data['pickup_end'],
            pickup_location=form_data['pickup_location'],
            dietary_tags=form_data.get('dietary_tags', []),
            estimated_calories=form_data.get('estimated_calories'),
            ingredients_list=form_data.get('ingredients_list', ''),
            allergen_info=form_data.get('allergen_info', ''),
        )

        # Add optional fields
        if form_data.get('latitude') and form_data.get('longitude'):
            donation.latitude = form_data['latitude']
            donation.longitude = form_data['longitude']
        
        if image_file:
            donation.image = image_file

        return donation

    @classmethod
    def claim_donation(cls, donation_id: int, recipient: User) -> ServiceResponse:
        """Claim a donation with comprehensive validation"""
        try:
            with transaction.atomic():
                # Use select_for_update to prevent race conditions
                donation = Donation.objects.select_for_update().select_related(
                    'donor', 'donor__profile'
                ).get(id=donation_id)
                
                recipient_profile = UserProfile.objects.get(user=recipient)
                
                # Comprehensive validation
                validation_error = cls._validate_claim_eligibility(
                    donation, recipient_profile, recipient
                )
                if validation_error:
                    return cls.error(validation_error)

                # Perform claim
                donation.claim(recipient)
                
                # Send notifications (async where possible)
                NotificationService.notify_donation_claimed(donation, recipient)
                EmailService.send_donation_claimed_email(donation, recipient)
                
                # Build response message
                message = f"Successfully claimed '{donation.title}'!"
                if not recipient_profile.is_dietary_compatible(donation):
                    message += " Note: This may not fully match your dietary preferences."
                
                return cls.success(data=donation, message=message)
                
        except Donation.DoesNotExist:
            return cls.error("Donation not found")
        except UserProfile.DoesNotExist:
            return cls.error("User profile not found")
        except Exception as e:
            return cls.handle_exception(e, "donation claim")

    @classmethod
    def _validate_claim_eligibility(
        cls, 
        donation: Donation, 
        recipient_profile: UserProfile, 
        recipient: User
    ) -> Optional[str]:
        """Validate all claim requirements"""
        if recipient_profile.user_type != UserProfile.RECIPIENT:
            return "Only recipients can claim donations"
        
        if not recipient_profile.email_verified:
            return "Please verify your email before claiming donations"
        
        if donation.status != Donation.AVAILABLE:
            return "This donation is no longer available"
        
        if donation.is_expired():
            donation.status = Donation.EXPIRED
            donation.save()
            return "This donation has expired"
        
        if donation.is_pickup_overdue():
            return "The pickup window has passed"
        
        # Check active claims limit
        active_claims = Donation.objects.filter(
            recipient=recipient,
            status=Donation.CLAIMED
        ).count()
        
        if active_claims >= cls.MAX_ACTIVE_CLAIMS:
            return f"You have {active_claims} active claims. Please complete some pickups first."
        
        return None

    @classmethod
    def complete_donation(cls, donation_id: int, user: User) -> ServiceResponse:
        """Complete a donation transaction"""
        try:
            with transaction.atomic():
                donation = Donation.objects.select_related(
                    'donor', 'recipient'
                ).get(id=donation_id)
                
                if donation.donor != user:
                    return cls.error("Only the donor can complete donations")
                
                if donation.status != Donation.CLAIMED:
                    return cls.error("Only claimed donations can be completed")
                
                donation.complete()
                cls._update_nutrition_impact(donation)
                
                # Notifications
                NotificationService.notify_donation_completed(donation)
                EmailService.send_donation_completed_email(donation)
                
                return cls.success(message="Donation completed successfully!")
                
        except Donation.DoesNotExist:
            return cls.error("Donation not found")
        except Exception as e:
            return cls.handle_exception(e, "donation completion")

    @classmethod
    def search_donations(cls, query_params: Dict, user: Optional[User] = None) -> List[Donation]:
        """Optimized donation search with efficient queries"""
        try:
            # FILTER AT DB LEVEL: Only fetch future expiry dates
            queryset = Donation.objects.filter(
                status=Donation.AVAILABLE,
                expiry_datetime__gt=timezone.now()
            ).select_related(
                'donor', 
                'donor__profile'
            ).prefetch_related(
                Prefetch('ratings', queryset=Rating.objects.select_related('rating_user'))
            )
            
            # Apply filters efficiently
            queryset = cls._apply_search_filters(queryset, query_params)
            
            # Now safe to limit
            return list(queryset[:50])
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    @classmethod
    def _apply_search_filters(cls, queryset, query_params: Dict):
        """Apply search filters efficiently"""
        # Text search
        if search_query := query_params.get('q'):
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(pickup_location__icontains=search_query)
            )
        
        # Category filter
        if category := query_params.get('food_category'):
            queryset = queryset.filter(food_category=category)
        
        # Nutrition filters
        if max_calories := query_params.get('max_calories'):
            try:
                queryset = queryset.filter(estimated_calories__lte=int(max_calories))
            except (ValueError, TypeError):
                pass
        
        if min_score := query_params.get('min_nutrition_score'):
            try:
                queryset = queryset.filter(nutrition_score__gte=int(min_score))
            except (ValueError, TypeError):
                pass
        
        if hasattr(query_params, 'getlist'):
            dietary_tags = query_params.getlist('dietary_tags')
        else:
            # Handle standard dict where value might be a list or single item
            tags = query_params.get('dietary_tags', [])
            dietary_tags = tags if isinstance(tags, list) else [tags] if tags else []

        if dietary_tags:
            for tag in dietary_tags:
                if tag: # Ensure empty strings don't filter
                    queryset = queryset.filter(dietary_tags__contains=[tag])
        
        return queryset

    @classmethod
    def get_user_donation_stats(cls, user: User) -> Dict[str, Any]:
        """Get comprehensive user statistics with single query"""
        try:
            user_profile = UserProfile.objects.get(user=user)
            
            # Build efficient query based on user type
            if user_profile.user_type == UserProfile.DONOR:
                donations = Donation.objects.filter(donor=user)
            else:
                donations = Donation.objects.filter(recipient=user)
            
            # Single aggregation query
            stats = donations.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status=Donation.COMPLETED)),
                active=Count('id', filter=Q(status__in=[Donation.AVAILABLE, Donation.CLAIMED])),
                total_calories=Sum('estimated_calories', filter=Q(status=Donation.COMPLETED)),
                avg_nutrition_score=Avg('nutrition_score', filter=Q(status=Donation.COMPLETED))
            )
            
            # Calculate completion rate
            completion_rate = 0
            if stats['total'] > 0:
                completion_rate = round((stats['completed'] / stats['total']) * 100, 2)
            
            return {
                'user_type': user_profile.user_type,
                'total_donations': stats['total'],
                'completed_donations': stats['completed'],
                'active_donations': stats['active'],
                'total_calories': stats['total_calories'] or 0,
                'avg_nutrition_score': round(stats['avg_nutrition_score'] or 0, 2),
                'completion_rate': completion_rate,
            }
            
        except UserProfile.DoesNotExist:
            return {'error': 'User profile not found'}
        except Exception as e:
            logger.error(f"Stats calculation error: {e}")
            return {'error': 'Failed to calculate statistics'}

    @classmethod
    def _calculate_nutrition_score(cls, donation: Donation) -> int:
        """Calculate nutrition score based on category and freshness"""
        score = 50  # Base score
        
        # Category bonuses
        category_bonus = {
            'fruits': 25, 'vegetables': 25, 'protein': 20,
            'grains': 15, 'dairy': 10, 'pantry': 5
        }
        score += category_bonus.get(donation.food_category, 0)
        
        # Freshness bonus
        if donation.expiry_datetime:
            hours_until_expiry = (
                donation.expiry_datetime - timezone.now()
            ).total_seconds() / 3600
            
            if hours_until_expiry > 48:
                score += 10
            elif hours_until_expiry > 24:
                score += 5
        
        return min(100, max(0, score))

    @classmethod
    def _update_nutrition_impact(cls, donation: Donation):
        """Update nutrition impact analytics efficiently"""
        try:
            today = timezone.now().date()
            
            # Update donor impact
            cls._update_user_impact(
                donation.donor, 
                today, 
                donations_made=1,
                calories=donation.estimated_calories
            )
            
            # Update recipient impact
            if donation.recipient:
                cls._update_user_impact(
                    donation.recipient,
                    today,
                    donations_received=1,
                    calories=donation.estimated_calories
                )
                
        except Exception as e:
            logger.error(f"Nutrition impact update error: {e}")

    @classmethod
    def _update_user_impact(cls, user: User, date, donations_made=0, donations_received=0, calories=0):
        """Update or create nutrition impact record"""
        impact, created = NutritionImpact.objects.get_or_create(
            user=user,
            date=date,
            defaults={
                'donations_made': donations_made,
                'donations_received': donations_received,
                'total_calories': calories or 0,
                'avg_nutrition_score': 0
            }
        )
        
        if not created:
            impact.donations_made += donations_made
            impact.donations_received += donations_received
            if calories:
                impact.total_calories += calories
            impact.save()


# Import at end to avoid circular dependency
from core.models import Rating
import logging
logger = logging.getLogger(__name__)