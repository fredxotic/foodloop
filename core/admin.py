# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Donation

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone_number')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__email', 'phone_number')

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('food_type', 'donor', 'status', 'pickup_time', 'created_at')
    list_filter = ('status', 'food_type')
    search_fields = ('donor__username', 'recipient__username', 'food_type')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('donor', 'food_type', 'quantity', 'description')
        }),
        ('Pickup Details', {
            'fields': ('pickup_time', 'location')
        }),
        ('Status', {
            'fields': ('status', 'recipient')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )