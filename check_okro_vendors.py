#!/usr/bin/env python
"""
Check database for vendors selling okro soup and related Nigerian dishes
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.models import VendorProfile, MenuItem
from django.db.models import Q

def check_okro_vendors():
    """Check for vendors selling okro soup or related dishes"""
    print("=== Checking Database for Okro Soup Vendors ===\n")
    
    # Check all vendors
    total_vendors = VendorProfile.objects.count()
    approved_vendors = VendorProfile.objects.filter(verification_status='approved').count()
    print(f"Total vendors: {total_vendors}")
    print(f"Approved vendors: {approved_vendors}")
    
    # Check for vendors with soup in their business category or description
    soup_vendors = VendorProfile.objects.filter(
        Q(business_category__icontains='soup') |
        Q(business_description__icontains='soup') |
        Q(business_name__icontains='soup')
    )
    print(f"\nVendors with 'soup' in category/description/name: {soup_vendors.count()}")
    
    for vendor in soup_vendors:
        print(f"  - {vendor.business_name} (Category: {vendor.business_category})")
        print(f"    Description: {vendor.business_description[:100]}...")
        print(f"    Verification: {vendor.verification_status}")
        print()
    
    # Check for vendors with Nigerian food
    nigerian_vendors = VendorProfile.objects.filter(
        Q(business_category__icontains='nigerian') |
        Q(business_description__icontains='nigerian') |
        Q(business_name__icontains='nigerian')
    )
    print(f"Vendors with 'nigerian' in category/description/name: {nigerian_vendors.count()}")
    
    for vendor in nigerian_vendors:
        print(f"  - {vendor.business_name} (Category: {vendor.business_category})")
        print(f"    Description: {vendor.business_description[:100]}...")
        print(f"    Verification: {vendor.verification_status}")
        print()
    
    # Check for okro specifically
    okro_vendors = VendorProfile.objects.filter(
        Q(business_category__icontains='okro') |
        Q(business_description__icontains='okro') |
        Q(business_name__icontains='okro')
    )
    print(f"Vendors with 'okro' in category/description/name: {okro_vendors.count()}")
    
    for vendor in okro_vendors:
        print(f"  - {vendor.business_name} (Category: {vendor.business_category})")
        print(f"    Description: {vendor.business_description[:100]}...")
        print(f"    Verification: {vendor.verification_status}")
        print()
    
    # Check menu items for okro or soup
    print("\n=== Checking Menu Items ===")
    total_menu_items = MenuItem.objects.count()
    print(f"Total menu items: {total_menu_items}")
    
    # Check for okro in menu items
    okro_menu_items = MenuItem.objects.filter(
        Q(dish_name__icontains='okro') |
        Q(item_description__icontains='okro')
    )
    print(f"Menu items with 'okro': {okro_menu_items.count()}")
    
    for item in okro_menu_items:
        print(f"  - {item.dish_name} (₦{item.price}) - {item.vendor.business_name}")
        print(f"    Description: {item.item_description[:100]}...")
        print(f"    Vendor verification: {item.vendor.verification_status}")
        print()
    
    # Check for soup in menu items
    soup_menu_items = MenuItem.objects.filter(
        Q(dish_name__icontains='soup') |
        Q(item_description__icontains='soup')
    )
    print(f"Menu items with 'soup': {soup_menu_items.count()}")
    
    for item in soup_menu_items:
        print(f"  - {item.dish_name} (₦{item.price}) - {item.vendor.business_name}")
        print(f"    Description: {item.item_description[:100]}...")
        print(f"    Vendor verification: {item.vendor.verification_status}")
        print()
    
    # Check all approved vendors and their categories
    print("\n=== All Approved Vendors and Their Categories ===")
    approved_vendors_list = VendorProfile.objects.filter(verification_status='approved')
    print(f"Approved vendors: {approved_vendors_list.count()}")
    
    for vendor in approved_vendors_list:
        print(f"  - {vendor.business_name}")
        print(f"    Category: {vendor.business_category}")
        print(f"    Description: {vendor.business_description[:100]}...")
        print(f"    Menu items: {vendor.menu_items.count()}")
        print()
    
    return {
        'total_vendors': total_vendors,
        'approved_vendors': approved_vendors,
        'soup_vendors': soup_vendors.count(),
        'nigerian_vendors': nigerian_vendors.count(),
        'okro_vendors': okro_vendors.count(),
        'okro_menu_items': okro_menu_items.count(),
        'soup_menu_items': soup_menu_items.count()
    }

if __name__ == "__main__":
    results = check_okro_vendors()
    print(f"\n=== Summary ===")
    print(f"Total vendors: {results['total_vendors']}")
    print(f"Approved vendors: {results['approved_vendors']}")
    print(f"Vendors with soup: {results['soup_vendors']}")
    print(f"Vendors with Nigerian food: {results['nigerian_vendors']}")
    print(f"Vendors with okro: {results['okro_vendors']}")
    print(f"Menu items with okro: {results['okro_menu_items']}")
    print(f"Menu items with soup: {results['soup_menu_items']}")



