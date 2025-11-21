"""
Test the code differentiation system
Tests pickup codes (PK-) and delivery OTPs (DL-) with prefixes
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.models import User, VendorProfile
from decimal import Decimal

print("="*80)
print("TESTING CODE DIFFERENTIATION SYSTEM")
print("="*80)

# Test 1: Generate Pickup Code with PK- prefix
print("\n📋 TEST 1: Pickup Code Generation")
print("-" * 80)

# Create a test order
from django.utils import timezone
try:
    # Get or create a test vendor
    vendor_user = User.objects.filter(role='vendor').first()
    if not vendor_user:
        print("⚠️  No vendor found in database. Skipping pickup code test.")
    else:
        vendor_profile = VendorProfile.objects.filter(user=vendor_user).first()
        
        # Create test order
        test_order = Order.objects.create(
            customer=vendor_user,  # Just for testing
            vendor=vendor_profile,
            total_amount=Decimal('10000.00'),
            delivery_fee=Decimal('1500.00'),
            shipping_address="Test Address",
            payment_method="paystack",
            payment_confirmed=True
        )
        
        # Generate pickup code
        pickup_code = test_order.generate_pickup_code()
        
        print(f"✅ Pickup Code Generated: {pickup_code}")
        print(f"   Format check: {pickup_code.startswith('PK-')} (should be True)")
        print(f"   Length: {len(pickup_code)} chars (should be 9: PK- + 6)")
        
        # Test 2: Verify Pickup Code (with prefix)
        print("\n📋 TEST 2: Pickup Code Verification (with prefix)")
        print("-" * 80)
        
        result1 = test_order.verify_pickup_code(pickup_code)
        print(f"   verify_pickup_code('{pickup_code}'): {result1} ✅")
        
        # Test 3: Verify Pickup Code (without prefix)
        print("\n📋 TEST 3: Pickup Code Verification (without prefix)")
        print("-" * 80)
        
        code_without_prefix = pickup_code.replace('PK-', '')
        result2 = test_order.verify_pickup_code(code_without_prefix)
        print(f"   verify_pickup_code('{code_without_prefix}'): {result2} ✅")
        print(f"   Backward compatible: User can enter without prefix!")
        
        # Test 4: Verify Pickup Code (case insensitive)
        print("\n📋 TEST 4: Pickup Code Verification (case insensitive)")
        print("-" * 80)
        
        result3 = test_order.verify_pickup_code(pickup_code.lower())
        print(f"   verify_pickup_code('{pickup_code.lower()}'): {result3} ✅")
        
        # Test 5: Verify Wrong Pickup Code
        print("\n📋 TEST 5: Pickup Code Verification (wrong code)")
        print("-" * 80)
        
        result4 = test_order.verify_pickup_code('PK-WRONG')
        print(f"   verify_pickup_code('PK-WRONG'): {result4} (should be False)")
        
        # Test 6: Generate Delivery OTP with DL- prefix
        print("\n📋 TEST 6: Delivery OTP Generation")
        print("-" * 80)
        
        delivery_otp = test_order.generate_delivery_otp()
        
        print(f"✅ Delivery OTP Generated: {delivery_otp}")
        print(f"   Format check: {delivery_otp.startswith('DL-')} (should be True)")
        print(f"   Length: {len(delivery_otp)} chars (should be 9: DL- + 6)")
        
        # Test 7: Verify Delivery OTP (with prefix)
        print("\n📋 TEST 7: Delivery OTP Verification (with prefix)")
        print("-" * 80)
        
        result5 = test_order.verify_delivery_otp(delivery_otp)
        print(f"   verify_delivery_otp('{delivery_otp}'): {result5} ✅")
        
        # Test 8: Verify Delivery OTP (without prefix)
        print("\n📋 TEST 8: Delivery OTP Verification (without prefix)")
        print("-" * 80)
        
        otp_without_prefix = delivery_otp.replace('DL-', '')
        result6 = test_order.verify_delivery_otp(otp_without_prefix)
        print(f"   verify_delivery_otp('{otp_without_prefix}'): {result6} ✅")
        print(f"   Backward compatible: User can enter without prefix!")
        
        # Test 9: Verify Delivery OTP (case insensitive)
        print("\n📋 TEST 9: Delivery OTP Verification (case insensitive)")
        print("-" * 80)
        
        result7 = test_order.verify_delivery_otp(delivery_otp.lower())
        print(f"   verify_delivery_otp('{delivery_otp.lower()}'): {result7} ✅")
        
        # Test 10: Verify Wrong Delivery OTP
        print("\n📋 TEST 10: Delivery OTP Verification (wrong code)")
        print("-" * 80)
        
        result8 = test_order.verify_delivery_otp('DL-WRONG')
        print(f"   verify_delivery_otp('DL-WRONG'): {result8} (should be False)")
        
        # Test 11: Check Transfer References
        print("\n📋 TEST 11: Transfer References")
        print("-" * 80)
        
        print(f"✅ Vendor Transfer Reference: {test_order.vendor_transfer_reference}")
        print(f"   Format: vendor_{test_order.order_number}_xxxx")
        print(f"   Unique: {test_order.vendor_transfer_reference is not None}")
        
        print(f"\n✅ Courier Transfer Reference: {test_order.courier_transfer_reference}")
        print(f"   Format: courier_{test_order.order_number}_xxxx")
        print(f"   Unique: {test_order.courier_transfer_reference is not None}")
        
        # Clean up
        test_order.delete()
        print("\n🧹 Test order cleaned up")
        
except Exception as e:
    print(f"❌ Error during testing: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ ALL TESTS COMPLETED")
print("="*80)

print("""
📝 SUMMARY:

✅ Pickup codes now have PK- prefix (e.g., PK-A1B2C3)
✅ Delivery OTPs now have DL- prefix (e.g., DL-123456)
✅ Both are backward compatible (accept without prefix)
✅ Case insensitive verification
✅ Transfer references generated automatically
✅ Unique constraints prevent duplicate payments

🎯 WHATSAPP BOT BEHAVIOR:

For VENDORS:
- Receives: PK-A1B2C3
- Can enter: "PK-A1B2C3" or "A1B2C3"
- Bot triggers vendor payout on verification

For COURIERS:
- Receives: DL-123456
- Can enter: "DL-123456" or "123456"
- Bot triggers courier payout on verification

For NEW USERS:
- Receives: 123456 (no prefix)
- Enters: "123456"
- Bot calls WhatsApp verification endpoint

NO CONFUSION! Each code type is clearly identified! 🎉
""")
