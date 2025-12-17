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
    
    # Default fallback origins (used only if settings.CORS_ALLOWED_ORIGINS is not set)
    DEFAULT_ALLOWED = [
        'http://localhost:3000',
        'http://localhost:3001',
        'http://localhost:3002',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
        'http://127.0.0.1:3002',
        'https://bestie-admin.vercel.app',
        'https://bestyy-web.vercel.app',
        'https://www.bestyyexpress.com',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Prefer origins defined in Django settings (e.g., from environment variable on Render)
        configured = getattr(settings, 'CORS_ALLOWED_ORIGINS', None)
        if configured:
            # Ensure it's a list
            try:
                self.allowed_origins = list(configured)
            except Exception:
                self.allowed_origins = [configured]
        else:
            self.allowed_origins = list(self.DEFAULT_ALLOWED)
    
    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN', '')
        
        print(f"🟢 CustomCorsMiddleware called! Method: {request.method}, Origin: {origin}")
        
        # Handle preflight OPTIONS requests - RETURN IMMEDIATELY, don't call get_response
        if request.method == 'OPTIONS' and origin in self.allowed_origins:
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
        
        if origin in self.allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Expose-Headers'] = 'x-cart-token'
        
        return response
