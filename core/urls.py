# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('recipient/dashboard/', views.recipient_dashboard, name='recipient_dashboard'),
    path('donation/create/', views.create_donation, name='create_donation'),
    path('donation/<int:donation_id>/claim/', views.claim_donation, name='claim_donation'),
    path('donation/<int:donation_id>/', views.donation_detail, name='donation_detail'),
]