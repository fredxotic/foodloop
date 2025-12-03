"""
Optimized Views for FoodLoop - Simplified & Synchronous
Phase 1: Complete implementation with all logic filled in
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from functools import wraps
import logging

from .models import (
    User, UserProfile, Donation, Rating, 
    Notification, EmailVerification
)
from .forms import (
    SignUpForm, ProfileUpdateForm, DonationForm, 
    RatingForm, NutritionSearchForm, DietaryPreferencesForm
)
from .services.donation_services import DonationService
from .services.notification_services import NotificationService
from .services.email_services import EmailService

logger = logging.getLogger(__name__)


# ============================================================================
# DECORATORS
# ============================================================================

def profile_required(view_func):
    """Ensure user has a profile before accessing view"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        
        try:
            request.user.profile
        except UserProfile.DoesNotExist:
            messages.error(request, "Please complete your profile setup.")
            return redirect('core:profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def donor_required(view_func):
    """Restrict access to donors only"""
    @wraps(view_func)
    @login_required
    @profile_required
    def wrapper(request, *args, **kwargs):
        if request.user.profile.user_type != UserProfile.DONOR:
            messages.error(request, "This page is only accessible to donors.")
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def recipient_required(view_func):
    """Restrict access to recipients only"""
    @wraps(view_func)
    @login_required
    @profile_required
    def wrapper(request, *args, **kwargs):
        if request.user.profile.user_type != UserProfile.RECIPIENT:
            messages.error(request, "This page is only accessible to recipients.")
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """User registration with profile creation"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        
        if form.is_valid():
            try:
                from django.db import transaction
                
                with transaction.atomic():
                    # ✅ FIX: Check if user already exists (case-insensitive)
                    username = form.cleaned_data['username'].lower()
                    email = form.cleaned_data['email'].lower()
                    
                    if User.objects.filter(username__iexact=username).exists():
                        messages.error(request, f"Username '{username}' is already taken.")
                        return render(request, 'auth/signup.html', {'form': form})
                    
                    if User.objects.filter(email__iexact=email).exists():
                        messages.error(request, f"Email '{email}' is already registered.")
                        return render(request, 'auth/signup.html', {'form': form})
                    
                    # Create user
                    user = form.save(commit=False)
                    user.email = email
                    user.username = username
                    user.save()
                    
                    # ✅ FIX: Use get_or_create to prevent duplicates
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'user_type': form.cleaned_data['user_type'],
                            'phone_number': form.cleaned_data['phone_number'],
                            'location': form.cleaned_data['location'],
                        }
                    )
                    
                    if not created:
                        logger.warning(f"Profile already exists for user: {user.username}")
                    
                    logger.info(f"New user registered: {user.username} ({profile.get_user_type_display()})")
                    
                    # Send verification email
                    try:
                        EmailService.send_verification_email(user)
                    except Exception as email_error:
                        logger.error(f"Failed to send verification email: {email_error}")
                    
                    # Log user in
                    login(request, user)
                    
                    messages.success(
                        request, 
                        f"Welcome to FoodLoop, {user.first_name}! Please check your email to verify your account."
                    )
                    return redirect('core:dashboard')
                    
            except Exception as e:
                logger.error(f"Signup error for {form.cleaned_data.get('username', 'unknown')}: {e}", exc_info=True)
                messages.error(request, "An error occurred during registration. Please try again.")
        else:
            # Show validation errors
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            messages.error(request, f"{error}")
                        else:
                            field_label = form.fields.get(field, {}).label or field.replace('_', ' ').title()
                            messages.error(request, f"{field_label}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """User authentication"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Redirect to next parameter or dashboard
            next_url = request.GET.get('next', 'core:dashboard')
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """User logout"""
    username = request.user.username
    logout(request)
    messages.success(request, f"Goodbye, {username}! You've been logged out.")
    return redirect('core:home')


def verify_email_view(request, token):
    """Handle email verification"""
    try:
        if isinstance(token, str) and '-' in token:
            import uuid
            try:
                token_uuid = uuid.UUID(token)
            except ValueError:
                messages.error(request, "Invalid verification link format.")
                return redirect('core:home')
        else:
            token_uuid = token
        
        # Query using UUID
        verification = EmailVerification.objects.get(token=token_uuid)
        
        if verification.is_valid():
            # Mark email as verified
            profile = verification.user.profile
            profile.email_verified = True
            profile.save()
            
            # Mark token as used
            verification.is_used = True
            verification.save()
            
            messages.success(request, "Email verified successfully! You can now access all features.")
            return redirect('core:dashboard')
        else:
            messages.error(request, "This verification link has expired or been used.")
            return redirect('core:profile')
            
    except EmailVerification.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect('core:home')
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        messages.error(request, "An error occurred during verification.")
        return redirect('core:home')


@login_required
def resend_verification_view(request):
    """Resend email verification link"""
    try:
        profile = request.user.profile
        
        if profile.email_verified:
            messages.info(request, "Your email is already verified.")
            return redirect('core:dashboard')
        
        # Check if there's a recent verification email (prevent spam)
        recent_verification = EmailVerification.objects.filter(
            user=request.user,
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).first()
        
        if recent_verification:
            messages.warning(
                request,
                "A verification email was recently sent. Please check your inbox or wait a few minutes before requesting another."
            )
            return redirect('core:profile')
        
        # Send new verification email
        EmailService.send_verification_email(request.user)
        
        messages.success(
            request,
            "Verification email sent! Please check your inbox and spam folder."
        )
        return redirect('core:profile')
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('core:home')
    except Exception as e:
        logger.error(f"Error resending verification for {request.user.username}: {e}")
        messages.error(request, "Error sending verification email. Please try again later.")
        return redirect('core:profile')


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
@profile_required
def dashboard_view(request):
    """Unified dashboard for donors and recipients"""
    try:
        profile = request.user.profile
        
        if profile.user_type == UserProfile.DONOR:
            # Donor dashboard
            recent_donations = Donation.objects.filter(
                donor=request.user
            ).select_related(
                'recipient', 'recipient__profile'
            ).order_by('-created_at')[:5]
            
            stats = DonationService.get_user_donation_stats(request.user)
            
            # Get pending ratings (completed donations not yet rated)
            pending_ratings = Donation.objects.filter(
                donor=request.user,
                status=Donation.COMPLETED
            ).exclude(
                ratings__rating_user=request.user
            ).select_related('recipient')[:3]
            
            context = {
                'recent_donations': recent_donations,
                'stats': stats,
                'pending_ratings': pending_ratings,
            }
            
            return render(request, 'dashboard/donor.html', context)
        
        else:
            # Recipient dashboard
            claimed_donations = Donation.objects.filter(
                recipient=request.user,
                status__in=[Donation.CLAIMED, Donation.COMPLETED]
            ).select_related('donor', 'donor__profile').order_by('-claimed_at')[:5]
            
            # Available donations (simple query, no GPS)
            available_donations = Donation.objects.filter(
                status=Donation.AVAILABLE
            ).select_related('donor', 'donor__profile').order_by('-created_at')[:6]
            
            stats = DonationService.get_user_donation_stats(request.user)
            
            # Pending ratings
            pending_ratings = Donation.objects.filter(
                recipient=request.user,
                status=Donation.COMPLETED
            ).exclude(
                ratings__rating_user=request.user
            ).select_related('donor')[:3]
            
            context = {
                'claimed_donations': claimed_donations,
                'available_donations': available_donations,
                'stats': stats,
                'pending_ratings': pending_ratings,
            }
            
            return render(request, 'dashboard/recipient.html', context)
        
    except Exception as e:
        logger.error(f"Dashboard error for {request.user.username}: {e}")
        messages.error(request, "Error loading dashboard. Please try again.")
        return redirect('core:home')


# ============================================================================
# DONATION VIEWS
# ============================================================================

@donor_required
def create_donation_view(request):
    """Create a new donation"""
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Prepare form data
                form_data = form.cleaned_data
                image_file = request.FILES.get('image')
                
                # Create donation via service
                result = DonationService.create_donation(
                    donor=request.user,
                    form_data=form_data,
                    image_file=image_file
                )
                
                if result.success:
                    messages.success(request, "Donation created successfully!")
                    return redirect('core:donation_detail', donation_id=result.data['donation'].id)
                else:
                    messages.error(request, result.message)
                    
            except Exception as e:
                logger.error(f"Donation creation error: {e}")
                messages.error(request, "An error occurred. Please try again.")
        else:
            # Show form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = DonationForm()
    
    return render(request, 'donor/create_donation.html', {'form': form})


def donation_detail_view(request, donation_id):
    """View donation details"""
    donation = DonationService.get_donation_detail(donation_id, request.user)
    
    if not donation:
        messages.error(request, "Donation not found.")
        return redirect('core:dashboard')
    
    # Check if user can claim (for recipients)
    can_claim = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            can_claim = (
                profile.user_type == UserProfile.RECIPIENT and
                donation.status == Donation.AVAILABLE and
                not donation.is_expired() and
                profile.email_verified
            )
        except UserProfile.DoesNotExist:
            pass
    
    # Check if user can complete (for donor or recipient)
    can_complete = (
        request.user.is_authenticated and
        donation.status == Donation.CLAIMED and
        (request.user == donation.donor or request.user == donation.recipient)
    )
    
    # Check if user needs to rate
    needs_rating = False
    if request.user.is_authenticated and donation.status == Donation.COMPLETED:
        needs_rating = not Rating.objects.filter(
            donation=donation,
            rating_user=request.user
        ).exists()
    
    context = {
        'donation': donation,
        'can_claim': can_claim,
        'can_complete': can_complete,
        'needs_rating': needs_rating,
    }
    
    return render(request, 'donation/detail.html', context)


@login_required
@recipient_required
def claim_donation_view(request, donation_id):
    """Claim a donation (recipients only)"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:donation_detail', donation_id=donation_id)
    
    # Get donation object first
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Pass donation.id (not donation object) to service
    result = DonationService.claim_donation(donation.id, request.user)
    
    if result.success:
        # Refresh donation to get updated data
        donation.refresh_from_db()
        
        # Send notification to donor
        NotificationService.notify_donation_claimed(donation, request.user)
        
        # Send email to donor
        EmailService.send_donation_claimed_email(donation, request.user)
        
        messages.success(request, result.message)

        # Send email to donor
        EmailService.send_donation_claimed_email(donation, request.user)
        
        messages.success(request, result.message)
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('core:donation_detail', args=[donation.id])
            })
        else:
            # Regular form submission - direct redirect
            return redirect('core:donation_detail', donation_id=donation.id)
    
    messages.error(request, result.message)
    
    # Handle error response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': result.message}, status=400)
    else:
        return redirect('core:donation_detail', donation_id=donation.id)


@login_required
def complete_donation_view(request, donation_id):
    """Mark donation as completed"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:donation_detail', donation_id=donation_id)
    
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Verify user authorization
    if donation.donor != request.user and donation.recipient != request.user:
        messages.error(request, "You are not authorized to complete this donation.")
        return redirect('core:donation_detail', donation_id=donation.id)
    
    # Pass donation.id instead of donation object
    result = DonationService.complete_donation(donation.id, request.user)
    
    if result.success:
        messages.success(request, result.message)

        #  Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('core:donation_detail', args=[donation.id])
            })
        else:
            # Regular form submission - direct redirect
            return redirect('core:donation_detail', donation_id=donation.id)

    messages.error(request, result.message)
    
    # Handle error response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': result.message}, status=400)
    else:
        return redirect('core:donation_detail', donation_id=donation.id)


