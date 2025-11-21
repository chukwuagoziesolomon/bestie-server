"""
Service for broadcasting order status updates via WebSockets
"""
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


class OrderStatusBroadcastService:
    """Service for broadcasting order status updates to WebSocket clients"""

    @staticmethod
    def broadcast_order_status_update(order, previous_status=None, updated_by=None):
        """Broadcast order status update to all relevant parties"""
        try:
            channel_layer = get_channel_layer()

            # Prepare status update data
            status_data = {
                'type': 'order_status_update',
                'data': {
                    'order_id': order.id,
                    'status': order.status,
                    'previous_status': previous_status,
                    'message': f'Order status changed to {order.status}',
                    'timestamp': timezone.now().isoformat(),
                    'updated_by': updated_by or 'system'
                }
            }

            # Broadcast to order tracking group
            async_to_sync(channel_layer.group_send)(
                f'order_{order.id}',
                status_data
            )

            # Also broadcast to vendor if they have WebSocket connection
            if hasattr(order.vendor, 'user'):
                async_to_sync(channel_layer.group_send)(
                    f'vendor_{order.vendor.id}',
                    {
                        'type': 'order_status_update',
                        'data': {
                            'order_id': order.id,
                            'customer_name': f"{order.customer.first_name} {order.customer.last_name}".strip() if order.customer else 'Guest',
                            'status': order.status,
                            'previous_status': previous_status,
                            'total_amount': float(order.total_amount),
                            'timestamp': timezone.now().isoformat(),
                            'message': f'Order #{order.id} status changed to {order.status}'
                        }
                    }
                )

            # Broadcast to courier if assigned
            if order.courier:
                async_to_sync(channel_layer.group_send)(
                    f'courier_{order.courier.id}',
                    {
                        'type': 'order_status_update',
                        'data': {
                            'order_id': order.id,
                            'status': order.status,
                            'previous_status': previous_status,
                            'pickup_location': order.vendor.business_address,
                            'delivery_location': order.delivery_address,
                            'timestamp': timezone.now().isoformat(),
                            'message': f'Order #{order.id} status changed to {order.status}'
                        }
                    }
                )

            logger.info(f"Broadcasted order {order.id} status update from {previous_status} to {order.status}")
            return True

        except Exception as e:
            logger.error(f"Error broadcasting order status update for order {order.id}: {str(e)}")
            return False

    @staticmethod
    def broadcast_payment_confirmed(order):
        """Broadcast payment confirmation to order tracking"""
        try:
            channel_layer = get_channel_layer()

            payment_data = {
                'type': 'payment_confirmed',
                'data': {
                    'order_id': order.id,
                    'amount': float(order.total_amount),
                    'payment_method': order.payment_method,
                    'transaction_id': f"CONFIRMED_{order.id}_{int(timezone.now().timestamp())}",
                    'timestamp': timezone.now().isoformat(),
                    'message': 'Payment has been confirmed'
                }
            }

            # Broadcast to order tracking group
            async_to_sync(channel_layer.group_send)(
                f'order_{order.id}',
                payment_data
            )

            logger.info(f"Broadcasted payment confirmation for order {order.id}")
            return True

        except Exception as e:
            logger.error(f"Error broadcasting payment confirmation for order {order.id}: {str(e)}")
            return False

    @staticmethod
    def broadcast_courier_location_update(order, courier, latitude, longitude, estimated_arrival=None):
        """Broadcast courier location update for delivery tracking"""
        try:
            channel_layer = get_channel_layer()

            location_data = {
                'type': 'courier_location_update',
                'data': {
                    'order_id': order.id,
                    'courier_id': courier.id,
                    'latitude': latitude,
                    'longitude': longitude,
                    'timestamp': timezone.now().isoformat(),
                    'estimated_arrival': estimated_arrival.isoformat() if estimated_arrival else None
                }
            }

            # Broadcast to order tracking group (customer)
            async_to_sync(channel_layer.group_send)(
                f'order_{order.id}',
                location_data
            )

            logger.info(f"Broadcasted courier location update for order {order.id}")
            return True

        except Exception as e:
            logger.error(f"Error broadcasting courier location update for order {order.id}: {str(e)}")
            return False

    @staticmethod
    def broadcast_new_delivery_request(order, nearby_couriers):
        """Broadcast new delivery request to nearby couriers"""
        try:
            channel_layer = get_channel_layer()

            # Calculate estimated distance and time (simplified)
            estimated_distance = "5-10 km"  # This should be calculated based on actual locations
            estimated_time = "15-30 min"
            estimated_payment = float(order.delivery_fee or 1500)  # Default delivery fee

            delivery_data = {
                'type': 'new_delivery_request',
                'data': {
                    'order_id': order.id,
                    'pickup_location': order.vendor.business_address,
                    'delivery_location': order.delivery_address,
                    'estimated_distance': estimated_distance,
                    'estimated_time': estimated_time,
                    'payment_amount': estimated_payment,
                    'timestamp': timezone.now().isoformat(),
                    'message': 'New delivery request available'
                }
            }

            # Broadcast to all nearby couriers
            for courier in nearby_couriers:
                async_to_sync(channel_layer.group_send)(
                    f'courier_{courier.id}',
                    delivery_data
                )

            logger.info(f"Broadcasted new delivery request for order {order.id} to {len(nearby_couriers)} couriers")
            return True

        except Exception as e:
            logger.error(f"Error broadcasting new delivery request for order {order.id}: {str(e)}")
            return False