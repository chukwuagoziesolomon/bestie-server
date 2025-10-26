#!/usr/bin/env python3
"""
Test script for email notifications
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from user.models import User, VendorProfile, Order, OrderItem, MenuItem
from user.services.notification_service import VendorNotificationService
from django.utils import timezone
from decimal import Decimal

def test_email_notification():
    """Test email notification functionality"""
    print("🧪 Testing Email Notifications...")
    print("=" * 50)
    
    try:
        # Create test data
        print("📝 Creating test order data...")
        
        # Get or create a test vendor user
        vendor_user, created = User.objects.get_or_create(
            email='vendor@testrestaurant.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Vendor',
                'phone': '+2348123456789'
            }
        )
        
        # Get or create a test vendor profile
        vendor, created = VendorProfile.objects.get_or_create(
            user=vendor_user,
            defaults={
                'business_name': 'Test Restaurant',
                'phone': '+2348123456789',
                'business_category': 'Restaurant',
                'business_description': 'Test restaurant for email notifications',
                'business_address': '123 Test Street, Lagos, Lagos State',
                'delivery_radius': '5km',
                'service_areas': 'Lagos Island, Victoria Island',
                'verification_status': 'approved',
                'is_suspended': False
            }
        )
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            email='customer@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Customer',
                'phone': '+2348765432109'
            }
        )
        
        # Get or create a test menu item
        menu_item, created = MenuItem.objects.get_or_create(
            dish_name='Test Burger',
            vendor=vendor,
            defaults={
                'item_description': 'A delicious test burger',
                'price': Decimal('2500.00'),
                'quantity': 10,
                'available_now': True
            }
        )
        
        # Create test order data
        order_data = {
            'vendor': vendor,
            'order': type('MockOrder', (), {
                'id': 999,
                'order_number': '#TEST999',
                'total_price': Decimal('2500.00'),
                'created_at': timezone.now(),
                'delivery_address': type('MockAddress', (), {
                    'street': '456 Customer Street',
                    'city': 'Lagos',
                    'state': 'Lagos',
                    'postal_code': '100001',
                    'landmark': 'Near Test Mall'
                })(),
                'delivery_instructions': 'Please call before delivery'
            })(),
            'order_items': [
                {
                    'name': 'Test Burger',
                    'quantity': 1,
                    'base_price': 2500.00,
                    'total_price': 2500.00,
                    'variants': [
                        {'name': 'Large Size', 'price': 500.00},
                        {'name': 'Extra Cheese', 'price': 200.00}
                    ],
                    'special_instructions': 'No onions please'
                }
            ],
            'customer': {
                'name': 'Test Customer',
                'email': 'customer@test.com',
                'phone': '+2348765432109'
            },
            'total_amount': 3200.00
        }
        
        print("📧 Sending email notification...")
        
        # Test email notification
        result = VendorNotificationService._send_email_notification(order_data)
        
        if result['success']:
            print("✅ Email notification sent successfully!")
            print(f"   Message: {result['message']}")
            print(f"   Vendor Email: {result.get('vendor_email', 'N/A')}")
        else:
            print("❌ Email notification failed!")
            print(f"   Error: {result['message']}")
        
        print("\n📋 Test Summary:")
        print(f"   Vendor: {vendor.business_name}")
        print(f"   Vendor Email: {vendor.user.email}")
        print(f"   Order Amount: ₦{order_data['total_amount']:,.2f}")
        print(f"   Items: {len(order_data['order_items'])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_full_notification_flow():
    """Test the full notification flow including email"""
    print("\n🔄 Testing Full Notification Flow...")
    print("=" * 50)
    
    try:
        # Create test order data
        order_data = {
            'vendor': VendorProfile.objects.first(),
            'order': type('MockOrder', (), {
                'id': 888,
                'order_number': '#TEST888',
                'total_price': Decimal('1500.00'),
                'created_at': timezone.now(),
                'delivery_address': None,
                'delivery_instructions': ''
            })(),
            'order_items': [
                {
                    'name': 'Test Item',
                    'quantity': 1,
                    'base_price': 1500.00,
                    'total_price': 1500.00,
                    'variants': [],
                    'special_instructions': ''
                }
            ],
            'customer': {
                'name': 'Test User',
                'email': 'test@example.com',
                'phone': '+2348123456789'
            },
            'total_amount': 1500.00
        }
        
        print("📱 Sending all notifications (WhatsApp, WebSocket, Email)...")
        
        # Test full notification
        results = VendorNotificationService.send_order_notification(order_data)
        
        print("\n📊 Notification Results:")
        for notification_type, result in results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {notification_type.upper()}: {status} {result.get('message', '')}")
        
        return results
        
    except Exception as e:
        print(f"❌ Full notification test failed: {str(e)}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("🚀 Starting Email Notification Tests...")
    print("=" * 60)
    
    # Test email notification only
    email_result = test_email_notification()
    
    # Test full notification flow
    full_result = test_full_notification_flow()
    
    print("\n🎯 Test Results Summary:")
    print("=" * 30)
    print(f"Email Test: {'✅ PASSED' if email_result.get('success') else '❌ FAILED'}")
    print(f"Full Flow Test: {'✅ PASSED' if full_result.get('success') else '❌ FAILED'}")
    
    if email_result.get('success'):
        print("\n📧 Email notifications are working!")
        print("   In development mode, emails will be printed to console.")
        print("   In production, configure EMAIL_HOST, EMAIL_HOST_USER, etc.")
    else:
        print("\n⚠️  Email notifications need configuration.")
        print("   Check your email settings in settings.py")
    
    print("\n🏁 Tests completed!")
