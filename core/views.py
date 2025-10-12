from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from datetime import timedelta
from django.db.models import Q
import math
import json
from datetime import datetime
from .models import UserProfile, Donation, EmailVerification, Notification, Rating, NutritionImpact
from .forms import SignUpForm, DonationForm, ProfileUpdateForm, DietaryPreferencesForm, RatingForm, NutritionSearchForm
from .decorators import donor_required, recipient_required, email_verified_required
from .utils import generate_verification_token, send_verification_email, send_donation_claimed_email, send_real_time_notification
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# AI Recommendation Engine
class FoodLoopAI:
    """Simple AI engine for food recommendations"""
    
    @staticmethod
    def get_personalized_recommendations(user, limit=5):
        """Get personalized donation recommendations for user"""
        try:
            user_profile = UserProfile.objects.get(user=user)
            available_donations = Donation.objects.filter(
                status=Donation.AVAILABLE
            ).exclude(donor=user)
            
            # Filter out expired donations
            available_donations = [d for d in available_donations if not d.is_expired()]
            
            # Score donations based on user preferences
            scored_donations = []
            for donation in available_donations:
                score = FoodLoopAI.calculate_match_score(user_profile, donation)
                scored_donations.append((donation, score))
            
            # Sort by score (descending) and return top matches
            scored_donations.sort(key=lambda x: x[1], reverse=True)
            return [donation for donation, score in scored_donations[:limit]]
            
        except Exception as e:
            print(f"AI recommendation error: {e}")
            return []
    
    @staticmethod
    def calculate_match_score(user_profile, donation):
        """Calculate how well a donation matches user preferences"""
        score = 0
        
        # Location proximity (if coordinates available)
        if user_profile.latitude and user_profile.longitude and donation.has_valid_coordinates:
            distance = calculate_distance(
                user_profile.latitude, user_profile.longitude,
                donation.latitude, donation.longitude
            )
            if distance and distance < 10:  # Within 10km
                score += (10 - distance) * 5  # Closer = higher score
        
        # Dietary compatibility
        dietary_score = user_profile.get_nutrition_match_score(donation)
        score += dietary_score * 0.6  # 60% weight to dietary match
        
        # Food type preferences
        if donation.food_type in user_profile.preferred_food_types:
            score += 20
        
        # Nutrition goals alignment
        if user_profile.nutrition_goals == 'weight_loss' and donation.nutrition_score > 70:
            score += 15
        elif user_profile.nutrition_goals == 'muscle_gain' and donation.food_type in ['protein', 'dairy']:
            score += 15
        
        # Recency bonus (newer donations get slight preference)
        days_old = (timezone.now() - donation.created_at).days
        if days_old == 0:
            score += 10
        elif days_old == 1:
            score += 5
        
        return min(score, 100)
    
    @staticmethod
    def get_nutrition_insights(user):
        """Get personalized nutrition insights for user"""
        try:
            user_profile = UserProfile.objects.get(user=user)
            insights = []
            
            # Recent donations analysis
            if user_profile.user_type == 'recipient':
                recent_donations = Donation.objects.filter(
                    recipient=user,
                    status=Donation.COMPLETED,
                    created_at__gte=timezone.now() - timedelta(days=30)
                )
                
                total_calories = sum(d.get_calorie_estimate() for d in recent_donations if d.get_calorie_estimate())
                avg_nutrition_score = sum(d.nutrition_score for d in recent_donations) / len(recent_donations) if recent_donations else 0
                
                if total_calories > 5000:
                    insights.append(f"You've received approximately {total_calories} calories from donations this month!")
                
                if avg_nutrition_score > 80:
                    insights.append("Great job! You're choosing highly nutritious donations.")
                elif avg_nutrition_score < 60:
                    insights.append("Consider choosing donations with higher nutrition scores for better health.")
            
            # Dietary pattern insights
            if user_profile.dietary_restrictions:
                restrictions_str = ", ".join(user_profile.dietary_restrictions)
                insights.append(f"Your dietary preferences ({restrictions_str}) are helping us find better matches for you.")
            
            return insights[:3]  # Return top 3 insights
            
        except Exception as e:
            print(f"Nutrition insights error: {e}")
            return ["We're learning your preferences to provide better recommendations."]

    @staticmethod
    def get_donor_recommendations(user):
        """Get recommendations for donors on what to donate"""
        try:
            user_profile = UserProfile.objects.get(user=user)
            recommendations = []
            
            # Analyze what's in high demand
            high_demand_foods = Donation.objects.filter(
                status=Donation.AVAILABLE,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).values('food_type').annotate(count=models.Count('id')).order_by('count')
            
            if high_demand_foods:
                least_available = high_demand_foods.first()
                recommendations.append(f"Consider donating {least_available['food_type']} - they're in high demand!")
            
            # Seasonal recommendations
            current_month = datetime.now().month
            if current_month in [6, 7, 8]:  # Summer months
                recommendations.append("Fresh fruits and vegetables are especially appreciated during summer!")
            elif current_month in [12, 1, 2]:  # Winter months
                recommendations.append("Warm cooked meals and hearty foods are in high demand during winter.")
            
            # Nutrition-focused recommendations
            recommendations.append("Foods with high nutrition scores (80+) help recipients maintain healthy diets.")
            
            return recommendations[:2]
            
        except Exception as e:
            print(f"Donor recommendations error: {e}")
            return ["Consider donating a variety of food types to help different dietary needs."]

