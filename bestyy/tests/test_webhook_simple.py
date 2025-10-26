#!/usr/bin/env python3
"""
Simple webhook test to debug environment and webhook issues
"""

import requests
import os
import sys

# Add Django project to path
sys.path.append(os.path.dirname(__file__))

def test_webhook():
    """Test the webhook endpoint"""
    
    print("=== WHATSAPP WEBHOOK TEST ===")
    print()
    
    # Test URL
    url = "http://localhost:8000/api/whatsapp/webhook/"
    
    # Test parameters
    test_params = {
        'hub.mode': 'subscribe',
        'hub.verify_token': '_EPmQOB2Fxjln47xEhmXPBurta2Q_biBfIOoW5BW2wE',
        'hub.challenge': 'test_challenge_123'
    }
    
    print(f"Testing URL: {url}")
    print(f"Test parameters: {test_params}")
    print()
    
    try:
        response = requests.get(url, params=test_params, timeout=10)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: '{response.text}'")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Webhook verification passed!")
        elif response.status_code == 403:
            print("❌ FAILED: Token verification failed")
        elif response.status_code == 400:
            print("❌ FAILED: Bad request - check parameters")
        elif response.status_code == 500:
            print("❌ FAILED: Server error - check Django logs")
        else:
            print(f"❌ UNEXPECTED: Status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to Django server")
        print("Make sure Django is running: python manage.py runserver")
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_basic_endpoint():
    """Test basic endpoint accessibility"""
    print("=== BASIC ENDPOINT TEST ===")
    url = "http://localhost:8000/api/whatsapp/webhook/"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Basic GET Status: {response.status_code}")
        print(f"Basic GET Response: '{response.text}'")
        
        if response.status_code in [400, 403, 405]:
            print("✅ Endpoint is accessible (expected error for no params)")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("WhatsApp Webhook Simple Test")
    print("=" * 50)
    
    # Test basic connectivity
    test_basic_endpoint()
    print()
    
    # Test webhook verification
    test_webhook()
    
    print()
    print("=" * 50)
    print("Test complete!")
    print()
    print("Next steps:")
    print("1. Check Django console for detailed logs")
    print("2. Make sure .env file exists with WHATSAPP_VERIFY_TOKEN")
    print("3. Restart Django server after creating .env file")

