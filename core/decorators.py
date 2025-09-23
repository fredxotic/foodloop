from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps
from .models import UserProfile
from django.contrib import messages

def donor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.user_type == 'donor':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'This page is only available to donors.')
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Please complete your profile setup.')
            return redirect('profile')
            
    return _wrapped_view

def recipient_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.user_type == 'recipient':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'This page is only available to recipients.')
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Please complete your profile setup.')
            return redirect('profile')
            
    return _wrapped_view

def email_verified_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if not user_profile.email_verified:
                messages.warning(request, '📧 Please verify your email address to access this feature.')
                return redirect('profile')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Please complete your profile setup.')
            return redirect('profile')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view