# =============================================================================
# CORE VIEWS
# =============================================================================

def home(request):
    """Enhanced home page with AI recommendations"""
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
        # Get available donations with nutrition info
        available_donations = Donation.objects.filter(status=Donation.AVAILABLE)[:6]
        available_donations = [d for d in available_donations if not d.is_expired()]
        
        # Add nutrition info to donations
        for donation in available_donations:
            donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
            donation.calorie_info = f"~{donation.get_calorie_estimate()} cal" if donation.get_calorie_estimate() else "Calories unknown"
            
    except Exception as e:
        print(f"Error getting donations: {e}")
        available_donations = []
    
    return render(request, 'home.html', {
        'available_donations': available_donations,
        'show_nutrition_info': True
    })

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
                messages.error(request, 'User profile not found. Please contact support.')
                return render(request, 'registration/login.html', {'error': 'User profile not found'})
            except Exception as e:
                print(f"Error in login_view: {e}")
                messages.error(request, 'An error occurred. Please try again.')
                return render(request, 'registration/login.html', {'error': 'An error occurred'})
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'registration/login.html')

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                # Check if user already exists with this username or email
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Username already exists. Please choose a different one.")
                    return render(request, "signup.html", {'form': form})
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, "Email already registered. Please use a different email or login.")
                    return render(request, "signup.html", {'form': form})
                
                # Create user using the form (which also creates UserProfile)
                user = form.save()
                
                # Double-check: Ensure only one UserProfile exists
                profile_count = UserProfile.objects.filter(user=user).count()
                if profile_count > 1:
                    # Clean up duplicates
                    profiles = UserProfile.objects.filter(user=user)
                    # Keep the first one, delete others
                    for profile in profiles[1:]:
                        profile.delete()
                    print(f"Cleaned up {profile_count - 1} duplicate profiles for {user.username}")
                
                # Create email verification
                token = generate_verification_token()
                # Delete any existing unverified tokens
                EmailVerification.objects.filter(user=user, is_verified=False).delete()
                EmailVerification.objects.create(user=user, token=token, created_at=timezone.now())

                verification_url = request.build_absolute_uri(f'/verify/{token}/')
                
                # Try to send verification email
                email_sent = send_verification_email(user, verification_url)
                
                if email_sent:
                    messages.success(request, "Account created! Please check your email to verify your account.")
                    return redirect("login")
                else:
                    messages.warning(request, 
                        "Account created, but we couldn't send the verification email. "
                        "Please contact support or try logging in to resend the verification email."
                    )
                    return redirect("login")
                
            except Exception as e:
                # Handle any errors during user creation
                error_msg = str(e)
                print(f"Signup error: {error_msg}")
                
                # Clean up: delete user if creation failed
                if 'user' in locals() and user.pk:
                    # Also delete any created profile
                    UserProfile.objects.filter(user=user).delete()
                    user.delete()
                
                messages.error(request, f"Error creating account: {error_msg}")
                
        else:
            # Form is invalid - show errors
            messages.error(request, "Please correct the errors below.")
            
    else:
        form = SignUpForm()

    context = {
        'form': form,
        'dietary_choices': UserProfile.DIETARY_RESTRICTION_CHOICES,
        'nutrition_goal_choices': UserProfile.NUTRITION_GOAL_CHOICES,
    }
    return render(request, "signup.html", context)

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def profile_view(request):
    """Enhanced profile view with dietary preferences"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    # Get pending email verification
    pending_verification = EmailVerification.objects.filter(user=request.user, is_verified=False).first()
    
    # Handle profile update
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile, user=request.user)
        if form.is_valid():
            # Update user info
            request.user.email = form.cleaned_data['email']
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            
            # Update profile with dietary preferences
            user_profile.phone_number = form.cleaned_data['phone_number']
            user_profile.address = form.cleaned_data.get('address', '')
            user_profile.dietary_restrictions = form.cleaned_data.get('dietary_restrictions', [])
            user_profile.allergies = form.cleaned_data.get('allergies', '')
            user_profile.preferred_food_types = form.cleaned_data.get('preferred_food_types', [])
            user_profile.nutrition_goals = form.cleaned_data.get('nutrition_goals', 'balanced')
            user_profile.health_notes = form.cleaned_data.get('health_notes', '')
            user_profile.latitude = form.cleaned_data.get('latitude')
            user_profile.longitude = form.cleaned_data.get('longitude')
            
            # Handle profile picture
            if 'profile_picture' in request.FILES:
                user_profile.profile_picture = request.FILES['profile_picture']
                
            user_profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user_profile, user=request.user)
    
    # Get user statistics
    is_donor = user_profile.user_type == 'donor'
    is_recipient = user_profile.user_type == 'recipient'
    
    if is_donor:
        user_rating = user_profile.get_average_rating()
        user_rating_count = user_profile.get_rating_count()
        completed_donations = Donation.objects.filter(donor=request.user, status=Donation.COMPLETED).count()
        completed_claims = 0
    else:
        user_rating = user_profile.get_average_rating()
        user_rating_count = user_profile.get_rating_count()
        completed_claims = Donation.objects.filter(recipient=request.user, status=Donation.COMPLETED).count()
        completed_donations = 0
    
    # Get nutrition insights
    nutrition_insights = FoodLoopAI.get_nutrition_insights(request.user)
    
    return render(request, 'profile.html', {
        'form': form,
        'user_profile': user_profile,
        'pending_verification': pending_verification,
        'is_donor': is_donor,
        'is_recipient': is_recipient,
        'user_rating': user_rating,
        'user_rating_count': user_rating_count,
        'completed_donations': completed_donations,
        'completed_claims': completed_claims,
        'nutrition_insights': nutrition_insights,
        'dietary_badges': user_profile.get_dietary_badges()
    })

@login_required
def resend_verification_email(request):
    """Resend email verification"""
    try:
        # Delete any existing unverified tokens
        EmailVerification.objects.filter(user=request.user, is_verified=False).delete()
        
        # Create new verification token
        token = generate_verification_token()
        EmailVerification.objects.create(user=request.user, token=token, created_at=timezone.now())

        verification_url = request.build_absolute_uri(f'/verify/{token}/')
        send_verification_email(request.user, verification_url)

        messages.success(request, "Verification email sent! Please check your inbox.")
    except Exception as e:
        messages.error(request, f"Error sending verification email: {str(e)}")
    
    return redirect('profile')

@login_required
def update_dietary_preferences(request):
    """Quick update for just dietary preferences"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = DietaryPreferencesForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dietary preferences updated successfully!')
            return redirect('profile')
    else:
        form = DietaryPreferencesForm(instance=user_profile)
    
    return render(request, 'profile/dietary_preferences.html', {
        'form': form,
        'user_profile': user_profile
    })

