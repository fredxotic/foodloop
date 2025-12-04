"""
Optimized Email Service - Async-ready and efficient
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.db import transaction  # FIXED: Moved to top
from datetime import timedelta
from typing import Tuple
import logging

from core.models import EmailVerification, Donation, User
from core.services.base import BaseService, ServiceResponse
from core.utils import send_email_with_template  # FIXED: Added import

logger = logging.getLogger(__name__)


class EmailService(BaseService):
    """
    Streamlined email service using utility functions
    """
    
    VERIFICATION_EXPIRY_HOURS = 24

    @classmethod
    def send_verification_email(cls, user: User) -> ServiceResponse:
        """Send email verification link"""
        try:
            # Delete any existing unused verifications
            EmailVerification.objects.filter(
                user=user,
                is_used=False
            ).delete()
            
            # Create new verification token
            verification = EmailVerification.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=48)
            )
            
            site_url = settings.FOODLOOP_CONFIG.get('SITE_URL', 'http://127.0.0.1:8000')
            verification_url = f"{site_url}/verify-email/{verification.token}/"
            
            # Render email template
            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop'),
            }
            
            html_content = render_to_string('emails/verification.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            email = EmailMultiAlternatives(
                subject='Verify Your FoodLoop Email',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Verification email sent to {user.email}")
            return cls.success(
                data={'verification_url': verification_url},
                message="Verification email sent successfully"
            )
            
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
    def send_donation_created_email(cls, donor: User, donation: Donation) -> bool:
        """Send email to donor when donation is created"""
        try:
            return send_email_with_template(
                recipient_email=donor.email,
                subject=f"Donation Created: {donation.title}",
                template_name="donation_created",
                context={
                    'user': donor,
                    'donation': donation,
                    'site_name': settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop'),
                }
            )
        except Exception as e:
            logger.error(f"Donation created email error: {e}")
            return False

    @classmethod
    def send_donation_claimed_email(cls, donation: Donation, recipient: User) -> ServiceResponse:
        """Send email to donor when donation is claimed"""
        try:
            site_url = settings.FOODLOOP_CONFIG.get('SITE_URL', 'http://127.0.0.1:8000')
            
            context = {
                'donation': donation,
                'recipient': recipient,
                'site_url': site_url,
                'site_name': settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop'),
            }
            
            html_content = render_to_string('emails/donation_claimed.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=f'Donation Claimed: {donation.title}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[donation.donor.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Donation claimed email sent to {donation.donor.email}")
            return cls.success(message="Donation claimed email sent")
        
        except Exception as e:
            return cls.handle_exception(e, "send donation claimed email")

    @classmethod
    def send_donation_completed_email(cls, donation: Donation) -> ServiceResponse:
        """Send completion emails to both donor and recipient"""
        try:
            site_url = settings.FOODLOOP_CONFIG.get('SITE_URL', 'http://127.0.0.1:8000')
            site_name = settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop')
            
            # Email to donor
            donor_context = {
                'donation': donation,
                'site_url': site_url,
                'site_name': site_name,
            }
            donor_html = render_to_string('emails/donation_completed_donor.html', donor_context)
            donor_text = strip_tags(donor_html)
            
            donor_email = EmailMultiAlternatives(
                subject=f'Donation Completed: {donation.title}',
                body=donor_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[donation.donor.email]
            )
            donor_email.attach_alternative(donor_html, "text/html")
            donor_email.send()

            # Email to recipient
            recipient_context = {
                'donation': donation,
                'site_url': site_url,
                'site_name': site_name,
            }
            recipient_html = render_to_string('emails/donation_completed_recipient.html', recipient_context)
            recipient_text = strip_tags(recipient_html)
            
            recipient_email = EmailMultiAlternatives(
                subject=f'Pickup Completed: {donation.title}',
                body=recipient_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[donation.recipient.email]
            )
            recipient_email.attach_alternative(recipient_html, "text/html")
            recipient_email.send()
            
            logger.info(f"Completion emails sent for donation {donation.id}")
            return cls.success(message="Completion emails sent")
        
        except Exception as e:
            return cls.handle_exception(e, "Send donation completed emails")

    @classmethod
    def send_rating_notification_email(cls, rating, rating_user: User) -> ServiceResponse:
        """Send email when user receives a rating"""
        try:
            site_url = settings.FOODLOOP_CONFIG.get('SITE_URL', 'http://127.0.0.1:8000')
            
            # Get updated rating stats
            rated_profile = rating.rated_user.profile
            
            context = {
                'rating': rating,
                'rating_user': rating_user,
                'rated_user': rating.rated_user,
                'updated_rating': rated_profile.average_rating,
                'total_ratings': rated_profile.total_ratings,
                'site_url': site_url,
                'site_name': settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop'),
            }
            
            html_content = render_to_string('emails/rating_received.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject='You Received a New Rating on FoodLoop!',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[rating.rated_user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        
            logger.info(f"Rating notification sent to {rating.rated_user.email}")
            return cls.success(message="Rating notification email sent")
        
        except Exception as e:
            return cls.handle_exception(e, "send rating notification email")

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
    def send_cancellation_notification_email(cls, recipient: User, donation: Donation) -> bool:
        """Send notification when donation is cancelled"""
        try:
            return send_email_with_template(
                recipient_email=recipient.email,
                subject=f"Donation Cancelled: {donation.title}",
                template_name="donation_cancelled",
                context={
                    'user': recipient,
                    'donation': donation,
                    'site_name': settings.FOODLOOP_CONFIG.get('SITE_NAME', 'FoodLoop'),
                }
            )
        except Exception as e:
            logger.error(f"Cancellation notification email error: {e}")
            return False

    @classmethod
    def verify_email_token(cls, token: str) -> ServiceResponse:
        """Verify email verification token"""
        try:
            verification = EmailVerification.objects.select_related('user').get(
                token=token,
                is_used=False  # FIXED: Changed from is_verified to is_used
            )
            
            # Check expiry
            if verification.expires_at < timezone.now():
                return cls.error("Verification link has expired. Please request a new one.")
            
            # Mark as used and update user profile
            with transaction.atomic():
                verification.is_used = True
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