# WebSocket Implementation

This document describes the WebSocket implementation for real-time notifications in the Bestyy platform.

## Overview

The WebSocket implementation provides real-time notifications for:

- Admin activities (new vendor registrations, approvals, rejections)
- Vendor notifications (verification status updates, order updates, etc.)

## WebSocket Endpoints

### Admin Activity Feed
- **URL**: `ws://<host>/ws/admin/activity/`
- **Authentication**: Staff users only
- **Events**:
  - `vendor.registered`: New vendor registration
  - `vendor.approved`: Vendor approved
  - `vendor.rejected`: Vendor rejected

### Vendor Notifications
- **URL**: `ws://<host>/ws/vendor/notifications/`
- **Authentication**: Vendor users only
- **Events**:
  - `verification.approved`: Vendor account approved
  - `verification.rejected`: Vendor account rejected
  - `order.updated`: Order status update
  - `payment.received`: Payment received

## Message Format

All WebSocket messages follow this format:

```json
{
  "type": "event.type",
  "timestamp": "2023-01-01T12:00:00Z",
  "data": {
    // Event-specific data
  }
}
```

## Implementation Details

### Backend

- **Consumers**:
  - `AdminActivityConsumer`: Handles admin activity feed
  - `VendorNotificationConsumer`: Handles vendor-specific notifications

- **Utilities**:
  - `websocket_notifications.py`: Helper functions for sending WebSocket notifications

### Frontend

The frontend should implement WebSocket clients to connect to these endpoints and handle incoming messages. Example:

```javascript
// Connect to WebSocket
const socket = new WebSocket(`ws://${window.location.host}/ws/vendor/notifications/`);

// Handle incoming messages
socket.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received message:', data);
  
  switch(data.type) {
    case 'verification.approved':
      // Handle approval
      break;
    case 'verification.rejected':
      // Handle rejection
      break;
    // Handle other event types
  }
};

// Handle connection open
socket.onopen = function() {
  console.log('WebSocket connection established');
};

// Handle errors
socket.onerror = function(error) {
  console.error('WebSocket error:', error);
};
```

## Testing

Run the WebSocket tests with:

```bash
python manage.py test user.tests.test_consumers user.tests.test_websocket_notifications
```

## Dependencies

- Django Channels
- Redis (for production channel layer)
- `channels_redis` (Redis channel layer backend)

## Deployment Notes

1. Ensure Redis is running and properly configured
2. Configure the `CHANNEL_LAYERS` setting in `settings.py`
3. Make sure your web server (e.g., Daphne, Uvicorn) is configured to handle WebSocket connections
4. Set up proper WebSocket proxy settings in your web server (Nginx/Apache) if needed