# =============================================================================
# DASHBOARD VIEWS
# =============================================================================

@login_required
@donor_required
def donor_dashboard(request):
    """Enhanced donor dashboard with nutrition analytics"""
    user_profile = UserProfile.objects.get(user=request.user)
    donations = Donation.objects.filter(donor=request.user).order_by('-created_at')
    
    # Update expired donations
    for donation in donations:
        if donation.is_expired() and donation.status != Donation.EXPIRED:
            donation.status = Donation.EXPIRED
            donation.save()
    
    # Statistics with nutrition data
    total_donations = donations.count()
    completed_donations = donations.filter(status=Donation.COMPLETED)
    claimed_donations = donations.filter(status=Donation.CLAIMED).count()
    available_donations = donations.filter(status=Donation.AVAILABLE).count()
    
    # Nutrition impact analytics
    total_calories_donated = sum(d.get_calorie_estimate() for d in completed_donations if d.get_calorie_estimate())
    avg_nutrition_score = sum(d.nutrition_score for d in completed_donations) / len(completed_donations) if completed_donations else 0
    
    # Recent activity
    recent_donations = donations.filter(created_at__gte=timezone.now()-timedelta(days=7))
    
    # Completion rate
    completion_rate = 0
    if total_donations > 0:
        completion_rate = round((completed_donations.count() / total_donations) * 100)
    
    # User rating
    user_rating = user_profile.get_average_rating()
    user_rating_count = user_profile.get_rating_count()
    
    # AI Recommendations for donor
    ai_recommendations = FoodLoopAI.get_donor_recommendations(request.user)
    
    return render(request, 'donor/dashboard.html', {
        'donations': donations,
        'user_profile': user_profile,
        'stats': {
            'total': total_donations,
            'completed': completed_donations.count(),
            'claimed': claimed_donations,
            'available': available_donations,
            'recent_count': recent_donations.count(),
            'total_calories': total_calories_donated,
            'avg_nutrition_score': round(avg_nutrition_score, 1),
        },
        'completion_rate': completion_rate,
        'user_rating': user_rating,
        'user_rating_count': user_rating_count,
        'ai_recommendations': ai_recommendations,
        'nutrition_impact': {
            'co2_saved': round(total_calories_donated * 0.001, 2),  # Rough estimate
            'meals_provided': round(total_calories_donated / 500),  # Assuming 500 cal per meal
        }
    })

