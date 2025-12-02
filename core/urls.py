"""
URL Configuration for Core App
Phase 1: Simplified routing
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Donations
    path('donations/create/', views.create_donation_view, name='create_donation'),
    path('donations/<int:donation_id>/', views.donation_detail_view, name='donation_detail'),
    path('donations/<int:donation_id>/claim/', views.claim_donation_view, name='claim_donation'),
    path('donations/<int:donation_id>/complete/', views.complete_donation_view, name='complete_donation'),
    path('donations/<int:donation_id>/cancel/', views.cancel_donation_view, name='cancel_donation'),
    path('donations/search/', views.nutrition_search_view, name='search_donations'),  # ✅ FIXED
    path('donations/my/', views.my_donations_view, name='my_donations'),
    path('donations/my-claims/', views.my_claims_view, name='my_claims'),  # ✅ ADDED
    
    # Ratings
    path('donations/<int:donation_id>/rate/', views.rate_user_view, name='rate_user'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/dietary/', views.dietary_preferences_view, name='dietary_preferences'),
    path('u/<str:username>/', views.public_profile_view, name='public_profile'),
    
    # Notifications (AJAX endpoints)
    path('notifications/', views.get_notifications_view, name='get_notifications'),  # ✅ FIXED
    path('notifications/count/', views.get_notifications_view, name='notification_count'),  # ✅ ADDED
    path('notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
    
    # Map & Analytics
    path('map/', views.map_view, name='map_view'),
    path('analytics/', views.analytics_view, name='analytics'),
    
    # Static Pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
]