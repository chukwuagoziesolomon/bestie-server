"""
Admin configuration for the user app.

This is a minimal admin configuration that provides basic model registration
without any custom admin views or templates, since the admin interface is
handled by the React frontend.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import path
from rest_framework import status

from .models import VendorProfile, CourierProfile, UserProfile

User = get_user_model()

class CustomUserAdmin(UserAdmin):
    """Custom UserAdmin configuration with email-based authentication."""
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


class VendorAdmin(admin.ModelAdmin):
    """Admin configuration for VendorProfile."""
    list_display = ('business_name', 'user_email', 'verification_status')
    list_filter = ('verification_status', 'business_category')
    search_fields = ('business_name', 'user__email', 'cac_number')
    readonly_fields = ('verification_date',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'


class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile."""
    list_display = ('user', 'phone')
    search_fields = ('user__email', 'phone')
    readonly_fields = ()


class CourierProfileAdmin(admin.ModelAdmin):
    """Admin configuration for CourierProfile."""
    list_display = ('user', 'phone', 'verification_status')
    list_filter = ('verification_status', 'vehicle_type')
    search_fields = ('user__email', 'phone')
    readonly_fields = ()


# Register models with their admin classes
admin.site.register(User, CustomUserAdmin)
admin.site.register(VendorProfile, VendorAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(CourierProfile, CourierProfileAdmin)
