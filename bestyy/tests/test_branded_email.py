#!/usr/bin/env python
"""
Test script to preview branded Bestyy emails
"""
import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from user.services.branded_email_service import BrandedEmailService

def test_verification_emails():
    """Test verification email templates"""
    print("Testing Branded Email Templates...")
    print("=" * 50)

    # Mock user profile for testing
    class MockUserProfile:
        def __init__(self):
            self.business_name = "Tasty Bites Restaurant"
            self.verification_date = None
            self.user = MockUser()

    class MockUser:
        def __init__(self):
            self.email = "chukwuagoziesolomon@gmail.com"
            self.get_full_name = lambda: "John Doe"

    user_profile = MockUserProfile()

    # Test approval email
    print("1. Testing Vendor Approval Email...")
    approval_html = BrandedEmailService.create_verification_email(
        user_type='vendor',
        user_profile=user_profile,
        status='approved'
    )

    with open('vendor_approval_email.html', 'w', encoding='utf-8') as f:
        f.write(approval_html)
    print("   ✓ Saved as: vendor_approval_email.html")

    # Test rejection email
    print("2. Testing Vendor Rejection Email...")
    rejection_html = BrandedEmailService.create_verification_email(
        user_type='vendor',
        user_profile=user_profile,
        status='rejected',
        admin_notes='Please provide clearer business documentation.'
    )

    with open('vendor_rejection_email.html', 'w', encoding='utf-8') as f:
        f.write(rejection_html)
    print("   ✓ Saved as: vendor_rejection_email.html")

    # Test courier approval email
    print("3. Testing Courier Approval Email...")
    courier_profile = MockUserProfile()
    courier_profile.business_name = None  # Courier doesn't have business name

    courier_approval_html = BrandedEmailService.create_verification_email(
        user_type='courier',
        user_profile=courier_profile,
        status='approved'
    )

    with open('courier_approval_email.html', 'w', encoding='utf-8') as f:
        f.write(courier_approval_html)
    print("   ✓ Saved as: courier_approval_email.html")

    # Test order notification email
    print("4. Testing Order Notification Email...")
    order_data = {
        'order_number': '#TEST-123',
        'customer_name': 'Jane Smith',
        'customer_phone': '+2348012345678',
        'delivery_address': '123 Victoria Island, Lagos',
        'special_instructions': 'Please call when you arrive',
        'total_amount': '₦5,800.00',
        'estimated_delivery': '30-45 minutes',
        'items': [
            {
                'name': 'Jollof Rice',
                'quantity': 2,
                'price': '₦2,500.00',
                'special_instructions': 'No onions please'
            },
            {
                'name': 'Chicken',
                'quantity': 1,
                'price': '₦800.00'
            }
        ]
    }

    order_html = BrandedEmailService.create_order_notification_email(order_data)

    with open('order_notification_email.html', 'w', encoding='utf-8') as f:
        f.write(order_html)
    print("   ✓ Saved as: order_notification_email.html")

    print("\n" + "=" * 50)
    print("✅ All branded email templates generated!")
    print("\n📁 Files created in current directory:")
    print("   - vendor_approval_email.html")
    print("   - vendor_rejection_email.html")
    print("   - courier_approval_email.html")
    print("   - order_notification_email.html")
    print("\n🔍 Open these HTML files in your browser to preview the branded emails!")
    print("\n🎨 Features:")
    print("   ✓ Bestyy logo and branding")
    print("   ✓ Teal gradient header (#23C7B2 to #25AC9B)")
    print("   ✓ Professional styling")
    print("   ✓ Mobile responsive")
    print("   ✓ Action buttons")

if __name__ == "__main__":
    test_verification_emails()