@login_required
@recipient_required
def recipient_dashboard(request):
    """Enhanced recipient dashboard with AI recommendations"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get AI-powered recommendations
    ai_recommendations = FoodLoopAI.get_personalized_recommendations(request.user, limit=6)
    nutrition_insights = FoodLoopAI.get_nutrition_insights(request.user)
    
    # Get available donations (filtered by dietary preferences)
    try:
        available_donations = Donation.objects.filter(status=Donation.AVAILABLE).exclude(donor=request.user)
        
        # Filter by dietary compatibility
        compatible_donations = []
        for donation in available_donations:
            if not donation.is_expired():
                # Add match score for display
                donation.match_score = user_profile.get_nutrition_match_score(donation)
                donation.calorie_info = f"~{donation.get_calorie_estimate()} cal" if donation.get_calorie_estimate() else "Calories unknown"
                donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
                compatible_donations.append(donation)
        
        # Sort by match score
        compatible_donations.sort(key=lambda x: x.match_score, reverse=True)
        
        my_donations = Donation.objects.filter(recipient=request.user).order_by('-created_at')
        
        # Statistics
        total_claims = my_donations.count()
        completed_claims = my_donations.filter(status=Donation.COMPLETED).count()
        active_claims = my_donations.filter(status=Donation.CLAIMED).count()
        
        # Nutrition analytics
        completed_donations = my_donations.filter(status=Donation.COMPLETED)
        total_calories_received = sum(d.get_calorie_estimate() for d in completed_donations if d.get_calorie_estimate())
        avg_nutrition_score = sum(d.nutrition_score for d in completed_donations) / len(completed_donations) if completed_donations else 0
        
    except Exception as e:
        print(f"Error getting donations: {e}")
        compatible_donations = []
        my_donations = []
        total_claims = 0
        completed_claims = 0
        active_claims = 0
        total_calories_received = 0
        avg_nutrition_score = 0
    
    return render(request, 'recipient/dashboard.html', {
        'available_donations': compatible_donations[:12],  # Show top 12
        'ai_recommendations': ai_recommendations,
        'my_donations': my_donations,
        'nutrition_insights': nutrition_insights,
        'user_profile': user_profile,
        'stats': {
            'total_claims': total_claims,
            'completed_claims': completed_claims,
            'active_claims': active_claims,
            'total_calories': total_calories_received,
            'avg_nutrition_score': round(avg_nutrition_score, 1),
        },
        'dietary_badges': user_profile.get_dietary_badges()
    })

# =============================================================================
# DONATION MANAGEMENT
# =============================================================================

@login_required
@donor_required
@email_verified_required
def create_donation(request):
    """Enhanced donation creation with nutrition info"""
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user
            donation.status = Donation.AVAILABLE
            
            # Handle dietary tags and nutrition data
            donation.dietary_tags = form.cleaned_data.get('dietary_tags', [])
            donation.estimated_calories = form.cleaned_data.get('estimated_calories')
            donation.ingredients = form.cleaned_data.get('ingredients', '')
            donation.preparation_method = form.cleaned_data.get('preparation_method', 'other')
            
            # Calculate nutrition score
            donation.nutrition_score = donation.calculate_nutrition_score()
            
            # Handle image
            if 'image' in request.FILES:
                donation.image = request.FILES['image']
                
            donation.save()
            
            # Create notification for compatible recipients
            send_dietary_match_notifications(donation)
            
            messages.success(request, 'Donation created successfully! 🥗')
            return redirect('donor_dashboard')
    else:
        form = DonationForm()
    
    return render(request, 'donor/create_donation.html', {
        'form': form,
        'nutrition_tips': get_nutrition_tips()
    })

@login_required
@recipient_required
@email_verified_required
@require_POST
def claim_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    user_profile = UserProfile.objects.get(user=request.user)
    
    if donation.status != Donation.AVAILABLE:
        messages.error(request, 'Donation is not available for claiming.')
        return redirect('recipient_dashboard')
    
    if donation.is_expired():
        donation.status = Donation.EXPIRED
        donation.save()
        messages.error(request, 'This donation has expired.')
        return redirect('recipient_dashboard')
    
    # Check dietary compatibility
    if not donation.is_dietary_compatible(user_profile):
        messages.warning(request, 
            'Note: This donation may not be fully compatible with your dietary preferences. '
            'Please review the ingredients and dietary tags carefully.'
        )
    
    donation.status = Donation.CLAIMED
    donation.recipient = request.user
    donation.save()
    
    # Send email notifications
    send_donation_claimed_notification(donation, request.user)
    
    messages.success(request, 
        f'You have successfully claimed the {donation.food_type} donation! '
        f'Nutrition Score: {donation.nutrition_score}/100 🥗'
    )
    
    return redirect('recipient_dashboard')

@login_required
def donation_detail(request, donation_id):
    """Enhanced donation detail with nutrition info"""
    donation = get_object_or_404(Donation, id=donation_id)
    user_profile = UserProfile.objects.get(user=request.user) if request.user.is_authenticated else None
    
    # Nutrition and dietary info
    nutrition_info = {
        'calories': donation.get_calorie_estimate(),
        'nutrition_score': donation.nutrition_score,
        'dietary_tags': donation.get_dietary_badges(),
        'ingredients': donation.ingredients,
        'preparation': donation.get_preparation_method_display() if donation.preparation_method else 'Unknown'
    }
    
    # Compatibility check for logged-in users
    compatibility = None
    if user_profile:
        compatibility = {
            'is_compatible': donation.is_dietary_compatible(user_profile),
            'match_score': user_profile.get_nutrition_match_score(donation),
            'dietary_issues': list(set(user_profile.dietary_restrictions) - set(donation.dietary_tags))
        }
    
    # Rating information
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
        'nutrition_info': nutrition_info,
        'compatibility': compatibility,
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
    
    # Update nutrition impact analytics
    update_nutrition_impact(donation)
    
    # Send completion notifications
    send_donation_completed_notification(donation)
    
    messages.success(request, 'Donation marked as completed! Thank you for your contribution.')
    return redirect('donor_dashboard')

# =============================================================================
# SEARCH & DISCOVERY
# =============================================================================

def search_donations(request):
    """Enhanced search with nutrition filters"""
    query = request.GET.get('q', '')
    food_type = request.GET.get('food_type', '')
    location = request.GET.get('location', '')
    
    # Nutrition filters
    max_calories = request.GET.get('max_calories')
    min_nutrition_score = request.GET.get('min_nutrition_score')
    dietary_tags = request.GET.getlist('dietary_tags')
    
    donations = Donation.objects.filter(status=Donation.AVAILABLE)
    
    # Basic filters
    if query:
        donations = donations.filter(
            Q(food_type__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(ingredients__icontains=query)
        )
    
    if food_type:
        donations = donations.filter(food_type=food_type)
    
    if location:
        donations = donations.filter(location__icontains=location)
    
    # Nutrition filters
    if max_calories:
        donations = donations.filter(estimated_calories__lte=max_calories)
    
    if min_nutrition_score:
        donations = donations.filter(nutrition_score__gte=min_nutrition_score)
    
    if dietary_tags:
        # Filter by dietary tags (JSON field contains all specified tags)
        for tag in dietary_tags:
            donations = donations.filter(dietary_tags__contains=tag)
    
    # Filter out expired donations and add nutrition info
    valid_donations = []
    for donation in donations:
        if not donation.is_expired():
            donation.calorie_info = f"~{donation.get_calorie_estimate()} cal" if donation.get_calorie_estimate() else "Calories unknown"
            donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
            valid_donations.append(donation)
    
    # Sort by nutrition score (descending)
    valid_donations.sort(key=lambda x: x.nutrition_score, reverse=True)
    
    return render(request, 'search.html', {
        'donations': valid_donations,
        'query': query,
        'food_type': food_type,
        'location': location,
        'max_calories': max_calories,
        'min_nutrition_score': min_nutrition_score,
        'dietary_tags': dietary_tags,
        'food_categories': Donation.FOOD_CATEGORIES,
        'nutrition_search_form': NutritionSearchForm(initial=request.GET)
    })

@login_required
def nutrition_search(request):
    """Advanced nutrition-based search"""
    form = NutritionSearchForm(request.GET or None)
    donations = []
    
    if form.is_valid():
        donations = Donation.objects.filter(status=Donation.AVAILABLE)
        
        # Apply filters
        if form.cleaned_data.get('food_type'):
            donations = donations.filter(food_type=form.cleaned_data['food_type'])
        
        if form.cleaned_data.get('dietary_tags'):
            for tag in form.cleaned_data['dietary_tags']:
                donations = donations.filter(dietary_tags__contains=tag)
        
        if form.cleaned_data.get('max_calories'):
            donations = donations.filter(estimated_calories__lte=form.cleaned_data['max_calories'])
        
        if form.cleaned_data.get('nutrition_score_min'):
            donations = donations.filter(nutrition_score__gte=form.cleaned_data['nutrition_score_min'])
        
        # Filter out expired and add nutrition info
        valid_donations = []
        for donation in donations:
            if not donation.is_expired():
                donation.calorie_info = f"~{donation.get_calorie_estimate()} cal" if donation.get_calorie_estimate() else "Calories unknown"
                donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
                valid_donations.append(donation)
        
        # Sorting
        sort_by = form.cleaned_data.get('sort_by', 'distance')
        if sort_by == 'nutrition_score':
            valid_donations.sort(key=lambda x: x.nutrition_score, reverse=True)
        elif sort_by == 'calories':
            valid_donations.sort(key=lambda x: x.get_calorie_estimate() or 0, reverse=True)
        elif sort_by == 'created_at':
            valid_donations.sort(key=lambda x: x.created_at, reverse=True)
        # Distance sorting would require user location
        
        donations = valid_donations
    
    return render(request, 'search/nutrition_search.html', {
        'form': form,
        'donations': donations,
        'show_advanced_filters': True
    })

# =============================================================================
# NUTRITION ANALYTICS
# =============================================================================

@login_required
def nutrition_analytics(request):
    """Nutrition impact analytics dashboard"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get nutrition impact data
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    if user_profile.user_type == 'donor':
        donations = Donation.objects.filter(
            donor=request.user,
            status=Donation.COMPLETED,
            created_at__gte=last_30_days
        )
    else:
        donations = Donation.objects.filter(
            recipient=request.user,
            status=Donation.COMPLETED,
            created_at__gte=last_30_days
        )
    
    # Calculate metrics
    total_donations = donations.count()
    total_calories = sum(d.get_calorie_estimate() for d in donations if d.get_calorie_estimate())
    avg_nutrition_score = sum(d.nutrition_score for d in donations) / len(donations) if donations else 0
    
    # Food type distribution
    food_type_distribution = {}
    for donation in donations:
        food_type = donation.food_type
        food_type_distribution[food_type] = food_type_distribution.get(food_type, 0) + 1
    
    # Dietary impact
    dietary_impact = {}
    for donation in donations:
        for tag in donation.dietary_tags:
            dietary_impact[tag] = dietary_impact.get(tag, 0) + 1
    
    # Environmental impact estimates
    environmental_impact = {
        'co2_saved_kg': round(total_calories * 0.001, 2),
        'water_saved_liters': round(total_calories * 2, 2),
        'meals_provided': round(total_calories / 500),
        'food_waste_prevented_kg': round(total_calories / 1000, 2)
    }
    
    return render(request, 'analytics/nutrition_analytics.html', {
        'user_profile': user_profile,
        'metrics': {
            'total_donations': total_donations,
            'total_calories': total_calories,
            'avg_nutrition_score': round(avg_nutrition_score, 1),
        },
        'food_type_distribution': food_type_distribution,
        'dietary_impact': dietary_impact,
        'environmental_impact': environmental_impact,
        'time_period': 'last_30_days'
    })

