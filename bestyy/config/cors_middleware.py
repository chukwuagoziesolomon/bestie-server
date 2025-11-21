"""
Custom CORS middleware - Complete replacement for django-cors-headers
django-cors-headers has a bug where it ignores CORS_ALLOW_HEADERS settings
"""
from django.http import HttpResponse
from django.conf import settings

class CustomCorsMiddleware:
    """
    Complete CORS middleware that properly handles x-cart-token header.
    Replaces django-cors-headers entirely.
    """
    
    ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:3001',
        'http://localhost:3002',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
        'http://127.0.0.1:3002',
        'https://bestie-admin.vercel.app',
        'https://bestyy-web.vercel.app',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN', '')
        
        print(f"🟢 CustomCorsMiddleware called! Method: {request.method}, Origin: {origin}")
        
        # Handle preflight OPTIONS requests - RETURN IMMEDIATELY, don't call get_response
        if request.method == 'OPTIONS' and origin in self.ALLOWED_ORIGINS:
            print(f"🟢 Handling OPTIONS preflight for {origin}")
            response = HttpResponse()
            response.status_code = 200
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response['Access-Control-Allow-Headers'] = 'accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-cart-token'
            response['Access-Control-Max-Age'] = '86400'
            print(f"🟢 Returning CORS headers with x-cart-token")
            return response
        
        # For actual requests, add CORS headers
        response = self.get_response(request)
        
        if origin in self.ALLOWED_ORIGINS:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Expose-Headers'] = 'x-cart-token'
        
        return response
