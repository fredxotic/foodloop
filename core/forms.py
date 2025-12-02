"""
Optimized Forms for FoodLoop - Phase 1 Complete
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, Donation, Rating
from .validators import validate_phone_number


class SignUpForm(UserCreationForm):
    """Enhanced user registration form with profile fields"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+254712345678'
        })
    )
    location = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Westlands, Nairobi'
        }),
        help_text="City or neighborhood"
    )
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    
    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'location', 'bio', 'profile_picture'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Westlands, Nairobi'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        """Validate email uniqueness (excluding current user)"""
        email = self.cleaned_data.get('email')
        if self.user:
            if User.objects.filter(email=email).exclude(id=self.user.id).exists():
                raise ValidationError("This email is already in use.")
        return email
    
    def save(self, commit=True):
        """Save both User and UserProfile"""
        profile = super().save(commit=False)
        
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            
            if commit:
                self.user.save()
                profile.save()
        
        return profile


class DietaryPreferencesForm(forms.ModelForm):
    """Form for managing dietary preferences"""
    
    DIETARY_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
    ]
    
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['dietary_restrictions']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert JSON list to choices format
        if self.instance and self.instance.dietary_restrictions:
            self.fields['dietary_restrictions'].initial = self.instance.dietary_restrictions


class DonationForm(forms.ModelForm):
    """Form for creating/editing donations - SIMPLIFIED (No GPS)"""
    
    DIETARY_TAG_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
    ]
    
    dietary_tags = forms.MultipleChoiceField(
        choices=DIETARY_TAG_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Select all that apply"
    )
    
    class Meta:
        model = Donation
        fields = [
            'title', 'food_category', 'description', 'quantity',
            'expiry_datetime', 'pickup_start', 'pickup_end',
            'pickup_location', 'image', 'dietary_tags',
            'estimated_calories', 'ingredients_list', 'allergen_info'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fresh Apples'
            }),
            'food_category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the food item...'
            }),
            'quantity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 5kg, 10 pieces'
            }),
            'expiry_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'pickup_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'pickup_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'pickup_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full address or meeting point'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'estimated_calories': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional'
            }),
            'ingredients_list': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., Flour, Sugar, Eggs (Optional)'
            }),
            'allergen_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'e.g., Contains nuts, dairy (Optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set minimum datetime to now
        now = timezone.now()
        min_datetime = now.strftime('%Y-%m-%dT%H:%M')
        
        self.fields['expiry_datetime'].widget.attrs['min'] = min_datetime
        self.fields['pickup_start'].widget.attrs['min'] = min_datetime
        self.fields['pickup_end'].widget.attrs['min'] = min_datetime
        
        # Convert existing dietary_tags to initial value
        if self.instance and self.instance.dietary_tags:
            self.fields['dietary_tags'].initial = self.instance.dietary_tags
    
    def clean(self):
        """Validate datetime logic"""
        cleaned_data = super().clean()
        expiry = cleaned_data.get('expiry_datetime')
        pickup_start = cleaned_data.get('pickup_start')
        pickup_end = cleaned_data.get('pickup_end')
        
        now = timezone.now()
        
        # Validate expiry is in future
        if expiry and expiry <= now:
            raise ValidationError("Expiry date must be in the future.")
        
        # Validate pickup times
        if pickup_start and pickup_start <= now:
            raise ValidationError("Pickup start time must be in the future.")
        
        if pickup_end and pickup_start and pickup_end <= pickup_start:
            raise ValidationError("Pickup end time must be after start time.")
        
        # Validate pickup is before expiry
        if expiry and pickup_end and pickup_end >= expiry:
            raise ValidationError("Pickup must be completed before expiry.")
        
        return cleaned_data
    
    def clean_estimated_calories(self):
        """Ensure calories are reasonable"""
        calories = self.cleaned_data.get('estimated_calories')
        if calories and (calories < 0 or calories > 10000):
            raise ValidationError("Calories must be between 0 and 10,000.")
        return calories


class RatingForm(forms.ModelForm):
    """Form for rating users after donation completion"""
    
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (5, '⭐⭐⭐⭐⭐ Excellent'),
                (4, '⭐⭐⭐⭐ Good'),
                (3, '⭐⭐⭐ Average'),
                (2, '⭐⭐ Poor'),
                (1, '⭐ Very Poor'),
            ], attrs={
                'class': 'form-check-input'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience... (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.donation = kwargs.pop('donation', None)
        self.rating_user = kwargs.pop('rating_user', None)
        super().__init__(*args, **kwargs)
    
    def clean_rating(self):
        """Validate rating value"""
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1 or rating > 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return rating
    
    def save(self, commit=True):
        """Set donation and users before saving"""
        rating = super().save(commit=False)
        
        if self.donation and self.rating_user:
            rating.donation = self.donation
            rating.rating_user = self.rating_user
            
            # Determine who is being rated
            if self.rating_user == self.donation.donor:
                rating.rated_user = self.donation.recipient
            else:
                rating.rated_user = self.donation.donor
            
            if commit:
                rating.save()
        
        return rating


class NutritionSearchForm(forms.Form):
    """Form for searching donations with nutrition filters"""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for food...'
        }),
        label='Search'
    )
    food_category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + Donation.FOOD_CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Category'
    )
    max_calories = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max calories'
        }),
        label='Max Calories'
    )
    min_nutrition_score = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min score (0-100)'
        }),
        label='Min Nutrition Score'
    )
    dietary_tags = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('vegetarian', 'Vegetarian'),
            ('vegan', 'Vegan'),
            ('halal', 'Halal'),
            ('kosher', 'Kosher'),
            ('gluten-free', 'Gluten-Free'),
            ('dairy-free', 'Dairy-Free'),
            ('nut-free', 'Nut-Free'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Dietary Tags'
    )