# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Donation

class SignUpForm(UserCreationForm):
    user_type = forms.ChoiceField(choices=UserProfile.USER_TYPE_CHOICES, widget=forms.RadioSelect)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ('food_type', 'quantity', 'description', 'pickup_time', 'location')
        widgets = {
            'pickup_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }