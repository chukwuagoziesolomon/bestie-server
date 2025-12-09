#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from bestyy.core_features.user.services.paystack_service import PaystackService

def test_paystack_connection():
    service = PaystackService()

    # Test bank resolution with OPay
    print("Testing bank account resolution with OPay...")
    result = service.verify_bank_account("9047918798", "999992")

    print(f"Result: {result}")

    if not result['success']:
        print(f"Error message: {result.get('message', 'Unknown error')}")

if __name__ == '__main__':
    test_paystack_connection()