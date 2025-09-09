import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

class AdminActivityConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for admin activity notifications.
    Handles real-time notifications for admin dashboard activities.
    """
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_group_name = 'admin_activity'
        user = self.scope.get('user')
        
        if not user or not user.is_authenticated or not user.is_superuser:
            logger.warning(f"Unauthorized WebSocket connection attempt by {user}")
            await self.close()
            return
        
        # Join admin activity group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Admin WebSocket connected: {self.channel_name} for user {user.id}")
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'data': {
                'message': 'Successfully connected to admin activity feed',
                'timestamp': timezone.now().isoformat(),
                'user_id': user.id
            }
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Vendor-specific notifications
    async def vendor_registered(self, event):
        """Handle new vendor registration notification"""
        await self.send_notification({
            'type': 'vendor.registered',
            'data': event.get('data', {})
        })

    async def vendor_approved(self, event):
        """Handle vendor approval notification"""
        await self.send_notification({
            'type': 'vendor.approved',
            'data': event.get('data', {})
        })

    async def vendor_rejected(self, event):
        """Handle vendor rejection notification"""
        await self.send_notification({
            'type': 'vendor.rejected',
            'data': event.get('data', {})
        })

    async def activity_update(self, event):
        """Handle generic activity updates for admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'activity_update',
            'activity': event.get('data', {})
        }))


class VendorNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for vendor-specific notifications.
    Handles real-time notifications for vendor activities and updates.
    """
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        
        if not user or not user.is_authenticated or not hasattr(user, 'vendor'):
            logger.warning(f"Unauthorized WebSocket connection attempt by {user}")
            await self.close()
            return
            
        self.vendor_id = str(user.vendor.id)
        self.room_group_name = f'vendor_{self.vendor_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Vendor WebSocket connected: {self.channel_name} for vendor {self.vendor_id}")
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'data': {
                'message': f'Successfully connected to vendor notifications',
                'vendor_id': self.vendor_id,
                'business_name': user.vendor.business_name,
                'timestamp': timezone.now().isoformat()
            }
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    # Status update notifications
    async def status_updated(self, event):
        """Handle vendor status update notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'status.updated',
                'data': {
                    'status': event.get('status'),
                    'message': 'Your account status has been updated',
                    'timestamp': timezone.now().isoformat()
                }
            }))
        except Exception as e:
            logger.error(f"Error sending status update: {str(e)}")
        
    async def approval_notification(self, event):
        """Handle vendor approval notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'account.approved',
                'data': {
                    'message': 'Your vendor account has been approved!',
                    'timestamp': timezone.now().isoformat(),
                    'next_steps': 'You can now access all vendor features.'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending approval notification: {str(e)}")
        
    async def rejection_notification(self, event):
        """Handle vendor rejection notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'account.rejected',
                'data': {
                    'message': 'Your vendor account application has been reviewed',
                    'status': 'rejected',
                    'reason': event.get('reason', 'No reason provided'),
                    'timestamp': timezone.now().isoformat(),
                    'contact_support': 'Please contact support for more information.'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending rejection notification: {str(e)}")


class CourierNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for courier-specific notifications.
    Handles real-time notifications for courier activities and updates.
    """
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        
        if not user or not user.is_authenticated or not hasattr(user, 'courier_profile'):
            logger.warning(f"Unauthorized WebSocket connection attempt by {user}")
            await self.close()
            return
            
        self.courier_id = str(user.courier_profile.id)
        self.room_group_name = f'courier_{self.courier_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Courier WebSocket connected: {self.channel_name} for courier {self.courier_id}")
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'data': {
                'message': 'Successfully connected to courier notifications',
                'timestamp': timezone.now().isoformat(),
                'courier_id': self.courier_id
            }
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def verification_approved(self, event):
        """Handle courier approval notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'account.approved',
                'data': {
                    'message': 'Your courier account has been approved!',
                    'status': 'approved',
                    'timestamp': timezone.now().isoformat(),
                    'next_steps': 'You can now start accepting delivery requests.'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending approval notification: {str(e)}")
        
    async def verification_rejected(self, event):
        """Handle courier rejection notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'account.rejected',
                'data': {
                    'message': 'Your courier account application has been reviewed',
                    'status': 'rejected',
                    'reason': event.get('reason', 'No reason provided'),
                    'timestamp': timezone.now().isoformat(),
                    'contact_support': 'Please contact support for more information.'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending rejection notification: {str(e)}")
