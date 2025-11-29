from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # =============================================================================
    # PUBLIC PAGES
    # =============================================================================
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('platform-stats/', views.platform_stats_view, name='platform_stats'),
    
    # =============================================================================
    # AUTHENTICATION
    # =============================================================================
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    
    # =============================================================================
    # DASHBOARD - UNIFIED
    # =============================================================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # =============================================================================
    # PROFILE MANAGEMENT
    # =============================================================================
    path('profile/', views.profile_view, name='profile'),
    path('profile/dietary/', views.dietary_preferences_view, name='dietary_preferences'),
    path('profile/<int:user_id>/', views.public_profile_view, name='public_profile'),
    
    # =============================================================================
    # DONATION MANAGEMENT
    # =============================================================================
    path('donation/create/', views.create_donation_view, name='create_donation'),
    path('donation/<int:donation_id>/', views.donation_detail_view, name='donation_detail'),
    path('donation/<int:donation_id>/claim/', views.claim_donation_view, name='claim_donation'),
    path('donation/<int:donation_id>/complete/', views.complete_donation_view, name='complete_donation'),
    path('donation/<int:donation_id>/cancel/', views.cancel_donation_view, name='cancel_donation'),
    path('my-donations/', views.my_donations_view, name='my_donations'),
    
    # =============================================================================
    # SEARCH & DISCOVERY
    # =============================================================================
    path('search/', views.search_donations_view, name='search_donations'),
    path('map/', views.map_view, name='map_view'),
    
    # =============================================================================
    # NOTIFICATIONS
    # =============================================================================
    path('notifications/', views.get_notifications_view, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
    
    # =============================================================================
    # RATING SYSTEM
    # =============================================================================
    path('rate/<int:donation_id>/', views.rate_user_view, name='rate_donation'),
    
    # =============================================================================
    # ANALYTICS
    # =============================================================================
    path('analytics/', views.analytics_view, name='analytics'),
]