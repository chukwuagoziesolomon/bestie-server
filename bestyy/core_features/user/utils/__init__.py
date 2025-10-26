"""
This package contains utility functions for the user app.
"""
# Make websocket_notifications available at the package level
from .websocket_notifications import (
    send_admin_notification,
    send_vendor_notification,
    send_courier_notification,
    notify_vendor_registered,
    notify_vendor_approved,
    notify_vendor_rejected,
    notify_vendor_suspended,
    notify_vendor_activated,
    notify_courier_registered,
    notify_courier_approved,
    notify_courier_rejected,
    notify_courier_suspended,
    notify_courier_activated,
    record_activity
)

from .websocket_auth import (
    WebSocketJWTAuthMiddleware,
    get_websocket_url,
    websocket_auth_middleware
)

__all__ = [
    # WebSocket Notifications
    'send_admin_notification',
    'send_vendor_notification',
    'send_courier_notification',
    'notify_vendor_registered',
    'notify_vendor_approved',
    'notify_vendor_rejected',
    'notify_vendor_suspended',
    'notify_vendor_activated',
    'notify_courier_registered',
    'notify_courier_approved',
    'notify_courier_rejected',
    'notify_courier_suspended',
    'notify_courier_activated',
    'record_activity',
    
    # WebSocket Auth
    'WebSocketJWTAuthMiddleware',
    'get_websocket_url',
    'websocket_auth_middleware'
]
