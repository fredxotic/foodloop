from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Donation, Rating, Notification, 
    EmailVerification, NutritionImpact
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'email_verified', 'has_location', 'created_at']
    list_filter = ['user_type', 'email_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'average_rating', 'total_ratings']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_type', 'email_verified', 'phone_verified')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'location', 'profile_picture')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Dietary Preferences', {
            'fields': ('dietary_restrictions',)
        }),
        ('Reputation', {
            'fields': ('average_rating', 'total_ratings')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_active'),
            'classes': ('collapse',)
        }),
    )
    
    def has_location(self, obj):
        return obj.has_valid_coordinates
    has_location.boolean = True
    has_location.short_description = 'Location Set'


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['title', 'donor', 'recipient', 'status', 'food_category', 'expiry_datetime', 'created_at']
    list_filter = ['status', 'food_category', 'created_at']
    search_fields = ['title', 'donor__username', 'recipient__username', 'description']
    readonly_fields = ['created_at', 'updated_at', 'claimed_at', 'completed_at', 'nutrition_score']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('donor', 'recipient', 'title', 'description', 'food_category', 'quantity', 'image')
        }),
        ('Status & Timing', {
            'fields': ('status', 'expiry_datetime', 'pickup_start', 'pickup_end', 'claimed_at', 'completed_at')
        }),
        ('Location', {
            'fields': ('pickup_location', 'latitude', 'longitude')
        }),
        ('Nutrition Information', {
            'fields': ('dietary_tags', 'estimated_calories', 'nutrition_score', 'ingredients_list', 'allergen_info')
        }),
    )


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rated_user', 'rating_user', 'rating', 'donation', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['rated_user__username', 'rating_user__username']
    readonly_fields = ['created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'is_verified', 'expires_at', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['token', 'created_at', 'verified_at']


@admin.register(NutritionImpact)
class NutritionImpactAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'donations_made', 'donations_received', 'total_calories']
    list_filter = ['date']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'


# Customize admin site
admin.site.site_header = "FoodLoop Administration"
admin.site.site_title = "FoodLoop Admin"
admin.site.index_title = "Welcome to FoodLoop Administration"