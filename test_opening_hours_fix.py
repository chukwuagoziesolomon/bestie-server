#!/usr/bin/env python
"""
Test script to verify that opening hours and closing hours are transferred
from signup data to vendor profile during account creation.
"""
import os
import sys
import django
from datetime import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from bestyy.core_features.user.models import PendingUser, VendorProfile
from django.contrib.auth import get_user_model

User = get_user_model()

def test_opening_hours_transfer():
    """Test that opening hours and closing hours are transferred from signup to profile"""

    # Create test data
    test_email = "test_opening_hours@example.com"
    test_phone = "+2348012345678"

    # Clean up any existing test data
    User.objects.filter(email=test_email).delete()
    PendingUser.objects.filter(email=test_email).delete()

    # Create pending user with opening hours data
    pending_user = PendingUser.objects.create(
        email=test_email,
        password="testpass123",
        first_name="Test",
        last_name="Vendor",
        phone=test_phone,
        user_type="vendor",
        verification_code="123456",
        profile_data={
            'business_name': 'Test Business',
            'business_category': 'Restaurant',
            'business_address': '123 Test Street',
            'opening_hours': '08:00:00',  # 8 AM
            'closing_hours': '22:00:00',  # 10 PM
            'delivery_radius': '5',
            'service_areas': 'Test Area',
            'offers_delivery': True,
            'business_description': 'Test business description',
            'logo': 'https://example.com/logo.jpg',
            'cover_photo': 'https://example.com/cover.jpg'
        }
    )

    # Set expiration (not expired)
    from django.utils import timezone
    from datetime import timedelta
    pending_user.expires_at = timezone.now() + timedelta(hours=1)
    pending_user.save()

    print("Created pending user with opening hours data")
    print(f"Opening hours in profile_data: {pending_user.profile_data.get('opening_hours')}")
    print(f"Closing hours in profile_data: {pending_user.profile_data.get('closing_hours')}")

    # Create user account
    user, message = pending_user.create_user_account()

    if user:
        print(f"Successfully created user: {user.email}")

        # Check if vendor profile was created with opening hours
        try:
            vendor_profile = VendorProfile.objects.get(user=user)
            print("Vendor profile created successfully")
            print(f"Opening hours in profile: {vendor_profile.opening_hours}")
            print(f"Closing hours in profile: {vendor_profile.closing_hours}")

            # Verify the values match
            expected_opening = time(8, 0, 0)  # 08:00:00
            expected_closing = time(22, 0, 0)  # 22:00:00

            if vendor_profile.opening_hours == expected_opening:
                print("✓ Opening hours transferred correctly")
            else:
                print(f"✗ Opening hours mismatch. Expected: {expected_opening}, Got: {vendor_profile.opening_hours}")

            if vendor_profile.closing_hours == expected_closing:
                print("✓ Closing hours transferred correctly")
            else:
                print(f"✗ Closing hours mismatch. Expected: {expected_closing}, Got: {vendor_profile.closing_hours}")

        except VendorProfile.DoesNotExist:
            print("✗ Vendor profile was not created")
    else:
        print(f"✗ Failed to create user account: {message}")

    # Clean up
    User.objects.filter(email=test_email).delete()
    PendingUser.objects.filter(email=test_email).delete()
    print("Test cleanup completed")

if __name__ == "__main__":
    test_opening_hours_transfer()