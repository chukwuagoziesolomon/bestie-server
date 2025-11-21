"""
Test script for Paystack Transfer API integration
Tests the automated payment system for vendors and couriers
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from decimal import Decimal
from bestyy.core_features.user.services.paystack_transfer_service import (
    PaystackTransferService,
    OrderPaymentAutomation
)


def test_paystack_transfer_service():
    """Test Paystack Transfer Service basic functionality."""
    print("\n" + "="*60)
    print("TESTING PAYSTACK TRANSFER SERVICE")
    print("="*60)
    
    service = PaystackTransferService()
    
    # Test 1: Get list of banks
    print("\n📋 Test 1: Getting list of banks")
    print("-" * 60)
    banks = service.get_banks(country='nigeria', currency='NGN')
    
    if banks:
        print(f"✅ Successfully retrieved {len(banks)} banks")
        print(f"Sample banks:")
        for bank in banks[:5]:
            print(f"   - {bank.get('name')} ({bank.get('code')})")
    else:
        print("❌ Failed to retrieve banks")
    
    # Test 2: Create transfer recipient (example - requires actual bank details)
    print("\n👤 Test 2: Create Transfer Recipient")
    print("-" * 60)
    print("ℹ️  Skipping actual recipient creation (requires valid bank details)")
    print("Example usage:")
    print("   recipient = service.create_transfer_recipient(")
    print("       account_number='0123456789',")
    print("       bank_code='058',  # GTBank")
    print("       name='Test Vendor',")
    print("       metadata={'vendor_id': '123'}")
    print("   )")
    
    # Test 3: Verify transfer reference format
    print("\n🔑 Test 3: Transfer Reference Generation")
    print("-" * 60)
    import uuid
    order_number = "ORD123456"
    vendor_ref = f"vendor_{order_number}_{uuid.uuid4().hex[:16]}"
    courier_ref = f"courier_{order_number}_{uuid.uuid4().hex[:16]}"
    
    print(f"✅ Vendor reference: {vendor_ref}")
    print(f"✅ Courier reference: {courier_ref}")
    print(f"   Length: {len(vendor_ref)} chars (should be 16-50)")
    
    # Test 4: Payout calculation
    print("\n💰 Test 4: Payout Calculation")
    print("-" * 60)
    from bestyy.restaurant_features.order.models import Order
    
    # Sample order data
    total_amount = Decimal('10000.00')  # ₦10,000
    delivery_fee = Decimal('1500.00')    # ₦1,500
    platform_fee_rate = Decimal('0.10')  # 10%
    
    platform_fee = total_amount * platform_fee_rate
    vendor_amount = total_amount - platform_fee - delivery_fee
    courier_amount = delivery_fee
    
    print(f"   Total Amount:    ₦{total_amount:,.2f}")
    print(f"   Platform Fee (10%): ₦{platform_fee:,.2f}")
    print(f"   Delivery Fee:    ₦{delivery_fee:,.2f}")
    print(f"   ---")
    print(f"   Vendor Gets:     ₦{vendor_amount:,.2f}")
    print(f"   Courier Gets:    ₦{courier_amount:,.2f}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    
    print("\n📝 NEXT STEPS:")
    print("1. Configure vendor/courier bank accounts in their profiles")
    print("2. Create transfer recipients on Paystack")
    print("3. Test pickup code verification → vendor payment")
    print("4. Test delivery OTP verification → courier payment")
    print("5. Set up Paystack webhook: https://yourdomain.com/api/webhooks/paystack/transfer/")
    print("6. Disable OTP in Paystack dashboard for automated transfers")


def test_order_payment_flow():
    """Test the complete order payment flow."""
    print("\n" + "="*60)
    print("TESTING ORDER PAYMENT AUTOMATION FLOW")
    print("="*60)
    
    from bestyy.restaurant_features.order.models import Order
    from bestyy.core_features.user.models import VendorProfile, CourierProfile, User
    
    # Check if there are any orders
    orders = Order.objects.filter(payment_confirmed=True).order_by('-created_at')[:5]
    
    if not orders:
        print("\n⚠️  No paid orders found in database")
        print("Create a test order first to test the payment flow")
        return
    
    print(f"\n📦 Found {orders.count()} recent orders")
    
    for order in orders:
        print(f"\n{'='*60}")
        print(f"Order: {order.order_number}")
        print(f"{'='*60}")
        print(f"Status: {order.status}")
        print(f"Total Amount: ₦{order.total_amount:,.2f}")
        print(f"Delivery Fee: ₦{order.delivery_fee or 0:,.2f}")
        
        # Calculate payouts
        payouts = order.calculate_payouts()
        print(f"\n💰 Calculated Payouts:")
        print(f"   Vendor:   ₦{payouts['vendor_amount']:,.2f}")
        print(f"   Courier:  ₦{payouts['courier_amount']:,.2f}")
        print(f"   Platform: ₦{payouts['platform_fee']:,.2f}")
        
        # Check vendor payment status
        print(f"\n👨‍💼 Vendor Payment:")
        print(f"   Paid: {order.vendor_paid}")
        if order.vendor_paid:
            print(f"   Paid At: {order.vendor_paid_at}")
            print(f"   Transfer Code: {order.vendor_transfer_code}")
            print(f"   Status: {order.vendor_transfer_status}")
        print(f"   Reference: {order.vendor_transfer_reference or 'Not generated'}")
        
        # Check courier payment status
        print(f"\n🚴 Courier Payment:")
        print(f"   Paid: {order.courier_paid}")
        if order.courier_paid:
            print(f"   Paid At: {order.courier_paid_at}")
            print(f"   Transfer Code: {order.courier_transfer_code}")
            print(f"   Status: {order.courier_transfer_status}")
        print(f"   Reference: {order.courier_transfer_reference or 'Not generated'}")
        
        # Check pickup code
        print(f"\n🔐 Verification Codes:")
        print(f"   Pickup Code: {order.pickup_code or 'Not generated'}")
        print(f"   Delivery OTP: {order.delivery_otp or 'Not generated'}")


if __name__ == '__main__':
    try:
        test_paystack_transfer_service()
        test_order_payment_flow()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
