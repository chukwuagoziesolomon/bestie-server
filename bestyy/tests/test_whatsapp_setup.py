#!/usr/bin/env python3
"""
Test script to demonstrate WhatsApp dual-service setup
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from django.conf import settings
from user.services.whatsapp_vendor_service import WhatsAppVendorNotificationService

def test_whatsapp_setup():
    """Test WhatsApp service configuration"""
    print("🔧 Testing WhatsApp Dual-Service Setup")
    print("=" * 50)
    
    # Check environment
    is_production = not getattr(settings, 'DEBUG', True)
    print(f"Environment: {'Production' if is_production else 'Development'}")
    print(f"DEBUG mode: {getattr(settings, 'DEBUG', True)}")
    
    # Check configurations
    twilio_configured = bool(getattr(settings, 'TWILIO_ACCOUNT_SID', None))
    whatsapp_business_configured = bool(getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None))
    
    print(f"\n📱 Service Configurations:")
    print(f"Twilio WhatsApp: {'✅ Configured' if twilio_configured else '❌ Not configured'}")
    print(f"WhatsApp Business API: {'✅ Configured' if whatsapp_business_configured else '❌ Not configured'}")
    
    # Initialize service
    try:
        service = WhatsAppVendorNotificationService()
        print(f"\n🎯 Service Selection:")
        print(f"Service Type: {service.service_type}")
        print(f"Environment: {service.environment}")
        
        # Test service availability
        if service.service_type:
            print(f"✅ WhatsApp service ready: {service.service_type}")
        else:
            print("❌ No WhatsApp service available")
            
    except Exception as e:
        print(f"❌ Error initializing service: {e}")
    
    print(f"\n📋 Expected Behavior:")
    if is_production:
        print("Production: Should use WhatsApp Business API (if configured)")
        print("Fallback: Twilio (if Business API not available)")
    else:
        print("Development: Should use Twilio (if configured)")
        print("Fallback: WhatsApp Business API (if Twilio not available)")
    
    print(f"\n🚀 Next Steps:")
    if not twilio_configured and not whatsapp_business_configured:
        print("1. Configure at least one WhatsApp service:")
        print("   - For development: Add Twilio credentials to .env")
        print("   - For production: Add WhatsApp Business API credentials to .env")
    else:
        print("1. Test the service:")
        print("   curl -X GET http://localhost:8000/api/user/whatsapp/config/")
        print("2. Send test message:")
        print("   curl -X POST http://localhost:8000/api/user/whatsapp/test/ \\")
        print("     -H 'Authorization: Bearer YOUR_TOKEN' \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"phone_number\": \"+234-123-456-7890\"}'")

if __name__ == "__main__":
    test_whatsapp_setup()






