"""
Custom validators for FoodLoop application
Consolidated and comprehensive validation logic
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.images import get_image_dimensions
import logging
import re


def validate_phone_number(value):
    """
    Validate phone number format
    Accepts formats like: +254712345678, 0712345678, 712345678
    """
    if not value:
        return
    
    # Remove spaces and common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    
    # Check for valid Kenyan phone number patterns
    patterns = [
        r'^\+254[17]\d{8}$',  # +254712345678
        r'^0[17]\d{8}$',      # 0712345678
        r'^[17]\d{8}$',       # 712345678
    ]
    
    if not any(re.match(pattern, cleaned) for pattern in patterns):
        raise ValidationError(
            _('Enter a valid Kenyan phone number (e.g., +254712345678, 0712345678)')
        )


def validate_image_size(image):
    """
    Validate uploaded image size and dimensions
    Max file size: 5MB
    Max dimensions: 4000x4000
    """
    # Return early if no image or no file attribute
    if not image:
        return
    
    # Check if it's a file upload (has 'size' attribute)
    if not hasattr(image, 'size') or image.size is None:
        return
    
    # Check file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if image.size > max_size:
        raise ValidationError(
            _('Image file size must be less than 5MB. Current size: %(size).1f MB'),
            params={'size': image.size / (1024 * 1024)}
        )
    
    # Check dimensions
    try:
        # Seek to beginning of file before reading dimensions
        if hasattr(image, 'seek'):
            image.seek(0)
        
        width, height = get_image_dimensions(image)
        
        # Reset file pointer after reading
        if hasattr(image, 'seek'):
            image.seek(0)
        
        max_dimension = 4000
        
        if width and height:
            if width > max_dimension or height > max_dimension:
                raise ValidationError(
                    _('Image dimensions must be less than %(max)dx%(max)d pixels. '
                      'Current dimensions: %(width)dx%(height)d'),
                    params={
                        'max': max_dimension,
                        'width': width,
                        'height': height
                    }
                )
        else:
            # FIXED: Fail if dimensions cannot be read (corrupt file)
            raise ValidationError(_("Unable to read image dimensions. The file may be corrupted."))
            
    except Exception as e:
        # Don't fail silently. Log and raise validation error.
        logger = logging.getLogger(__name__)
        logger.warning(f"Image validation error: {e}")
        raise ValidationError(_("Invalid image file. Please upload a valid image."))


def validate_dietary_tags(tags):
    """
    Validate dietary tags list
    """
    if not tags:
        return
    
    if not isinstance(tags, list):
        raise ValidationError(_('Dietary tags must be a list'))
    
    valid_tags = [
        'vegetarian', 'vegan', 'gluten-free', 'dairy-free',
        'nut-free', 'halal', 'kosher', 'organic'
    ]
    
    invalid_tags = [tag for tag in tags if tag.lower() not in valid_tags]
    
    if invalid_tags:
        raise ValidationError(
            _('Invalid dietary tags: %(tags)s. Valid tags are: %(valid)s'),
            params={
                'tags': ', '.join(invalid_tags),
                'valid': ', '.join(valid_tags)
            }
        )


def validate_expiry_datetime(expiry_datetime):
    """
    Validate that expiry datetime is in the future
    """
    from django.utils import timezone
    
    if not expiry_datetime:
        return
    
    if expiry_datetime <= timezone.now():
        raise ValidationError(
            _('Expiry date and time must be in the future')
        )
    
    # Check it's not too far in the future (e.g., 1 year)
    max_future = timezone.now() + timezone.timedelta(days=365)
    if expiry_datetime > max_future:
        raise ValidationError(
            _('Expiry date cannot be more than 1 year in the future')
        )


def validate_pickup_times(pickup_start, pickup_end):
    """
    Validate pickup time window
    """
    from django.utils import timezone
    
    if not pickup_start or not pickup_end:
        return
    
    # Pickup start must be in the future
    if pickup_start <= timezone.now():
        raise ValidationError(
            _('Pickup start time must be in the future')
        )
    
    # Pickup end must be after pickup start
    if pickup_end <= pickup_start:
        raise ValidationError(
            _('Pickup end time must be after pickup start time')
        )
    
    # Pickup window should be reasonable (not more than 48 hours)
    max_window = timezone.timedelta(hours=48)
    if (pickup_end - pickup_start) > max_window:
        raise ValidationError(
            _('Pickup window cannot exceed 48 hours')
        )


def validate_quantity(quantity):
    """
    Validate donation quantity
    """
    if quantity is not None:
        if quantity <= 0:
            raise ValidationError(_('Quantity must be greater than 0'))
        
        if quantity > 1000:
            raise ValidationError(_('Quantity seems unreasonably high. Please contact support for bulk donations.'))


def validate_rating_value(rating):
    """
    Validate rating value
    """
    if rating is not None:
        if not (1 <= rating <= 5):
            raise ValidationError(_('Rating must be between 1 and 5'))


def validate_email_domain(email):
    """
    Validate email domain (can block disposable emails)
    """
    if not email:
        return
    
    # List of known disposable email domains to block (optional)
    disposable_domains = [
        'tempmail.com', 'guerrillamail.com', '10minutemail.com',
        'throwaway.email', 'mailinator.com'
    ]
    
    domain = email.split('@')[-1].lower()
    
    if domain in disposable_domains:
        raise ValidationError(
            _('Please use a permanent email address, not a disposable one')
        )