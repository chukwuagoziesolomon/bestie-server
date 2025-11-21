"""
Check the actual payment_confirmed status of all orders
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.restaurant_features.order.models import Order
from decimal import Decimal

print("=" * 70)
print("CHECKING ACTUAL PAYMENT_CONFIRMED STATUS")
print("=" * 70)

# Get all orders
all_orders = Order.objects.all().order_by('-created_at')[:20]

print(f"\nTotal orders in database: {Order.objects.count()}")
print("\nRecent orders (last 20):")
print("-" * 70)

confirmed_total = Decimal('0.00')
unconfirmed_total = Decimal('0.00')

for order in all_orders:
    vendor_name = order.vendor.business_name if order.vendor else "No vendor"
    status_icon = "✅" if order.payment_confirmed else "❌"
    
    print(f"\n{status_icon} Order #{str(order.id)[:8]}...")
    print(f"   Amount: ₦{float(order.total_amount):,.2f}")
    print(f"   Vendor: {vendor_name}")
    print(f"   Payment Confirmed: {order.payment_confirmed}")
    print(f"   Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    if order.payment_confirmed:
        confirmed_total += order.total_amount
    else:
        unconfirmed_total += order.total_amount

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total revenue from CONFIRMED payments: ₦{float(confirmed_total):,.2f}")
print(f"Total revenue from UNCONFIRMED payments: ₦{float(unconfirmed_total):,.2f}")
print(f"Grand total: ₦{float(confirmed_total + unconfirmed_total):,.2f}")

# Check specifically the orders from this month
from django.utils import timezone
now = timezone.now()
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

month_orders = Order.objects.filter(
    created_at__gte=start_of_month,
    created_at__lte=now
).order_by('-created_at')

print(f"\n\nORDERS THIS MONTH (Nov 2025):")
print("-" * 70)
print(f"Total orders this month: {month_orders.count()}")

month_confirmed = Decimal('0.00')
month_unconfirmed = Decimal('0.00')

for order in month_orders:
    vendor_name = order.vendor.business_name if order.vendor else "No vendor"
    status_icon = "✅" if order.payment_confirmed else "❌"
    
    print(f"\n{status_icon} Order #{str(order.id)[:8]}... - ₦{float(order.total_amount):,.2f}")
    print(f"   Vendor: {vendor_name}")
    print(f"   Payment Confirmed: {order.payment_confirmed}")
    
    if order.payment_confirmed:
        month_confirmed += order.total_amount
    else:
        month_unconfirmed += order.total_amount

print("\n" + "=" * 70)
print("THIS MONTH BREAKDOWN")
print("=" * 70)
print(f"✅ Confirmed payments: ₦{float(month_confirmed):,.2f}")
print(f"❌ Unconfirmed payments: ₦{float(month_unconfirmed):,.2f}")
print(f"📊 Total: ₦{float(month_confirmed + month_unconfirmed):,.2f}")

print("\n⚠️  THE PROBLEM:")
print(f"   The endpoint shows ₦28,316.00 but only ₦{float(month_confirmed):,.2f} is confirmed!")
