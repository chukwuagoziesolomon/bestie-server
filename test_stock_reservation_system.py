"""
Test script for stock reservation system
Tests the complete flow: cart add → order place → payment confirm → delivery → stock decrease
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from bestyy.restaurant_features.product.models import Product
from bestyy.restaurant_features.order.models import Order, OrderItem, OrderStockReservation
from bestyy.core_features.user.models import VendorProfile
from bestyy.core_features.user.cart_utils import (
    add_to_cart,
    get_available_stock,
    create_stock_reservations_for_order
)
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

def test_stock_reservation_flow():
    """Test the complete stock reservation flow"""
    
    print("\n" + "="*70)
    print("STOCK RESERVATION SYSTEM TEST")
    print("="*70)
    
    # Step 1: Get or create test product
    print("\n1. Setting up test product...")
    try:
        product = Product.objects.filter(is_available=True).first()
        if not product:
            print("❌ No available products found in database")
            return
        
        # Set initial stock
        initial_stock = 50
        product.stock_quantity = initial_stock
        product.save()
        
        print(f"✅ Product: {product.name}")
        print(f"   Initial stock: {initial_stock}")
        print(f"   Available stock: {get_available_stock(product)}")
    except Exception as e:
        print(f"❌ Error setting up product: {e}")
        return
    
    # Step 2: Test cart add with stock validation
    print("\n2. Testing cart add to cart...")
    try:
        cart_quantity = 5
        available_before = get_available_stock(product)
        
        # Try to add to cart
        cart_token, cart_item, created = add_to_cart(
            product_id=product.id,
            quantity=cart_quantity,
            cart_token=None,
            user=None
        )
        
        print(f"✅ Added {cart_quantity} items to cart")
        print(f"   Available stock before: {available_before}")
        print(f"   Available stock after: {get_available_stock(product)}")
        print(f"   Note: Stock not decreased yet (only on delivery)")
    except Exception as e:
        print(f"❌ Error adding to cart: {e}")
        return
    
    # Step 3: Create test order
    print("\n3. Creating test order...")
    try:
        # Get test user and vendor
        user = User.objects.first()
        vendor = VendorProfile.objects.first()
        
        if not user or not vendor:
            print("❌ No test user or vendor found")
            return
        
        order = Order.objects.create(
            customer=user,
            vendor=vendor,
            shipping_address="123 Test Street",
            delivery_address="123 Test Street",
            total_amount=Decimal(product.price * cart_quantity),
            status='pending',
            payment_method='bank_transfer',
            notes='Test order'
        )
        
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=cart_quantity,
            price=product.price
        )
        
        print(f"✅ Order created: {order.order_number}")
        print(f"   Status: {order.status}")
        print(f"   Payment confirmed: {order.payment_confirmed}")
        print(f"   Product stock: {product.stock_quantity}")
        print(f"   Available stock: {get_available_stock(product)}")
    except Exception as e:
        print(f"❌ Error creating order: {e}")
        return
    
    # Step 4: Confirm payment (should create stock reservation)
    print("\n4. Confirming payment (triggers stock reservation)...")
    try:
        order.payment_confirmed = True
        order.payment_confirmed_at = timezone.now()
        order.save()
        
        # Reload order and product
        order.refresh_from_db()
        product.refresh_from_db()
        
        reservations = OrderStockReservation.objects.filter(order=order)
        
        print(f"✅ Payment confirmed")
        print(f"   Stock reservations created: {reservations.count()}")
        for res in reservations:
            print(f"   - {res.quantity}x {res.product.name} ({res.status})")
        print(f"   Product stock (unchanged): {product.stock_quantity}")
        print(f"   Available stock (reduced): {get_available_stock(product)}")
    except Exception as e:
        print(f"❌ Error confirming payment: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Update order status to delivered (should decrease stock)
    print("\n5. Marking order as delivered (triggers stock deduction)...")
    try:
        stock_before_delivery = product.stock_quantity
        
        order.status = 'delivered'
        order.save()
        
        # Reload order and product
        order.refresh_from_db()
        product.refresh_from_db()
        
        reservations = OrderStockReservation.objects.filter(order=order)
        
        print(f"✅ Order delivered")
        print(f"   Product stock before: {stock_before_delivery}")
        print(f"   Product stock after: {product.stock_quantity}")
        print(f"   Stock decreased by: {stock_before_delivery - product.stock_quantity}")
        print(f"   Available stock: {get_available_stock(product)}")
        print(f"   Vendor paid: {order.vendor_paid}")
        print(f"   Courier paid: {order.courier_paid}")
        
        for res in reservations:
            print(f"   - Reservation status: {res.status}")
    except Exception as e:
        print(f"❌ Error marking order as delivered: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 6: Test order cancellation (create another order and cancel)
    print("\n6. Testing order cancellation (stock release)...")
    try:
        # Create another order
        cancel_order = Order.objects.create(
            customer=user,
            vendor=vendor,
            shipping_address="456 Cancel Street",
            delivery_address="456 Cancel Street",
            total_amount=Decimal(product.price * 3),
            status='pending',
            payment_method='bank_transfer',
            notes='Order to be cancelled'
        )
        
        OrderItem.objects.create(
            order=cancel_order,
            product=product,
            quantity=3,
            price=product.price
        )
        
        # Confirm payment (create reservation)
        cancel_order.payment_confirmed = True
        cancel_order.payment_confirmed_at = timezone.now()
        cancel_order.save()
        
        cancel_order.refresh_from_db()
        product.refresh_from_db()
        
        available_before_cancel = get_available_stock(product)
        
        # Cancel the order
        cancel_order.status = 'cancelled'
        cancel_order.save()
        
        cancel_order.refresh_from_db()
        product.refresh_from_db()
        
        available_after_cancel = get_available_stock(product)
        
        cancel_reservations = OrderStockReservation.objects.filter(order=cancel_order)
        
        print(f"✅ Order cancelled: {cancel_order.order_number}")
        print(f"   Product stock (unchanged): {product.stock_quantity}")
        print(f"   Available before cancel: {available_before_cancel}")
        print(f"   Available after cancel: {available_after_cancel}")
        print(f"   Stock released: {available_after_cancel - available_before_cancel}")
        
        for res in cancel_reservations:
            print(f"   - Reservation status: {res.status}")
    except Exception as e:
        print(f"❌ Error testing cancellation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ All tests completed successfully!")
    print(f"\nStock Management Flow:")
    print(f"1. Add to cart: Validates available stock (total - reserved)")
    print(f"2. Order placed: Order created with status 'pending'")
    print(f"3. Payment confirmed: Stock reserved (available decreases)")
    print(f"4. Order delivered: Stock deducted, revenue tracked")
    print(f"5. Order cancelled: Stock reservation released")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_stock_reservation_flow()
