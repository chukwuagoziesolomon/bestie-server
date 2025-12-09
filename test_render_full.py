#!/usr/bin/env python
import requests
import json

def test_phone_verification():
    """First get a JWT token from phone verification"""
    url = "https://bestie-server.onrender.com/api/auth/verify-whatsapp-signup/"

    data = {
        "phone": "+2348012345678",  # Test phone
        "code": "123456"  # Test code
    }

    print("Testing phone verification to get JWT token...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            if "tokens" in response_data:
                access_token = response_data["tokens"]["access"]
                print(f"\n✅ Got access token: {access_token[:50]}...")
                return access_token

    except Exception as e:
        print(f"Error: {e}")

    return None

def test_bank_verification(access_token):
    """Test bank verification with valid JWT token"""
    url = "https://bestie-server.onrender.com/api/user/verification/verify-bank/"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    data = {
        "account_number": "9047918798",
        "account_name": "ofodile franklin",
        "bank_name": "OPay Digital Services Limited (OPay)"
    }

    print(f"\nTesting bank verification with valid token...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 400:
            response_data = response.json()
            if "error" in response_data and "Invalid key" in response_data["error"]:
                print("\n✅ CONFIRMED: The 'Invalid key' error is from Paystack API")
                print("PAYSTACK_SECRET_KEY is not configured on Render.com")
            else:
                print(f"\nDifferent error: {response_data}")

    except Exception as e:
        print(f"Error: {e}")

def main():
    # First try to get a JWT token
    access_token = test_phone_verification()

    if access_token:
        # Then test bank verification
        test_bank_verification(access_token)
    else:
        print("Could not get JWT token. Testing bank verification with invalid token...")

        # Test with invalid token to see if we get past auth
        url = "https://bestie-server.onrender.com/api/user/verification/verify-bank/"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token"
        }
        data = {
            "account_number": "9047918798",
            "account_name": "ofodile franklin",
            "bank_name": "OPay Digital Services Limited (OPay)"
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    main()