@donor_required
@require_POST
def cancel_donation_view(request, donation_id):
    """Cancel a donation (donor only)"""
    result = DonationService.cancel_donation(donation_id, request.user)
    
    if result.success:
        messages.success(request, result.message)
    else:
        messages.error(request, result.message)
    
    return redirect('core:my_donations')


@donor_required
def my_donations_view(request):
    """View all donations by the logged-in donor"""
    status_filter = request.GET.get('status')
    
    donations = Donation.objects.filter(
        donor=request.user
    ).select_related('recipient', 'recipient__profile').order_by('-created_at')
    
    if status_filter:
        donations = donations.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(donations, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'donations': page_obj,
        'status_filter': status_filter,
        'total_count': donations.count(),
    }

    return render(request, 'donor/my_donations.html', context)


@recipient_required
def my_claims_view(request):
    """View all claimed donations by the logged-in recipient"""
    status_filter = request.GET.get('status')
    
    # Get donations where user is the RECIPIENT
    donations = Donation.objects.filter(
        recipient=request.user
    ).select_related('donor', 'donor__profile').order_by('-claimed_at')
    
    if status_filter:
        donations = donations.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(donations, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'donations': page_obj,
        'status_filter': status_filter,
        'total_count': donations.count(),
    }
    
    return render(request, 'recipient/my_claims.html', context)

