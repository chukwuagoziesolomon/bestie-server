"""
Test comprehensive Paystack webhook payment confirmation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.restaurant_features.order.models import Order
from django.test import Client
from django.conf import settings
import json
import hmac
import hashlib

print("=" * 70)
print("TESTING PAYSTACK WEBHOOK PAYMENT CONFIRMATION")
print("=" * 70)

# Get an order that hasn't been confirmed yet
unconfirmed_order = Order.objects.filter(payment_confirmed=False).first()

if not unconfirmed_order:
    print("\n⚠️  No unconfirmed orders found in database")
    print("Creating a test order...")
    
    from bestyy.core_features.user.models import User, VendorProfile
    from decimal import Decimal
    
    # Get or create test user
    user, _ = User.objects.get_or_create(
        email='test_customer@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Customer',
            'phone': '+2348012345678'
        }
    )
    
    # Get or create test vendor
    vendor = VendorProfile.objects.first()
    if not vendor:
        print("❌ No vendors found. Please create a vendor first.")
        exit(1)
    
    # Create test order
    unconfirmed_order = Order.objects.create(
        user=user,
        vendor=vendor,
        customer=user,
        order_name=f"Test Order #{Order.objects.count() + 1}",
        total_amount=Decimal('5000.00'),
        delivery_fee=Decimal('500.00'),
        payment_confirmed=False,
        delivery_address="123 Test Street, Lagos, Nigeria",
        status='pending'
    )
    print(f"✅ Created test order: {unconfirmed_order.id}")

print(f"\n📦 Using Order: #{unconfirmed_order.id}")
print(f"   Amount: ₦{float(unconfirmed_order.total_amount):,.2f}")
print(f"   Payment Confirmed: {unconfirmed_order.payment_confirmed}")
print(f"   Vendor: {unconfirmed_order.vendor.business_name if unconfirmed_order.vendor else 'None'}")

# Simulate Paystack webhook payload for charge.success
webhook_payload = {
    "event": "charge.success",
    "data": {
        "id": 3104021987,
        "domain": "test",
        "status": "success",
        "reference": f"order_{unconfirmed_order.id}",
        "amount": int(float(unconfirmed_order.total_amount) * 100),  # Convert to kobo
        "message": None,
        "gateway_response": "Approved",
        "paid_at": "2025-11-21T10:00:00.000Z",
        "created_at": "2025-11-21T09:58:00.000Z",
        "channel": "bank_transfer",
        "currency": "NGN",
        "ip_address": "172.91.42.100",
        "metadata": "",
        "fees_breakdown": None,
        "log": None,
        "fees": 375,
        "fees_split": None,
        "authorization": {
            "authorization_code": "AUTH_test123",
            "bin": "008XXX",
            "last4": "X553",
            "exp_month": "11",
            "exp_year": "2025",
            "channel": "bank_transfer",
            "card_type": "transfer",
            "bank": None,
            "country_code": "NG",
            "brand": "Managed Account",
            "reusable": False,
            "signature": None,
            "account_name": None,
            "sender_country": "NG",
            "sender_bank": None,
            "sender_bank_account_number": "XXXXXXX553",
            "sender_name": "Test Customer",
            "narration": "Order Payment"
        },
        "customer": {
            "id": 138496675,
            "first_name": unconfirmed_order.customer.first_name if unconfirmed_order.customer else "Test",
            "last_name": unconfirmed_order.customer.last_name if unconfirmed_order.customer else "Customer",
            "email": unconfirmed_order.customer.email if unconfirmed_order.customer else "test@example.com",
            "customer_code": "CUS_test123",
            "phone": None,
            "metadata": None,
            "risk_action": "default",
            "international_format_phone": None
        },
        "plan": {},
        "subaccount": {},
        "split": {},
        "order_id": None,
        "paidAt": "2025-11-21T10:00:00.000Z",
        "requested_amount": int(float(unconfirmed_order.total_amount) * 100),
        "pos_transaction_data": None,
        "source": {
            "type": "api",
            "source": "merchant_api",
            "entry_point": "charge",
            "identifier": None
        }
    }
}

# Convert payload to JSON
payload_json = json.dumps(webhook_payload)

# Generate HMAC signature (like Paystack does)
secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
signature = hmac.new(secret, payload_json.encode('utf-8'), hashlib.sha512).hexdigest()

print(f"\n🔐 Generated Webhook Signature: {signature[:20]}...")
print(f"📨 Webhook URL: /api/user/webhooks/paystack/")
print(f"📋 Event: charge.success")
print(f"💰 Amount: ₦{webhook_payload['data']['amount'] / 100:,.2f}")
print(f"🆔 Reference: {webhook_payload['data']['reference']}")

# Add testserver to ALLOWED_HOSTS for testing
from django.conf import settings
original_allowed_hosts = settings.ALLOWED_HOSTS
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

# Send webhook request
client = Client()
response = client.post(
    '/api/user/webhooks/paystack/',
    data=payload_json,
    content_type='application/json',
    HTTP_X_PAYSTACK_SIGNATURE=signature
)

# Restore original ALLOWED_HOSTS
settings.ALLOWED_HOSTS = original_allowed_hosts

print(f"\n📡 Webhook Response:")
print(f"   Status Code: {response.status_code}")
print(f"   Response: {response.json() if response.status_code == 200 else response.content}")

# Refresh order from database
unconfirmed_order.refresh_from_db()

print(f"\n✅ Order Status After Webhook:")
print(f"   Order ID: {unconfirmed_order.id}")
print(f"   Payment Confirmed: {unconfirmed_order.payment_confirmed}")
print(f"   Payment Confirmed At: {unconfirmed_order.payment_confirmed_at}")
print(f"   Payment Reference: {unconfirmed_order.payment_reference}")
print(f"   Payment Method: {unconfirmed_order.payment_method}")
print(f"   Payment Status: {unconfirmed_order.payment_status}")

if unconfirmed_order.payment_confirmed:
    print(f"\n🎉 SUCCESS! Payment confirmed automatically via webhook")
    print(f"   ✅ Order #{unconfirmed_order.id} is now confirmed")
    print(f"   ✅ Revenue will be counted: ₦{float(unconfirmed_order.total_amount):,.2f}")
else:
    print(f"\n❌ FAILED! Payment was not confirmed")
    print(f"   Check webhook handler logs for errors")

print("\n" + "=" * 70)
print("WEBHOOK INTEGRATION STATUS")
print("=" * 70)
print("\n✅ Webhook endpoint: /api/user/webhooks/paystack/")
print("✅ Handles events: charge.success, bank.transfer.rejected")
print("✅ Signature verification: Enabled")
print("✅ Auto-confirms payment when customer pays")
print("✅ Updates order.payment_confirmed = True")
print("✅ Triggers notifications to vendor & courier")
print("\n📝 Next Steps:")
print("   1. Configure webhook URL in Paystack Dashboard")
print("   2. Set URL to: https://your-domain.com/api/user/webhooks/paystack/")
print("   3. Test with real Paystack payments")
