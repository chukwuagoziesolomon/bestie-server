#!/usr/bin/env python
"""
Test script to verify that bank details cannot be updated directly via PATCH /api/user/vendors/profile/
and must go through the bank verification process.
"""
import os
import sys
import django
from unittest.mock import patch, MagicMock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from bestyy.core_features.user.models import VendorProfile

User = get_user_model()

class VendorProfileBankUpdateTest(APITestCase):
    """Test that bank details require verification"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='vendor'
        )

        # Create vendor profile
        self.vendor_profile = VendorProfile.objects.create(
            user=self.user,
            business_name='Test Business',
            business_category='Restaurant',
            business_address='123 Test St',
            phone='+2348012345678'
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_bank_fields_blocked_in_profile_update(self):
        """Test that bank fields cannot be updated directly"""
        bank_update_data = {
            'bank_account_number': '1234567890',
            'bank_code': '044',
            'bank_name': 'Access Bank'
        }

        response = self.client.patch('/api/user/vendors/profile/', bank_update_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('success', response.data)
        self.assertFalse(response.data['success'])
        self.assertIn('bank_verification_endpoint', response.data)
        self.assertIn('verify-bank', response.data['bank_verification_endpoint'])

    def test_non_bank_fields_allowed(self):
        """Test that non-bank fields can still be updated"""
        update_data = {
            'business_name': 'Updated Business Name',
            'business_description': 'Updated description'
        }

        response = self.client.patch('/api/user/vendors/profile/', update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vendor_profile.refresh_from_db()
        self.assertEqual(self.vendor_profile.business_name, 'Updated Business Name')
        self.assertEqual(self.vendor_profile.business_description, 'Updated description')

    def test_mixed_fields_bank_blocked(self):
        """Test that requests with both bank and non-bank fields are blocked"""
        mixed_data = {
            'business_name': 'Updated Business Name',
            'bank_account_number': '1234567890',
            'business_description': 'Updated description'
        }

        response = self.client.patch('/api/user/vendors/profile/', mixed_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Bank details cannot be updated directly', response.data['error'])

        # Verify business_name was NOT updated
        self.vendor_profile.refresh_from_db()
        self.assertNotEqual(self.vendor_profile.business_name, 'Updated Business Name')

if __name__ == '__main__':
    # Run the tests
    import unittest
    unittest.main()