from django.db import OperationalError, ProgrammingError
from django.contrib.auth.models import User
from .models import UserProfile, Rating, Donation

def user_profile(request):
    context = {
        'user_profile': None,
        'is_donor': False,
        'is_recipient': False,
    }
    
    if not request.user.is_authenticated:
        return context
    
    try:
        from .models import UserProfile, Rating
        
        profile = UserProfile.objects.get(user=request.user)
        context['user_profile'] = profile
        context['is_donor'] = profile.user_type == 'donor'
        context['is_recipient'] = profile.user_type == 'recipient'
        
        # Add rating statistics
        context['user_rating'] = profile.get_average_rating()
        context['user_rating_count'] = profile.get_rating_count()
        
    except UserProfile.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error in context processor: {e}")
    
    return context