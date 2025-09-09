# WebSocket Setup and Testing

This document provides instructions for setting up and testing the WebSocket functionality in the Bestyy backend.

## Prerequisites

- Python 3.8+
- Redis server (for production)
- Django Channels
- ASGI server (Daphne or Uvicorn)

## Installation

1. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

2. For development, install the additional development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

## Configuration

1. Make sure your `settings.py` includes the following:

   ```python
   # Add 'channels' to INSTALLED_APPS
   INSTALLED_APPS = [
       # ...
       'channels',
       # ...
   ]

   # Configure ASGI application
   ASGI_APPLICATION = 'bestyy.asgi.application'

   # Channel layers configuration (development with in-memory layer)
   CHANNEL_LAYERS = {
       'default': {
           'BACKEND': 'channels.layers.InMemoryChannelLayer',
       },
   }

   # For production, use Redis:
   # CHANNEL_LAYERS = {
   #     'default': {
   #         'BACKEND': 'channels_redis.core.RedisChannelLayer',
   #         'CONFIG': {
   #             "hosts": [('redis', 6379)],
   #         },
   #     },
   # }
   ```

## Running the Server

1. Start the Redis server (if using Redis):

   ```bash
   redis-server
   ```

2. Run the Django development server with Daphne:

   ```bash
   daphne bestyy.asgi:application
   ```

   Or with Uvicorn:

   ```bash
   uvicorn bestyy.asgi:application --reload
   ```

## Testing WebSockets

### Using the Test Script

1. Install the test dependencies:

   ```bash
   pip install websockets
   ```

2. Run the test script:

   ```bash
   python test_websocket.py --token YOUR_JWT_TOKEN --type vendor
   ```

   Replace `YOUR_JWT_TOKEN` with a valid JWT token for an admin or vendor user.

### Manual Testing with Python Console

1. Open a Python shell:

   ```bash
   python manage.py shell
   ```

2. Test sending a notification:

   ```python
   from user.utils.websocket_notifications import send_admin_notification, send_vendor_notification
   
   # Send a test notification to all admins
   send_admin_notification(
       'test.notification',
       {'message': 'This is a test notification', 'type': 'test'}
   )
   
   # Send a test notification to a specific vendor
   from user.models import VendorProfile
   vendor = VendorProfile.objects.first()
   send_vendor_notification(
       vendor.id,
       'test.notification',
       {'message': 'Hello vendor!', 'type': 'test'}
   )
   ```

### Frontend Testing

1. Start your frontend development server (typically on port 3000).
2. Make sure CORS is properly configured in your Django settings to allow WebSocket connections from the frontend.
3. Use the example frontend code provided in `docs/FRONTEND_WEBSOCKET_EXAMPLE.md` to test the WebSocket connection.

## Troubleshooting

### Connection Issues

- **"WebSocket connection failed"**: Make sure the WebSocket server is running and accessible.
- **"403 Forbidden"**: Check your authentication token and CORS settings.
- **"Connection refused"**: Verify that Redis is running if you're using it in production.

### Performance Issues

- If you experience high latency, consider using a production-grade ASGI server like Daphne or Uvicorn with multiple workers.
- For high-traffic applications, consider using a Redis cluster for the channel layer.

## Deployment

1. Configure your web server (Nginx/Apache) to proxy WebSocket connections:

   **Nginx example:**
   ```nginx
   location /ws/ {
       proxy_pass http://django_asgi_server;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_redirect off;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Host $server_name;
   }
   ```

2. Use a process manager like Supervisor or systemd to manage the ASGI server process.

## Monitoring

- Monitor WebSocket connections and message rates using Django's logging or a monitoring solution like Prometheus.
- Set up alerts for connection failures or high error rates.

## Security Considerations

- Always use WSS (WebSocket Secure) in production.
- Validate and sanitize all WebSocket messages on the server.
- Implement rate limiting to prevent abuse.
- Use secure WebSocket origins to prevent cross-site WebSocket hijacking (CSWSH).