# =============================================================================
# AI RECOMMENDATIONS
# =============================================================================

@login_required
def ai_recommendations(request):
    """Dedicated AI recommendations page"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.user_type == 'recipient':
        recommendations = FoodLoopAI.get_personalized_recommendations(request.user, limit=12)
        nutrition_insights = FoodLoopAI.get_nutrition_insights(request.user)
        
        # Add detailed match information
        for donation in recommendations:
            donation.match_score = user_profile.get_nutrition_match_score(donation)
            donation.match_reason = get_match_reason(user_profile, donation)
    else:
        recommendations = []
        nutrition_insights = ["As a donor, you're making a positive impact! Consider donating nutritious foods."]
    
    return render(request, 'recommendations/ai_recommendations.html', {
        'recommendations': recommendations,
        'nutrition_insights': nutrition_insights,
        'user_profile': user_profile
    })

@login_required
@require_POST
def refresh_recommendations(request):
    """AJAX endpoint to refresh recommendations"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.user_type == 'recipient':
        recommendations = FoodLoopAI.get_personalized_recommendations(request.user, limit=6)
        recommendations_data = []
        
        for donation in recommendations:
            recommendations_data.append({
                'id': donation.id,
                'food_type': donation.food_type,
                'description': donation.description[:100] + '...' if len(donation.description) > 100 else donation.description,
                'nutrition_score': donation.nutrition_score,
                'calories': donation.get_calorie_estimate(),
                'image_url': donation.get_image_url(),
                'match_score': user_profile.get_nutrition_match_score(donation),
                'detail_url': f'/donation/{donation.id}/'
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations_data
        })
    
    return JsonResponse({'success': False, 'error': 'Only for recipients'})

