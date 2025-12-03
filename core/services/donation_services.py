"""
Optimized Donation Service - Clean, focused, and efficient
Phase 1: Complete implementation with all logic filled in
"""
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Avg, Sum, Prefetch
from datetime import timedelta
from typing import Optional, List, Dict, Any
import logging

from core.models import Donation, UserProfile, User, Rating
from core.services.notification_services import NotificationService
from core.services.email_services import EmailService
from core.services.base import BaseService, ServiceResponse

logger = logging.getLogger(__name__)


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
                # Build donation instance
                donation = cls._build_donation_instance(donor, form_data, image_file)
                
                # Calculate nutrition score
                donation.nutrition_score = cls._calculate_nutrition_score(donation)
                
                # Save donation
                donation.save()
                
                # Send notifications to nearby recipients (simplified - no GPS)
                NotificationService.notify_new_donation(donation)

                # ✅ REMOVE: EmailService.send_donation_created_email(donor, donation)
                # (This method doesn't exist - we'll add it later if needed)
            
                logger.info(f"Donation created: {donation.id} by {donor.username}")
                return cls.success(
                    data={'donation': donation},
                    message="Donation created successfully"
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
        
        if image_file:
            donation.image = image_file

        return donation

    @classmethod
    def claim_donation(cls, donation_id: int, recipient: User) -> ServiceResponse:
        """Claim a donation with comprehensive validation"""
        try:
            with transaction.atomic():
                # Lock the donation row to prevent race conditions
                donation = Donation.objects.select_for_update().get(id=donation_id)
                recipient_profile = UserProfile.objects.get(user=recipient)
                
                # Validate claim eligibility
                validation_error = cls._validate_claim_eligibility(
                    donation, recipient_profile, recipient
                )
                if validation_error:
                    return cls.error(validation_error)
                
                # Claim the donation
                donation.claim(recipient)
                
                # Send notifications
                NotificationService.notify_donation_claimed(donation, recipient)


                # ✅ REMOVE: These methods don't exist
                # EmailService.send_claim_confirmation_email(recipient, donation)
                # EmailService.send_donor_claim_notification_email(donation.donor, donation, recipient)
                
                # ✅ ADD: Use existing method
                EmailService.send_donation_claimed_email(donation, recipient)
                
                logger.info(f"Donation {donation.id} claimed by {recipient.username}")
                return cls.success(
                    data={'donation': donation},
                    message="Donation claimed successfully"
                )
            
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
            return f"This donation is {donation.get_status_display().lower()}"
        
        if donation.is_expired():
            return "This donation has expired"
        
        if donation.is_pickup_overdue():
            return "The pickup window has passed"
        
        # Check active claims limit
        active_claims = Donation.objects.filter(
            recipient=recipient,
            status=Donation.CLAIMED
        ).count()
        
        if active_claims >= cls.MAX_ACTIVE_CLAIMS:
            return f"You have reached the maximum of {cls.MAX_ACTIVE_CLAIMS} active claims"
        
        return None

    # Find complete_donation method (around line 150) and UPDATE:

    @classmethod
    def complete_donation(cls, donation_id: int, user: User) -> ServiceResponse:
        """Complete a donation transaction"""
        try:
            with transaction.atomic():
                donation = Donation.objects.select_for_update().get(id=donation_id)
                
                # Validate user is donor or recipient
                if user != donation.donor and user != donation.recipient:
                    return cls.error("You are not authorized to complete this donation")
                
                # Validate donation is claimed
                if donation.status != Donation.CLAIMED:
                    return cls.error("Only claimed donations can be completed")
                
                # Complete the donation
                donation.complete()
                
                # Send notifications
                NotificationService.notify_donation_completed(donation)
                
                # ✅ REMOVE: These methods don't exist
                # EmailService.send_completion_confirmation_email(donation.donor, donation)
                # EmailService.send_completion_confirmation_email(donation.recipient, donation)
                
                # ✅ ADD: Use existing method (sends to both parties)
                EmailService.send_donation_completed_email(donation)
                
                logger.info(f"Donation {donation.id} completed by {user.username}")
                return cls.success(
                    data={'donation': donation},
                    message="Donation completed successfully. Please rate your experience!"
                )
                
        except Donation.DoesNotExist:
            return cls.error("Donation not found")
        except Exception as e:
            return cls.handle_exception(e, "donation completion")

    @classmethod
    def search_donations(cls, query_params: Dict, user: Optional[User] = None) -> List[Donation]:
        """Optimized donation search with efficient queries"""
        try:
            # Base queryset - only available donations
            queryset = Donation.objects.filter(
                status=Donation.AVAILABLE
            ).select_related(
                'donor', 'donor__profile'
            ).prefetch_related(
                Prefetch('ratings', queryset=Rating.objects.all())
            )
            
            # Apply filters
            queryset = cls._apply_search_filters(queryset, query_params)
            
            # Order by created date (newest first)
            queryset = queryset.order_by('-created_at')
            
            # ✅ NEW: Filter out expired donations in Python (since expiry logic is in the model method)
            available_donations = [d for d in queryset if not d.is_expired()]
            
            return available_donations
        
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
                pass  # Invalid input, ignore filter
        
        if min_score := query_params.get('min_nutrition_score'):
            try:
                queryset = queryset.filter(nutrition_score__gte=int(min_score))
            except (ValueError, TypeError):
                pass  # Invalid input, ignore filter
        
        # Dietary tags filter
        dietary_tags = query_params.get('dietary_tags', [])
        
        # Handle both request.GET.getlist() and regular list
        if hasattr(query_params, 'getlist'):
            dietary_tags = query_params.getlist('dietary_tags')
        else:
            dietary_tags = query_params.get('dietary_tags', [])

        if dietary_tags:
            # Filter donations that have at least one matching tag
            for tag in dietary_tags:
                queryset = queryset.filter(dietary_tags__contains=[tag])
        
        return queryset

    @classmethod
    def get_user_donation_stats(cls, user: User) -> Dict[str, Any]:
        """Get comprehensive user statistics with single query"""
        try:
            profile = UserProfile.objects.get(user=user)
            
            if profile.user_type == UserProfile.DONOR:
                # Donor statistics
                stats = Donation.objects.filter(donor=user).aggregate(
                    total=Count('id'),
                    completed=Count('id', filter=Q(status=Donation.COMPLETED)),
                    active=Count('id', filter=Q(status__in=[Donation.AVAILABLE, Donation.CLAIMED])),
                    claimed=Count('id', filter=Q(status=Donation.CLAIMED)),
                )
                
                return {
                    'total_donations': stats['total'],
                    'completed_donations': stats['completed'],
                    'active_donations': stats['active'],
                    'claimed_donations': stats['claimed'],
                    'average_rating': float(profile.average_rating),
                    'total_ratings': profile.total_ratings,
                }
            else:
                # Recipient statistics
                stats = Donation.objects.filter(recipient=user).aggregate(
                    total=Count('id'),
                    completed=Count('id', filter=Q(status=Donation.COMPLETED)),
                    active=Count('id', filter=Q(status=Donation.CLAIMED)),
                )
                
                return {
                    'total_claims': stats['total'],
                    'completed_claims': stats['completed'],
                    'active_claims': stats['active'],
                    'average_rating': float(profile.average_rating),
                    'total_ratings': profile.total_ratings,
                }
            
        except UserProfile.DoesNotExist:
            return {
                'total_donations': 0,
                'completed_donations': 0,
                'active_donations': 0,
                'average_rating': 0.0,
                'total_ratings': 0,
            }
        except Exception as e:
            logger.error(f"Stats error for user {user.id}: {e}")
            return {}

    @classmethod
    def _calculate_nutrition_score(cls, donation: Donation) -> int:
        """Calculate nutrition score based on category and freshness"""
        score = 50  # Base score
        
        # Category bonuses
        category_bonus = {
            'fruits': 25, 
            'vegetables': 25, 
            'protein': 20,
            'grains': 15, 
            'dairy': 10, 
            'pantry': 5,
            'prepared': 10,
            'beverages': 5,
            'other': 5,
        }
        score += category_bonus.get(donation.food_category, 0)
        
        # Freshness bonus (based on time until expiry)
        if donation.expiry_datetime:
            now = timezone.now()
            hours_until_expiry = (donation.expiry_datetime - now).total_seconds() / 3600
            
            if hours_until_expiry > 48:
                score += 15  # Very fresh (>2 days)
            elif hours_until_expiry > 24:
                score += 10  # Fresh (>1 day)
            elif hours_until_expiry > 12:
                score += 5   # Moderate (>12 hours)
            # No bonus for < 12 hours
        
        # Calories penalty (if too high or unknown)
        if donation.estimated_calories:
            if donation.estimated_calories > 500:
                score -= 5  # High calorie penalty
        
        # Dietary tags bonus (more tags = more accessible)
        if donation.dietary_tags:
            score += min(len(donation.dietary_tags) * 2, 10)  # Max 10 bonus
        
        return min(100, max(0, score))  # Clamp between 0-100

    @classmethod
    def cancel_donation(cls, donation_id: int, user: User) -> ServiceResponse:
        """Cancel a donation (donor only)"""
        try:
            with transaction.atomic():
                donation = Donation.objects.select_for_update().get(id=donation_id)
                
                # Validate user is donor
                if user != donation.donor:
                    return cls.error("Only the donor can cancel this donation")
                
                # Can't cancel completed donations
                if donation.status == Donation.COMPLETED:
                    return cls.error("Cannot cancel completed donations")
                
                # If claimed, notify recipient
                if donation.status == Donation.CLAIMED and donation.recipient:
                    NotificationService.notify_donation_cancelled(donation, donation.recipient)
                    EmailService.send_cancellation_notification_email(donation.recipient, donation)
                
                # Cancel the donation
                donation.cancel()
                
                logger.info(f"Donation {donation.id} cancelled by {user.username}")
                return cls.success(
                    data={'donation': donation},
                    message="Donation cancelled successfully"
                )
                
        except Donation.DoesNotExist:
            return cls.error("Donation not found")
        except Exception as e:
            return cls.handle_exception(e, "donation cancellation")

    @classmethod
    def get_donation_detail(cls, donation_id: int, user: Optional[User] = None) -> Optional[Donation]:
        """Get detailed donation with optimized queries"""
        try:
            queryset = Donation.objects.select_related(
                'donor', 'donor__profile',
                'recipient', 'recipient__profile'
            ).prefetch_related(
                Prefetch('ratings', queryset=Rating.objects.select_related('rating_user'))
            )
            
            donation = queryset.get(id=donation_id)
            return donation
            
        except Donation.DoesNotExist:
            logger.warning(f"Donation {donation_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching donation {donation_id}: {e}")
            return None

    @classmethod
    def get_user_donations(cls, user: User, status_filter: Optional[str] = None) -> List[Donation]:
        """Get all donations for a user (as donor or recipient)"""
        try:
            profile = UserProfile.objects.get(user=user)
            
            if profile.user_type == UserProfile.DONOR:
                queryset = Donation.objects.filter(donor=user)
            else:
                queryset = Donation.objects.filter(recipient=user)
            
            # Apply status filter
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Optimize query
            queryset = queryset.select_related(
                'donor', 'donor__profile',
                'recipient', 'recipient__profile'
            ).order_by('-created_at')
            
            return list(queryset)
            
        except UserProfile.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error fetching user donations: {e}")
            return []