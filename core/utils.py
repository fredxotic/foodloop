"""
Optimized Utility Functions - Clean & Synchronous
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import Optional, Dict, Any
import logging

from .models import Notification

logger = logging.getLogger(__name__)


def send_email_with_template(
    recipient_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    from_email: Optional[str] = None
) -> bool:
    """
    Unified email sender with template support.
    Runs synchronously.
    """
    try:
        # Add default context
        context.update({
            'site_name': getattr(settings, 'SITE_NAME', 'FoodLoop'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        # Render templates
        html_content = render_to_string(f'emails/{template_name}.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return True
        
    except Exception as e:
        logger.error(f"Email sending error to {recipient_email}: {e}")
        return False


def send_realtime_notification(
    user,
    notification_type: str,
    title: str,
    message: str,
    related_url: Optional[str] = None,
    related_donation=None
) -> Optional[Notification]:
    """
    Unified notification creator.
    Removed WebSocket logic - only creates DB record now.
    """
    try:
        # Create notification record
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_url=related_url,
            related_donation=related_donation
        )
        return notification
        
    except Exception as e:
        logger.error(f"Notification creation error: {e}")
        return None


def format_phone_number(phone: str) -> str:
    """Format phone number to standard Kenyan format"""
    import re
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    if cleaned.startswith('0'):
        return f'+254{cleaned[1:]}'
    elif not cleaned.startswith('+'):
        return f'+254{cleaned}'
    
    return cleaned