from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from core.models import Donation, Rating, Notification, UserProfile

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            profile = user.profile
            token['role'] = profile.user_type
            token['email_verified'] = profile.email_verified
        except Exception:
            token['role'] = None
            token['email_verified'] = False
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    class Meta:
        model = UserProfile
        fields = [
            'user_type', 'phone_number', 'location', 'profile_picture',
            'bio', 'dietary_restrictions', 'email_verified', 
            'average_rating', 'total_ratings'
        ]
        read_only_fields = ['average_rating', 'total_ratings', 'email_verified']


class UserSerializer(serializers.ModelSerializer):
    """User serializer with profile data"""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'profile', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'date_joined']


class DonorSerializer(serializers.ModelSerializer):
    """Minimal donor info for donation listings"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    user_type = serializers.CharField(source='profile.user_type', read_only=True)
    average_rating = serializers.DecimalField(
        source='profile.average_rating', 
        max_digits=3, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'user_type', 'average_rating']


class DonationSerializer(serializers.ModelSerializer):
    """Donation serializer"""
    donor = DonorSerializer(read_only=True)
    recipient = DonorSerializer(read_only=True)
    time_until_expiry = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    can_be_claimed = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Donation
        fields = [
            'id', 'donor', 'recipient', 'title', 'description', 
            'food_category', 'quantity', 'status', 'expiry_datetime',
            'pickup_start', 'pickup_end', 'pickup_location', 'image',
            'image_url', 'dietary_tags', 'estimated_calories', 
            'nutrition_score', 'ingredients_list', 'allergen_info',
            'created_at', 'updated_at', 'claimed_at', 'completed_at',
            'time_until_expiry', 'is_expired', 'can_be_claimed'
        ]
        read_only_fields = [
            'id', 'donor', 'recipient', 'status', 'created_at', 
            'updated_at', 'claimed_at', 'completed_at', 'nutrition_score'
        ]
    
    def get_time_until_expiry(self, obj):
        """Get human-readable time until expiry"""
        return obj.get_time_until_expiry()
    
    def get_is_expired(self, obj):
        """Check if donation is expired"""
        return obj.is_expired()
    
    def get_can_be_claimed(self, obj):
        """Check if donation can be claimed"""
        return (
            obj.status == Donation.AVAILABLE and 
            not obj.is_expired() and 
            not obj.is_pickup_overdue()
        )
    
    def get_image_url(self, obj):
        """Get image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class RatingSerializer(serializers.ModelSerializer):
    """Rating serializer"""
    rating_user = DonorSerializer(read_only=True)
    rated_user = DonorSerializer(read_only=True)
    donation_title = serializers.CharField(source='donation.title', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'rated_user', 'rating_user', 'donation', 
            'donation_title', 'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'rating_user', 'created_at']
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate(self, data):
        """Validate that user can rate this donation"""
        request = self.context.get('request')
        donation = data.get('donation')
        
        if not donation:
            raise serializers.ValidationError("Donation is required")
        
        if donation.status != Donation.COMPLETED:
            raise serializers.ValidationError("Can only rate completed donations")
        
        # Check if user is part of this donation
        if request.user not in [donation.donor, donation.recipient]:
            raise serializers.ValidationError(
                "You can only rate donations you were involved in"
            )
        
        # Check for duplicate rating
        if Rating.objects.filter(rating_user=request.user, donation=donation).exists():
            raise serializers.ValidationError(
                "You have already rated this donation"
            )
        
        return data


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer"""
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 
            'is_read', 'read_at', 'related_url', 'created_at',
            'time_since'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']
    
    def get_time_since(self, obj):
        """Get human-readable time since notification"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)