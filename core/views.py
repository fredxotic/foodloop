from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from datetime import timedelta
from django.db.models import Q
import math
from .models import Rating
from .forms import RatingForm
from django.views.decorators.http import require_http_methods

from .models import UserProfile, Donation, EmailVerification
from .forms import SignUpForm, DonationForm, ProfileUpdateForm
from .decorators import donor_required, recipient_required, email_verified_required
from .utils import generate_verification_token, send_verification_email, send_donation_claimed_email
from django.conf import settings  # ADD THIS IMPORT

def home(request):
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.user_type == UserProfile.DONOR:
                return redirect('donor_dashboard')
            else:
                return redirect('recipient_dashboard')
        except Exception as e:
            print(f"Error in home view: {e}")
            pass
    
    try:
        available_donations = Donation.objects.filter(status=Donation.AVAILABLE)[:6]
        available_donations = [d for d in available_donations if not d.is_expired()]
    except Exception as e:
        print(f"Error getting donations: {e}")
        available_donations = []
    
    return render(request, 'home.html', {'available_donations': available_donations})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            try:
                user_profile = UserProfile.objects.get(user=user)
                if user_profile.user_type == UserProfile.DONOR:
                    next_url = request.GET.get('next', 'donor_dashboard')
                    return redirect(next_url)
                else:
                    next_url = request.GET.get('next', 'recipient_dashboard')
                    return redirect(next_url)
            except UserProfile.DoesNotExist:
                return redirect('home')
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'registration/login.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            user_type = request.POST.get('user_type')
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.user_type = user_type
            user_profile.phone_number = request.POST.get('phone_number', '')
            user_profile.address = request.POST.get('address', '')
            
            if hasattr(user_profile, 'email_verified'):
                user_profile.email_verified = False
                
            user_profile.save()
            
            try:
                token = generate_verification_token()
                EmailVerification.objects.create(user=user, token=token)
                verification_url = f"{request.scheme}://{request.get_host()}/verify/{token}/"
                send_verification_email(user, verification_url)
                messages.success(request, 'Account created successfully! Please check your email for verification.')
            except Exception as e:
                print(f"Error sending verification email: {e}")
                messages.success(request, 'Account created successfully!')
            
            # Authenticate and login the user
            user = authenticate(username=user.username, password=form.cleaned_data['password1'])
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome {user.username}! You are now logged in.')
                
                if user_type == 'donor':
                    return redirect('donor_dashboard')
                else:
                    return redirect('recipient_dashboard')
            else:
                messages.error(request, 'Login failed after signup. Please log in manually.')
                return redirect('login')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def profile_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile, user=request.user)
        if form.is_valid():
            # Update user info
            request.user.email = form.cleaned_data['email']
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            
            # Update profile
            user_profile.phone_number = form.cleaned_data['phone_number']
            user_profile.address = form.cleaned_data.get('address', '')
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                user_profile.profile_picture = request.FILES['profile_picture']
                
            user_profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user_profile, user=request.user)
    
    # Check for pending verification
    pending_verification = EmailVerification.objects.filter(user=request.user, is_verified=False).first()
    
    return render(request, 'profile.html', {
        'form': form,
        'user_profile': user_profile,
        'pending_verification': pending_verification
    })

@login_required
def verify_email(request):
    if request.method == 'POST':
        try:
            # Delete old verification tokens
            EmailVerification.objects.filter(user=request.user).delete()
            
            # Create new verification token
            token = generate_verification_token()
            EmailVerification.objects.create(user=request.user, token=token)
            
            verification_url = f"{request.scheme}://{request.get_host()}/verify/{token}/"
            
            # Try to send email
            try:
                send_verification_email(request.user, verification_url)
                messages.info(request, 'Verification email sent! Please check your inbox (or console output).')
            except Exception as e:
                # If email fails, show the link directly
                messages.warning(request, f'Email sending failed. Here is your verification link: {verification_url}')
                print(f"Email error: {e}")
            
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error creating verification: {e}')
            return redirect('profile')
    
    return redirect('profile')

def verify_email_confirm(request, token):
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to verify your email.')
        return redirect('login')
    
    try:
        verification = EmailVerification.objects.get(token=token, user=request.user)
        if not verification.is_verified:
            verification.is_verified = True
            verification.save()
            
            # Update user profile email verification status
            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.email_verified = True
            user_profile.save()
            
            messages.success(request, 'Email verified successfully!')
        else:
            messages.info(request, 'Email already verified.')
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification token.')
    
    return redirect('profile')

