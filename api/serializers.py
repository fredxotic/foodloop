from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Donation, Rating, Notification, UserProfile
from core.validators import validate_phone_number

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer with additional user data"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            profile = user.profile
            token['role'] = profile.user_type
            token['is_verified'] = profile.email_verified
        except Exception:
            token['role'] = None
        
        token['email'] = user.email
        token['full_name'] = user.get_full_name()
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            profile = self.user.profile
            role = profile.user_type
            is_verified = profile.email_verified
        except Exception:
            role = None
            is_verified = False

        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'role': role,
            'full_name': self.user.get_full_name(),
            'is_verified': is_verified,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with Profile data flattened"""
    full_name = serializers.SerializerMethodField()
    role = serializers.CharField(source='profile.user_type', read_only=True)
    phone_number = serializers.CharField(source='profile.phone_number', required=False)
    address = serializers.CharField(source='profile.location', required=False)
    latitude = serializers.DecimalField(source='profile.latitude', max_digits=9, decimal_places=6, read_only=True)
    longitude = serializers.DecimalField(source='profile.longitude', max_digits=9, decimal_places=6, read_only=True)
    bio = serializers.CharField(source='profile.bio', required=False)
    profile_picture = serializers.ImageField(source='profile.profile_picture', read_only=True)
    email_verified = serializers.BooleanField(source='profile.email_verified', read_only=True)
    average_rating = serializers.DecimalField(source='profile.average_rating', max_digits=3, decimal_places=2, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'role', 'phone_number', 'address', 
            'latitude', 'longitude', 'bio', 'profile_picture',
            'email_verified', 'date_joined', 'average_rating'
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for Donation model"""
    donor_name = serializers.CharField(source='donor.get_full_name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    is_claimed = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Donation
        fields = [
            'id', 'donor', 'donor_name', 'title', 
            'description', 'food_category', 'quantity',
            'expiry_datetime', 'pickup_location', 'latitude', 'longitude',
            'status', 'dietary_tags', 'allergen_info', 'image',
            'created_at', 'updated_at', 'is_claimed', 'is_expired',
            'distance', 'recipient', 'recipient_name', 'claimed_at', 'completed_at'
        ]
        read_only_fields = ['id', 'donor', 'status', 'created_at', 'updated_at', 'recipient', 'claimed_at', 'completed_at']
    
    def get_is_claimed(self, obj):
        return obj.status in [Donation.CLAIMED, Donation.COMPLETED]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_distance(self, obj):
        """Calculate distance from user location if provided in context"""
        request = self.context.get('request')
        if request and request.query_params.get('lat') and request.query_params.get('lng'):
            try:
                from core.services.ai_services import AIService
                return AIService._calculate_distance(
                    request.query_params['lat'],
                    request.query_params['lng'],
                    obj.latitude,
                    obj.longitude
                )
            except Exception:
                pass
        return None


class DonationDetailSerializer(DonationSerializer):
    """Detailed serializer for single donation view"""
    donor = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    
    class Meta(DonationSerializer.Meta):
        pass


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for Rating model"""
    rater_name = serializers.CharField(source='rating_user.get_full_name', read_only=True)
    rated_user_name = serializers.CharField(source='rated_user.get_full_name', read_only=True)
    donation_title = serializers.CharField(source='donation.title', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'rating_user', 'rater_name', 'rated_user', 'rated_user_name',
            'donation', 'donation_title', 'rating', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'rating_user', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'is_read', 'related_url', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']