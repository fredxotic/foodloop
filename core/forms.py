"""
Optimized Forms for FoodLoop - FIXED VERSION
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, Donation, Rating
from .validators import validate_phone_number, validate_coordinates


class SignUpForm(UserCreationForm):
    """
    Enhanced user registration form with profile fields
    """
    # Define dietary restriction choices here
    DIETARY_RESTRICTION_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('organic', 'Organic'),
    ]
    
    # Basic fields
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    # Profile fields
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+254712345678'
        })
    )
    
    # Location fields
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your address',
            'id': 'id_address'
        })
    )
    latitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    # Dietary preferences (for recipients)
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_RESTRICTION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
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
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def clean(self):
        """Validate coordinates if address is provided"""
        cleaned_data = super().clean()
        address = cleaned_data.get('address')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if address and (not latitude or not longitude):
            raise ValidationError(
                'Please select your location from the map or address suggestions.'
            )
        
        if latitude or longitude:
            validate_coordinates(latitude, longitude)
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save user with email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
        
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile
    """
    DIETARY_RESTRICTION_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('organic', 'Organic'),
    ]
    
    # User fields
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
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    # Profile fields
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_RESTRICTION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'location', 'latitude', 'longitude',
            'profile_picture', 'bio', 'dietary_restrictions'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your location',
                'id': 'id_location'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
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
        if self.user and User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        """Save profile and update user fields"""
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
    """
    Simplified form for managing dietary preferences
    """
    DIETARY_RESTRICTION_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('organic', 'Organic'),
    ]
    
    dietary_restrictions = forms.MultipleChoiceField(
        choices=DIETARY_RESTRICTION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['dietary_restrictions']


class DonationForm(forms.ModelForm):
    """
    Form for creating and editing food donations
    """
    DIETARY_TAG_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('organic', 'Organic'),
    ]
    
    dietary_tags = forms.MultipleChoiceField(
        choices=DIETARY_TAG_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select all dietary preferences this food meets'
    )
    
    class Meta:
        model = Donation
        fields = [
            'title', 'description', 'food_category', 'quantity',
            'expiry_datetime', 'pickup_start', 'pickup_end',
            'pickup_location', 'latitude', 'longitude',
            'image', 'dietary_tags', 'estimated_calories',
            'ingredients_list', 'allergen_info'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fresh Vegetables, Prepared Meals'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the food items in detail...'
            }),
            'food_category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Number of servings/items'
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
                'placeholder': 'Where can this be picked up?',
                'id': 'id_pickup_location'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'estimated_calories': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Estimated calories (optional)'
            }),
            'ingredients_list': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List main ingredients (optional)'
            }),
            'allergen_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any allergens? (e.g., contains nuts, dairy)'
            }),
        }
    
    def clean(self):
        """Validate donation data"""
        cleaned_data = super().clean()
        
        expiry = cleaned_data.get('expiry_datetime')
        pickup_start = cleaned_data.get('pickup_start')
        pickup_end = cleaned_data.get('pickup_end')
        
        # Validate pickup times
        if pickup_start and pickup_end:
            if pickup_end <= pickup_start:
                raise ValidationError({
                    'pickup_end': 'Pickup end time must be after pickup start time.'
                })
        
        # Validate expiry vs pickup
        if expiry and pickup_end:
            if pickup_end > expiry:
                raise ValidationError({
                    'pickup_end': 'Pickup must be completed before food expires.'
                })
        
        # Validate coordinates
        pickup_location = cleaned_data.get('pickup_location')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if pickup_location and (not latitude or not longitude):
            raise ValidationError(
                'Please select your pickup location from the map or address suggestions.'
            )
        
        if latitude or longitude:
            validate_coordinates(latitude, longitude)
        
        return cleaned_data


class RatingForm(forms.ModelForm):
    """
    Form for rating users after donation completion
    """
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience (optional)...',
                'maxlength': '500'
            }),
        }
    
    def clean_rating(self):
        """Validate rating value"""
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise ValidationError('Rating must be between 1 and 5 stars.')
        return rating


class NutritionSearchForm(forms.Form):
    """
    Form for searching donations with nutrition filters
    """
    DIETARY_TAG_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten-free', 'Gluten-Free'),
        ('dairy-free', 'Dairy-Free'),
        ('nut-free', 'Nut-Free'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('organic', 'Organic'),
    ]
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search donations...'
        })
    )
    
    food_category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + list(Donation.FOOD_CATEGORY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    max_calories = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max calories'
        })
    )
    
    min_nutrition_score = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min nutrition score (0-100)'
        })
    )
    
    dietary_tags = forms.MultipleChoiceField(
        required=False,
        choices=DIETARY_TAG_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    def clean_min_nutrition_score(self):
        """Validate nutrition score range"""
        score = self.cleaned_data.get('min_nutrition_score')
        if score is not None and (score < 0 or score > 100):
            raise ValidationError('Nutrition score must be between 0 and 100.')
        return score