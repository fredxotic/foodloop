from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Donation, EmailVerification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone_number', 'email_verified')
    list_filter = ('user_type', 'email_verified')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('user',)

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('food_type', 'donor', 'status', 'expiry_date', 'pickup_time', 'created_at')
    list_filter = ('status', 'food_type')
    search_fields = ('donor__username', 'recipient__username', 'food_type', 'location')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('donor', 'food_type', 'quantity', 'description', 'image')
        }),
        ('Timing Information', {
            'fields': ('expiry_date', 'pickup_time', 'pickup_deadline')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Status', {
            'fields': ('status', 'recipient')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)