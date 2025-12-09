#!/usr/bin/env python
import requests
import json

def test_paystack_direct():
    """Test Paystack API directly on Render by calling the supported banks endpoint"""
    # This should work if PAYSTACK_SECRET_KEY is configured
    paystack_url = "https://api.paystack.co/bank"
    headers = {
        "Authorization": "Bearer sk_live_33a98259a53797f9a82c17670d17d5f028dc0f54",  # From .env
        "Content-Type": "application/json"
    }

    print("Testing Paystack API directly...")
    print(f"URL: {paystack_url}")

    try:
        response = requests.get(paystack_url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Paystack API works directly")
            banks = data.get('data', [])
            opay_found = any('opay' in bank.get('name', '').lower() for bank in banks)
            print(f"OPay found: {opay_found}")
        else:
            print(f"❌ Paystack API failed: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

def test_resolve_account():
    """Test the specific resolve account endpoint that bank verification uses"""
    paystack_url = "https://api.paystack.co/bank/resolve"
    headers = {
        "Authorization": "Bearer sk_live_33a98259a53797f9a82c17670d17d5f028dc0f54",
        "Content-Type": "application/json"
    }
    params = {
        "account_number": "9047918798",
        "bank_code": "999992"  # OPay
    }

    print(f"\nTesting resolve account endpoint...")
    print(f"URL: {paystack_url}")
    print(f"Params: {params}")

    try:
        response = requests.get(paystack_url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("✅ Account resolution works")
        else:
            print(f"❌ Account resolution failed")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_paystack_direct()
    test_resolve_account()