# ============================================================================
# SEARCH VIEWS
# ============================================================================

def nutrition_search_view(request):
    """Search donations with nutrition filters"""
    form = NutritionSearchForm(request.GET or None)
    donations = []
    
    if form.is_valid():
        query_params = form.cleaned_data
        donations = DonationService.search_donations(query_params, request.user)
    else:
        # Show all available donations if no search
        donations = DonationService.search_donations({}, request.user)
    
    # Pagination
    paginator = Paginator(donations, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'donations': page_obj,
        'total_results': len(donations),
    }
    
    return render(request, 'search/nutrition_search.html', context)

def search_donations_view(request):
    """Search donations - redirect to nutrition search"""
    return nutrition_search_view(request)


# ============================================================================
# RATING VIEWS
# ============================================================================

@login_required
def rate_user_view(request, donation_id):
    """Rate user after donation completion"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Verify authorization
    if donation.donor != request.user and donation.recipient != request.user:
        messages.error(request, "You are not authorized to rate this donation.")
        return redirect('core:donation_detail', donation_id=donation.id)
    
    # Verify donation is completed
    if donation.status != Donation.COMPLETED:
        messages.error(request, "You can only rate completed donations.")
        return redirect('core:donation_detail', donation_id=donation.id)
    
    # Check if already rated
    rated_user = donation.recipient if request.user == donation.donor else donation.donor
    existing_rating = Rating.objects.filter(
        donation=donation,
        rating_user=request.user,
        rated_user=rated_user
    ).first()
    
    if existing_rating:
        messages.info(request, "You have already rated this exchange.")
        return redirect('core:donation_detail', donation_id=donation.id)
    
    if request.method == 'POST':
        form = RatingForm(
            request.POST,
            donation=donation,
            rating_user=request.user
        )
        
        if form.is_valid():
            try:
                # Save rating
                rating = form.save()
                
                # Send notification to rated user
                NotificationService.notify_rating_received(rating, request.user)
                
                # Send email notification
                EmailService.send_rating_notification_email(rating, request.user)
                
                messages.success(
                    request,
                    f"Thank you for rating {rated_user.get_full_name() or rated_user.username}!"
                )
                return redirect('core:donation_detail', donation_id=donation.id)
            
            except Exception as e:
                logger.error(f"Rating submission error: {e}")
                messages.error(request, "An error occurred while submitting your rating. Please try again.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RatingForm(
            donation=donation,
            rating_user=request.user
        )
    
    context = {
        'form': form,
        'donation': donation,
        'rated_user': rated_user,
        'existing_rating': existing_rating,
    }
    
    return render(request, 'ratings/rating_form.html', context)

# ============================================================================
# PROFILE VIEWS
# ============================================================================

# Find profile_view (around line 580) and UPDATE:

@login_required
@profile_required
def profile_view(request):
    """View and edit user profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST, 
            request.FILES,  # ✅ CRITICAL: Pass FILES for image upload
            instance=profile,
            user=request.user
        )
        
        if form.is_valid():
            try:
                # Save profile first (this handles the image)
                profile = form.save(commit=False)
                
                # Update user fields manually
                request.user.first_name = form.cleaned_data['first_name']
                request.user.last_name = form.cleaned_data['last_name']
                
                # Only update email if it changed
                new_email = form.cleaned_data['email']
                if new_email != request.user.email:
                    # Check if email is already taken by another user
                    if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                        messages.error(request, "This email is already in use by another account.")
                        return render(request, 'profile/profile.html', {'form': form, 'profile': profile})
                    
                    request.user.email = new_email
                    # Mark as unverified if email changed
                    profile.email_verified = False
                
                request.user.save()
                profile.save()
                
                messages.success(request, "Profile updated successfully!")
                return redirect('core:profile')
                
            except Exception as e:
                logger.error(f"Profile update error: {e}")
                messages.error(request, "An error occurred while updating your profile.")
        else:
            # Show specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'profile/profile.html', context)



