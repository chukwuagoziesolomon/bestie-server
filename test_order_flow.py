"""
Test Script: Verify Order Flow After "PAID" Confirmation
Tests:
1. Vendor notification (WhatsApp + Websocket)
2. Courier assignment
3. Websocket updates to customer
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.utils import timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import after Django setup
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.models import VendorProfile, CourierProfile
from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService


def test_vendor_notification():
    """Test if vendor receives notification when order is confirmed"""
    print("\n" + "="*60)
    print("TEST 1: Vendor Notification System")
    print("="*60)
    
    # Get most recent confirmed order
    order = Order.objects.filter(
        status='confirmed',
        payment_status=True
    ).order_by('-created_at').first()
    
    if not order:
        print("❌ No confirmed orders found to test")
        return False
    
    print(f"\n✅ Found test order: {order.order_number}")
    print(f"   Vendor: {order.vendor.business_name if order.vendor else 'None'}")
    print(f"   Customer: {order.customer.username if order.customer else 'None'}")
    print(f"   Amount: ₦{order.total_amount}")
    
    # Test vendor notification
    print("\n📤 Sending vendor notification...")
    try:
        result = VendorOrderNotificationService.notify_vendor_new_order(order)
        if result:
            print("✅ Vendor notification sent successfully!")
            print(f"   - WhatsApp notification sent to vendor")
            print(f"   - Vendor should receive order details via WhatsApp")
            return True
        else:
            print("❌ Vendor notification failed")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_courier_assignment():
    """Test if courier assignment works"""
    print("\n" + "="*60)
    print("TEST 2: Courier Assignment System")
    print("="*60)
    
    # Get confirmed order without courier
    order = Order.objects.filter(
        status='confirmed',
        courier__isnull=True
    ).order_by('-created_at').first()
    
    if not order:
        print("❌ No confirmed orders without courier found")
        # Check if there are any couriers at all
        courier_count = CourierProfile.objects.filter(is_suspended=False).count()
        print(f"ℹ️ Available couriers in system: {courier_count}")
        return False
    
    print(f"\n✅ Found order needing courier: {order.order_number}")
    print(f"   Vendor: {order.vendor.business_name if order.vendor else 'None'}")
    print(f"   Delivery Address: {order.delivery_address}")
    
    # Check available couriers
    couriers = CourierProfile.objects.filter(is_suspended=False)
    print(f"\n📍 Available couriers: {couriers.count()}")
    
    if couriers.count() == 0:
        print("⚠️ No active couriers in the system")
        print("   Create a courier account to test assignment")
        return False
    
    # Test courier assignment
    print("\n🚗 Attempting courier assignment...")
    try:
        from bestyy.core_features.user.services.vendor_ready_service import VendorReadyService
        ready_service = VendorReadyService()
        result = ready_service._assign_courier_to_order(order, order.vendor)
        
        if result.get('success'):
            print("✅ Courier assigned successfully!")
            print(f"   - Courier: {result.get('courier_name', 'Unknown')}")
            print(f"   - Distance: {result.get('distance', 'N/A')}")
            print(f"   - Courier should receive WhatsApp notification")
            return True
        else:
            print(f"❌ Courier assignment failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_updates():
    """Test if websocket notifications are configured"""
    print("\n" + "="*60)
    print("TEST 3: Websocket Configuration")
    print("="*60)
    
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            print("❌ Channel layer not configured")
            print("   Websockets will not work")
            return False
        
        print("✅ Channel layer configured")
        print(f"   Backend: {channel_layer.__class__.__name__}")
        
        # Test sending notification
        from asgiref.sync import async_to_sync
        print("\n📡 Testing websocket send...")
        
        try:
            async_to_sync(channel_layer.group_send)(
                'test_group',
                {
                    'type': 'test_message',
                    'data': {'message': 'Test notification'}
                }
            )
            print("✅ Websocket send successful")
            print("   Real-time notifications should work")
            return True
        except Exception as e:
            print(f"❌ Websocket send failed: {str(e)}")
            return False
            
    except ImportError:
        print("❌ Django Channels not installed")
        print("   Install: pip install channels channels-redis")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    print("\n" + "="*60)
    print("🧪 ORDER FLOW INTEGRATION TEST")
    print("="*60)
    print("\nThis script tests the complete order flow after 'PAID' confirmation:")
    print("1. Vendor receives notification (WhatsApp + Websocket)")
    print("2. System assigns nearest courier")
    print("3. Websocket updates work for real-time notifications")
    
    # Run tests
    results = {
        'vendor_notification': test_vendor_notification(),
        'courier_assignment': test_courier_assignment(),
        'websocket': test_websocket_updates()
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All systems working! Order flow is complete.")
    else:
        print(f"\n⚠️ {total - passed} system(s) need attention.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
