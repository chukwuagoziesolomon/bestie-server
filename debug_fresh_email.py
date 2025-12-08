#!/usr/bin/env python3
"""
Debug WhatsApp email processing for fresh database
"""
import os
import sys
import django
import re

# Set up Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from bestyy.communication.whatsapp.models import WhatsAppConversation

User = get_user_model()

def test_fresh_email_flow():
    """Test email flow with fresh database"""
    
    test_email = "chukwuagoziesolomon@gmail.com"
    test_phone = "+2348123456789"  # Example phone
    
    print("=== FRESH DATABASE EMAIL FLOW TEST ===")
    print(f"Testing email: {test_email}")
    print(f"Testing phone: {test_phone}")
    print()
    
    # Step 1: Verify database is fresh
    print("Step 1: Checking database state...")
    total_users = User.objects.count()
    total_conversations = WhatsAppConversation.objects.count()
    print(f"  Total users in database: {total_users}")
    print(f"  Total conversations in database: {total_conversations}")
    
    # Step 2: Check if this specific email exists
    print(f"\nStep 2: Checking if {test_email} exists...")
    existing_user = User.objects.filter(email=test_email).first()
    if existing_user:
        print(f"  ❌ User exists: {existing_user.email} (ID: {existing_user.id})")
        print(f"  This should NOT happen in fresh database!")
    else:
        print(f"  ✅ No user found - this is correct for fresh database")
    
    # Step 3: Test email regex
    print(f"\nStep 3: Testing email regex...")
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    content = test_email
    email_match = re.search(email_pattern, content)
    if email_match:
        extracted = email_match.group()
        print(f"  ✅ Email regex matched: '{extracted}'")
        print(f"  Extracted email equals test email: {extracted == test_email}")
    else:
        print(f"  ❌ Email regex failed")
    
    # Step 4: Simulate the flow logic
    print(f"\nStep 4: Simulating WhatsApp flow logic...")
    
    # Check what would happen
    if not existing_user:
        print("  Expected flow: Create new user account")
        print("  Expected message: Account creation success + welcome")
        
        # Test the API endpoint URL construction
        from django.conf import settings
        base_url = (
            getattr(settings, 'SELF_BASE_URL', '') or
            getattr(settings, 'PUBLIC_BASE_URL', '') or
            getattr(settings, 'API_BASE_URL', '') or
            getattr(settings, 'BASE_URL', '')
        ).rstrip('/') or 'http://127.0.0.1:8000'
        endpoint = f"{base_url}/api/user/register/multi-role/"
        print(f"  Registration endpoint: {endpoint}")
        
        # Test payload structure
        contact_name = "Test User"  # Simulate contact name
        import secrets
        password = secrets.token_urlsafe(8)
        payload = {
            'email': test_email,
            'first_name': (contact_name.split()[0] if contact_name else 'WhatsApp'),
            'last_name': (' '.join(contact_name.split()[1:]) if contact_name and len(contact_name.split()) > 1 else 'User'),
            'phone': test_phone,
            'password': password,
            'confirm_password': password,
            'roles': ['user']
        }
        print(f"  Registration payload:")
        for key, value in payload.items():
            if key in ['password', 'confirm_password']:
                print(f"    {key}: [REDACTED]")
            else:
                print(f"    {key}: {value}")
    else:
        print("  Unexpected flow: User exists (shouldn't happen)")
    
    print()
    print("=== ANALYSIS ===")
    if total_users == 0:
        print("✅ Database is fresh - ready for testing")
        print("✅ Email should trigger new user creation")
        print("❓ If bot still repeats email request, issue is in flow logic")
    else:
        print("⚠️  Database has existing users - may affect testing")
    
    print("=== TEST COMPLETE ===")

if __name__ == '__main__':
    test_fresh_email_flow()