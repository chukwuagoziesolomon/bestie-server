"""
URL patterns for Paystack webhooks
Separated to avoid circular imports
"""
from django.urls import path

urlpatterns = [
    # Import here to avoid circular dependency
    path('', lambda request: __import__('bestyy.core_features.user.api.webhook_views', fromlist=['PaystackTransferWebhookView']).PaystackTransferWebhookView.as_view()(request), name='paystack-transfer-webhook'),
]
