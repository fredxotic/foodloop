from rest_framework import permissions
from core.models import UserProfile

class IsDonorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow donors to create donations.
    Other users can only view donations.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Check if user has a profile and is a donor
        try:
            return (
                request.user and 
                request.user.is_authenticated and 
                request.user.profile.user_type == UserProfile.DONOR
            )
        except Exception:
            return False
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.donor == request.user


class IsRecipientOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow recipients to perform certain actions.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
            
        try:
            return request.user.profile.user_type == UserProfile.RECIPIENT
        except Exception:
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
            
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user