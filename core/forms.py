from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.utils import timezone
from .models import UserProfile, Donation, Rating
from .validators import validate_phone_number

class SignUpForm(UserCreationForm):
    user_type = forms.ChoiceField(choices=UserProfile.USER_TYPE_CHOICES, widget=forms.RadioSelect)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False, validators=[validate_phone_number])
    address = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            validate_phone_number(phone_number)
        return phone_number

class DonationForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput, 
                           help_text="Upload a photo of your donation")
    
    class Meta:
        model = Donation
        fields = ('food_type', 'quantity', 'description', 'image', 
                 'expiry_date', 'pickup_time', 'pickup_deadline', 'location')
        widgets = {
            'pickup_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'pickup_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'food_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
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

class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone_number = forms.CharField(max_length=15, required=False, validators=[validate_phone_number])
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput)
    latitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
    )
    
    class Meta:
        model = UserProfile
        fields = ('profile_picture', 'phone_number', 'address', 'latitude', 'longitude')
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

        # Add CSS classes for better styling
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
