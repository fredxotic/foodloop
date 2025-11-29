"""
Custom decorators for FoodLoop application
Optimized with better error handling and caching
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from core.models import UserProfile


def donor_required(view_func):
    """
    Decorator that requires user to be a verified donor.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            profile = request.user.profile
            
            if profile.user_type != UserProfile.DONOR:
                messages.error(request, "This page is only accessible to donors.")
                return redirect('core:dashboard')
            
            if not profile.email_verified:
                messages.warning(request, "Please verify your email to access donor features.")
                return redirect('core:profile')
            
            return view_func(request, *args, **kwargs)
            
        except UserProfile.DoesNotExist:
            messages.error(request, "Profile not found. Please complete your profile.")
            return redirect('core:profile')
    
    return _wrapped_view


def recipient_required(view_func):
    """
    Decorator that requires user to be a verified recipient.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            profile = request.user.profile
            
            if profile.user_type != UserProfile.RECIPIENT:
                messages.error(request, "This page is only accessible to recipients.")
                return redirect('core:dashboard')
            
            if not profile.email_verified:
                messages.warning(request, "Please verify your email to access recipient features.")
                return redirect('core:profile')
            
            return view_func(request, *args, **kwargs)
            
        except UserProfile.DoesNotExist:
            messages.error(request, "Profile not found. Please complete your profile.")
            return redirect('core:profile')
    
    return _wrapped_view


def email_verified_required(view_func):
    """
    Decorator that requires user to have verified their email address.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            profile = request.user.profile
            
            if not profile.email_verified:
                messages.warning(
                    request, 
                    "Please verify your email address to access this feature. "
                    "Check your inbox for the verification link."
                )
                return redirect('core:profile')
            
            return view_func(request, *args, **kwargs)
            
        except UserProfile.DoesNotExist:
            messages.error(request, "Profile not found. Please complete your profile.")
            return redirect('core:profile')
    
    return _wrapped_view


def profile_required(view_func):
    """
    Decorator that ensures user has a complete profile.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            profile = request.user.profile
            
            # Check if profile is complete (has basic required fields)
            if not profile.user_type:
                messages.warning(request, "Please complete your profile before continuing.")
                return redirect('core:profile')
            
            return view_func(request, *args, **kwargs)
            
        except UserProfile.DoesNotExist:
            messages.error(request, "Profile not found. Please complete your profile setup.")
            return redirect('core:profile')
    
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator that requires user to be staff/admin.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def ajax_required(view_func):
    """
    Decorator that requires the request to be AJAX.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden("This endpoint only accepts AJAX requests")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def cache_page_for_user(timeout=300):
    """
    Decorator to cache page per user with specified timeout.
    Use for user-specific content that doesn't change frequently.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            from core.cache import CacheManager
            
            if not request.user.is_authenticated:
                # Don't cache for anonymous users
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            cache_key = CacheManager.make_key(
                'page',
                request.user.id,
                request.path,
                request.GET.urlencode()
            )
            
            # Try to get from cache
            from django.core.cache import cache
            cached_response = cache.get(cache_key)
            if cached_response:
                return cached_response
            
            # Generate response
            response = view_func(request, *args, **kwargs)
            
            # Cache the response
            cache.set(cache_key, response, timeout)
            
            return response
        
        return _wrapped_view
    
    return decorator