"""
Admin package for user app.
This package contains all admin-related functionality including models,
views, and authentication components.
"""
from .models import (
    CustomUserAdmin,
    VendorAdmin,
    UserProfileAdmin,
    CourierProfileAdmin
)
from .auth import (
    CustomAdminSite,
    CustomUserCreationForm,
    CustomUserChangeForm,
    CustomUserAdmin
)
from .views import (
    PendingVerificationList,
    AdminDashboardStatsView,
    AdminRevenueBreakdownView
)

__all__ = [
    'CustomUserAdmin',
    'VendorAdmin',
    'UserProfileAdmin',
    'CourierProfileAdmin',
    'CustomAdminSite',
    'CustomUserCreationForm',
    'CustomUserChangeForm',
    'PendingVerificationList',
    'AdminDashboardStatsView',
    'AdminRevenueBreakdownView'
]