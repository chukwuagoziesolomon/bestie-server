#!/usr/bin/env python
"""
Test WhatsApp configuration and token validity
"""
import os
import sys
import django
import requests
from decouple import config

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.conf import settings

def test_whatsapp_config():
    """Test WhatsApp configuration"""
    print("🔍 Testing WhatsApp Configuration...")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    print(f"WHATSAPP_ACCESS_TOKEN: {'✅ SET' if config('WHATSAPP_ACCESS_TOKEN', default='') else '❌ NOT SET'}")
    print(f"WHATSAPP_PHONE_NUMBER_ID: {'✅ SET' if config('WHATSAPP_PHONE_NUMBER_ID', default='') else '❌ NOT SET'}")
    print(f"WHATSAPP_VERIFY_TOKEN: {'✅ SET' if config('WHATSAPP_VERIFY_TOKEN', default='') else '❌ NOT SET'}")
    
    # Check Django settings
    print("\n⚙️ Django Settings:")
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
    verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', None)
    
    print(f"WHATSAPP_ACCESS_TOKEN: {'✅ SET' if access_token else '❌ NOT SET'}")
    print(f"WHATSAPP_PHONE_NUMBER_ID: {'✅ SET' if phone_number_id else '❌ NOT SET'}")
    print(f"WHATSAPP_VERIFY_TOKEN: {'✅ SET' if verify_token else '❌ NOT SET'}")
    
    if not access_token or not phone_number_id:
        print("\n❌ Missing required WhatsApp configuration!")
        return False
    
    # Test token validity
    print("\n🔐 Testing Access Token...")
    try:
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Access token is valid!")
            print(f"📱 Phone Number: {data.get('display_phone_number', 'N/A')}")
            print(f"🆔 Phone Number ID: {data.get('id', 'N/A')}")
            print(f"📊 Status: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"❌ Access token validation failed!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing access token: {str(e)}")
        return False

def test_webhook_verification():
    """Test webhook verification"""
    print("\n🔗 Testing Webhook Verification...")
    print("=" * 50)
    
    verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', None)
    if not verify_token:
        print("❌ WHATSAPP_VERIFY_TOKEN not configured!")
        return False
    
    print(f"✅ Verify token is configured: {verify_token[:10]}...")
    print("📝 To test webhook verification:")
    print("1. Go to your WhatsApp Business API dashboard")
    print("2. Set webhook URL to: https://your-domain.com/api/whatsapp/webhook/")
    print(f"3. Set verify token to: {verify_token}")
    print("4. Click 'Verify and Save'")
    
    return True

if __name__ == "__main__":
    print("🚀 WhatsApp Configuration Test")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_whatsapp_config()
    
    # Test webhook
    webhook_ok = test_webhook_verification()
    
    print("\n" + "=" * 50)
    if config_ok and webhook_ok:
        print("🎉 WhatsApp configuration looks good!")
        print("\n📋 Next steps:")
        print("1. Make sure your .env file has the correct tokens")
        print("2. Restart your Django server")
        print("3. Test sending a message via WhatsApp")
    else:
        print("❌ WhatsApp configuration needs attention!")
        print("\n🔧 Fix these issues:")
        if not config_ok:
            print("- Update your .env file with valid WhatsApp tokens")
        if not webhook_ok:
            print("- Configure webhook verification in WhatsApp dashboard")


