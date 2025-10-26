"""
Tests for WebSocket notification utilities.
"""
import json
from unittest.mock import patch, MagicMock
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from channels.routing import URLRouter
from django.urls import re_path
from channels.layers import get_channel_layer
from channels.testing import HttpCommunicator

from ..consumers import AdminActivityConsumer, VendorNotificationConsumer
from ..models import VendorProfile
from ..utils.websocket_notifications import (
    send_admin_notification,
    send_vendor_notification,
    send_courier_notification,
    notify_vendor_registered,
    notify_vendor_approved,
    notify_vendor_rejected,
    notify_courier_registered,
    notify_courier_approved,
    notify_courier_rejected
)

User = get_user_model()

@override_settings(CHANNEL_LAYERS={
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
})
class TestWebSocketNotifications(TestCase):
    """Test the WebSocket notification utilities."""
    
    @classmethod
    def setUpTestData(cls):
        ""Set up test data."""
        cls.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpassword123',
            is_staff=True
        )
        
        cls.vendor_user = User.objects.create_user(
            email='vendor@example.com',
            password='vendorpassword123'
        )
        
        cls.vendor = VendorProfile.objects.create(
            user=cls.vendor_user,
            business_name='Test Vendor',
            verification_status='pending'
        )
    
    async def test_send_admin_notification(self):
        ""Test sending a notification to admin users."""
        # Create a test application
        application = URLRouter([
            re_path(r'ws/admin/activity/$', AdminActivityConsumer.as_asgi()),
        ])
        
        # Connect as admin
        communicator = WebsocketCommunicator(
            application,
            '/ws/admin/activity/',
            headers=[
                (b'cookie', f'sessionid={self.admin_user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Skip the connection message
        await communicator.receive_json_from()
        
        # Send a test notification
        test_data = {'message': 'Test notification', 'type': 'test'}
        await send_admin_notification('test_notification', test_data)
        
        # Check if the notification was received
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'test_notification')
        self.assertEqual(response['data']['message'], 'Test notification')
        
        await communicator.disconnect()
    
    async def test_send_vendor_notification(self):
        ""Test sending a notification to a specific vendor."""
        # Create a test application
        application = URLRouter([
            re_path(r'ws/vendor/notifications/$', VendorNotificationConsumer.as_asgi()),
        ])
        
        # Connect as vendor
        communicator = WebsocketCommunicator(
            application,
            '/ws/vendor/notifications/',
            headers=[
                (b'cookie', f'sessionid={self.vendor_user.session_key}'.encode('ascii')),
            ]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Skip the connection message
        await communicator.receive_json_from()
        
        # Send a test notification
        test_data = {'message': 'Test vendor notification', 'status': 'test'}
        await send_vendor_notification(self.vendor.id, 'test_notification', test_data)
        
        # Check if the notification was received
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'test_notification')
        self.assertEqual(response['data']['message'], 'Test vendor notification')
        
        await communicator.disconnect()
    
    @patch('user.utils.websocket_notifications.send_admin_notification')
    async def test_notify_vendor_registered(self, mock_send_admin_notification):
        ""Test notifying admins about a new vendor registration."""
        await notify_vendor_registered(self.vendor)
        
        # Check if the admin notification was sent
        mock_send_admin_notification.assert_called_once()
        args, kwargs = mock_send_admin_notification.call_args
        self.assertEqual(kwargs['notification_type'], 'vendor.registered')
        self.assertEqual(kwargs['data']['business_name'], 'Test Vendor')
    
    @patch('user.utils.websocket_notifications.send_admin_notification')
    @patch('user.utils.websocket_notifications.send_vendor_notification')
    async def test_notify_vendor_approved(
        self, 
        mock_send_vendor_notification, 
        mock_send_admin_notification
    ):
        ""Test notifying about a vendor approval."""
        self.vendor.verification_status = 'approved'
        await self.vendor.save()
        
        await notify_vendor_approved(self.vendor, self.admin_user)
        
        # Check if admin notification was sent
        mock_send_admin_notification.assert_called_once()
        
        # Check if vendor notification was sent
        mock_send_vendor_notification.assert_called_once()
        args, kwargs = mock_send_vendor_notification.call_args
        self.assertEqual(kwargs['notification_type'], 'verification.approved')
        self.assertEqual(kwargs['data']['status'], 'approved')
    
    @patch('user.utils.websocket_notifications.send_admin_notification')
    @patch('user.utils.websocket_notifications.send_vendor_notification')
    async def test_notify_vendor_rejected(
        self, 
        mock_send_vendor_notification, 
        mock_send_admin_notification
    ):
        ""Test notifying about a vendor rejection."""
        self.vendor.verification_status = 'rejected'
        await self.vendor.save()
        
        reason = 'Incomplete documentation'
        await notify_vendor_rejected(self.vendor, self.admin_user, reason)
        
        # Check if admin notification was sent
        mock_send_admin_notification.assert_called_once()
        
        # Check if vendor notification was sent with the reason
        mock_send_vendor_notification.assert_called_once()
        args, kwargs = mock_send_vendor_notification.call_args
        self.assertEqual(kwargs['notification_type'], 'verification.rejected')
        self.assertEqual(kwargs['data']['status'], 'rejected')
        self.assertEqual(kwargs['data']['reason'], reason)