@login_required
@donor_required
def donor_dashboard(request):
    donations = Donation.objects.filter(donor=request.user).order_by('-created_at')
    
    # Update expired donations
    for donation in donations:
        if donation.is_expired() and donation.status != Donation.EXPIRED:
            donation.status = Donation.EXPIRED
            donation.save()
    
    # Statistics
    total_donations = donations.count()
    completed_donations = donations.filter(status=Donation.COMPLETED).count()
    claimed_donations = donations.filter(status=Donation.CLAIMED).count()
    available_donations = donations.filter(status=Donation.AVAILABLE).count()
    
    # Recent activity (last 7 days)
    recent_donations = donations.filter(created_at__gte=timezone.now()-timedelta(days=7))
    
    return render(request, 'donor/dashboard.html', {
        'donations': donations,
        'stats': {
            'total': total_donations,
            'completed': completed_donations,
            'claimed': claimed_donations,
            'available': available_donations,
            'recent_count': recent_donations.count(),
        }
    })

@login_required
@recipient_required
def recipient_dashboard(request):
    print(f"DEBUG: Recipient dashboard accessed by {request.user.username}")
    
    # Check if user has recipient profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        print(f"DEBUG: User profile found - type: {user_profile.user_type}")
        
        if user_profile.user_type != UserProfile.RECIPIENT:
            print("DEBUG: User is not a recipient, redirecting to home")
            messages.error(request, 'This page is only for recipients.')
            return redirect('home')
            
    except UserProfile.DoesNotExist:
        print("DEBUG: User profile not found")
        messages.error(request, 'Please complete your profile setup.')
        return redirect('profile')
    
    # Get available donations (not expired and available)
    try:
        available_donations = Donation.objects.filter(status=Donation.AVAILABLE).exclude(donor=request.user)
        # Filter out expired donations
        available_donations = [d for d in available_donations if not d.is_expired()]
        
        my_donations = Donation.objects.filter(recipient=request.user).order_by('-created_at')
        
        # Statistics
        total_claims = my_donations.count()
        completed_claims = my_donations.filter(status=Donation.COMPLETED).count()
        active_claims = my_donations.filter(status=Donation.CLAIMED).count()
        
        print(f"DEBUG: Found {len(available_donations)} available donations")
        print(f"DEBUG: Found {len(my_donations)} user donations")
        
    except Exception as e:
        print(f"DEBUG: Error getting donations: {e}")
        available_donations = []
        my_donations = []
        total_claims = 0
        completed_claims = 0
        active_claims = 0
    
    return render(request, 'recipient/dashboard.html', {
        'available_donations': available_donations,
        'my_donations': my_donations,
        'stats': {
            'total_claims': total_claims,
            'completed_claims': completed_claims,
            'active_claims': active_claims,
        }
    })

@login_required
@donor_required
@email_verified_required
def create_donation(request):
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user
            donation.status = Donation.AVAILABLE
            
            # Handle image upload
            if 'image' in request.FILES:
                donation.image = request.FILES['image']
                
            donation.save()
            
            messages.success(request, 'Donation created successfully!')
            return redirect('donor_dashboard')
    else:
        form = DonationForm()
    
    return render(request, 'donor/create_donation.html', {'form': form})

@login_required
@recipient_required
@email_verified_required
@require_POST
def claim_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    
    if donation.status != Donation.AVAILABLE:
        messages.error(request, 'Donation is not available for claiming.')
        return redirect('recipient_dashboard')
    
    if donation.is_expired():
        donation.status = Donation.EXPIRED
        donation.save()
        messages.error(request, 'This donation has expired.')
        return redirect('recipient_dashboard')
    
    donation.status = Donation.CLAIMED
    donation.recipient = request.user
    donation.save()
    
    # Send notification to donor
    send_donation_claimed_email(donation, request.user)
    
    messages.success(request, 
        f'You have successfully claimed the {donation.food_type} donation! '
        f'The donor has been notified and will contact you soon.'
    )
    
    return redirect('recipient_dashboard')

