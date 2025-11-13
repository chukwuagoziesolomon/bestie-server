from django.urls import re_path, path
from . import consumers

# Define the app name for URL namespacing
app_name = 'user'

# WebSocket URL patterns
websocket_urlpatterns = [
    # Admin activity notifications
    path('ws/admin/activity/', consumers.AdminActivityConsumer.as_asgi(), name='ws_admin_activity'),

    # Frontend compatibility - redirect /admin/activity/ to /ws/admin/activity/
    path('admin/activity/', consumers.AdminActivityConsumer.as_asgi(), name='ws_admin_activity_compat'),

    # Vendor-specific notifications
    path('ws/vendor/notifications/', consumers.VendorNotificationConsumer.as_asgi(), name='ws_vendor_notifications'),

    # Frontend compatibility - redirect /vendor/notifications/ to /ws/vendor/notifications/
    path('vendor/notifications/', consumers.VendorNotificationConsumer.as_asgi(), name='ws_vendor_notifications_compat'),

    # Courier-specific notifications
    path('ws/courier/notifications/', consumers.CourierNotificationConsumer.as_asgi(), name='ws_courier_notifications'),

    # Frontend compatibility - redirect /courier/notifications/ to /ws/courier/notifications/
    path('courier/notifications/', consumers.CourierNotificationConsumer.as_asgi(), name='ws_courier_notifications_compat'),

    # Order tracking for real-time updates
    re_path(r'ws/orders/(?P<order_id>\d+)/track/', consumers.OrderTrackingConsumer.as_asgi(), name='ws_order_tracking'),
]
