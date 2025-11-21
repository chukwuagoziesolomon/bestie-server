"""
Debug script to check vendor categories and order data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.db.models import Sum, Count
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.models import VendorProfile
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

print("=" * 70)
print("DEBUGGING REVENUE BREAKDOWN ENDPOINT")
print("=" * 70)

# Check vendor categories
print("\n1. VENDOR BUSINESS CATEGORIES")
print("-" * 70)
vendors = VendorProfile.objects.all()
print(f"Total vendors: {vendors.count()}")

for vendor in vendors[:10]:  # First 10 vendors
    print(f"\nVendor: {vendor.business_name}")
    print(f"  Category: '{vendor.business_category}'")
    print(f"  Category is empty: {vendor.business_category == ''}")
    print(f"  Category is None: {vendor.business_category is None}")

# Check orders with payment_confirmed
print("\n2. ORDERS WITH PAYMENT CONFIRMED")
print("-" * 70)
confirmed_orders = Order.objects.filter(payment_confirmed=True)
print(f"Total orders with payment_confirmed=True: {confirmed_orders.count()}")

for order in confirmed_orders[:5]:  # First 5
    vendor_name = order.vendor.business_name if order.vendor else "No vendor"
    vendor_category = order.vendor.business_category if order.vendor else "N/A"
    print(f"\nOrder #{order.id}: ₦{float(order.total_amount):,.2f}")
    print(f"  Vendor: {vendor_name}")
    print(f"  Category: '{vendor_category}'")
    print(f"  Created: {order.created_at}")

# Simulate the revenue breakdown logic
print("\n3. SIMULATING REVENUE BREAKDOWN (Current Month)")
print("-" * 70)
now = timezone.now()
start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

orders = Order.objects.filter(
    payment_confirmed=True,
    created_at__gte=start_date,
    created_at__lte=now
).select_related('vendor')

print(f"Orders in current month: {orders.count()}")
print(f"Date range: {start_date} to {now}")

# Group by category
category_totals = {}
total_revenue = Decimal('0.00')

for order in orders:
    if not order.vendor:
        print(f"\n  Order #{order.id} has no vendor - SKIPPED")
        continue

    category = order.vendor.business_category
    print(f"\n  Order #{order.id}:")
    print(f"    Amount: ₦{float(order.total_amount):,.2f}")
    print(f"    Vendor: {order.vendor.business_name}")
    print(f"    Category: '{category}' (length: {len(category)})")
    
    if category not in category_totals:
        category_totals[category] = Decimal('0.00')
    category_totals[category] += order.total_amount
    total_revenue += order.total_amount

print("\n4. CATEGORY BREAKDOWN RESULTS")
print("-" * 70)
print(f"Total Revenue: ₦{float(total_revenue):,.2f}")
print(f"\nCategories found: {len(category_totals)}")

for category, amount in category_totals.items():
    percentage = round((amount / total_revenue * 100) if total_revenue else 0, 1)
    print(f"\nCategory: '{category}'")
    print(f"  Revenue: ₦{float(amount):,.2f}")
    print(f"  Percentage: {percentage}%")
    print(f"  Is empty string: {category == ''}")

# Check if vendors have empty categories
print("\n5. VENDORS WITH EMPTY/NULL CATEGORIES")
print("-" * 70)
empty_category_vendors = VendorProfile.objects.filter(business_category='')
null_category_vendors = VendorProfile.objects.filter(business_category__isnull=True)

print(f"Vendors with empty string category: {empty_category_vendors.count()}")
print(f"Vendors with NULL category: {null_category_vendors.count()}")

if empty_category_vendors.exists():
    print("\nVendors with empty categories:")
    for vendor in empty_category_vendors[:5]:
        order_count = Order.objects.filter(vendor=vendor, payment_confirmed=True).count()
        print(f"  - {vendor.business_name} (Orders: {order_count})")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)
print("\n⚠️  The issue: Vendors have empty business_category field")
print("⚠️  This causes all orders to be grouped under '' (empty string)")
print("⚠️  The total is correct, but the breakdown is meaningless")
print("\n💡 Solution: Either set proper categories OR handle empty categories better")