@login_required
def donation_detail(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Get rating information
    can_rate, rate_message = get_rating_eligibility(request.user, donation)
    existing_rating = None
    if can_rate:
        existing_rating = Rating.objects.filter(
            donation=donation, 
            donor=donation.donor, 
            recipient=donation.recipient
        ).first()
    
    return render(request, 'donation/detail.html', {
        'donation': donation,
        'can_rate': can_rate,
        'rate_message': rate_message,
        'existing_rating': existing_rating,
        'rating_form': RatingForm(instance=existing_rating) if existing_rating else RatingForm()
    })

@login_required
@donor_required
@require_POST
def complete_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, donor=request.user)
    
    if donation.status != Donation.CLAIMED:
        messages.error(request, 'Only claimed donations can be completed.')
        return redirect('donor_dashboard')
    
    donation.status = Donation.COMPLETED
    donation.save()
    
    messages.success(request, 'Donation marked as completed! Thank you for your contribution.')
    return redirect('donor_dashboard')

def search_donations(request):
    query = request.GET.get('q', '')
    food_type = request.GET.get('food_type', '')
    location = request.GET.get('location', '')
    
    donations = Donation.objects.filter(status=Donation.AVAILABLE)
    
    if query:
        donations = donations.filter(
            models.Q(food_type__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(location__icontains=query)
        )
    
    if food_type:
        donations = donations.filter(food_type=food_type)
    
    if location:
        donations = donations.filter(location__icontains=location)
    
    # Filter out expired donations
    donations = [d for d in donations if not d.is_expired()]
    
    return render(request, 'search.html', {
        'donations': donations,
        'query': query,
        'food_type': food_type,
        'location': location,
        'food_categories': Donation.FOOD_CATEGORIES,
    })

@login_required
def rate_donation(request, donation_id):
    """Display rating form for a donation"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Check if user can rate this donation
    can_rate, rate_message = get_rating_eligibility(request.user, donation)
    if not can_rate:
        messages.error(request, rate_message)
        return redirect('donor_dashboard' if request.user.userprofile.user_type == 'donor' else 'recipient_dashboard')
    
    # Get existing rating if it exists
    existing_rating = Rating.objects.filter(
        donation=donation, 
        donor=donation.donor, 
        recipient=donation.recipient
    ).first()
    
    if existing_rating:
        form = RatingForm(instance=existing_rating)
    else:
        form = RatingForm()
    
    return render(request, 'ratings/rating_form.html', {
        'donation': donation,
        'form': form,
        'existing_rating': existing_rating
    })

# Helper function to get user type
def get_user_type(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.user_type
    except UserProfile.DoesNotExist:
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    try:
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except (ValueError, TypeError):
        return None
        

@login_required
def map_view(request):
    """Interactive map view of all donations"""
    try:
        donations = Donation.objects.filter(status=Donation.AVAILABLE)
        
        # Filter out expired donations and add distance if user has location
        valid_donations = []
        user_lat = request.GET.get('lat')
        user_lon = request.GET.get('lon')
        
        for donation in donations:
            if not donation.is_expired():
                # Initialize distance_km for every donation to avoid AttributeError
                donation.distance_km = None
                
                if user_lat and user_lon and donation.has_valid_coordinates:
                    try:
                        distance_km = calculate_distance(
                            float(user_lat), float(user_lon),
                            donation.latitude, donation.longitude
                        )
                        if distance_km is not None:
                            donation.distance_km = round(distance_km, 1)
                    except (ValueError, TypeError) as e:
                        print(f"Distance calculation error: {e}")
                        donation.distance_km = None
                
                valid_donations.append(donation)
        
        # Sort by distance if available (only if we have user coordinates)
        if user_lat and user_lon:
            valid_donations.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))
        
        # Set default center (Nairobi)
        try:
            center_lat = float(user_lat) if user_lat else -1.286389
            center_lon = float(user_lon) if user_lon else 36.817223
        except (ValueError, TypeError):
            center_lat = -1.286389
            center_lon = 36.817223
        
        return render(request, 'map/map_view.html', {
            'donations': valid_donations,
            'map_center_lat': center_lat,
            'map_center_lon': center_lon,
        })
        
    except Exception as e:
        print(f"Error in map_view: {e}")
        return render(request, 'map/map_view.html', {
            'donations': [],
            'map_center_lat': -1.286389,
            'map_center_lon': 36.817223,
        })

@login_required
@require_http_methods(["GET", "POST"])
def create_rating(request, donation_id):
    """Handle rating creation/update"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Check if user can rate this donation
    can_rate, rate_message = get_rating_eligibility(request.user, donation)
    if not can_rate:
        messages.error(request, rate_message)
        return redirect('donor_dashboard' if request.user.userprofile.user_type == 'donor' else 'recipient_dashboard')
    
    # Get existing rating if it exists
    existing_rating = None
    try:
        existing_rating = Rating.objects.get(
            donation=donation, 
            donor=donation.donor, 
            recipient=donation.recipient
        )
    except Rating.DoesNotExist:
        existing_rating = None
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.donation = donation
            rating.donor = donation.donor
            rating.recipient = donation.recipient
            rating.save()
            
            if existing_rating:
                messages.success(request, "Rating updated successfully!")
            else:
                messages.success(request, "Thank you for your rating!")
            
            # Redirect based on user type
            if request.user.userprofile.user_type == 'donor':
                return redirect('donor_dashboard')
            else:
                return redirect('recipient_dashboard')
        else:
            messages.error(request, "There was an error with your rating. Please try again.")
    else:
        # GET request - show the form
        if existing_rating:
            form = RatingForm(instance=existing_rating)
        else:
            form = RatingForm()
    
    return render(request, 'ratings/rating_form.html', {
        'donation': donation,
        'form': form,
        'existing_rating': existing_rating
    })

@login_required
def rating_success(request, donation_id):
    """Display rating success page"""
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'ratings/success.html', {'donation': donation})

