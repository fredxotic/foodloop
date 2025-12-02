from django.contrib import admin
from .models import (
    UserProfile, Donation, Rating, Notification, 
    EmailVerification
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'email_verified', 'location', 'average_rating', 'created_at']
    list_filter = ['user_type', 'email_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'location', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'average_rating', 'total_ratings']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'user_type', 'email_verified')
        }),
        ('Contact & Location', {
            'fields': ('phone_number', 'location')
        }),
        ('Profile', {
            'fields': ('bio', 'profile_picture')
        }),
        ('Dietary Preferences', {
            'fields': ('dietary_restrictions',)
        }),
        ('Reputation', {
            'fields': ('average_rating', 'total_ratings'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'donor', 'status', 'food_category', 
        'expiry_datetime', 'pickup_location', 'created_at'
    ]
    list_filter = ['status', 'food_category', 'created_at']
    search_fields = ['title', 'description', 'pickup_location', 'donor__username']
    readonly_fields = ['created_at', 'updated_at', 'nutrition_score', 'claimed_at', 'completed_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('donor', 'recipient', 'title', 'food_category', 'description', 'quantity')
        }),
        ('Timing', {
            'fields': ('expiry_datetime', 'pickup_start', 'pickup_end')
        }),
        ('Location', {
            'fields': ('pickup_location',)
        }),
        ('Status', {
            'fields': ('status', 'claimed_at', 'completed_at')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Nutrition Info', {
            'fields': ('dietary_tags', 'estimated_calories', 'nutrition_score', 'ingredients_list', 'allergen_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('donor', 'recipient')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['donation', 'rating_user', 'rated_user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['rating_user__username', 'rated_user__username', 'donation__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Rating Details', {
            'fields': ('donation', 'rating_user', 'rated_user', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('donation', 'rating_user', 'rated_user')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'notification_type', 'title', 'message', 'is_read')
        }),
        ('Related Objects', {
            'fields': ('related_donation', 'related_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Bulk action to mark notifications as read"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        """Bulk action to mark notifications as unread"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notification(s) marked as unread.')
    mark_as_unread.short_description = "Mark selected as unread"


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    # FIXED: Changed 'is_verified' to 'is_used' (the actual field name)
    list_display = ['user', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'token']
    readonly_fields = ['created_at', 'updated_at', 'token']
    
    fieldsets = (
        ('Verification Info', {
            'fields': ('user', 'token', 'is_used', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user')


admin.site.site_header = "FoodLoop Administration"
admin.site.site_title = "FoodLoop Admin"
admin.site.index_title = "Welcome to FoodLoop Administration"