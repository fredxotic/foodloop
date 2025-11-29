"""
Optimized Email Service - Async-ready and efficient
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from typing import Tuple
import logging

from core.models import EmailVerification, Donation, User
from core.services.base import BaseService, ServiceResponse
from core.utils import send_email_with_template

logger = logging.getLogger(__name__)


class EmailService(BaseService):
    """
    Streamlined email service using utility functions
    """
    
    VERIFICATION_EXPIRY_HOURS = 24

    @classmethod
    def send_verification_email(cls, user: User) -> ServiceResponse:
        """
        Send email verification link
        """
        try:
            # Create or update verification token
            verification, created = EmailVerification.objects.get_or_create(
                user=user,
                defaults={'expires_at': timezone.now() + timedelta(hours=cls.VERIFICATION_EXPIRY_HOURS)}
            )
            
            if not created:
                # Update expiry if token exists
                verification.expires_at = timezone.now() + timedelta(hours=cls.VERIFICATION_EXPIRY_HOURS)
                verification.save()
            
            # Build verification URL
            verification_url = f"{settings.SITE_URL}/verify-email/{verification.token}/"
            
            # Send email using utility function
            success = send_email_with_template(
                recipient_email=user.email,
                subject="Verify Your FoodLoop Account",
                template_name="verification",
                context={
                    'user': user,
                    'verification_url': verification_url,
                    'expiry_hours': cls.VERIFICATION_EXPIRY_HOURS
                }
            )
            
            if success:
                return cls.success(
                    data={'token': str(verification.token)},
                    message="Verification email sent successfully"
                )
            else:
                return cls.error("Failed to send verification email")
                
        except Exception as e:
            return cls.handle_exception(e, "send verification email")

    @classmethod
    def send_welcome_email(cls, user: User) -> bool:
        """Send welcome email after verification"""
        try:
            return send_email_with_template(
                recipient_email=user.email,
                subject="Welcome to FoodLoop! 🎉",
                template_name="welcome",
                context={'user': user}
            )
        except Exception as e:
            logger.error(f"Welcome email error: {e}")
            return False

    @classmethod
    def send_donation_claimed_email(cls, donation: Donation, recipient: User) -> bool:
        """Notify donor when donation is claimed"""
        try:
            return send_email_with_template(
                recipient_email=donation.donor.email,
                subject=f"Your {donation.food_category} Donation Has Been Claimed!",
                template_name="donation_claimed",
                context={
                    'donor': donation.donor,
                    'recipient': recipient,
                    'donation': donation,
                    'pickup_time': donation.pickup_end.strftime('%B %d, %Y at %I:%M %p')
                }
            )
        except Exception as e:
            logger.error(f"Claimed email error: {e}")
            return False

    @classmethod
    def send_donation_completed_email(cls, donation: Donation) -> bool:
        """Notify both parties when donation is completed"""
        try:
            # Email to donor
            donor_success = send_email_with_template(
                recipient_email=donation.donor.email,
                subject="Donation Completed Successfully! ✅",
                template_name="donation_completed_donor",
                context={
                    'user': donation.donor,
                    'donation': donation,
                    'recipient': donation.recipient
                }
            )
            
            # Email to recipient
            recipient_success = send_email_with_template(
                recipient_email=donation.recipient.email,
                subject="Thank You for Picking Up Your Donation!",
                template_name="donation_completed_recipient",
                context={
                    'user': donation.recipient,
                    'donation': donation,
                    'donor': donation.donor
                }
            )
            
            return donor_success and recipient_success
            
        except Exception as e:
            logger.error(f"Completion email error: {e}")
            return False

    @classmethod
    def send_rating_notification_email(cls, rating, rater: User) -> bool:
        """Notify user when they receive a rating"""
        try:
            rated_user = rating.rated_user
            
            return send_email_with_template(
                recipient_email=rated_user.email,
                subject=f"You Received a New Rating from {rater.get_full_name()}",
                template_name="rating_received",
                context={
                    'user': rated_user,
                    'rater': rater,
                    'rating': rating
                }
            )
        except Exception as e:
            logger.error(f"Rating email error: {e}")
            return False

    @classmethod
    def send_expiry_reminder_email(cls, donation: Donation, hours_until_expiry: int) -> bool:
        """Send reminder before donation expires"""
        try:
            return send_email_with_template(
                recipient_email=donation.donor.email,
                subject=f"Reminder: Your Donation Expires in {hours_until_expiry} Hours",
                template_name="expiry_reminder",
                context={
                    'user': donation.donor,
                    'donation': donation,
                    'hours': hours_until_expiry,
                    'expiry_time': donation.expiry_datetime.strftime('%B %d, %Y at %I:%M %p')
                }
            )
        except Exception as e:
            logger.error(f"Expiry reminder error: {e}")
            return False

    @classmethod
    def verify_email_token(cls, token: str) -> ServiceResponse:
        """Verify email verification token"""
        try:
            verification = EmailVerification.objects.select_related('user').get(
                token=token,
                is_verified=False
            )
            
            # Check expiry
            if verification.expires_at < timezone.now():
                return cls.error("Verification link has expired. Please request a new one.")
            
            # Mark as verified
            with transaction.atomic():
                verification.is_verified = True
                verification.verified_at = timezone.now()
                verification.save()
                
                # Update user profile
                user_profile = verification.user.profile
                user_profile.email_verified = True
                user_profile.save()
            
            # Send welcome email
            cls.send_welcome_email(verification.user)
            
            return cls.success(
                data={'user': verification.user},
                message="Email verified successfully!"
            )
            
        except EmailVerification.DoesNotExist:
            return cls.error("Invalid or already used verification link")
        except Exception as e:
            return cls.handle_exception(e, "email verification")


# Import at end to avoid circular dependency
from django.db import transaction