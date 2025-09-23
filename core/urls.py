from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('verify/<str:token>/', views.verify_email_confirm, name='verify_email_confirm'),
    path('search/', views.search_donations, name='search_donations'),
    
    # Map routes
    path('map/', views.map_view, name='map_view'),
    path('map/search/', views.search_donations_map, name='search_donations_map'),
    
    # Donor routes
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('donation/create/', views.create_donation, name='create_donation'),
    path('donation/<int:donation_id>/complete/', views.complete_donation, name='complete_donation'),
    
    # Recipient routes
    path('recipient/dashboard/', views.recipient_dashboard, name='recipient_dashboard'),
    path('donation/<int:donation_id>/claim/', views.claim_donation, name='claim_donation'),
    path('donation/<int:donation_id>/', views.donation_detail, name='donation_detail'),

    # Rating routes - allow both GET and POST
    path('donation/<int:donation_id>/rate/', views.create_rating, name='create_rating'),
    path('donation/<int:donation_id>/rating/success/', views.rating_success, name='rating_success'),
]