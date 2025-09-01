# core/context_processors.py
from .models import UserProfile

def user_profile(request):
    if request.user.is_authenticated:
        try:
            return {'user_profile': UserProfile.objects.get(user=request.user)}
        except UserProfile.DoesNotExist:
            return {'user_profile': None}
    return {'user_profile': None}