def public_profile_view(request, username):
    """View public profile of another user"""
    profile_user = get_object_or_404(User, username=username)  
    
    try:
        profile = profile_user.profile 
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('core:home')
    
    # Get user's donations or claims based on their type
    if profile.user_type == UserProfile.DONOR:
        recent_donations = Donation.objects.filter(
            donor=profile_user,
            status__in=[Donation.AVAILABLE, Donation.COMPLETED]
        ).select_related('recipient', 'recipient__profile').order_by('-created_at')[:6]
        
        active_donations_count = Donation.objects.filter(
            donor=profile_user,
            status=Donation.AVAILABLE
        ).count()
    else:
        recent_donations = Donation.objects.filter(
            recipient=profile_user,
            status=Donation.COMPLETED
        ).select_related('donor', 'donor__profile').order_by('-completed_at')[:6]
        
        active_donations_count = Donation.objects.filter(
            recipient=profile_user,
            status__in=[Donation.CLAIMED, Donation.AVAILABLE]
        ).count()
    
    # Get ratings received by this user
    recent_ratings = Rating.objects.filter(
        rated_user=profile_user
    ).select_related('rating_user', 'rating_user__profile', 'donation').order_by('-created_at')[:5]
    
    context = {
        'profile_user': profile_user,  
        'profile': profile,             
        'recent_donations': recent_donations,
        'active_donations_count': active_donations_count,
        'recent_ratings': recent_ratings,
    }
    
    return render(request, 'profile/public_profile.html', context)


