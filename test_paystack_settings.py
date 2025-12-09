#!/usr/bin/env python
import requests

def test_paystack_settings():
    """Test if Paystack settings are loaded correctly on Render"""
    url = "https://bestie-server.onrender.com/api/user/verification/test-paystack/"

    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"Paystack key loaded: {data.get('key_loaded', 'Unknown')}")
            print(f"Key starts with sk_: {data.get('starts_with_sk', 'Unknown')}")
        else:
            print("Test endpoint not available or failed")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_paystack_settings()