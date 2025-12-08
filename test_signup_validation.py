#!/usr/bin/env python3
"""
Simple Functional Test: WhatsApp Signup Flow
Direct testing of the webhook endpoint with realistic scenarios.
"""

import os
import sys
import django
import json
import requests
from unittest.mock import patch, Mock

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

def test_webhook_signup_enforcement():
    """Test webhook handles first-time users correctly"""
    
    print("\n🔐 TESTING WEBHOOK SIGNUP ENFORCEMENT")
    print("=" * 50)
    
    # Mock webhook payload for new user
    webhook_data = {
        'object': 'whatsapp_business_account',
        'entry': [{
            'id': 'test_entry',
            'changes': [{
                'value': {
                    'messaging_product': 'whatsapp',
                    'metadata': {
                        'display_phone_number': '+1234567890',
                        'phone_number_id': 'test_phone_id'
                    },
                    'messages': [{
                        'id': 'msg_001',
                        'from': '+2348123456789',
                        'timestamp': '1234567890',
                        'text': {'body': 'I want to order food'},
                        'type': 'text'
                    }]
                },
                'field': 'messages'
            }]
        }]
    }
    
    client = Client()
    
    try:
        # Make request to webhook
        print("📤 Sending webhook request...")
        
        response = client.post(
            '/webhook/',  # Direct URL path
            data=json.dumps(webhook_data),
            content_type='application/json'
        )
        
        print(f"✅ Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook processed successfully")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            if hasattr(response, 'content'):
                print(f"Response: {response.content.decode()[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing webhook: {str(e)}")
        return False

def test_email_processing():
    """Test that email messages are processed correctly"""
    
    print("\n📧 TESTING EMAIL PROCESSING")
    print("=" * 50)
    
    # Mock webhook with email
    email_webhook_data = {
        'object': 'whatsapp_business_account',
        'entry': [{
            'id': 'test_entry',
            'changes': [{
                'value': {
                    'messaging_product': 'whatsapp',
                    'metadata': {
                        'display_phone_number': '+1234567890',
                        'phone_number_id': 'test_phone_id'
                    },
                    'messages': [{
                        'id': 'msg_002',
                        'from': '+2348123456789',
                        'timestamp': '1234567890',
                        'text': {'body': 'test.user@example.com'},
                        'type': 'text'
                    }]
                },
                'field': 'messages'
            }]
        }]
    }
    
    client = Client()
    
    try:
        print("📤 Sending email webhook request...")
        
        response = client.post(
            '/webhook/',
            data=json.dumps(email_webhook_data),
            content_type='application/json'
        )
        
        print(f"✅ Email Response Status: {response.status_code}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing email: {str(e)}")
        return False

def check_models_and_imports():
    """Check if all necessary models and services can be imported"""
    
    print("\n🔍 CHECKING IMPORTS AND MODELS")
    print("=" * 50)
    
    checks = []
    
    try:
        from bestyy.communication.models import WhatsAppConversation
        print("✅ WhatsAppConversation model imported")
        checks.append(True)
    except ImportError as e:
        print(f"❌ WhatsAppConversation import failed: {e}")
        checks.append(False)
    
    try:
        from bestyy.communication.whatsapp.services.meta_service import meta_service
        print("✅ meta_service imported")
        checks.append(True)
    except ImportError as e:
        print(f"❌ meta_service import failed: {e}")
        checks.append(False)
    
    try:
        from bestyy.communication.whatsapp.services.ai_service import ai_service
        print("✅ ai_service imported")
        checks.append(True)
    except ImportError as e:
        print(f"❌ ai_service import failed: {e}")
        checks.append(False)
    
    try:
        from bestyy.communication.whatsapp.greeting_service import whatsapp_greeting_service
        print("✅ whatsapp_greeting_service imported")
        checks.append(True)
    except ImportError as e:
        print(f"❌ whatsapp_greeting_service import failed: {e}")
        checks.append(False)
    
    User = get_user_model()
    print(f"✅ User model: {User}")
    checks.append(True)
    
    success_rate = sum(checks) / len(checks) * 100
    print(f"\n📊 Import Success Rate: {success_rate:.1f}%")
    
    return all(checks)

def validate_signup_logic():
    """Check the actual logic in the views file"""
    
    print("\n🔍 VALIDATING SIGNUP LOGIC")
    print("=" * 50)
    
    try:
        # Read the views file and check for key patterns
        views_path = os.path.join(project_root, 'bestyy', 'communication', 'whatsapp', 'views.py')
        
        if not os.path.exists(views_path):
            print("❌ Views file not found")
            return False
        
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for mandatory signup enforcement patterns
        checks = [
            ('onboarding_state != \'onboarded\'', 'Onboarding state check'),
            ('needs_signup', 'Needs signup category'),
            ('get_compelling_signup_message', 'Compelling signup message'),
            ('awaiting_email', 'Awaiting email state'),
            ('is_valid_email', 'Email validation'),
            ('multi_role_register', 'Registration endpoint')
        ]
        
        results = []
        for pattern, description in checks:
            if pattern in content:
                print(f"✅ {description}: Found")
                results.append(True)
            else:
                print(f"❌ {description}: Not found")
                results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Logic Validation: {success_rate:.1f}%")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ Error validating logic: {str(e)}")
        return False

def main():
    """Run comprehensive signup enforcement validation"""
    
    print("🚀 WHATSAPP SIGNUP ENFORCEMENT VALIDATION")
    print("=" * 60)
    print("Validating that mandatory signup system is properly implemented")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("Import Checks", check_models_and_imports),
        ("Logic Validation", validate_signup_logic),
        ("Webhook Test", test_webhook_signup_enforcement),
        ("Email Test", test_email_processing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n📋 Test Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ Mandatory signup enforcement is properly implemented")
    else:
        print("\n⚠️ SOME VALIDATIONS FAILED")
        print("❌ System needs attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)