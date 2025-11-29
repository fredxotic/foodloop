from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

from core.models import Donation, Rating, Notification, UserProfile
from core.services import DonationService, NotificationService, AnalyticsService
from .serializers import (
    DonationSerializer,
    DonationDetailSerializer,
    UserSerializer,
    RatingSerializer,
    NotificationSerializer,
    CustomTokenObtainPairSerializer,
)
from .permissions import IsDonorOrReadOnly, IsOwnerOrReadOnly
from .throttles import BurstRateThrottle, SustainedRateThrottle

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with additional user data"""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [BurstRateThrottle]


class DonationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing food donations.
    """
    serializer_class = DonationSerializer
    permission_classes = [IsAuthenticated, IsDonorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'food_category']
    ordering_fields = ['created_at', 'expiry_datetime', 'quantity']
    ordering = ['-created_at']
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    def get_queryset(self):
        """Filter queryset based on user role and query parameters"""
        queryset = Donation.objects.select_related('donor__profile')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            # Default: show only available donations for recipients
            try:
                if self.request.user.profile.user_type == UserProfile.RECIPIENT:
                    queryset = queryset.filter(status=Donation.AVAILABLE)
            except Exception:
                pass
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(food_category=category)
            
        # Filter by expiry
        expiring_soon = self.request.query_params.get('expiring_soon', None)
        if expiring_soon:
            tomorrow = timezone.now() + timedelta(days=1)
            queryset = queryset.filter(expiry_datetime__lte=tomorrow)
        
        return queryset

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return DonationDetailSerializer
        return DonationSerializer

    def perform_create(self, serializer):
        """Set the donor as the current user"""
        # Use the service to create donation
        DonationService.create_donation(
            donor=self.request.user,
            form_data=serializer.validated_data
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def claim(self, request, pk=None):
        """Claim a donation"""
        try:
            response = DonationService.claim_donation(pk, request.user)
            if response.success:
                serializer = DonationDetailSerializer(response.data)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({'error': response.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error claiming donation: {str(e)}")
            return Response({'error': 'Failed to claim donation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """Mark donation as completed"""
        try:
            response = DonationService.complete_donation(pk, request.user)
            if response.success:
                return Response({'status': 'Donation completed'})
            return Response({'error': response.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def my_donations(self, request):
        """Get donations created or claimed by the current user"""
        user = request.user
        try:
            if user.profile.user_type == UserProfile.DONOR:
                donations = Donation.objects.filter(donor=user)
            else:
                donations = Donation.objects.filter(recipient=user)
            
            serializer = self.get_serializer(donations, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [SustainedRateThrottle]

    def get_queryset(self):
        """Users can only see their own data unless staff"""
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class RatingViewSet(viewsets.ModelViewSet):
    """ViewSet for ratings"""
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [BurstRateThrottle]

    def get_queryset(self):
        """Filter ratings based on user"""
        user = self.request.user
        return Rating.objects.filter(
            Q(rating_user=user) | Q(rated_user=user)
        ).select_related('rating_user', 'rated_user', 'donation')

    def perform_create(self, serializer):
        """Set the rater as current user"""
        serializer.save(rating_user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notifications (read-only)"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [SustainedRateThrottle]

    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        NotificationService.mark_notification_read(pk, request.user)
        return Response({'status': 'Notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        NotificationService.mark_all_read(request.user)
        return Response({'status': 'All notifications marked as read'})