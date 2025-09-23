import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def generate_verification_token():
    return secrets.token_urlsafe(32)

def send_verification_email(user, verification_url):
    subject = 'Verify Your FoodLoop Account'
    
    # Render HTML template
    html_message = render_to_string('emails/verification_email.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    # Create proper plain text version (without HTML/CSS)
    plain_message = f"""
Hi {user.username},

Welcome to FoodLoop! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

Once verified, you'll be able to:
- {user.userprofile.get_user_type_display()} food items
- Connect with other community members  
- Receive notifications about new opportunities
- Find donations near your location

Thank you for joining our community fighting food waste!

Best regards,
The FoodLoop Team
"""
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

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
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [donation.donor.email],
        html_message=html_message,
        fail_silently=False,
    )