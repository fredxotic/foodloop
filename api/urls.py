from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    DonationViewSet,
    UserViewSet,
    RatingViewSet,
    NotificationViewSet,
    CustomTokenObtainPairView,
)

app_name = 'api'

# API v1 Router
router_v1 = DefaultRouter()
router_v1.register(r'donations', DonationViewSet, basename='donation')
router_v1.register(r'users', UserViewSet, basename='user')
router_v1.register(r'ratings', RatingViewSet, basename='rating')
router_v1.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # API Version 1
    path('v1/', include([
        path('', include(router_v1.urls)),
        path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    ])),
]