# =============================================================================
# MAP VIEWS
# =============================================================================

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
                
                # Add nutrition info
                donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
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
                            donation.nutrition_badge = "🥗" if donation.nutrition_score > 80 else "🍎" if donation.nutrition_score > 60 else "🍽️"
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

# =============================================================================
# RATING SYSTEM
# =============================================================================

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
            
            # Send rating notification - pass the user who submitted the rating
            send_rating_notification(rating, request.user)
            
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

# =============================================================================
# NOTIFICATION SYSTEM
# =============================================================================

@login_required
def notification_list(request):
    """Get user's notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request - return JSON
        from django.utils.timesince import timesince
        data = [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'related_url': n.related_url,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'time_ago': timesince(n.created_at)
        } for n in notifications]
        
        return JsonResponse({'notifications': data})
    
    return render(request, 'notifications/list.html', {'notifications': notifications})

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    return JsonResponse({'success': True})

@login_required
def notification_count(request):
    """Get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return JsonResponse({'count': count})

# =============================================================================
# EMAIL VERIFICATION
# =============================================================================

def verify_email(request, token):
    try:
        vtoken = EmailVerification.objects.get(token=token)
        user = vtoken.user
        user.is_active = True
        user.save()
        vtoken.delete()

        messages.success(request, "✅ Email verified! You can now log in.")
        return redirect("login")

    except EmailVerification.DoesNotExist:
        return HttpResponse("❌ Invalid or expired verification link.", status=400)

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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def send_dietary_match_notifications(donation):
    """Send notifications to users with matching dietary preferences"""
    try:
        compatible_users = UserProfile.objects.filter(
            user_type='recipient',
            dietary_restrictions__overlap=donation.dietary_tags
        )
        
        for user_profile in compatible_users[:10]:  # Limit to first 10
            if donation.is_dietary_compatible(user_profile):
                Notification.objects.create(
                    user=user_profile.user,
                    notification_type='dietary_match',
                    title='New Donation Matches Your Preferences!',
                    message=f'A new {donation.food_type} donation matches your dietary preferences.',
                    related_url=f'/donation/{donation.id}/'
                )
    except Exception as e:
        print(f"Dietary match notification error: {e}")

