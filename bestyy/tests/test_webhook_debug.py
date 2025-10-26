#!/usr/bin/env python3
"""
Debug script for WhatsApp webhook testing
Run this script to test your webhook endpoint locally
"""

import requests
import os
from decouple import config

def test_webhook_verification():
    """Test the webhook verification endpoint"""
    
    # Get your verify token from environment
    verify_token = config('WHATSAPP_VERIFY_TOKEN', default='your_verify_token')
    
    # Test parameters
    test_challenge = "test_challenge_123"
    
    # Test URLs
    local_url = "http://localhost:8000/api/whatsapp/webhook/"
    
    print(f"Testing webhook verification...")
    print(f"Verify Token from .env: {verify_token}")
    print(f"Token length: {len(verify_token) if verify_token else 0}")
    print(f"Challenge: {test_challenge}")
    print("-" * 50)
    
    # Test 1: With dot parameters (Meta format) - Primary test
    print("Test 1: Using dot parameters (Meta format)")
    params_dot = {
        'hub.mode': 'subscribe',
        'hub.verify_token': verify_token,
        'hub.challenge': test_challenge
    }
    
    try:
        response = requests.get(local_url, params=params_dot)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print("✅ SUCCESS: Webhook verification passed!")
        else:
            print("❌ FAILED: Webhook verification failed")
    except Exception as e:
        print(f"Error: {e}")
    
    print("-" * 50)
    
    # Test 2: With underscore parameters (Django format)
    print("Test 2: Using underscore parameters (Django format)")
    params_underscore = {
        'hub_mode': 'subscribe',
        'hub_verify_token': verify_token,
        'hub_challenge': test_challenge
    }
    
    try:
        response = requests.get(local_url, params=params_underscore)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("-" * 50)
    
    # Test 3: Wrong token
    print("Test 3: Using wrong token")
    params_wrong = {
        'hub.mode': 'subscribe',
        'hub.verify_token': 'wrong_token',
        'hub.challenge': test_challenge
    }
    
    try:
        response = requests.get(local_url, params=params_wrong)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 403:
            print("✅ SUCCESS: Wrong token correctly rejected!")
        else:
            print("❌ FAILED: Wrong token should be rejected")
    except Exception as e:
        print(f"Error: {e}")

def test_basic_endpoint():
    """Test basic endpoint accessibility"""
    local_url = "http://localhost:8000/api/whatsapp/webhook/"
    
    print("Testing basic endpoint accessibility...")
    try:
        response = requests.get(local_url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("WhatsApp Webhook Debug Tool")
    print("=" * 50)
    
    # Check if Django server is running
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print("✅ Django server is running")
    except:
        print("❌ Django server is not running. Please start it with: python manage.py runserver")
        exit(1)
    
    print()
    test_basic_endpoint()
    print()
    test_webhook_verification()
    
    print("\n" + "=" * 50)
    print("Debug complete!")
    print("\nIf you're still getting 400 errors, check:")
    print("1. Django logs for detailed error messages")
    print("2. Make sure WHATSAPP_VERIFY_TOKEN is set in your .env file")
    print("3. Check if any middleware is interfering with the request")
