#!/usr/bin/env python
"""
Simple test script to verify bank update restriction works
"""
import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')

django.setup()

from django.contrib.auth import get_user_model
from bestyy.core_features.user.models import VendorProfile
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

def test_bank_update_restriction():
    """Test that bank fields are blocked in profile updates"""

    # Create test user and profile
    user = User.objects.create_user(
        email='test_bank@example.com',
        password='testpass123',
        first_name='Test',
        last_name='Bank',
        role='vendor'
    )

    vendor_profile = VendorProfile.objects.create(
        user=user,
        business_name='Test Bank Business',
        business_category='Test',
        business_address='123 Test St',
        phone='+2348012345678'
    )

    # Test with APIClient
    client = APIClient()
    client.force_authenticate(user=user)

    print("Testing bank field restriction...")

    # Test 1: Try to update bank fields directly
    bank_data = {
        'bank_account_number': '1234567890',
        'bank_code': '044',
        'bank_name': 'Access Bank'
    }

    response = client.patch('/api/user/vendors/profile/', bank_data, format='json')
    print(f"Bank update response status: {response.status_code}")
    print(f"Response data: {response.data}")

    if response.status_code == 400:
        print("✓ Bank fields correctly blocked")
        assert 'bank_verification_endpoint' in response.data
        assert 'verify-bank' in response.data['bank_verification_endpoint']
    else:
        print("✗ Bank fields were not blocked")
        return False

    # Test 2: Try updating non-bank fields (should work)
    normal_data = {
        'business_name': 'Updated Business Name',
        'business_description': 'Updated description'
    }

    response = client.patch('/api/user/vendors/profile/', normal_data, format='json')
    print(f"Normal update response status: {response.status_code}")

    if response.status_code == 200:
        print("✓ Non-bank fields can be updated")
        vendor_profile.refresh_from_db()
        assert vendor_profile.business_name == 'Updated Business Name'
    else:
        print("✗ Non-bank fields could not be updated")
        return False

    # Test 3: Mixed data with bank fields (should be blocked)
    mixed_data = {
        'business_name': 'Another Update',
        'bank_account_number': '0987654321'
    }

    response = client.patch('/api/user/vendors/profile/', mixed_data, format='json')
    print(f"Mixed update response status: {response.status_code}")

    if response.status_code == 400:
        print("✓ Mixed requests with bank fields are blocked")
        # Verify business_name was NOT updated
        vendor_profile.refresh_from_db()
        assert vendor_profile.business_name == 'Updated Business Name'  # Should still be the previous value
    else:
        print("✗ Mixed requests were not blocked")
        return False

    # Clean up
    vendor_profile.delete()
    user.delete()

    print("✓ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_bank_update_restriction()
        if success:
            print("\n🎉 Bank update restriction is working correctly!")
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)