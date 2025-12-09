#!/usr/bin/env python
"""
Test script to debug Paystack bank verification API key issue
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')

# Setup Django
django.setup()

from bestyy.core_features.user.services.paystack_service import PaystackService

def test_paystack_api_key():
    """Test if Paystack API key is working"""
    print("Testing Paystack API Key...")

    paystack_service = PaystackService()

    # Test 1: Check if secret key is loaded
    print(f"Secret Key loaded: {'Yes' if paystack_service.secret_key else 'No'}")
    print(f"Secret Key starts with: {paystack_service.secret_key[:10] if paystack_service.secret_key else 'None'}...")

    # Test 2: Try to get supported banks (simple API call)
    print("\nTesting get_supported_banks()...")
    banks_result = paystack_service.get_supported_banks()

    if banks_result['success']:
        print(f"✅ Success! Found {len(banks_result['banks'])} banks")
        # Show first few banks
        for bank in banks_result['banks'][:3]:
            print(f"  - {bank.get('name')} (code: {bank.get('code')})")
    else:
        print(f"❌ Failed: {banks_result.get('error', 'Unknown error')}")

    # Test 3: Try bank account verification with a test account
    print("\nTesting verify_bank_account() with test data...")
    # Using a known test account (this might not work in live mode)
    test_account = "0123456789"  # Test account number
    test_bank_code = "044"  # Access Bank

    verification_result = paystack_service.verify_bank_account(test_account, test_bank_code)

    if verification_result['success']:
        print("✅ Bank verification successful!")
        print(f"Account Name: {verification_result.get('account_name')}")
    else:
        print(f"❌ Bank verification failed: {verification_result.get('message')}")

if __name__ == "__main__":
    test_paystack_api_key()