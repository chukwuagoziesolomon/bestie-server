#!/usr/bin/env python
import requests
import json

def test_bank_verification():
    url = "https://bestie-server.onrender.com/api/user/verification/verify-bank/"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_token"  # This will fail auth but should get past Paystack check
    }

    data = {
        "account_number": "9047918798",
        "account_name": "ofodile franklin",
        "bank_name": "OPay Digital Services Limited (OPay)"
    }

    print(f"Testing URL: {url}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 400:
            response_data = response.json()
            if "error" in response_data and "Invalid key" in response_data["error"]:
                print("\n✅ CONFIRMED: The 'Invalid key' error is from Paystack API")
                print("This means PAYSTACK_SECRET_KEY is not set correctly on Render.com")
            else:
                print(f"\nDifferent error: {response_data}")

    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == '__main__':
    test_bank_verification()