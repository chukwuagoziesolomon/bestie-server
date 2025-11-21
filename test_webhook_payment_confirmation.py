"""
Test Paystack webhook payment confirmation
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.restaurant_features.order.models import Order
from django.test.client import Client
from django.urls import reverse

print("=" * 70)
print("TESTING PAYSTACK WEBHOOK PAYMENT CONFIRMATION")
print("=" * 70)

# Get an order to test with
orders = Order.objects.filter(payment_confirmed=False).order_by('-created_at')[:5]

if not orders.exists():
    print("\n❌ No orders with payment_confirmed=False found")
    print("Creating a test scenario...")
    
    # Show orders with confirmed payments
    confirmed_orders = Order.objects.filter(payment_confirmed=True)[:3]
    print(f"\nOrders with confirmed payments: {confirmed_orders.count()}")
    for order in confirmed_orders:
        print(f"  Order #{order.id}: ₦{float(order.total_amount):,.2f} - Confirmed at {order.payment_confirmed_at}")
else:
    print(f"\n📋 Found {orders.count()} orders with unconfirmed payments:")
    for order in orders:
        print(f"\n  Order #{order.id}")
        print(f"    Amount: ₦{float(order.total_amount):,.2f}")
        print(f"    Payment Confirmed: {order.payment_confirmed}")
        print(f"    Created: {order.created_at}")

    # Test webhook payload for first order
    test_order = orders.first()
    
    print(f"\n{'=' * 70}")
    print(f"SIMULATING WEBHOOK FOR ORDER #{test_order.id}")
    print(f"{'=' * 70}")

    # Create webhook payload
    webhook_payload = {
        "event": "charge.success",
        "data": {
            "id": 3104021987,
            "domain": "test",
            "status": "success",
            "reference": f"order_{test_order.id}",
            "amount": int(float(test_order.total_amount) * 100),  # Convert to kobo
            "message": None,
            "gateway_response": "Approved",
            "paid_at": "2025-11-20T18:00:00.000Z",
            "created_at": "2025-11-20T17:58:00.000Z",
            "channel": "bank_transfer",
            "currency": "NGN",
            "ip_address": "172.91.42.100",
            "metadata": {},
            "fees": int(float(test_order.total_amount) * 100 * 0.015),  # 1.5% fee
            "authorization": {
                "authorization_code": "AUTH_test123",
                "channel": "bank_transfer",
                "card_type": "transfer",
                "bank": None,
                "country_code": "NG",
                "brand": "Managed Account",
                "sender_name": "Test Customer",
                "sender_bank_account_number": "0123456789"
            },
            "customer": {
                "id": 138496675,
                "email": test_order.customer.email if test_order.customer else "test@example.com",
                "customer_code": "CUS_test123"
            }
        }
    }

    print("\nWebhook Payload:")
    print("-" * 70)
    print(json.dumps(webhook_payload, indent=2))

    print("\n\nBEFORE WEBHOOK:")
    print("-" * 70)
    print(f"Order #{test_order.id}:")
    print(f"  payment_confirmed: {test_order.payment_confirmed}")
    print(f"  payment_confirmed_at: {test_order.payment_confirmed_at}")
    print(f"  payment_status: {test_order.payment_status}")
    print(f"  payment_reference: {test_order.payment_reference}")

    # Create Django test client
    client = Client()
    
    # Send webhook request
    print("\n\nSENDING WEBHOOK REQUEST...")
    print("-" * 70)
    
    response = client.post(
        '/api/user/webhooks/paystack/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.content.decode('utf-8')}")

    # Refresh order from database
    test_order.refresh_from_db()

    print("\n\nAFTER WEBHOOK:")
    print("-" * 70)
    print(f"Order #{test_order.id}:")
    print(f"  payment_confirmed: {test_order.payment_confirmed}")
    print(f"  payment_confirmed_at: {test_order.payment_confirmed_at}")
    print(f"  payment_status: {test_order.payment_status}")
    print(f"  payment_reference: {test_order.payment_reference}")
    print(f"  payment_method: {test_order.payment_method}")

    if test_order.payment_confirmed:
        print("\n✅ SUCCESS! Payment was confirmed by webhook")
    else:
        print("\n❌ FAILED! Payment was not confirmed")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
