"""
Centralized choices for FoodLoop application.
This ensures consistent data across Models, Forms, and Search logic.

Phase 1: Zone-Based Location Standardization
- Single source of truth for location data
- Grouped categories for easy navigation
- Clean slug values for database storage
- Human-readable labels for display
"""

# ============================================================================
# NAIROBI LOCATIONS - Grouped by Geographic/Delivery Zones
# ============================================================================

# Central Business District & Surroundings
NAIROBI_CBD = [
    ('cbd', 'Nairobi CBD'),
    ('upperhill', 'Upper Hill'),
    ('ngara', 'Ngara'),
    ('parklands', 'Parklands'),
    ('westlands', 'Westlands'),
]

# Westlands & Upper-Class Suburbs (West Nairobi)
NAIROBI_WEST = [
    ('kileleshwa', 'Kileleshwa'),
    ('kilimani', 'Kilimani'),
    ('lavington', 'Lavington'),
    ('hurlingham', 'Hurlingham'),
    ('runda', 'Runda'),
    ('muthaiga', 'Muthaiga'),
    ('gigiri', 'Gigiri'),
    ('spring_valley', 'Spring Valley'),
]

# South Nairobi (Residential & Growing Areas)
NAIROBI_SOUTH = [
    ('southb', 'South B'),
    ('southc', 'South C'),
    ('langata', 'Langata'),
    ('karen', 'Karen'),
    ('imara', 'Imara Daima'),
    ('nyayo', 'Nyayo Estate'),
    ('madaraka', 'Madaraka'),
]

# East Nairobi (Working-Class & Middle-Income)
NAIROBI_EAST = [
    ('eastleigh', 'Eastleigh'),
    ('buruburu', 'Buruburu'),
    ('donholm', 'Donholm'),
    ('umoja', 'Umoja'),
    ('embakasi', 'Embakasi'),
    ('pipeline', 'Pipeline'),
    ('kayole', 'Kayole'),
    ('komarock', 'Komarock'),
]

# North Nairobi & Thika Road Corridor
NAIROBI_NORTH = [
    ('roysambu', 'Roysambu'),
    ('kasarani', 'Kasarani'),
    ('kahawa_west', 'Kahawa West'),
    ('kahawa_sukari', 'Kahawa Sukari'),
    ('zimmerman', 'Zimmerman'),
    ('thika_rd', 'Thika Road'),
    ('ruaraka', 'Ruaraka'),
]

# Satellite Towns & Peri-Urban Nairobi
NAIROBI_SATELLITE = [
    ('ruaka', 'Ruaka'),
    ('kitisuru', 'Kitisuru'),
    ('runda', 'Runda'),
    ('membley', 'Membley'),
    ('thindigua', 'Thindigua'),
    ('juja', 'Juja'),
]

# Southern Suburbs & Commuter Belt
NAIROBI_OUTER_SOUTH = [
    ('syokimau', 'Syokimau'),
    ('ongata_rongai', 'Ongata Rongai'),
    ('kitengela', 'Kitengela'),
    ('ngong', 'Ngong'),
    ('kiserian', 'Kiserian'),
]

# ============================================================================
# MAJOR CITIES - Outside Nairobi Metropolitan Area
# ============================================================================

MAJOR_CITIES = [
    # Coastal Region
    ('mombasa', 'Mombasa'),
    ('malindi', 'Malindi'),
    ('kilifi', 'Kilifi'),
    ('lamu', 'Lamu'),
    ('watamu', 'Watamu'),
    
    # Western Kenya
    ('kisumu', 'Kisumu'),
    ('eldoret', 'Eldoret'),
    ('kakamega', 'Kakamega'),
    ('bungoma', 'Bungoma'),
    ('kitale', 'Kitale'),
    
    # Central Kenya
    ('nakuru', 'Nakuru'),
    ('thika', 'Thika Town'),
    ('nyeri', 'Nyeri'),
    ('nanyuki', 'Nanyuki'),
    ('naivasha', 'Naivasha'),
    ('murang\'a', 'Murang\'a'),
    
    # Eastern Kenya
    ('machakos', 'Machakos'),
    ('embu', 'Embu'),
    ('meru', 'Meru'),
    ('garissa', 'Garissa'),
    
    # Rift Valley
    ('narok', 'Narok'),
    ('kericho', 'Kericho'),
    ('bomet', 'Bomet'),
    
    # Nyanza Region
    ('kisii', 'Kisii'),
    ('homa_bay', 'Homa Bay'),
    ('migori', 'Migori'),
]

# ============================================================================
# FINAL LOCATION CHOICES - Grouped for Django Forms
# ============================================================================

LOCATION_CHOICES = [
    ('', 'Select your location...'),  # Empty default for validation
    
    # Nairobi Metropolitan Area (Grouped)
    ('Nairobi - CBD & Central', NAIROBI_CBD),
    ('Nairobi - West (Westlands, Lavington, etc.)', NAIROBI_WEST),
    ('Nairobi - South (Karen, Langata, etc.)', NAIROBI_SOUTH),
    ('Nairobi - East (Eastleigh, Buruburu, etc.)', NAIROBI_EAST),
    ('Nairobi - North (Kasarani, Roysambu, etc.)', NAIROBI_NORTH),
    ('Nairobi - Satellite Towns', NAIROBI_SATELLITE),
    ('Nairobi - Outer South (Rongai, Kitengela)', NAIROBI_OUTER_SOUTH),
    
    # Major Cities
    ('Major Cities (Outside Nairobi)', MAJOR_CITIES),
    
    # Fallback
    ('other', 'Other Location (Not Listed)'),
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_flat_location_choices():
    """
    Get a flat list of all location choices (without groups).
    Useful for model field choices where groups aren't needed.
    """
    flat_choices = [('', 'Select your location...')]
    
    for item in LOCATION_CHOICES[1:]:  # Skip the empty choice
        if isinstance(item[1], list):
            # It's a group - add all items from the group
            flat_choices.extend(item[1])
        else:
            # It's a single choice
            flat_choices.append(item)
    
    return flat_choices


def get_location_display_name(slug):
    """
    Get the human-readable display name for a location slug.
    
    Args:
        slug (str): The location slug (e.g., 'westlands', 'mombasa')
    
    Returns:
        str: The display name (e.g., 'Westlands', 'Mombasa') or the slug if not found
    """
    flat_choices = get_flat_location_choices()
    location_dict = dict(flat_choices)
    return location_dict.get(slug, slug.title())


def get_all_location_slugs():
    """
    Get a set of all valid location slugs.
    Useful for validation and search logic.
    
    Returns:
        set: Set of all valid location slugs (excluding empty string)
    """
    flat_choices = get_flat_location_choices()
    return {slug for slug, label in flat_choices if slug}


# ============================================================================
# VALIDATION
# ============================================================================

def validate_location_choice(value):
    """
    Validate that a location value is in the approved choices.
    
    Args:
        value (str): The location value to validate
    
    Raises:
        ValidationError: If the location is not in the approved choices
    """
    from django.core.exceptions import ValidationError
    
    if not value:
        raise ValidationError("Please select a location.")
    
    valid_slugs = get_all_location_slugs()
    if value not in valid_slugs:
        raise ValidationError(
            f"'{value}' is not a valid location. "
            "Please select from the available options."
        )
