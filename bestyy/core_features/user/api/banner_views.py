"""
Banner management API views - DISABLED (Banner model removed)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status


class BannerListView(APIView):
    """
    GET /api/user/banners/ - Get active banners for frontend
    POST /api/user/banners/ - Create new banner (admin only)
    """
    permission_classes = [AllowAny]  # GET is public, POST requires authentication check

    def get(self, request):
        """Get active banners for frontend display"""
        try:
            # Banner model removed - return empty response
            return Response({
                'success': True,
                'count': 0,
                'banner_type': request.query_params.get('type', 'homepage'),
                'banners': [],
                'message': 'Banner system is currently disabled'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create new banner (admin only)"""
        try:
            # Banner model removed - return error
            return Response({
                'success': False,
                'error': 'Banner system is currently disabled',
                'message': 'Banner creation is not available'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BannerDetailView(APIView):
    """
    GET /api/user/banners/{id}/ - Get banner details
    PUT /api/user/banners/{id}/ - Update banner (admin only)
    DELETE /api/user/banners/{id}/ - Delete banner (admin only)
    """
    permission_classes = [AllowAny]  # GET is public, PUT/DELETE require authentication check

    def get(self, request, banner_id):
        """Get banner details"""
        try:
            # Banner model removed - return error
            return Response({
                'success': False,
                'error': 'Banner system is currently disabled',
                'message': 'Banner details are not available'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, banner_id):
        """Update banner (admin only)"""
        try:
            # Banner model removed - return error
            return Response({
                'success': False,
                'error': 'Banner system is currently disabled',
                'message': 'Banner updates are not available'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, banner_id):
        """Delete banner (admin only)"""
        try:
            # Banner model removed - return error
            return Response({
                'success': False,
                'error': 'Banner system is currently disabled',
                'message': 'Banner deletion is not available'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BannerManagementView(APIView):
    """
    GET /api/user/banners/admin/ - Get all banners for admin management
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all banners for admin management"""
        try:
            # Banner model removed - return error
            return Response({
                'success': False,
                'error': 'Banner system is currently disabled',
                'message': 'Banner management is not available',
                'count': 0,
                'total_count': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'has_next': False,
                'has_previous': False,
                'banners': []
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

