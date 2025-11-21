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
        response = self.get_response(request)
        
        # For all requests, ensure x-cart-token is in the allowed headers
        if 'Access-Control-Allow-Headers' in response:
            existing_headers = response['Access-Control-Allow-Headers']
            
            # Add x-cart-token if not already present
            if 'x-cart-token' not in existing_headers.lower():
                response['Access-Control-Allow-Headers'] = f"{existing_headers}, x-cart-token"
        
        return response
