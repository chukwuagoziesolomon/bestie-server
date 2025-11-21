"""
URL configuration for payment webhooks
"""
from django.urls import path
from bestyy.core_features.user.api.webhook_views import PaystackTransferWebhookView

app_name = 'payment'

urlpatterns = [
    # Paystack Transfer Webhook
    path('webhooks/paystack/transfer/', PaystackTransferWebhookView.as_view(), name='paystack_transfer_webhook'),
]