def get_nutrition_tips():
    """Get nutrition tips for donation creation"""
    return [
        "Add dietary tags to help recipients with restrictions find your donation",
        "Estimate calories to help recipients track their nutrition",
        "List ingredients to help people with allergies",
        "Fresh produce typically has higher nutrition scores",
        "Consider donating a variety of food types for balanced nutrition"
    ]

def get_match_reason(user_profile, donation):
    """Get reason why donation was recommended"""
    reasons = []
    
    if donation.food_type in user_profile.preferred_food_types:
        reasons.append("matches your preferred food types")
    
    if set(user_profile.dietary_restrictions).issubset(set(donation.dietary_tags)):
        reasons.append("compatible with your dietary restrictions")
    
    if donation.nutrition_score > 80:
        reasons.append("high nutrition score")
    elif donation.nutrition_score > 60:
        reasons.append("good nutrition score")
    
    if user_profile.nutrition_goals == 'weight_loss' and donation.nutrition_score > 70:
        reasons.append("supports your weight loss goals")
    elif user_profile.nutrition_goals == 'muscle_gain' and donation.food_type in ['protein', 'dairy']:
        reasons.append("supports your muscle gain goals")
    
    return ", ".join(reasons) if reasons else "personalized match"

def update_nutrition_impact(donation):
    """Update nutrition impact analytics when donation is completed"""
    try:
        today = timezone.now().date()
        
        # Update donor impact
        donor_impact, created = NutritionImpact.objects.get_or_create(
            user=donation.donor,
            date=today,
            defaults={
                'donations_made': 0,
                'total_calories': 0,
            }
        )
        donor_impact.donations_made += 1
        donor_impact.total_calories += donation.get_calorie_estimate() or 0
        donor_impact.save()
        
        # Update recipient impact
        if donation.recipient:
            recipient_impact, created = NutritionImpact.objects.get_or_create(
                user=donation.recipient,
                date=today,
                defaults={
                    'donations_received': 0,
                    'total_calories': 0,
                }
            )
            recipient_impact.donations_received += 1
            recipient_impact.total_calories += donation.get_calorie_estimate() or 0
            recipient_impact.save()
            
    except Exception as e:
        print(f"Nutrition impact update error: {e}")

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

