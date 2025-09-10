from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET', 'POST', 'OPTIONS'])
@permission_classes([AllowAny])
def cors_test(request):
    """
    Test endpoint to verify CORS is working properly
    """
    if request.method == 'OPTIONS':
        # Handle preflight request
        return Response(status=status.HTTP_200_OK)
    
    return Response({
        'message': 'CORS is working!',
        'method': request.method,
        'origin': request.META.get('HTTP_ORIGIN', 'No origin header'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'No user agent'),
        'cors_headers': {
            'access_control_allow_origin': request.META.get('HTTP_ACCESS_CONTROL_ALLOW_ORIGIN', 'Not set'),
            'access_control_allow_methods': request.META.get('HTTP_ACCESS_CONTROL_ALLOW_METHODS', 'Not set'),
            'access_control_allow_headers': request.META.get('HTTP_ACCESS_CONTROL_ALLOW_HEADERS', 'Not set'),
        }
    }, status=status.HTTP_200_OK)
