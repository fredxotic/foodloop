"""
Custom Template Filters for FoodLoop
Contains only formatting and utility filters.
Business logic and math operations belong in Views/Services.
"""
from django import template
from django.utils.html import strip_tags as django_strip_tags
from django.utils import timezone
from django.utils.timesince import timesince
from datetime import datetime

register = template.Library()


# ============================================================================
# DICTIONARY & LIST UTILITIES
# ============================================================================

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary - useful for dynamic key access in templates"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter"""
    try:
        if value:
            return value.split(delimiter)
        return []
    except (AttributeError, TypeError):
        return []


# ============================================================================
# STRING FORMATTING
# ============================================================================

@register.filter
def truncate_chars(value, max_length):
    """Truncate a string after a certain number of characters"""
    try:
        max_length = int(max_length)
        if len(value) > max_length:
            return value[:max_length] + '...'
        return value
    except (TypeError, AttributeError, ValueError):
        return value


@register.filter
def trim(value):
    """Trim whitespace from string"""
    try:
        return value.strip()
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


# ============================================================================
# HTML UTILITIES
# ============================================================================

@register.filter
def strip_tags(value):
    """Strip HTML tags from string"""
    try:
        return django_strip_tags(value)
    except (AttributeError, TypeError):
        return value


# ============================================================================
# PLURALIZATION
# ============================================================================

@register.filter
def pluralize(value, singular='', plural='s'):
    """Return singular or plural suffix based on value"""
    try:
        if int(value) == 1:
            return singular
        return plural
    except (ValueError, TypeError):
        return plural


# ============================================================================
# FILE & SIZE FORMATTING
# ============================================================================

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


# ============================================================================
# DATE & TIME FORMATTING
# ============================================================================

@register.filter
def timestamp_to_date(value, format_string='%Y-%m-%d %H:%M:%S'):
    """Convert timestamp to formatted date string"""
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
    try:
        if value:
            return timesince(value)
        return ''
    except (ValueError, TypeError):
        return value