def can_user_rate_donation(user, donation):
    """Check if user can rate a specific donation"""
    if not user.is_authenticated:
        return False
    
    # Donation must be completed
    if donation.status != Donation.COMPLETED:
        return False
    
    # User must be either donor or recipient of this donation
    if user not in [donation.donor, donation.recipient]:
        return False
    
    # Check if rating period is valid (within 30 days of completion)
    rating_period = timezone.now() - timedelta(days=30)
    if donation.updated_at < rating_period:
        return False
    
    return True

def get_rating_eligibility(user, donation):
    """Get rating eligibility status and message"""
    if not user.is_authenticated:
        return False, "Please log in to rate donations."
    
    # Donation must be completed
    if donation.status != Donation.COMPLETED:
        return False, "You can only rate completed donations."
    
    # User must be either donor or recipient of this donation
    if user not in [donation.donor, donation.recipient]:
        return False, "You can only rate donations you're involved with."
    
    # Check if donation has recipient (should have if completed)
    if not donation.recipient:
        return False, "This donation doesn't have a recipient to rate."
    
    # Check if rating period is valid (within 30 days of completion)
    rating_period = timezone.now() - timedelta(days=30)
    if donation.updated_at < rating_period:
        return False, "Rating period has expired for this donation."
    
    return True, "You can rate this donation."

@login_required
def search_donations_map(request):
    """Map-based search with filters"""
    try:
        query = request.GET.get('q', '')
        food_type = request.GET.get('food_type', '')
        radius_km = request.GET.get('radius', '10')
        user_lat = request.GET.get('lat', '')
        user_lon = request.GET.get('lon', '')
        
        donations = Donation.objects.filter(status=Donation.AVAILABLE)
        
        # Apply filters
        if query:
            donations = donations.filter(
                Q(food_type__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
        
        if food_type:
            donations = donations.filter(food_type=food_type)
        
        # Filter by radius if coordinates provided
        nearby_donations = []
        if user_lat and user_lon:
            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
                radius_km = float(radius_km)
                
                for donation in donations:
                    if not donation.is_expired() and donation.has_valid_coordinates:
                        distance = calculate_distance(
                            user_lat, user_lon,
                            donation.latitude, donation.longitude
                        )
                        if distance is not None and distance <= radius_km:
                            donation.distance_km = round(distance, 1)
                            nearby_donations.append(donation)
            except (ValueError, TypeError) as e:
                print(f"Radius filter error: {e}")
                nearby_donations = [d for d in donations if not d.is_expired()]
        else:
            nearby_donations = [d for d in donations if not d.is_expired()]
        
        # Sort by distance
        if user_lat and user_lon:
            nearby_donations.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))
        
        return render(request, 'map/search_map.html', {
            'donations': nearby_donations,
            'query': query,
            'food_type': food_type,
            'radius_km': radius_km,
            'user_lat': user_lat,
            'user_lon': user_lon,
            'food_categories': Donation.FOOD_CATEGORIES,
        })
        
    except Exception as e:
        print(f"Error in search_donations_map: {e}")
        return render(request, 'map/search_map.html', {
            'donations': [],
            'query': query,
            'food_type': food_type,
            'radius_km': radius_km,
            'user_lat': user_lat,
            'user_lon': user_lon,
            'food_categories': Donation.FOOD_CATEGORIES,
        })
