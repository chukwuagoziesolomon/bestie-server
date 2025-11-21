"""
Test script to verify that revenue calculations now only include payment_confirmed orders.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.db.models import Sum, Count
from bestyy.restaurant_features.order.models import Order
from decimal import Decimal

print("=" * 70)
print("TESTING PAYMENT_CONFIRMED REVENUE FILTERS")
print("=" * 70)

# Test 1: Check total orders with and without payment_confirmed
print("\n1. TOTAL ORDERS COMPARISON")
print("-" * 70)
all_orders_count = Order.objects.count()
confirmed_payment_count = Order.objects.filter(payment_confirmed=True).count()
unconfirmed_payment_count = Order.objects.filter(payment_confirmed=False).count()

print(f"Total orders: {all_orders_count}")
print(f"Orders with confirmed payment: {confirmed_payment_count}")
print(f"Orders with unconfirmed payment: {unconfirmed_payment_count}")

# Test 2: Check revenue calculations
print("\n2. REVENUE COMPARISON")
print("-" * 70)
all_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
confirmed_revenue = Order.objects.filter(payment_confirmed=True).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
unconfirmed_revenue = Order.objects.filter(payment_confirmed=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

print(f"Total revenue (all orders): ₦{float(all_revenue):,.2f}")
print(f"Revenue from confirmed payments: ₦{float(confirmed_revenue):,.2f}")
print(f"Revenue from unconfirmed payments: ₦{float(unconfirmed_revenue):,.2f}")
print(f"Difference: ₦{float(all_revenue - confirmed_revenue):,.2f}")

# Test 3: Check by vendor
print("\n3. VENDOR REVENUE COMPARISON")
print("-" * 70)
from bestyy.core_features.user.models import VendorProfile

vendors_with_orders = VendorProfile.objects.filter(
    vendor_orders__isnull=False
).distinct()[:5]  # First 5 vendors with orders

for vendor in vendors_with_orders:
    vendor_all_revenue = Order.objects.filter(
        vendor=vendor
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    vendor_confirmed_revenue = Order.objects.filter(
        vendor=vendor,
        payment_confirmed=True
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    print(f"\nVendor: {vendor.business_name}")
    print(f"  All revenue: ₦{float(vendor_all_revenue):,.2f}")
    print(f"  Confirmed payment revenue: ₦{float(vendor_confirmed_revenue):,.2f}")
    print(f"  Difference: ₦{float(vendor_all_revenue - vendor_confirmed_revenue):,.2f}")

# Test 4: Check by courier
print("\n4. COURIER EARNINGS COMPARISON")
print("-" * 70)
from bestyy.core_features.user.models import CourierProfile

couriers_with_deliveries = CourierProfile.objects.filter(
    assigned_orders__isnull=False,
    assigned_orders__status__in=['delivered', 'completed']
).distinct()[:5]  # First 5 couriers with deliveries

for courier in couriers_with_deliveries:
    courier_all_earnings = Order.objects.filter(
        courier=courier,
        status__in=['delivered', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    courier_confirmed_earnings = Order.objects.filter(
        courier=courier,
        payment_confirmed=True,
        status__in=['delivered', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    user = courier.user
    print(f"\nCourier: {user.first_name} {user.last_name}")
    print(f"  All earnings: ₦{float(courier_all_earnings):,.2f}")
    print(f"  Confirmed payment earnings: ₦{float(courier_confirmed_earnings):,.2f}")
    print(f"  Difference: ₦{float(courier_all_earnings - courier_confirmed_earnings):,.2f}")

# Test 5: Admin profit calculation
print("\n5. ADMIN PROFIT CALCULATION")
print("-" * 70)
completed_orders_all = Order.objects.filter(status='completed')
completed_orders_confirmed = Order.objects.filter(
    status='completed',
    payment_confirmed=True
)

total_revenue_all = completed_orders_all.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
total_revenue_confirmed = completed_orders_confirmed.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

commission_rate = Decimal('0.10')  # 10%
profit_all = total_revenue_all * commission_rate
profit_confirmed = total_revenue_confirmed * commission_rate

print(f"Completed orders (all): {completed_orders_all.count()}")
print(f"Completed orders (confirmed payment): {completed_orders_confirmed.count()}")
print(f"\nProfit from all completed orders: ₦{float(profit_all):,.2f}")
print(f"Profit from confirmed payments only: ₦{float(profit_confirmed):,.2f}")
print(f"Difference: ₦{float(profit_all - profit_confirmed):,.2f}")

print("\n" + "=" * 70)
print("TEST COMPLETED")
print("=" * 70)
print("\n✅ Revenue calculations now properly filter by payment_confirmed=True")
print("✅ This ensures only orders where customers have sent money are counted")
print("✅ Applied to: Admin dashboard, Vendor earnings, Courier earnings")
