"""
User app package.

This package contains all user-related functionality including authentication,
profiles, and related models/views/serializers.
"""
# This file is intentionally kept minimal to avoid circular imports
# Import only what's absolutely necessary at the module level

from django.apps import AppConfig

class UserConfig(AppConfig):
    """User app config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        # Import signals to register them
        import user.signals  # noqa

# Define __all__ to control what gets imported with 'from user import *'
__all__ = [
    'UserConfig',
    'get_user_serializer',
    'get_courier_views',
    'get_admin_urls',
]

def get_user_serializer():
    """Lazy import for UserSerializer to avoid circular imports."""
    from .serializers.user_serializers import UserSerializer
    return UserSerializer

def get_courier_views():
    """Lazy import for courier views to avoid circular imports."""
    from .api.courier_views import (
        CourierListView,
        CourierDetailView,
        CourierVerificationView
    )
    return {
        'CourierListView': CourierListView,
        'CourierDetailView': CourierDetailView,
        'CourierVerificationView': CourierVerificationView,
    }

def get_admin_urls():
    """Lazy import for admin URLs to avoid circular imports."""
    from .admin_urls import urlpatterns as admin_urls
    return admin_urls