"""
API package for the user app.
This package contains all API views and related functionality.
"""

# Import views to make them available when importing from user.api
from user.api.courier_views import (
    CourierListView,
    CourierDetailView,
    CourierVerificationView
)

__all__ = [
    'CourierListView',
    'CourierDetailView',
    'CourierVerificationView'
]
