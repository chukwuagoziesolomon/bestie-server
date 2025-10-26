"""
Utilities for WebSocket authentication.
"""
import json
import logging
from urllib.parse import parse_qs
from django.conf import settings
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import AccessToken
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
User = get_user_model()

class WebSocketJWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication of WebSocket connections.
    """
    async def __call__(self, scope, receive, send):
        # Close old database connections to prevent connection leaks
        close_old_connections()
        
        # Initialize user as None by default
        scope['user'] = None
        
        try:
            # Get token from query string
            query_string = scope.get('query_string', b'').decode('utf-8')
            logger.debug(f"WebSocket connection attempt. Query string: {query_string}")
            
            query_params = parse_qs(query_string)
            tokens = query_params.get('token', [])
            
            if not tokens:
                logger.warning("No token provided in WebSocket connection")
                # Send error message to client and close connection
                await send({
                    'type': 'websocket.close',
                    'code': 4001,
                    'reason': 'Authentication token not provided'
                })
                return
                
            token = tokens[0]
            logger.debug(f"Token found: {token[:10]}...")
            
            try:
                # Validate token
                access_token = AccessToken(token)
                user = await self.get_user(access_token['user_id'])
                
                if not user:
                    raise Exception("User not found")
                    
                if not user.is_active:
                    raise Exception("User account is disabled")
                
                scope['user'] = user
                logger.info(f"WebSocket authenticated for user: {user.email}")
                
                # Continue with the connection
                return await super().__call__(scope, receive, send)
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Authentication failed: {error_msg}")
                
                # Send appropriate error message based on error type
                if "expired" in error_msg.lower():
                    close_code = 4002
                    close_reason = "Authentication token has expired. Please refresh your token."
                elif "invalid" in error_msg.lower():
                    close_code = 4003
                    close_reason = "Invalid authentication token."
                else:
                    close_code = 4004
                    close_reason = "Authentication failed. Please log in again."
                
                await send({
                    'type': 'websocket.close',
                    'code': close_code,
                    'reason': close_reason
                })
                return
                
        except Exception as e:
            logger.error(f"Unexpected error during WebSocket authentication: {str(e)}")
            await send({
                'type': 'websocket.close',
                'code': 4000,
                'reason': 'Internal server error during authentication'
            })
            return

    @sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

def get_websocket_url(path, token):
    """
    Generate a WebSocket URL with authentication token.
    
    Args:
        path (str): WebSocket path (e.g., '/ws/vendor/notifications/')
        token (str): JWT token for authentication
        
    Returns:
        str: Full WebSocket URL with token
    """
    # Get the base URL from settings or use the current host
    base_url = getattr(settings, 'WEBSOCKET_BASE_URL', '')
    if not base_url:
        # Fallback to current host if not set
        import os
        host = os.environ.get('HOST', 'localhost:8000')
        protocol = 'wss' if os.environ.get('HTTPS') == 'on' else 'ws'
        base_url = f"{protocol}://{host}"
    
    # Ensure path starts with a slash
    if not path.startswith('/'):
        path = f'/{path}'
    
    # Build the URL with token
    query_params = {'token': token}
    return f"{base_url}{path}?{urlencode(query_params)}"

def websocket_auth_middleware(inner):
    """
    Middleware for WebSocket authentication.
    
    Usage:
        application = ProtocolTypeRouter({
            "websocket": WebSocketJWTAuthMiddleware(
                AuthMiddlewareStack(
                    URLRouter(
                        # Your WebSocket routing here
                    )
                )
            ),
        })
    """
    return WebSocketJWTAuthMiddleware(AuthMiddlewareStack(inner))
