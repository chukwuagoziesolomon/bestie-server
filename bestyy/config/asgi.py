"""
ASGI config for bestyy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import logging
import django
from django.core.asgi import get_asgi_application
from django.conf import settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')

logger.info("Initializing Django...")
# Initialize Django ASGI application first
django.setup()

# Now import other dependencies that might use Django models
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Get the ASGI application
django_asgi_app = get_asgi_application()

# CORS middleware for ASGI
class CORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add CORS headers for HTTP requests
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    # Add CORS headers
                    headers = dict(message.get("headers", []))
                    
                    # Get origin from request
                    origin = None
                    for name, value in scope.get("headers", []):
                        if name == b"origin":
                            origin = value.decode()
                            break
                    
                    # Check if origin is allowed
                    allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
                    if origin in allowed_origins:
                        headers[b"access-control-allow-origin"] = origin.encode()
                        headers[b"access-control-allow-credentials"] = b"true"
                        headers[b"access-control-allow-methods"] = b"GET, POST, PUT, DELETE, OPTIONS, PATCH"
                        headers[b"access-control-allow-headers"] = b"Content-Type, Authorization, X-CSRFToken, X-Requested-With, Accept, Origin"
                        headers[b"access-control-max-age"] = b"86400"
                    
                    # Convert headers back to list format
                    message["headers"] = [(k, v) for k, v in headers.items()]
                
                await send(message)
            
            # Handle OPTIONS preflight requests
            if scope["method"] == "OPTIONS":
                # Get origin from request
                origin = None
                for name, value in scope.get("headers", []):
                    if name == b"origin":
                        origin = value.decode()
                        break
                
                # Check if origin is allowed
                allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
                if origin in allowed_origins:
                    await send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            (b"access-control-allow-origin", origin.encode()),
                            (b"access-control-allow-credentials", b"true"),
                            (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                            (b"access-control-allow-headers", b"Content-Type, Authorization, X-CSRFToken, X-Requested-With, Accept, Origin"),
                            (b"access-control-max-age", b"86400"),
                            (b"content-length", b"0"),
                        ],
                    })
                    await send({"type": "http.response.body", "body": b""})
                    return
                else:
                    await send({
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-length", b"0")],
                    })
                    await send({"type": "http.response.body", "body": b""})
                    return
            
            await self.app(scope, receive, send_with_cors)
        else:
            # For WebSocket and other protocols, pass through
            await self.app(scope, receive, send)

# Import WebSocket URL patterns from the user app
try:
    logger.info("Importing WebSocket URL patterns...")
    from bestyy.core_features.user.routing import websocket_urlpatterns
    from bestyy.core_features.user.utils.websocket_auth import WebSocketJWTAuthMiddleware
    
    logger.info(f"Found {len(websocket_urlpatterns)} WebSocket URL patterns")
    
    # Define the ASGI application with WebSocket support and CORS
    application = ProtocolTypeRouter({
        "http": CORSMiddleware(django_asgi_app),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                WebSocketJWTAuthMiddleware(
                    URLRouter(
                        websocket_urlpatterns
                    )
                )
            )
        ),
    })
    logger.info("ASGI application configured with WebSocket support and CORS")
    
    # Log WebSocket configuration
    allowed_hosts = getattr(django.conf.settings, 'ALLOWED_HOSTS', [])
    logger.info(f"WebSocket allowed hosts: {allowed_hosts}")
    logger.info("WebSocket endpoints:")
    for pattern in websocket_urlpatterns:
        logger.info(f"  - {pattern.pattern}")
        
except ImportError as e:
    logger.error(f"Failed to import WebSocket URL patterns: {e}", exc_info=True)
    application = CORSMiddleware(django_asgi_app)
except Exception as e:
    logger.error(f"Error setting up WebSocket: {str(e)}", exc_info=True)
    # Fall back to HTTP-only if WebSocket setup fails
    application = CORSMiddleware(django_asgi_app)