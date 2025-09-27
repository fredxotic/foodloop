import secrets
from django.conf import settings
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Notification


# -----------------------------
# TOKEN GENERATION
# -----------------------------
def generate_verification_token():
    """Generate secure token for email verification"""
    return secrets.token_urlsafe(32)


# -----------------------------
# GENERIC EMAIL SENDER
# -----------------------------
def send_email(subject, template_name, context, recipient_list):
    """
    Send HTML + plain text email.
    Uses template rendering and settings.DEFAULT_FROM_EMAIL.
    """
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        return True
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        return False


# -----------------------------
# EMAIL HELPERS
# -----------------------------
def send_verification_email(user, verification_url):
    """Send account verification email"""
    return send_email(
        subject="Verify Your FoodLoop Account",
        template_name="emails/verification.html",
        context={"user": user, "verification_url": verification_url},
        recipient_list=[user.email],
    )


def send_donation_claimed_email(donation, recipient):
    """Notify donor when their donation is claimed"""
    context = {"donation": donation, "recipient": recipient}
    return send_email(
        subject=f"Your {donation.food_type} donation has been claimed!",
        template_name="emails/donation_claimed.html",
        context=context,
        recipient_list=[donation.donor.email],
    )


# -----------------------------
# REAL-TIME NOTIFICATIONS
# -----------------------------
def send_real_time_notification(user, notification_type, title, message, related_url=None):
    """Send WebSocket + DB notification"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_url=related_url,
    )

    # Push via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user.id}",
        {
            "type": "notification_message",
            "message": {
                "id": notification.id,
                "type": notification_type,
                "title": title,
                "message": message,
                "related_url": related_url,
                "created_at": notification.created_at.isoformat(),
                "is_read": False,
            },
        },
    )
    return notification
