"""
Diagnostic Script: Check Vendor Profile Setup
"""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import VendorProfile
from bestyy.communication.whatsapp.models import WhatsAppConversation

def check_vendor_setup():
    print("\n" + "="*60)
    print("🔍 VENDOR PROFILE DIAGNOSTIC")
    print("="*60)
    
    # Check vendors
    vendors = VendorProfile.objects.all()
    print(f"\n📊 Total vendors in system: {vendors.count()}")
    
    for vendor in vendors:
        print(f"\n{'='*60}")
        print(f"🏪 Vendor: {vendor.business_name}")
        print(f"   ID: {vendor.id}")
        print(f"   User: {vendor.user.username if vendor.user else 'No user'}")
        print(f"   Phone: {vendor.phone}")
        print(f"   Suspended: {vendor.is_suspended}")
        
        # Check if vendor has WhatsApp conversation
        if vendor.user:
            convs = WhatsAppConversation.objects.filter(user=vendor.user)
            print(f"\n   📱 WhatsApp Conversations: {convs.count()}")
            for conv in convs:
                print(f"      - Phone: {conv.phone_number}")
                print(f"      - Last: {conv.updated_at}")
        else:
            # Try to find conversation by phone
            convs = WhatsAppConversation.objects.filter(phone_number__icontains=vendor.phone[-10:])
            print(f"\n   ⚠️ Vendor has no User account linked!")
            print(f"   📱 WhatsApp Conversations found by phone: {convs.count()}")
            for conv in convs:
                print(f"      - Phone: {conv.phone_number}")
                print(f"      - User: {conv.user.username if conv.user else 'None'}")
                print(f"      - Last: {conv.updated_at}")
        
        # Check pending orders
        from bestyy.restaurant_features.order.models import Order
        pending = Order.objects.filter(
            vendor=vendor,
            status='confirmed',
            payment_status=True
        ).count()
        print(f"\n   📦 Pending orders (waiting for ACCEPT): {pending}")
    
    print("\n" + "="*60)
    print("💡 INSTRUCTIONS:")
    print("="*60)
    print("1. Make sure vendor is logged in via WhatsApp at least once")
    print("2. Vendor's WhatsApp number must match the phone in VendorProfile")
    print("3. Vendor must have state='onboarded' in WhatsAppConversation")
    print("4. When vendor types ACCEPT, system should recognize them")
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        check_vendor_setup()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
