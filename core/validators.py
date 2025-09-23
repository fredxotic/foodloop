import re
from django.core.exceptions import ValidationError

def validate_phone_number(value):
    if not value:  # Phone number is optional
        return
    # Basic phone validation - adjust regex as needed
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid phone number (9-15 digits, optional + prefix).')