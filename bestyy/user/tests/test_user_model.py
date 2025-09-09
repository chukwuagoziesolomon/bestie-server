"""
Tests for the User model and related functionality.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserModelTest(TestCase):
    def test_user_creation(self):
        """Test user creation with role"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='user'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'user')
        self.assertTrue(hasattr(user, 'profile'))
        
    def test_role_change(self):
        """Test changing user role"""
        user = User.objects.create_user(
            email='vendor@example.com',
            password='testpass123',
            role='vendor'
        )
        
        # Change role to courier
        user.role = 'courier'
        user.save()
        
        # Refresh from db
        user.refresh_from_db()
        self.assertEqual(user.role, 'courier')
        
    def test_profile_creation(self):
        """Test profile creation based on role"""
        # Test user profile
        user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='user'
        )
        self.assertTrue(hasattr(user, 'profile'))
        
        # Test vendor profile
        vendor = User.objects.create_user(
            email='vendor@example.com',
            password='testpass123',
            role='vendor'
        )
        self.assertTrue(hasattr(vendor, 'vendor_profile'))
        
        # Test courier profile
        courier = User.objects.create_user(
            email='courier@example.com',
            password='testpass123',
            role='courier'
        )
        self.assertTrue(hasattr(courier, 'courier_profile'))
