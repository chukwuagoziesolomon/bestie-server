from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    message = _('Only admin users are allowed to access this endpoint.')
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class IsVerified(permissions.BasePermission):
    """
    Permission class that checks if the user is verified.
    
    This permission allows access only to users who have a verified vendor or courier profile.
    For vendors, checks if verification_status is 'verified'.
    For couriers, checks if verification_status is 'verified'.
    
    Raises:
        PermissionDenied: With a descriptive message if the user is not verified.
    """
    message = "You must be a verified vendor or courier to access this resource."
    
    def has_permission(self, request, view):
        user = request.user
        
        if hasattr(user, 'vendor_profile'):
            if user.vendor_profile.verification_status == 'verified':
                return True
            elif user.vendor_profile.verification_status == 'pending':
                self.message = "Your vendor account is pending verification. Please wait for admin approval."
            elif user.vendor_profile.verification_status == 'rejected':
                self.message = "Your vendor account verification was rejected. Please contact support for more information."
            else:
                self.message = "Your vendor account is not verified. Please complete the verification process."
            return False
            
        elif hasattr(user, 'courier_profile'):
            if user.courier_profile.verification_status == 'verified':
                return True
            elif user.courier_profile.verification_status == 'pending':
                self.message = "Your courier account is pending verification. Please wait for admin approval."
            elif user.courier_profile.verification_status == 'rejected':
                self.message = "Your courier account verification was rejected. Please contact support for more information."
            else:
                self.message = "Your courier account is not verified. Please complete the verification process."
            return False
            
        self.message = "No vendor or courier profile found. Please complete your profile setup."
        return False


class IsVerifiedVendor(permissions.BasePermission):
    """
    Permission class that checks if the user is a verified vendor.
    
    This permission allows access only to users who have a verified vendor profile.
    """
    message = _("You must be a verified vendor to access this resource.")
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            self.message = _("Authentication credentials were not provided.")
            return False
            
        if not hasattr(request.user, 'vendor_profile'):
            self.message = _("No vendor profile found. Please register as a vendor first.")
            return False
            
        if request.user.vendor_profile.verification_status != 'approved':
            if request.user.vendor_profile.verification_status == 'pending':
                self.message = _("Your vendor account is pending verification. Please wait for admin approval.")
            elif request.user.vendor_profile.verification_status == 'rejected':
                self.message = _("Your vendor account verification was rejected. Please contact support for more information.")
            else:
                self.message = _("Your vendor account is not verified. Please complete the verification process.")
            return False
            
        return True


class IsVerifiedCourier(permissions.BasePermission):
    """
    Permission class that checks if the user is a verified courier.
    
    This permission allows access only to users who have a verified courier profile.
    
    Raises:
        PermissionDenied: With a descriptive message if the user is not a verified courier.
    """
    message = "You must be a verified courier to access this resource."
    
    def has_permission(self, request, view):
        user = request.user
        
        if not hasattr(user, 'courier_profile'):
            self.message = "No courier profile found. Please sign up as a courier first."
            return False
            
        if user.courier_profile.verification_status == 'verified':
            return True
        elif user.courier_profile.verification_status == 'pending':
            self.message = "Your courier account is pending verification. Please wait for admin approval."
        elif user.courier_profile.verification_status == 'rejected':
            self.message = "Your courier account verification was rejected. Please contact support for more information."
        else:
            self.message = "Your courier account is not verified. Please complete the verification process."
            
        return False
