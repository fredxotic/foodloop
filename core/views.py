# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.models import User
from .models import UserProfile, Donation
from django.contrib import messages
from .forms import SignUpForm, DonationForm

# core/views.py - Updated home function
def home(request):
    if request.user.is_authenticated:
        # Get user profile to check user type
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.user_type == UserProfile.DONOR:
                return redirect('donor_dashboard')
            else:
                return redirect('recipient_dashboard')
        except UserProfile.DoesNotExist:
            # If user profile doesn't exist, stay on home page
            pass
    return render(request, 'home.html')

# core/views.py - Updated login_view function
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Get user profile to determine dashboard
            try:
                user_profile = UserProfile.objects.get(user=user)
                if user_profile.user_type == UserProfile.DONOR:
                    return redirect('donor_dashboard')
                else:
                    return redirect('recipient_dashboard')
            except UserProfile.DoesNotExist:
                # If no profile exists, redirect to home
                return redirect('home')
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Get the selected user type from the form
            user_type = request.POST.get('user_type')
            
            # Create or update user profile with the CORRECT type
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.user_type = user_type  # This is the key fix!
            user_profile.phone_number = request.POST.get('phone_number', '')
            user_profile.address = request.POST.get('address', '')
            user_profile.save()
            
            login(request, user)
            
            # Redirect based on the actual user type
            if user_type == 'donor':  # Use string comparison
                return redirect('donor_dashboard')
            else:
                return redirect('recipient_dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def donor_dashboard(request):
    # Check if user has donor profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != UserProfile.DONOR:
            return redirect('home')
    except UserProfile.DoesNotExist:
        return redirect('home')
    
    donations = Donation.objects.filter(donor=request.user).order_by('-created_at')
    return render(request, 'donor/dashboard.html', {'donations': donations})

@login_required
def recipient_dashboard(request):
    # Check if user has recipient profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != UserProfile.RECIPIENT:
            return redirect('home')
    except UserProfile.DoesNotExist:
        return redirect('home')
    
    available_donations = Donation.objects.filter(status=Donation.AVAILABLE).exclude(donor=request.user)
    my_donations = Donation.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'recipient/dashboard.html', {
        'available_donations': available_donations,
        'my_donations': my_donations
    })

@login_required
def create_donation(request):
    # Check if user has donor profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != UserProfile.DONOR:
            return redirect('home')
    except UserProfile.DoesNotExist:
        return redirect('home')
    
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user
            donation.status = Donation.AVAILABLE
            donation.save()
            return redirect('donor_dashboard')
    else:
        form = DonationForm()
    
    return render(request, 'donor/create_donation.html', {'form': form})

# core/views.py - Update the claim_donation view
@login_required
@require_POST
def claim_donation(request, donation_id):
    # Check if user has recipient profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != UserProfile.RECIPIENT:
            messages.error(request, 'Only recipients can claim donations')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Only recipients can claim donations')
        return redirect('home')
    
    donation = get_object_or_404(Donation, id=donation_id)
    
    if donation.status != Donation.AVAILABLE:
        messages.error(request, 'Donation is not available')
        return redirect('recipient_dashboard')
    
    donation.status = Donation.CLAIMED
    donation.recipient = request.user
    donation.save()
    
    messages.success(request, f'You have successfully claimed the {donation.food_type} donation!')
    return redirect('recipient_dashboard')

@login_required
def donation_detail(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'recipient/donation_detail.html', {'donation': donation})

# Helper function to get user type
def get_user_type(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.user_type
    except UserProfile.DoesNotExist:
        return None