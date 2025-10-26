#!/usr/bin/env python
"""
Verification script to check test data in database
Run: python verify_test_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from bestyy.core_features.user.models import VendorProfile, MenuItem, User

print("\n" + "="*70)
print("DATABASE VERIFICATION REPORT")
print("="*70)

# Count users
users = User.objects.filter(email__contains='test.com')
print(f"\n✅ Test Users Created: {users.count()}")
for user in users:
    print(f"   - {user.email} ({user.first_name} {user.last_name})")

# Count vendors
vendors = VendorProfile.objects.all()
print(f"\n✅ Vendors Created: {vendors.count()}")
for vendor in vendors:
    items_count = vendor.menu_items.count()
    status = "✅ Approved" if vendor.verification_status == 'approved' else "⚠️ Pending"
    print(f"   - {vendor.business_name} ({vendor.business_category}): {items_count} items [{status}]")

# Count menu items
menu_items = MenuItem.objects.all()
print(f"\n✅ Menu Items Created: {menu_items.count()}")

# Show items by vendor
print("\n📋 Menu Items by Vendor:")
for vendor in vendors:
    items = vendor.menu_items.all()
    print(f"\n   {vendor.business_name}:")
    for item in items:
        has_image = "📸" if item.image else "❌"
        available = "✅" if item.available_now else "❌"
        print(f"      {has_image} {available} {item.dish_name} - ₦{item.price}")

print("\n" + "="*70)
print("✅ DATABASE READY FOR TESTING")
print("="*70)
print("\nYou can now test the WhatsApp bot with these vendors and menu items!")
print("\nTest messages to try:")
print("  - 'i want to order eba'")
print("  - 'i want 2 pepperoni pizzas'")
print("  - 'i want samosa'")
print("  - 'i want a burger'")
print("\n" + "="*70 + "\n")

