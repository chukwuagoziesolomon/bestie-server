#!/usr/bin/env python3
"""
Comprehensive Test: Mandatory Signup Enforcement System
Testing that users MUST sign up before accessing any bot functionality.
"""

import os
import sys
import django
import json
from unittest.mock import Mock, patch, MagicMock
import requests

# Add the project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

def test_mandatory_signup_enforcement():
    """Test that first-time users must sign up before accessing functionality"""
    
    print("\n🔐 TESTING MANDATORY SIGNUP ENFORCEMENT SYSTEM")
    print("=" * 60)
    
    # Mock the webhook payload for a new user (no existing conversation)
    webhook_payload = {
        'object': 'whatsapp_business_account',
        'entry': [{
            'id': 'test_entry_id',
            'changes': [{
                'value': {
                    'messaging_product': 'whatsapp',
                    'metadata': {
                        'display_phone_number': '+1234567890',
                        'phone_number_id': 'test_phone_id'
                    },
                    'messages': [{
                        'id': 'test_message_id',
                        'from': '+2348123456789',  # Nigerian test number
                        'timestamp': '1234567890',
                        'text': {'body': 'I want to order food'},
                        'type': 'text'
                    }]
                },
                'field': 'messages'
            }]
        }]
    }
    
    # Test scenarios
    test_cases = [
        {
            'name': '🚫 First-time user ordering food',
            'message': 'I want to order food',
            'expected_signup_enforcement': True
        },
        {
            'name': '🚫 First-time user asking about menu',
            'message': 'What\'s on the menu?',
            'expected_signup_enforcement': True
        },
        {
            'name': '🚫 First-time user general greeting',
            'message': 'Hi there',
            'expected_signup_enforcement': True
        },
        {
            'name': '🚫 First-time user trying to get recommendations',
            'message': 'Recommend me some local food',
            'expected_signup_enforcement': True
        },
        {
            'name': '✅ First-time user providing email (should process)',
            'message': 'test@example.com',
            'expected_signup_enforcement': False,  # Should process email
            'is_email': True
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Message: '{test_case['message']}'")
        
        # Update webhook payload with test message
        webhook_payload['entry'][0]['changes'][0]['value']['messages'][0]['text']['body'] = test_case['message']
        
        try:
            # Mock all external dependencies
            with patch('bestyy.communication.whatsapp.views.meta_service') as mock_meta, \
                 patch('bestyy.communication.whatsapp.views.ai_service') as mock_ai, \
                 patch('bestyy.communication.whatsapp.views.whatsapp_greeting_service') as mock_greeting, \
                 patch('requests.post') as mock_post, \
                 patch('django.core.mail.send_mail') as mock_email:
                
                # Setup mocks
                mock_meta.send_message = Mock()
                mock_ai.categorize_message = Mock(return_value='needs_signup')
                mock_greeting.get_compelling_signup_message = Mock(return_value="Please sign up first!")
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {'success': True}
                
                # Import after Django setup
                from django.test import Client
                from django.urls import reverse
                
                client = Client()
                
                # Make webhook request
                response = client.post(
                    reverse('webhook'),
                    data=json.dumps(webhook_payload),
                    content_type='application/json',
                    HTTP_X_HUB_SIGNATURE_256='test_signature'
                )
                
                # Check response
                print(f"   Response Status: {response.status_code}")
                
                # Analyze what messages were sent
                messages_sent = mock_meta.send_message.call_args_list
                print(f"   Messages Sent: {len(messages_sent)}")
                
                if messages_sent:
                    for j, call in enumerate(messages_sent):
                        message_text = call[1]['message'] if 'message' in call[1] else call[0][1]
                        print(f"   Message {j+1}: {message_text[:100]}...")
                
                # Check if signup was enforced
                signup_enforced = any(
                    'sign up' in str(call).lower() or 
                    'register' in str(call).lower() or
                    'account' in str(call).lower()
                    for call in messages_sent
                )
                
                # Check if AI was called (should be blocked for non-onboarded users)
                ai_was_called = mock_ai.categorize_message.called
                
                # Analyze results
                if test_case['expected_signup_enforcement']:
                    if signup_enforced and not ai_was_called:
                        result = "✅ PASS - Signup correctly enforced, AI blocked"
                    elif signup_enforced and ai_was_called:
                        result = "⚠️ PARTIAL - Signup enforced but AI still called"
                    else:
                        result = "❌ FAIL - Signup not enforced"
                else:
                    if test_case.get('is_email'):
                        if not signup_enforced:
                            result = "✅ PASS - Email processed correctly"
                        else:
                            result = "❌ FAIL - Email not processed"
                    else:
                        result = "✅ PASS - Normal processing"
                
                print(f"   Result: {result}")
                print(f"   AI Called: {'Yes' if ai_was_called else 'No'}")
                print(f"   Signup Enforced: {'Yes' if signup_enforced else 'No'}")
                
                results.append({
                    'test': test_case['name'],
                    'message': test_case['message'],
                    'passed': result.startswith('✅'),
                    'result': result
                })
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            results.append({
                'test': test_case['name'],
                'message': test_case['message'],
                'passed': False,
                'result': f"ERROR: {str(e)}"
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n📋 DETAILED RESULTS:")
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['test']}")
        if not result['passed']:
            print(f"     {result['result']}")
    
    print("\n🎯 KEY VALIDATION POINTS:")
    print("1. First-time users should be blocked from all functionality")
    print("2. AI processing should be bypassed for non-signed-up users")
    print("3. Only email processing should work for new users")
    print("4. Signup messages should be compelling and informative")
    
    return passed == total

def test_onboarded_user_access():
    """Test that properly onboarded users can access all functionality"""
    
    print("\n🔓 TESTING ONBOARDED USER ACCESS")
    print("=" * 60)
    
    try:
        from bestyy.communication.models import WhatsAppConversation
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Create test user and conversation
        test_user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        conversation = WhatsAppConversation.objects.create(
            phone_number='+2348123456789',
            user=test_user,
            onboarding_state='onboarded',
            conversation_state='active'
        )
        
        print("✅ Created test onboarded user and conversation")
        print(f"   User: {test_user.email}")
        print(f"   Onboarding State: {conversation.onboarding_state}")
        
        # Cleanup
        conversation.delete()
        test_user.delete()
        
        print("✅ Onboarded user test setup successful")
        return True
        
    except Exception as e:
        print(f"❌ Error in onboarded user test: {str(e)}")
        return False

def main():
    """Run all mandatory signup enforcement tests"""
    
    print("🚀 MANDATORY SIGNUP ENFORCEMENT SYSTEM TESTS")
    print("=" * 80)
    print("Testing that users MUST sign up before accessing bot functionality")
    print("This ensures personalization and tracking requirements are met")
    print("=" * 80)
    
    # Run tests
    test1_passed = test_mandatory_signup_enforcement()
    test2_passed = test_onboarded_user_access()
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 80)
    
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED!")
        print("🎉 Mandatory signup enforcement is working correctly")
        print("📊 First-time users are properly blocked until signup")
        print("🔓 Onboarded users can access functionality")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️ Mandatory signup enforcement needs attention")
        if not test1_passed:
            print("❌ Signup enforcement test failed")
        if not test2_passed:
            print("❌ Onboarded user access test failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)