# Find and UPDATE the dietary_preferences_view function (around line 690):

@recipient_required
def dietary_preferences_view(request):
    """Manage dietary preferences (recipients only)"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = DietaryPreferencesForm(request.POST, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Dietary preferences updated!")
            return redirect('core:profile')
        else:
            # Show validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = DietaryPreferencesForm(instance=profile)
    
    context = {
        'form': form,
        'dietary_choices': Donation.FOOD_CATEGORY_CHOICES,
    }
    
    return render(request, 'profile/dietary_preferences.html', context)


# ============================================================================
# NOTIFICATION VIEWS
# ============================================================================

@login_required
def notifications_view(request):
    """View all notifications"""
    notifications = request.user.notifications.select_related(
        'related_donation'
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/list.html', {'notifications': page_obj})


@login_required
@require_POST
def mark_notification_read_view(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('core:notifications')


@login_required
def get_notifications_view(request):
    """Get notifications as JSON (for AJAX polling)"""
    try:
        notifications = NotificationService.get_user_notifications(
            request.user, 
            limit=10
        )
        
        notifications_data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'notification_type': n.notification_type,
            'is_read': n.is_read,
            'time_ago': _format_time_ago(n.created_at),
            'related_url': n.related_url or '#',
        } for n in notifications]
        
        unread_count = NotificationService.get_unread_count(request.user)
        
        return JsonResponse({
            'notifications': notifications_data,
            'unread_count': unread_count
        })
        
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
def notification_count_view(request):
    """Get unread notification count"""
    try:
        count = NotificationService.get_unread_count(request.user)
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _format_time_ago(dt):
    """Helper function to format datetime as 'time ago' string"""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 30:
        return f"{diff.days // 30} month{'s' if diff.days // 30 > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

@login_required
@require_POST
def mark_all_notifications_read_view(request):
    """Mark all notifications as read"""
    count = request.user.notifications.filter(is_read=False).update(is_read=True)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'count': count})
    
    messages.success(request, f"{count} notifications marked as read.")
    return redirect('core:notifications')


# ============================================================================
# STATIC PAGE VIEWS
# ============================================================================

def home_view(request):
    """Landing page"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    # Get recent stats (with error handling)
    try:
        stats = {
            'total_donations': Donation.objects.count(),
            'completed_donations': Donation.objects.filter(status=Donation.COMPLETED).count(),
            'active_users': UserProfile.objects.filter(email_verified=True).count(),
        }
        
        # Get recent available donations for preview
        recent_donations = Donation.objects.filter(
            status=Donation.AVAILABLE
        ).select_related('donor', 'donor__profile').order_by('-created_at')[:6]
    except Exception as e:
        logger.warning(f"Database not ready: {e}")
        stats = {
            'total_donations': 0,
            'completed_donations': 0,
            'active_users': 0,
        }
        recent_donations = []
    
    context = {
        'stats': stats,
        'recent_donations': recent_donations,
    }
    
    return render(request, 'pages/home.html', context)


def about_view(request):
    """About page"""
    return render(request, 'pages/about.html')


def contact_view(request):
    """Contact page"""
    return render(request, 'pages/contact.html')


def privacy_view(request):
    """Privacy policy page"""
    return render(request, 'pages/privacy.html')


def terms_view(request):
    """Terms of service page"""
    return render(request, 'pages/terms.html')


# ============================================================================
# MAP VIEW (Simplified - No GPS)
# ============================================================================

def map_view(request):
    """Simple map showing donation locations (text-based)"""
    donations = Donation.objects.filter(
        status=Donation.AVAILABLE
    ).select_related('donor', 'donor__profile').order_by('-created_at')
    
    context = {
        'donations': donations,
    }
    
    return render(request, 'map/map_view.html', context)


# ============================================================================
# ANALYTICS VIEW (Simplified)
# ============================================================================

@login_required
@profile_required
def analytics_view(request):
    """Simple analytics dashboard"""
    profile = request.user.profile
    
    if profile.user_type == UserProfile.DONOR:
        # Donor analytics
        stats = DonationService.get_user_donation_stats(request.user)
        
        # Category breakdown
        category_stats = Donation.objects.filter(
            donor=request.user
        ).values('food_category').annotate(count=Count('id')).order_by('-count')
        
        context = {
            'stats': stats,
            'category_stats': category_stats,
        }
        
        return render(request, 'analytics/nutrition_analytics.html', context)
    else:
        messages.error(request, "Analytics are only available for donors.")
        return redirect('core:dashboard')