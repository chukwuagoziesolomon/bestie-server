"""
Custom CORS decorator to handle x-cart-token header
This bypasses django-cors-headers for specific views
"""
from django.http import HttpResponse
from functools import wraps


def cors_allow_x_cart_token(view_func):
    """
    Decorator that adds x-cart-token to CORS allowed headers for a specific view.
    Use this on views that need the x-cart-token custom header.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = HttpResponse()
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response['Access-Control-Allow-Headers'] = 'accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-cart-token'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
            return response
        
        # For actual requests, call the view and add CORS headers to response
        response = view_func(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Expose-Headers'] = 'x-cart-token'
        return response
    
    return wrapped_view
