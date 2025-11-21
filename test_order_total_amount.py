"""
Check what Order.total_amount actually stores in your database
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.restaurant_features.order.models import Order
from decimal import Decimal

print("="*80)
print("CHECKING Order.total_amount FIELD")
print("="*80)

# Get recent orders with delivery fees
orders = Order.objects.filter(
    delivery_fee__isnull=False,
    delivery_fee__gt=0
).order_by('-created_at')[:5]

if not orders.exists():
    print("\n⚠️  No orders with delivery fees found in database")
    print("\nLet's check ALL orders:")
    all_orders = Order.objects.all().order_by('-created_at')[:5]
    
    for order in all_orders:
        print(f"\n{'─'*80}")
        print(f"Order: {order.order_number}")
        print(f"  total_amount: ₦{order.total_amount:,.2f}")
        print(f"  delivery_fee: ₦{order.delivery_fee or 0:,.2f}")
        print(f"  Status: {order.status}")
else:
    print(f"\n✅ Found {orders.count()} orders with delivery fees\n")
    
    for order in orders:
        print(f"\n{'='*80}")
        print(f"Order: {order.order_number}")
        print(f"{'='*80}")
        
        print(f"\n📊 Stored Values:")
        print(f"   total_amount:  ₦{order.total_amount:,.2f}")
        print(f"   delivery_fee:  ₦{order.delivery_fee:,.2f}")
        
        # Calculate what food subtotal would be
        if order.total_amount > order.delivery_fee:
            possible_food_subtotal = order.total_amount - order.delivery_fee
            print(f"\n🔍 Analysis:")
            print(f"   If total_amount includes delivery:")
            print(f"      → Food subtotal would be: ₦{possible_food_subtotal:,.2f}")
            print(f"      → total_amount = food + delivery")
            print(f"      → ₦{possible_food_subtotal:,.2f} + ₦{order.delivery_fee:,.2f} = ₦{order.total_amount:,.2f} ✓")
        else:
            print(f"\n🔍 Analysis:")
            print(f"   total_amount does NOT include delivery")
            print(f"      → total_amount = food only (₦{order.total_amount:,.2f})")
            print(f"      → delivery_fee separate (₦{order.delivery_fee:,.2f})")
        
        # Show current payout calculation
        print(f"\n💰 Current calculate_payouts() result:")
        payouts = order.calculate_payouts()
        print(f"   Vendor gets:   ₦{payouts['vendor_amount']:,.2f}")
        print(f"   Courier gets:  ₦{payouts['courier_amount']:,.2f}")
        print(f"   Platform gets: ₦{payouts['platform_fee']:,.2f}")
        
        total_distributed = payouts['vendor_amount'] + payouts['courier_amount'] + payouts['platform_fee']
        print(f"   {'─'*40}")
        print(f"   Total distributed: ₦{total_distributed:,.2f}")
        
        # Verify the math
        if order.total_amount > order.delivery_fee:
            # Assuming total_amount includes delivery
            expected_total = order.total_amount
        else:
            # Assuming total_amount excludes delivery
            expected_total = order.total_amount + order.delivery_fee
        
        difference = abs(expected_total - total_distributed)
        
        if difference < Decimal('0.01'):
            print(f"\n   ✅ Math checks out! Money adds up correctly.")
        else:
            print(f"\n   ⚠️  WARNING: Money doesn't add up!")
            print(f"   Expected: ₦{expected_total:,.2f}")
            print(f"   Distributed: ₦{total_distributed:,.2f}")
            print(f"   Difference: ₦{difference:,.2f}")
        
        # Check order items to see actual food cost
        items = order.items.all()
        if items.exists():
            print(f"\n📦 Order Items:")
            items_total = Decimal('0')
            for item in items:
                item_total = item.quantity * item.price
                items_total += item_total
                print(f"   - {item.quantity}x @ ₦{item.price:,.2f} = ₦{item_total:,.2f}")
            print(f"   {'─'*40}")
            print(f"   Items Total: ₦{items_total:,.2f}")
            
            # Compare with total_amount
            if abs(items_total - order.total_amount) < Decimal('0.01'):
                print(f"\n   ✅ CONFIRMED: total_amount = Food Items Only")
                print(f"   total_amount (₦{order.total_amount:,.2f}) matches items_total")
            elif abs(items_total + order.delivery_fee - order.total_amount) < Decimal('0.01'):
                print(f"\n   ✅ CONFIRMED: total_amount = Food Items + Delivery")
                print(f"   total_amount (₦{order.total_amount:,.2f}) = items (₦{items_total:,.2f}) + delivery (₦{order.delivery_fee:,.2f})")
            else:
                print(f"\n   ⚠️  MISMATCH DETECTED!")
                print(f"   Items total: ₦{items_total:,.2f}")
                print(f"   total_amount: ₦{order.total_amount:,.2f}")
                print(f"   Difference: ₦{abs(items_total - order.total_amount):,.2f}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

# Final recommendation
print("""
Based on the data above, your total_amount field stores:
[ ] Food items only
[ ] Food items + Delivery fee

Your current calculate_payouts() implementation is:
    platform_fee = total_amount * 0.10
    vendor_amount = total_amount - platform_fee - delivery_fee
    courier_amount = delivery_fee

This is CORRECT if total_amount = Food items only
This is WRONG if total_amount = Food + Delivery (platform takes 10% of delivery too!)

Recommendation: Update the code to be explicit about what it's calculating!
""")
