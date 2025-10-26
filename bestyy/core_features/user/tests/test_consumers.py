"""
Tests for WebSocket consumers.
"""
import json
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from channels.routing import URLRouter
from django.urls import re_path
from ..consumers import AdminActivityConsumer, VendorNotificationConsumer, CourierNotificationConsumer
from ..models import VendorProfile

User = get_user_model()

class TestAdminActivityConsumer(TestCase):
    """Test the AdminActivityConsumer WebSocket consumer."""
    
    async def test_connect_unauthenticated(self):
        ""Test that unauthenticated connections are rejected."""
        application = URLRouter([
            re_path(r'ws/admin/activity/$', AdminActivityConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(application, '/ws/admin/activity/')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
    
    async def test_connect_non_staff(self):
        ""Test that non-staff users are rejected."""
        user = await User.objects.create_user(
            'test@example.com',
            'testpassword123'
        )
        
        application = URLRouter([
            re_path(r'ws/admin/activity/$', AdminActivityConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(
            application,
            '/ws/admin/activity/',
            headers=[
                (b'cookie', f'sessionid={user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
    
    async def test_connect_authenticated_staff(self):
        ""Test that staff users can connect."""
        user = await User.objects.create_user(
            'admin@example.com',
            'adminpassword123',
            is_staff=True
        )
        
        application = URLRouter([
            re_path(r'ws/admin/activity/$', AdminActivityConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(
            application,
            '/ws/admin/activity/',
            headers=[
                (b'cookie', f'sessionid={user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Test receiving a message
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'connection_established')
        
        await communicator.disconnect()


class TestVendorNotificationConsumer(TestCase):
    ""Test the VendorNotificationConsumer WebSocket consumer."""
    
    async def test_connect_unauthenticated(self):
        ""Test that unauthenticated connections are rejected."""
        application = URLRouter([
            re_path(r'ws/vendor/notifications/$', VendorNotificationConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(application, '/ws/vendor/notifications/')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
    
    async def test_connect_non_vendor(self):
        ""Test that non-vendor users are rejected."""
        user = await User.objects.create_user(
            'user@example.com',
            'userpassword123'
        )
        
        application = URLRouter([
            re_path(r'ws/vendor/notifications/$', VendorNotificationConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(
            application,
            '/ws/vendor/notifications/',
            headers=[
                (b'cookie', f'sessionid={user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
    
    async def test_connect_authenticated_vendor(self):
        ""Test that vendor users can connect."""
        user = await User.objects.create_user(
            'vendor@example.com',
            'vendorpassword123'
        )
        vendor = await VendorProfile.objects.create(
            user=user,
            business_name='Test Vendor',
            verification_status='pending'
        )
        
        application = URLRouter([
            re_path(r'ws/vendor/notifications/$', VendorNotificationConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(
            application,
            '/ws/vendor/notifications/',
            headers=[
                (b'cookie', f'sessionid={user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Test receiving a message
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'connection_established')
        
        # Test receiving a notification
        await communicator.send_json_to({
            'type': 'verification.approved',
            'data': {
                'message': 'Your vendor account has been approved!',
                'status': 'approved'
            }
        })
        
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'verification.approved')
        
        await communicator.disconnect()
