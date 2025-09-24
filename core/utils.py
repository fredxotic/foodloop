import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def generate_verification_token():
    return secrets.token_urlsafe(32)

def send_verification_email(user, verification_url):
    subject = 'Verify Your FoodLoop Account'
    
    # HTML content
    html_content = render_to_string('emails/verification.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    # Text content (fallback)
    text_content = strip_tags(html_content)
    
    # Create email
    email = EmailMultiAlternatives(
        subject,
        text_content,
        DEFAULT_FROM_EMAIL,
        [user.email]
    )
    email.attach_alternative(html_content, "text/html")
    
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def send_donation_claimed_email(donation, recipient):
    subject = f'Your {donation.food_type} donation has been claimed!'
    
    html_message = render_to_string('emails/donation_claimed.html', {
        'donation': donation,
        'recipient': recipient,
    })
    
    # Proper plain text version
    plain_message = f"""
Hi {donation.donor.username},

Great news! Your {donation.food_type} donation has been claimed by {recipient.username}.

Donation Details:
- Food Type: {donation.food_type}
- Quantity: {donation.quantity}
- Pickup Time: {donation.pickup_time}
- Location: {donation.location}

Recipient Contact:
- Name: {recipient.get_full_name() or recipient.username}
- Email: {recipient.email}

Please coordinate with the recipient for pickup arrangements.

Thank you for your generosity!

Best regards,
FoodLoop Team
"""

    # Send real-time notification to donor
    send_real_time_notification(
        user=donation.donor,
        notification_type='donation_claimed',
        title='Donation Claimed! 🎉',
        message=f'Your {donation.food_type} donation has been claimed by {recipient.username}.',
        related_url=f'/donation/{donation.id}/'
    )


def send_real_time_notification(user, notification_type, title, message, related_url=None):
    """Send real-time notification to user via WebSocket"""
    from .models import Notification
    
    # Create notification in database
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_url=related_url
    )
    
    # Send via WebSocket
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user.id}',
        {
            'type': 'notification_message',
            'message': {
                'id': notification.id,
                'type': notification_type,
                'title': title,
                'message': message,
                'related_url': related_url,
                'created_at': notification.created_at.isoformat(),
                'is_read': False
            }
        }
    )
    
    return notification