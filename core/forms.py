from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.utils import timezone
from .models import UserProfile, Donation, Rating
from .validators import validate_phone_number

class SignUpForm(UserCreationForm):
    USER_TYPE_CHOICES = [
        ('donor', 'Food Donor'),
        ('recipient', 'Food Recipient'),
    ]
    
    # Dietary choices for the form
    DIETARY_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-Free'),
        ('dairy_free', 'Dairy-Free'),
        ('nut_free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('low_carb', 'Low-Carb'),
        ('diabetic', 'Diabetic-Friendly'),
    ]
    
    # Nutrition goal choices
    NUTRITION_GOAL_CHOICES = [
        ('', 'Select your primary nutrition goal...'),
        ('weight_loss', 'Weight Loss'),
        ('weight_gain', 'Weight Gain'),
        ('maintenance', 'Weight Maintenance'),
        ('muscle_building', 'Muscle Building'),
        ('healthy_eating', 'Healthy Eating'),
        ('medical_condition', 'Medical Condition'),
        ('other', 'Other'),
    ]
    
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'})
    )
    
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your first name'})
    )
    
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your last name'})
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254 712 345 678'})
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Your general location'})
    )
    
    dietary_restrictions = forms.MultipleChoiceField(
        required=False,
        choices=DIETARY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List any food allergies...'})
    )
    
    nutrition_goals = forms.ChoiceField(
        required=False,
        choices=NUTRITION_GOAL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the terms and conditions'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to username and password fields
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Create a strong password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Repeat your password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Check if profile already exists before creating
            try:
                user_profile = UserProfile.objects.get(user=user)
                # Update existing profile
                user_profile.user_type = self.cleaned_data['user_type']
                user_profile.phone_number = self.cleaned_data.get('phone_number', '')
                user_profile.address = self.cleaned_data.get('address', '')
                user_profile.allergies = self.cleaned_data.get('allergies', '')
                user_profile.nutrition_goals = self.cleaned_data.get('nutrition_goals', '')
            except UserProfile.DoesNotExist:
                # Create new profile only if it doesn't exist
                user_profile = UserProfile.objects.create(
                    user=user,
                    user_type=self.cleaned_data['user_type'],
                    phone_number=self.cleaned_data.get('phone_number', ''),
                    address=self.cleaned_data.get('address', ''),
                    allergies=self.cleaned_data.get('allergies', ''),
                    nutrition_goals=self.cleaned_data.get('nutrition_goals', '')
                )
            
            # Handle dietary restrictions
            dietary_restrictions = self.cleaned_data.get('dietary_restrictions', [])
            if dietary_restrictions:
                user_profile.dietary_restrictions = dietary_restrictions
                user_profile.save()
        
        return user

class DonationForm(forms.ModelForm):
    # Dietary tags for the donation
    DIETARY_TAG_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-Free'),
        ('dairy_free', 'Dairy-Free'),
        ('nut_free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('low_carb', 'Low-Carb'),
        ('diabetic', 'Diabetic-Friendly'),
    ]
    
    image = forms.ImageField(
        required=False, 
        widget=forms.FileInput,
        help_text="Upload a photo of your donation (max 5MB)"
    )
    
    # NEW: Nutrition & Dietary Fields
    dietary_tags = forms.MultipleChoiceField(
        choices=DIETARY_TAG_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select applicable dietary tags for this donation"
    )
    
    estimated_calories = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500'}),
        help_text="Estimated total calories (optional)"
    )
    
    ingredients = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'List main ingredients...'}),
        help_text="Main ingredients (optional)"
    )
    
    preparation_method = forms.ChoiceField(
        choices=[
            ('', 'Select preparation method'),
            ('raw', 'Raw'),
            ('cooked', 'Cooked'),
            ('baked', 'Baked'),
            ('fried', 'Fried'),
            ('other', 'Other')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Donation
        fields = [
            'food_type', 'quantity', 'description', 'image',
            'expiry_date', 'pickup_time', 'pickup_deadline', 'location',
            'dietary_tags', 'estimated_calories', 'ingredients', 'preparation_method'
        ]
        widgets = {
            'pickup_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'pickup_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Describe the food donation...'}),
            'food_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2 kg, 5 pieces, 1 container'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter pickup location...'}),
        }
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date <= timezone.now():
            raise forms.ValidationError("Expiry date must be in the future.")
        return expiry_date
    
    def clean_pickup_deadline(self):
        pickup_deadline = self.cleaned_data.get('pickup_deadline')
        if pickup_deadline and pickup_deadline <= timezone.now():
            raise forms.ValidationError("Pickup deadline must be in the future.")
        return pickup_deadline
    
    def clean_estimated_calories(self):
        calories = self.cleaned_data.get('estimated_calories')
        if calories and calories > 100000:  # Reasonable upper limit
            raise forms.ValidationError("Calorie estimate seems too high. Please verify.")
        return calories


class ProfileUpdateForm(forms.ModelForm):
    # Dietary preferences
    DIETARY_RESTRICTION_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-Free'),
        ('dairy_free', 'Dairy-Free'),
        ('nut_free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('low_carb', 'Low-Carb'),
        ('diabetic', 'Diabetic-Friendly'),
    ]
    
    PREFERRED_FOOD_CHOICES = [
        ('vegetables', 'Vegetables'),
        ('fruits', 'Fruits'),
        ('dairy', 'Dairy'),
        ('bakery', 'Bakery'),
        ('cooked', 'Cooked Food'),
        ('grains', 'Grains & Cereals'),
        ('protein', 'Proteins'),
        ('beverages', 'Beverages'),
    ]
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone_number = forms.CharField(max_length=15, required=False, validators=[validate_phone_number])
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput)
    
    # NEW: Dietary Preference Fields
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_RESTRICTION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select your dietary restrictions"
    )
    
    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'e.g., peanuts, shellfish, eggs...'}),
        help_text="List any food allergies (comma separated)"
    )
    
    preferred_food_types = forms.MultipleChoiceField(
        choices=PREFERRED_FOOD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select your preferred food types"
    )
    
    nutrition_goals = forms.ChoiceField(
        choices=UserProfile.NUTRITION_GOAL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select your primary nutrition goal"
    )
    
    health_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Any additional health notes...'}),
        help_text="Additional health or nutrition information"
    )
    
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'phone_number', 'address', 
            'dietary_restrictions', 'allergies', 'preferred_food_types',
            'nutrition_goals', 'health_notes', 'latitude', 'longitude'
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['email'].initial = self.user.email
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
        
        # Add CSS classes for styling
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Start typing your address...',
            'id': 'address-input'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email
    
    def save(self, commit=True):
        # Save user profile first
        profile = super().save(commit=False)
        
        # Update user info
        if self.user:
            self.user.email = self.cleaned_data['email']
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        
        return profile


