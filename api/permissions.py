from rest_framework import permissions
from core.models import UserProfile

class IsDonorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow donors to create donations.
    Only the donation owner (donor) can modify or delete their donations.
    Other users can only view donations.
    """
    
    def has_permission(self, request, view):
        # Allow authenticated users to read
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # For write operations (POST, PUT, PATCH, DELETE), user must be a donor
        try:
            return (
                request.user and 
                request.user.is_authenticated and 
                request.user.profile.user_type == UserProfile.DONOR
            )
        except Exception:
            return False
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check for donations"""
        # Allow read access to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For PUT, PATCH, DELETE: explicitly verify ownership
        # Only the donor who created the donation can modify/delete it
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return (
                hasattr(obj, 'donor') and 
                obj.donor == request.user
            )
        
        # For other write operations (POST handled in has_permission)
        return False


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
    Explicitly checks ownership for PUT, PATCH, and DELETE operations.
    Staff users have full access.
    """
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission for user-owned objects"""
        # Allow read access to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Staff users have full access
        if request.user and request.user.is_staff:
            return True
        
        # For PUT, PATCH, DELETE: explicitly verify ownership
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            # Check if object has a 'user' attribute (like UserProfile)
            if hasattr(obj, 'user'):
                return obj.user == request.user
            # Check if object is the user itself
            return obj == request.user
        
        # Deny other write operations by default
        return False