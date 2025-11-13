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
        
        if not user or not user.is_authenticated or not hasattr(user, 'vendor_profile'):
            logger.warning(f"Unauthorized WebSocket connection attempt by {user}")
            await self.close()
            return
            
        self.vendor_id = str(user.vendor_profile.id)
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
                'business_name': user.vendor_profile.business_name,
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

    async def new_delivery_request(self, event):
        """Handle new delivery request notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'delivery.request',
                'data': {
                    'order_id': event.get('order_id'),
                    'pickup_location': event.get('pickup_location'),
                    'delivery_location': event.get('delivery_location'),
                    'estimated_distance': event.get('estimated_distance'),
                    'estimated_time': event.get('estimated_time'),
                    'payment_amount': event.get('payment_amount'),
                    'timestamp': timezone.now().isoformat(),
                    'message': 'New delivery request available'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending delivery request notification: {str(e)}")


class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order tracking.
    Handles order status updates and location tracking for customers, vendors, and couriers.
    """
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        order_id = self.scope['url_route']['kwargs'].get('order_id')

        if not user or not user.is_authenticated:
            logger.warning(f"Unauthorized WebSocket connection attempt by {user}")
            await self.close()
            return

        if not order_id:
            logger.warning("Order ID required for order tracking connection")
            await self.close()
            return

        # Check if user has permission to track this order
        if not await self.can_track_order(user, order_id):
            logger.warning(f"User {user.id} not authorized to track order {order_id}")
            await self.close()
            return

        self.order_id = order_id
        self.user_id = str(user.id)
        self.room_group_name = f'order_{self.order_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Order tracking WebSocket connected: {self.channel_name} for order {self.order_id} by user {self.user_id}")

        # Send initial connection message with current order status
        initial_status = await self.get_order_status(order_id)
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'data': {
                'message': 'Successfully connected to order tracking',
                'order_id': self.order_id,
                'current_status': initial_status,
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

    async def order_status_update(self, event):
        """Handle order status update notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'order.status_update',
                'data': {
                    'order_id': event.get('order_id'),
                    'status': event.get('status'),
                    'previous_status': event.get('previous_status'),
                    'message': event.get('message', 'Order status updated'),
                    'timestamp': event.get('timestamp', timezone.now().isoformat()),
                    'updated_by': event.get('updated_by')
                }
            }))
        except Exception as e:
            logger.error(f"Error sending order status update: {str(e)}")

    async def courier_location_update(self, event):
        """Handle courier location update for delivery tracking"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'courier.location_update',
                'data': {
                    'order_id': event.get('order_id'),
                    'courier_id': event.get('courier_id'),
                    'latitude': event.get('latitude'),
                    'longitude': event.get('longitude'),
                    'timestamp': event.get('timestamp', timezone.now().isoformat()),
                    'estimated_arrival': event.get('estimated_arrival')
                }
            }))
        except Exception as e:
            logger.error(f"Error sending courier location update: {str(e)}")

    async def payment_confirmed(self, event):
        """Handle payment confirmation notification"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'payment.confirmed',
                'data': {
                    'order_id': event.get('order_id'),
                    'amount': event.get('amount'),
                    'payment_method': event.get('payment_method'),
                    'transaction_id': event.get('transaction_id'),
                    'timestamp': event.get('timestamp', timezone.now().isoformat()),
                    'message': 'Payment has been confirmed'
                }
            }))
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")

    @database_sync_to_async
    def can_track_order(self, user, order_id):
        """Check if user can track this order"""
        try:
            from restaurant_features.order.models import Order
            order = Order.objects.get(id=order_id)

            # Customer can track their own orders
            if order.user == user:
                return True

            # Vendor can track orders for their restaurant
            if hasattr(user, 'vendor_profile') and order.vendor == user.vendor_profile:
                return True

            # Courier can track orders assigned to them
            if hasattr(user, 'courier_profile') and order.courier == user.courier_profile:
                return True

            # Admin can track all orders
            if user.is_superuser:
                return True

            return False
        except Exception:
            return False

    @database_sync_to_async
    def get_order_status(self, order_id):
        """Get current order status"""
        try:
            from restaurant_features.order.models import Order
            order = Order.objects.get(id=order_id)
            return {
                'status': order.status,
                'status_display': order.get_status_display(),
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat()
            }
        except Exception:
            return None
