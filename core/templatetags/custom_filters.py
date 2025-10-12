from django import template
from urllib.parse import urlparse, parse_qs, urlencode

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        if float(arg) != 0:
            return float(value) / float(arg)
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def remove_param(url, param):
    """Remove a parameter from URL"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if param in query_params:
            del query_params[param]
        
        new_query = urlencode(query_params, doseq=True)
        return parsed._replace(query=new_query).geturl()
    except Exception:
        return url

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key, 0)

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if total and float(total) > 0:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter"""
    try:
        if value:
            return value.split(delimiter)
        return []
    except (AttributeError, TypeError):
        return []

@register.filter
def trim(value):
    """Trim whitespace from string"""
    try:
        return value.strip()
    except (AttributeError, TypeError):
        return value

@register.filter
def add(value, arg):
    """Add the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except TypeError:
            return value

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def default_if_none(value, default):
    """Return default value if value is None"""
    return value if value is not None else default

@register.filter
def truncate_chars(value, max_length):
    """Truncate a string after a certain number of characters"""
    try:
        if len(value) > max_length:
            return value[:max_length] + '...'
        return value
    except (TypeError, AttributeError):
        return value

@register.filter
def join_list(value, separator=', '):
    """Join a list with a separator"""
    try:
        return separator.join(str(item) for item in value)
    except (TypeError, AttributeError):
        return value

@register.filter
def range_filter(value):
    """Create a range from 0 to value-1"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return []

@register.filter
def to_int(value):
    """Convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def to_float(value):
    """Convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@register.filter
def absolute(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def floor(value):
    """Return floor value"""
    try:
        import math
        return math.floor(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def ceil(value):
    """Return ceiling value"""
    try:
        import math
        return math.ceil(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def round_value(value, decimals=0):
    """Round value to specified decimal places"""
    try:
        return round(float(value), int(decimals))
    except (ValueError, TypeError):
        return value

@register.filter
def startswith(value, arg):
    """Check if string starts with argument"""
    try:
        return value.startswith(arg)
    except (AttributeError, TypeError):
        return False

@register.filter
def endswith(value, arg):
    """Check if string ends with argument"""
    try:
        return value.endswith(arg)
    except (AttributeError, TypeError):
        return False

@register.filter
def contains(value, arg):
    """Check if value contains argument"""
    try:
        return arg in value
    except TypeError:
        return False

@register.filter
def length(value):
    """Return length of value"""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0

@register.filter
def get_range(value):
    """Get range from 0 to value-1"""
    try:
        return range(value)
    except (TypeError, ValueError):
        return []

@register.filter
def json_dumps(value):
    """Convert value to JSON string"""
    import json
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return ''

@register.filter
def json_loads(value):
    """Convert JSON string to Python object"""
    import json
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value

@register.filter
def replace(value, old, new):
    """Replace occurrences of old with new in string"""
    try:
        return value.replace(old, new)
    except (AttributeError, TypeError):
        return value

@register.filter
def upper(value):
    """Convert string to uppercase"""
    try:
        return value.upper()
    except (AttributeError, TypeError):
        return value

@register.filter
def lower(value):
    """Convert string to lowercase"""
    try:
        return value.lower()
    except (AttributeError, TypeError):
        return value

@register.filter
def title_case(value):
    """Convert string to title case"""
    try:
        return value.title()
    except (AttributeError, TypeError):
        return value

@register.filter
def capitalize(value):
    """Capitalize the first character of string"""
    try:
        return value.capitalize()
    except (AttributeError, TypeError):
        return value

@register.filter
def strip_tags(value):
    """Strip HTML tags from string"""
    try:
        from django.utils.html import strip_tags
        return strip_tags(value)
    except (ImportError, AttributeError, TypeError):
        return value

@register.filter
def safe_html(value):
    """Mark string as safe HTML"""
    try:
        from django.utils.safestring import mark_safe
        return mark_safe(value)
    except (ImportError, AttributeError, TypeError):
        return value

@register.filter
def pluralize(value, singular='', plural='s'):
    """Return singular or plural suffix based on value"""
    try:
        if int(value) == 1:
            return singular
        return plural
    except (ValueError, TypeError):
        return plural

@register.filter
def file_size(value):
    """Format file size in human readable format"""
    try:
        value = int(value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"
    except (ValueError, TypeError):
        return "0 B"

@register.filter
def timestamp_to_date(value, format_string='%Y-%m-%d %H:%M:%S'):
    """Convert timestamp to formatted date string"""
    from django.utils import timezone
    from datetime import datetime
    try:
        if value:
            if isinstance(value, (int, float)):
                # Handle Unix timestamp
                dt = datetime.fromtimestamp(value, tz=timezone.utc)
            else:
                # Assume it's already a datetime object
                dt = value
            return dt.strftime(format_string)
        return ''
    except (ValueError, TypeError, OSError):
        return value

@register.filter
def time_since(value):
    """Return human readable time since"""
    from django.utils import timezone
    from django.utils.timesince import timesince
    try:
        if value:
            return timesince(value)
        return ''
    except (ValueError, TypeError):
        return value