def get_user_type(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.user_type
    except UserProfile.DoesNotExist:
        return None

# =============================================================================
# EMAIL NOTIFICATION FUNCTIONS
# =============================================================================

def send_notification_email(user, subject, template_name, context):
    """Send HTML email notification to user"""
    try:
        html_message = render_to_string(f'emails/{template_name}', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"📧 Email sent to {user.email}: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email sending failed to {user.email}: {e}")
        return False

def send_verification_email(user, verification_url):
    """Send email verification with corrected template path"""
    try:
        subject = "Verify Your Email - FoodLoop"
        
        # Use the correct template path (without the extra emails/ prefix)
        html_message = render_to_string('emails/verification.html', {
            'user': user,
            'verification_url': verification_url
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Verification email sent to {user.email}")
        return True
    except Exception as e:
        print(f"❌ Verification email failed: {e}")
        return False

def send_donation_claimed_notification(donation, claimed_by):
    """Send email to donor when donation is claimed"""
    subject = "🎉 Your Donation Has Been Claimed!"
    context = {
        'donor': donation.donor,
        'recipient': claimed_by,
        'donation': donation,
        'claim_date': timezone.now(),
        'donation_url': f"{settings.EMAIL_VERIFICATION_URL}/donation/{donation.id}/"
    }
    
    send_notification_email(donation.donor, subject, 'donation_claimed.html', context)
    
    recipient_subject = "✅ Donation Claim Confirmed"
    recipient_context = {
        'recipient': claimed_by,
        'donation': donation,
        'donor': donation.donor,
        'donation_url': f"{settings.EMAIL_VERIFICATION_URL}/donation/{donation.id}/"
    }
    
    send_notification_email(claimed_by, recipient_subject, 'emails/donation_claim_confirmation.html', recipient_context)

def send_donation_completed_notification(donation):
    """Send email when donation is completed"""
    if donation.recipient:
        subject = "✨ Donation Successfully Completed!"
        context = {
            'recipient': donation.recipient,
            'donation': donation,
            'completion_date': timezone.now(),
            'donor': donation.donor
        }
        
        send_notification_email(donation.recipient, subject, 'emails/donation_completed.html', context)
    
    donor_subject = "🏆 Donation Marked as Completed"
    donor_context = {
        'donor': donation.donor,
        'donation': donation,
        'recipient': donation.recipient,
        'completion_date': timezone.now()
    }
    
    send_notification_email(donation.donor, donor_subject, 'emails/donation_completed_donor.html', donor_context)

def send_rating_notification(rating, rater_user):
    """Send email when someone rates you"""
    if rater_user == rating.donor:
        rated_user = rating.recipient
    else:
        rated_user = rating.donor
    
    subject = "⭐ You Received a New Rating!"
    context = {
        'rated_user': rated_user,
        'rater_user': rater_user,
        'rating': rating,
        'donation': rating.donation,
        'rating_url': f"{settings.EMAIL_VERIFICATION_URL}/donation/{rating.donation.id}/"
    }
    
    send_notification_email(rated_user, subject, 'emails/rating_received.html', context)

def send_welcome_email(user):
    """Send welcome email after verification"""
    subject = "🎊 Welcome to FoodLoop!"
    context = {
        'user': user,
        'login_url': f"{settings.EMAIL_VERIFICATION_URL}/login/"
    }
    
    send_notification_email(user, subject, 'emails/welcome.html', context)