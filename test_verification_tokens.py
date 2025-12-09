#!/usr/bin/env python
"""
Test script to verify that the GET verification status endpoint returns JWT tokens for verified users.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from bestyy.core_features.user.models import PendingUser, UserProfile
from rest_framework.test import APITestCase
from rest_framework import status

def test_verified_user_gets_tokens():
    """Test that GET /api/auth/verification-status/ returns tokens for verified users"""

    # Create a test user and profile
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser123',
        email='test@example.com',
        first_name='John',
        last_name='Doe',
        password='testpass123'
    )

    # Create user profile with phone
    profile = UserProfile.objects.create(
        user=user,
        phone='+2348012345678'
    )

    # Create a verified PendingUser with the same phone
    pending = PendingUser.objects.create(
        email='test@example.com',
        password='hashedpass',
        first_name='John',
        last_name='Doe',
        phone='+2348012345678',
        user_type='user',
        verification_code='123456',
        is_verified=True
    )

    # Test the GET endpoint
    client = Client()
    response = client.get('/api/auth/verification-status/?phone=+2348012345678')

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.json()}")

    data = response.json()

    # Check that tokens are returned
    assert data['ok'] == True
    assert data['verified'] == True
    assert data['verification_complete'] == True
    assert 'tokens' in data
    assert 'access' in data['tokens']
    assert 'refresh' in data['tokens']
    assert data['user_id'] == str(user.id)
    assert data['role'] == 'user'
    assert data['first_name'] == 'John'

    print("✅ Test passed: GET endpoint returns JWT tokens for verified users")

    # Cleanup
    pending.delete()
    profile.delete()
    user.delete()

if __name__ == '__main__':
    test_verified_user_gets_tokens()