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
                # Create user
                user = form.save(commit=False)
                user.email = form.cleaned_data['email']
                user.save()
                
                # Create profile
                UserProfile.objects.create(
                    user=user,
                    user_type=form.cleaned_data['user_type'],
                    phone_number=form.cleaned_data['phone_number'],
                    location=form.cleaned_data['location'],
                )
                
                # Send verification email
                EmailService.send_verification_email(user)
                
                # Log user in
                login(request, user)
                
                messages.success(
                    request, 
                    "Welcome to FoodLoop! Please check your email to verify your account."
                )
                return redirect('core:dashboard')
                
            except Exception as e:
                logger.error(f"Signup error: {e}")
                messages.error(request, "An error occurred during signup. Please try again.")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
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
        # Token is now a string, not UUID
        verification = EmailVerification.objects.get(token=token)
        
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
@profile_required
@require_POST
def claim_donation_view(request, donation_id):
    """Claim a donation (recipients only)"""
    result = DonationService.claim_donation(donation_id, request.user)
    
    if result.success:
        messages.success(request, result.message)
        return redirect('core:donation_detail', donation_id=donation_id)
    else:
        messages.error(request, result.message)
        return redirect('core:donation_detail', donation_id=donation_id)


@login_required
@profile_required
@require_POST
def complete_donation_view(request, donation_id):
    """Mark donation as completed"""
    result = DonationService.complete_donation(donation_id, request.user)
    
    if result.success:
        messages.success(request, result.message)
        return redirect('core:rate_user', donation_id=donation_id)
    else:
        messages.error(request, result.message)
        return redirect('core:donation_detail', donation_id=donation_id)


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
    
    # ✅ FIXED: Get donations where user is the RECIPIENT
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
@profile_required
def rate_user_view(request, donation_id):
    """Rate a user after donation completion"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Verify user can rate
    if request.user != donation.donor and request.user != donation.recipient:
        messages.error(request, "You cannot rate this transaction.")
        return redirect('core:dashboard')
    
    if donation.status != Donation.COMPLETED:
        messages.error(request, "Can only rate completed donations.")
        return redirect('core:donation_detail', donation_id=donation_id)
    
    # Check if already rated
    existing_rating = Rating.objects.filter(
        donation=donation,
        rating_user=request.user
    ).first()
    
    if existing_rating:
        messages.info(request, "You have already rated this transaction.")
        return redirect('core:donation_detail', donation_id=donation_id)
    
    if request.method == 'POST':
        form = RatingForm(
            request.POST,
            donation=donation,
            rating_user=request.user
        )
        
        if form.is_valid():
            rating = form.save()
            
            # Send notification to rated user
            rated_user = donation.recipient if request.user == donation.donor else donation.donor
            NotificationService.notify_rating_received(rated_user, rating)
            
            messages.success(request, "Thank you for your rating!")
            return redirect('core:dashboard')
    else:
        form = RatingForm(donation=donation, rating_user=request.user)
    
    # Determine who is being rated
    rated_user = donation.recipient if request.user == donation.donor else donation.donor
    
    context = {
        'form': form,
        'donation': donation,
        'rated_user': rated_user,
    }
    
    return render(request, 'ratings/rating_form.html', context)


# ============================================================================
# PROFILE VIEWS
# ============================================================================

@login_required
@profile_required
def profile_view(request):
    """View and edit user profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user
        )
        
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('core:profile')
        else:
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
        notifications = request.user.notifications.select_related(
            'related_donation'
        ).order_by('-created_at')[:10]
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'type': notif.notification_type,
                'title': notif.title,
                'message': notif.message,
                'related_url': notif.related_url,
                'is_read': notif.is_read,
                'time_ago': _format_time_ago(notif.created_at),
                'created_at': notif.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': request.user.notifications.filter(is_read=False).count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching notifications for {request.user.username}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error loading notifications'
        }, status=500)


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
    
    # Get recent stats
    stats = {
        'total_donations': Donation.objects.count(),
        'completed_donations': Donation.objects.filter(status=Donation.COMPLETED).count(),
        'active_users': UserProfile.objects.filter(email_verified=True).count(),
    }
    
    # Get recent available donations for preview
    recent_donations = Donation.objects.filter(
        status=Donation.AVAILABLE
    ).select_related('donor', 'donor__profile').order_by('-created_at')[:6]
    
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