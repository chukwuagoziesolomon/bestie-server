"""
Custom CORS middleware to handle x-cart-token header.
This middleware ensures the x-cart-token header is properly included in CORS responses.
"""

class CustomCorsMiddleware:
    """
    Custom CORS middleware that ensures x-cart-token is included in allowed headers.
    This works alongside django-cors-headers to add our custom header.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Handle preflight OPTIONS requests
        if request.method == 'OPTIONS':
            response = self.get_response(request)
            
            # Get existing allowed headers from django-cors-headers
            existing_headers = response.get('Access-Control-Allow-Headers', '')
            
            # Add x-cart-token if not already present
            if 'x-cart-token' not in existing_headers.lower():
                if existing_headers:
                    response['Access-Control-Allow-Headers'] = f"{existing_headers}, x-cart-token"
                else:
                    response['Access-Control-Allow-Headers'] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-cart-token"
            
            return response
        
        # For non-OPTIONS requests, just pass through
        response = self.get_response(request)
        return response
