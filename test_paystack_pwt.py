#!/usr/bin/env python
"""
Test script for Paystack Pay with Transfer functionality
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')

# Setup Django
django.setup()

from bestyy.core_features.user.services.paystack_service import PaystackService
from django.contrib.auth import get_user_model

User = get_user_model()

def test_paystack_pay_with_transfer():
    """Test Paystack Pay with Transfer functionality"""
    print("="*80)
    print("TESTING PAYSTACK PAY WITH TRANSFER")
    print("="*80)

    # Initialize Paystack service
    paystack_service = PaystackService()
    print(f"Paystack secret key configured: {'YES' if paystack_service.secret_key else 'NO'}")
    print(f"Paystack base URL: {paystack_service.base_url}")

    # Create test user
    test_user, created = User.objects.get_or_create(
        email='test_paystack@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Paystack',
            'username': 'test_paystack'
        }
    )
    print(f"Test user: {test_user.email} (created: {created})")

    # 1. Test customer creation
    print("\n1. Testing customer creation...")
    customer_result = paystack_service.create_customer(test_user)
    print(f"Customer creation result: {customer_result}")
    success = customer_result.get('success', False)
    print(f"✓ Customer creation successful: {success}")

    if not success:
        print("❌ Customer creation failed, stopping tests")
        return

    # 2. Test Pay with Transfer initialization
    print("\n2. Testing Pay with Transfer initialization...")
    amount_kobo = 50000  # ₦500.00 in kobo
    import uuid
    unique_ref = f"TEST-{uuid.uuid4().hex[:12]}"
    pwt_result = paystack_service.initialize_pay_with_transfer(
        email=test_user.email,
        amount=amount_kobo,
        reference=unique_ref,
        expiry_hours=4
    )

    print(f"Pay with Transfer result: {pwt_result}")
    success = pwt_result.get('success', False)
    print(f"✓ Pay with Transfer successful: {success}")

    if success:
        account_details = pwt_result.get('account_details', {})
        print(f"Account details:")
        print(f"  - Account Number: {account_details.get('account_number', 'N/A')}")
        print(f"  - Account Name: {account_details.get('account_name', 'N/A')}")
        print(f"  - Bank Name: {account_details.get('bank_name', 'N/A')}")
        print(f"  - Amount Expected: ₦{account_details.get('amount_expected', 0):,.2f}")
        print(f"  - Reference: {account_details.get('reference', 'N/A')}")
        print(f"  - Expires At: {account_details.get('expires_at', 'N/A')}")

        # Instructions for testing
        print(f"\n🚀 TEST INSTRUCTIONS:")
        print(f"1. Go to your banking app")
        print(f"2. Make a transfer of ₦{account_details.get('amount_expected', 0):,.2f}")
        print(f"3. Transfer to account: {account_details.get('account_number', 'N/A')}")
        print(f"4. Account name: {account_details.get('account_name', 'N/A')}")
        print(f"5. Bank: {account_details.get('bank_name', 'N/A')}")
        print(f"6. Check webhook events for 'charge.success'")
    else:
        error_msg = pwt_result.get('error', 'Unknown error')
        print(f"❌ Pay with Transfer failed: {error_msg}")

    print("="*80)
    print("PAY WITH TRANSFER TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    test_paystack_pay_with_transfer()