class DietaryPreferencesForm(forms.ModelForm):
    """Simplified form for just dietary preferences"""
    DIETARY_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-Free'),
        ('dairy_free', 'Dairy-Free'),
        ('nut_free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
    ]
    
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dietary-checkboxes'}),
        required=False,
        label="Dietary Restrictions"
    )
    
    allergies = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'List any food allergies separated by commas...'
        }),
        required=False,
        label="Food Allergies"
    )
    
    nutrition_goals = forms.ChoiceField(
        choices=UserProfile.NUTRITION_GOAL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Nutrition Goals"
    )
    
    class Meta:
        model = UserProfile
        fields = ['dietary_restrictions', 'allergies', 'nutrition_goals']


class RatingForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'rating-stars'}),
        label='Your Rating'
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Share your experience (optional)'
        }),
        required=False,
        max_length=500,
        label='Comments'
    )
    
    class Meta:
        model = Rating
        fields = ('rating', 'comment')
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        return int(rating)


class NutritionSearchForm(forms.Form):
    """Form for nutrition-based donation search"""
    food_type = forms.ChoiceField(
        choices=[('', 'All Food Types')] + Donation.FOOD_CATEGORIES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    dietary_tags = forms.MultipleChoiceField(
        choices=DonationForm.DIETARY_TAG_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Dietary Requirements"
    )
    
    max_calories = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max calories'}),
        label="Maximum Calories"
    )
    
    nutrition_score_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min nutrition score'}),
        label="Minimum Nutrition Score"
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('distance', 'Distance'),
            ('nutrition_score', 'Nutrition Score'),
            ('calories', 'Calories'),
            ('created_at', 'Newest First')
        ],
        required=False,
        initial='distance',
        widget=forms.Select(attrs={'class': 'form-control'})
    )