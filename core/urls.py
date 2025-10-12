from django.urls import path
from . import views

urlpatterns = [
    # Core URLs (existing)
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Email Verification
    path('verify/<str:token>/', views.verify_email, name='verify_email'),
    path('verify-email/<str:token>/', views.verify_email_confirm, name='verify_email_confirm'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    
    # Donation Management
    path('donation/create/', views.create_donation, name='create_donation'),
    path('donation/<int:donation_id>/', views.donation_detail, name='donation_detail'),
    path('donation/<int:donation_id>/claim/', views.claim_donation, name='claim_donation'),
    path('donation/<int:donation_id>/complete/', views.complete_donation, name='complete_donation'),
    
    # Dashboards
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('recipient/dashboard/', views.recipient_dashboard, name='recipient_dashboard'),
    
    # Search & Discovery
    path('search/', views.search_donations, name='search_donations'),
    path('map/', views.map_view, name='map_view'),
    path('map/search/', views.search_donations_map, name='search_donations_map'),
    
    # NEW: Nutrition & AI Features
    path('search/nutrition/', views.nutrition_search, name='nutrition_search'),
    path('analytics/nutrition/', views.nutrition_analytics, name='nutrition_analytics'),
    path('recommendations/ai/', views.ai_recommendations, name='ai_recommendations'),
    path('recommendations/refresh/', views.refresh_recommendations, name='refresh_recommendations'),
    path('profile/dietary-preferences/', views.update_dietary_preferences, name='update_dietary_preferences'),
    
    # Rating System
    path('donation/<int:donation_id>/rate/', views.rate_donation, name='rate_donation'),
    path('donation/<int:donation_id>/rating/create/', views.create_rating, name='create_rating'),
    path('donation/<int:donation_id>/rating/success/', views.rating_success, name='rating_success'),
    
    # Notification System
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/count/', views.notification_count, name='notification_count'),
]