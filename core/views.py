"""
Optimized Views for FoodLoop - FIXED VERSION WITH CORRECT TEMPLATE PATHS
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Prefetch, Sum
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from datetime import datetime, timedelta
import logging

# Import models
from .models import UserProfile, Donation, EmailVerification, Notification, Rating

# Import forms
from .forms import (
    SignUpForm, DonationForm, ProfileUpdateForm, 
    DietaryPreferencesForm, RatingForm, NutritionSearchForm
)

# Import services
from .services import (
    DonationService, NotificationService, EmailService,
    AIService, AnalyticsService
)

# Import decorators
from .decorators import (
    donor_required, recipient_required, email_verified_required,
    profile_required, ajax_required
)

# Import cache
from .cache import CacheManager, CacheWarmupManager

logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """User registration with automatic profile creation"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.save()
                
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'user_type': form.cleaned_data['user_type'],
                        'phone_number': form.cleaned_data.get('phone_number', ''),
                        'location': form.cleaned_data.get('address', ''),
                        'latitude': form.cleaned_data.get('latitude'),
                        'longitude': form.cleaned_data.get('longitude'),
                    }
                )
                
                EmailService.send_verification_email(user)
                login(request, user)
                
                messages.success(
                    request,
                    'Welcome to FoodLoop! Please check your email to verify your account.'
                )
                
                CacheWarmupManager.warmup_user_data(user.id)
                return redirect('core:dashboard')
                
            except Exception as e:
                logger.error(f"Signup error: {e}")
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """User login with cache warmup"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            CacheWarmupManager.warmup_user_data(user.id)
            
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


def verify_email_view(request, token):
    """Email verification handler"""
    response = EmailService.verify_email_token(token)
    
    if response.success:
        messages.success(request, response.message)
        return redirect('core:dashboard')
    else:
        messages.error(request, response.message)
        return redirect('core:profile')


@login_required
def resend_verification_view(request):
    """Resend verification email"""
    response = EmailService.send_verification_email(request.user)
    
    if response.success:
        messages.success(request, 'Verification email sent! Please check your inbox.')
    else:
        messages.error(request, 'Failed to send verification email. Please try again.')
    
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
        stats = AnalyticsService.get_user_analytics(request.user, date_range='30d')
        
        if profile.user_type == UserProfile.DONOR:
            donations = Donation.objects.filter(
                donor=request.user
            ).select_related('recipient', 'recipient__profile').order_by('-created_at')[:10]
            
            recommendations = AIService.get_donor_recommendations(request.user)
            
            context = {
                'profile': profile,
                'stats': stats,
                'recent_donations': donations,
                'recommendations': recommendations,
                'is_donor': True,
            }
            template = 'dashboard/donor.html'
        else:
            recommendations = AIService.get_personalized_recommendations(request.user, limit=8)
            
            claimed = Donation.objects.filter(
                recipient=request.user,
                status=Donation.CLAIMED
            ).select_related('donor', 'donor__profile').order_by('-claimed_at')[:5]
            
            nutrition_insights = AIService.get_nutrition_insights(request.user)
            
            context = {
                'profile': profile,
                'stats': stats,
                'recommendations': recommendations,
                'claimed_donations': claimed,
                'nutrition_insights': nutrition_insights,
                'is_donor': False,
            }
            template = 'dashboard/recipient.html'
        
        return render(request, template, context)
        
    except Exception as e:
        logger.error(f"Dashboard error for user {request.user.id}: {e}")
        messages.error(request, 'Error loading dashboard. Please try again.')
        return redirect('core:profile')


# ============================================================================
# DONATION VIEWS
# ============================================================================

@login_required
@donor_required
def create_donation_view(request):
    """Create new donation - donors only"""
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                response = DonationService.create_donation(
                    donor=request.user,
                    form_data=form.cleaned_data,
                    image_file=request.FILES.get('image')
                )
                
                if response.success:
                    messages.success(request, response.message)
                    CacheManager.invalidate_user_donations(request.user.id)
                    return redirect('core:donation_detail', donation_id=response.data.id)
                else:
                    messages.error(request, response.message)
            except Exception as e:
                logger.error(f"Donation creation error: {e}")
                messages.error(request, 'Failed to create donation. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DonationForm()
    
    return render(request, 'donor/create_donation.html', {'form': form})


@login_required
@profile_required
def donation_detail_view(request, donation_id):
    """View donation details with efficient queries"""
    try:
        donation = get_object_or_404(
            Donation.objects.select_related(
                'donor', 'donor__profile',
                'recipient', 'recipient__profile'
            ).prefetch_related(
                Prefetch('ratings', queryset=Rating.objects.select_related('rating_user', 'rated_user'))
            ),
            id=donation_id
        )
        
        profile = request.user.profile
        is_donor = donation.donor == request.user
        is_recipient = donation.recipient == request.user
        can_claim = (
            profile.user_type == UserProfile.RECIPIENT and
            donation.status == Donation.AVAILABLE and
            not donation.is_expired() and
            profile.email_verified
        )
        
        can_rate = False
        if donation.status == Donation.COMPLETED:
            if is_donor and donation.recipient:
                can_rate = not Rating.objects.filter(
                    rating_user=request.user, donation=donation
                ).exists()
            elif is_recipient:
                can_rate = not Rating.objects.filter(
                    rating_user=request.user, donation=donation
                ).exists()
        
        context = {
            'donation': donation,
            'is_donor': is_donor,
            'is_recipient': is_recipient,
            'can_claim': can_claim,
            'can_rate': can_rate,
            'is_expired': donation.is_expired(),
            'time_until_expiry': donation.time_until_expiry(),
        }
        
        return render(request, 'donation/detail.html', context)
        
    except Exception as e:
        logger.error(f"Donation detail error: {e}")
        messages.error(request, 'Error loading donation details.')
        return redirect('core:dashboard')


@login_required
@recipient_required
@require_POST
def claim_donation_view(request, donation_id):
    """Claim a donation - recipients only"""
    response = DonationService.claim_donation(donation_id, request.user)
    
    if response.success:
        messages.success(request, response.message)
        donation = response.data
        CacheManager.invalidate_donation_related(
            donation.id, donation.donor.id, request.user.id
        )
        CacheManager.invalidate_recommendations(request.user.id)
    else:
        messages.error(request, response.message)
    
    return redirect('core:donation_detail', donation_id=donation_id)


@login_required
@donor_required
@require_POST
def complete_donation_view(request, donation_id):
    """Mark donation as completed - donors only"""
    response = DonationService.complete_donation(donation_id, request.user)
    
    if response.success:
        messages.success(request, response.message)
        CacheManager.invalidate_donation(donation_id)
        CacheManager.invalidate_user_donations(request.user.id)
    else:
        messages.error(request, response.message)
    
    return redirect('core:donation_detail', donation_id=donation_id)


@login_required
@donor_required
@require_POST
def cancel_donation_view(request, donation_id):
    """Cancel donation - donors only"""
    try:
        donation = get_object_or_404(Donation, id=donation_id, donor=request.user)
        donation.cancel()
        
        messages.success(request, 'Donation cancelled successfully.')
        CacheManager.invalidate_donation(donation_id)
        CacheManager.invalidate_user_donations(request.user.id)
        
    except Exception as e:
        logger.error(f"Cancel donation error: {e}")
        messages.error(request, str(e))
    
    return redirect('core:my_donations')


@login_required
@profile_required
def search_donations_view(request):
    """Search donations with efficient filtering"""
    form = NutritionSearchForm(request.GET)
    
    query_params = {
        'q': request.GET.get('q', ''),
        'food_category': request.GET.get('food_category', ''),
        'max_calories': request.GET.get('max_calories', ''),
        'min_nutrition_score': request.GET.get('min_nutrition_score', ''),
        'dietary_tags': request.GET.getlist('dietary_tags'),
    }
    
    donations = DonationService.search_donations(query_params, request.user)
    
    paginator = Paginator(donations, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'donations': page_obj,
        'query_params': query_params,
        'total_results': len(donations),
    }
    
    return render(request, 'search/nutrition_search.html', context)


@login_required
@profile_required
def my_donations_view(request):
    """View user's donations (donor or recipient)"""
    profile = request.user.profile
    
    if profile.user_type == UserProfile.DONOR:
        donations = Donation.objects.filter(
            donor=request.user
        ).select_related('recipient', 'recipient__profile').order_by('-created_at')
        title = "My Donations"
        template = 'donor/my_donations.html'
    else:
        donations = Donation.objects.filter(
            recipient=request.user
        ).select_related('donor', 'donor__profile').order_by('-claimed_at')
        title = "My Claimed Donations"
        template = 'recipient/my_donations.html'
    
    status = request.GET.get('status', 'all')
    if status != 'all':
        donations = donations.filter(status=status)
    
    paginator = Paginator(donations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    stats = DonationService.get_user_donation_stats(request.user)
    
    context = {
        'donations': page_obj,
        'title': title,
        'stats': stats,
        'current_status': status,
        'is_donor': profile.user_type == UserProfile.DONOR,
    }
    
    return render(request, template, context)


# ============================================================================
# RATING VIEWS
# ============================================================================

@login_required
@profile_required
def rate_user_view(request, donation_id):
    """Rate a user after completed donation"""
    try:
        donation = get_object_or_404(
            Donation.objects.select_related('donor', 'recipient'),
            id=donation_id,
            status=Donation.COMPLETED
        )
        
        # Determine who to rate
        if donation.donor == request.user:
            rated_user = donation.recipient
            if not rated_user:
                messages.error(request, 'No recipient to rate.')
                return redirect('core:donation_detail', donation_id=donation_id)
        elif donation.recipient == request.user:
            rated_user = donation.donor
        else:
            messages.error(request, 'You cannot rate this donation.')
            return redirect('core:donation_detail', donation_id=donation_id)
        
        existing_rating = Rating.objects.filter(
            rating_user=request.user,
            donation=donation
        ).first()
        
        if request.method == 'POST':
            form = RatingForm(request.POST, instance=existing_rating)
            if form.is_valid():
                try:
                    rating = form.save(commit=False)
                    rating.rating_user = request.user
                    rating.rated_user = rated_user
                    rating.donation = donation
                    rating.save()
                    
                    NotificationService.notify_rating_received(rating, request.user)
                    
                    messages.success(request, 'Thank you for your rating!')
                    return redirect('core:donation_detail', donation_id=donation_id)
                    
                except Exception as e:
                    logger.error(f"Rating save error: {e}")
                    messages.error(request, 'Failed to save rating.')
                    return redirect('core:donation_detail', donation_id=donation_id)
        else:
            form = RatingForm(instance=existing_rating)
        
        context = {
            'form': form,
            'donation': donation,
            'rated_user': rated_user,
            'existing_rating': existing_rating,
        }
        
        return render(request, 'ratings/rating_form.html', context)
        
    except Exception as e:
        logger.error(f"Rate user error: {e}")
        messages.error(request, 'Error loading rating page.')
        return redirect('core:dashboard')


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
            try:
                form.save()
                CacheManager.invalidate_user_profile(request.user.id)
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('core:profile')
            except Exception as e:
                logger.error(f"Profile update error: {e}")
                messages.error(request, 'Failed to update profile.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)
    
    ratings_received = Rating.objects.filter(
        rated_user=request.user
    ).select_related('rating_user', 'donation').order_by('-created_at')[:5]
    
    analytics = AnalyticsService.get_user_analytics(request.user, date_range='all')
    
    context = {
        'form': form,
        'profile': profile,
        'ratings_received': ratings_received,
        'analytics': analytics,
    }
    
    return render(request, 'profile/profile.html', context)


@login_required
@recipient_required
def dietary_preferences_view(request):
    """Manage dietary preferences - recipients only"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = DietaryPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            CacheManager.invalidate_recommendations(request.user.id)
            
            messages.success(request, 'Dietary preferences updated!')
            return redirect('core:profile')
    else:
        form = DietaryPreferencesForm(instance=profile)
    
    return render(request, 'profile/dietary_preferences.html', {'form': form})


def public_profile_view(request, user_id):
    """View public profile of a user"""
    try:
        user = get_object_or_404(User, id=user_id, is_active=True)
        profile = get_object_or_404(UserProfile, user=user)
        
        ratings = Rating.objects.filter(
            rated_user=user
        ).select_related('rating_user', 'donation').order_by('-created_at')[:10]
        
        if profile.user_type == UserProfile.DONOR:
            donation_count = Donation.objects.filter(
                donor=user, status=Donation.COMPLETED
            ).count()
        else:
            donation_count = Donation.objects.filter(
                recipient=user, status=Donation.COMPLETED
            ).count()
        
        context = {
            'viewed_user': user,
            'profile': profile,
            'ratings': ratings,
            'donation_count': donation_count,
        }
        
        return render(request, 'profile/public_profile.html', context)
        
    except Exception as e:
        logger.error(f"Public profile error: {e}")
        messages.error(request, 'Profile not found.')
        return redirect('core:dashboard')


# ============================================================================
# NOTIFICATION VIEWS
# ============================================================================

@login_required
@ajax_required
def get_notifications_view(request):
    """Get notifications via AJAX"""
    try:
        notifications = NotificationService.get_user_notifications(
            request.user,
            limit=20,
            unread_only=request.GET.get('unread_only') == 'true'
        )
        
        data = {
            'notifications': [
                {
                    'id': n.id,
                    'type': n.notification_type,
                    'title': n.title,
                    'message': n.message,
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                    'related_url': n.related_url,
                }
                for n in notifications
            ],
            'unread_count': NotificationService.get_unread_count(request.user)
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        return JsonResponse({'error': 'Failed to load notifications'}, status=500)


@login_required
@ajax_required
@require_POST
def mark_notification_read_view(request, notification_id):
    """Mark notification as read via AJAX"""
    response = NotificationService.mark_notification_read(notification_id, request.user)
    
    if response.success:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': response.message}, status=400)


@login_required
@ajax_required
@require_POST
def mark_all_notifications_read_view(request):
    """Mark all notifications as read via AJAX"""
    response = NotificationService.mark_all_read(request.user)
    
    if response.success:
        return JsonResponse({'success': True, 'count': response.data['count']})
    else:
        return JsonResponse({'success': False, 'error': response.message}, status=400)


# ============================================================================
# MAP VIEWS
# ============================================================================

@login_required
@profile_required
def map_view(request):
    """Interactive map of donations"""
    donations = Donation.objects.filter(
        status=Donation.AVAILABLE,
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('donor', 'donor__profile').values(
        'id', 'title', 'food_category', 'latitude', 
        'longitude', 'nutrition_score', 'expiry_datetime'
    )[:100]
    
    donations_list = list(donations)
    active_donations = [
        d for d in donations_list 
        if d['expiry_datetime'] > timezone.now()
    ]
    
    profile = request.user.profile
    user_location = None
    if profile.has_valid_coordinates:
        user_location = {
            'lat': float(profile.latitude),
            'lng': float(profile.longitude)
        }
    
    context = {
        'donations': active_donations,
        'user_location': user_location,
    }
    
    return render(request, 'map/map_view.html', context)


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

@login_required
@profile_required
def analytics_view(request):
    """Personal analytics dashboard"""
    date_range = request.GET.get('range', '30d')
    
    analytics = AnalyticsService.get_user_analytics(request.user, date_range)
    
    days_map = {'7d': 7, '30d': 30, '90d': 90}
    days = days_map.get(date_range, 30)
    trends = AnalyticsService.get_donation_trends(days)
    
    context = {
        'analytics': analytics,
        'trends': trends,
        'date_range': date_range,
    }
    
    return render(request, 'analytics/nutrition_analytics.html', context)


@cache_page(60 * 15)
def platform_stats_view(request):
    """Public platform statistics"""
    overview = AnalyticsService.get_platform_overview()
    nutrition_insights = AnalyticsService.get_nutrition_insights_summary()
    
    context = {
        'overview': overview,
        'nutrition_insights': nutrition_insights,
    }
    
    return render(request, 'analytics/platform_stats.html', context)


# ============================================================================
# UTILITY VIEWS
# ============================================================================

def home_view(request):
    """Landing page"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    stats = {
        'total_donations': Donation.objects.filter(status=Donation.COMPLETED).count(),
        'active_users': UserProfile.objects.filter(email_verified=True).count(),
        'calories_saved': Donation.objects.filter(
            status=Donation.COMPLETED
        ).aggregate(total=Sum('estimated_calories'))['total'] or 0,
    }
    
    return render(request, 'pages/home.html', {'stats': stats})


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
# ERROR HANDLERS - UPDATED TO USE errors/ FOLDER
# ============================================================================

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    """Custom 403 error handler"""
    return render(request, 'errors/403.html', status=403)


def handler400(request, exception):
    """Custom 400 error handler"""
    return render(request, 'errors/400.html', status=400)