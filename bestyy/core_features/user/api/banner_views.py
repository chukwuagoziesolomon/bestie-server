"""
Banner management API views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from bestyy.core_features.user.models import Banner, User


class BannerListView(APIView):
    """
    GET /api/user/banners/ - Get active banners for frontend
    POST /api/user/banners/ - Create new banner (admin only)
    """
    permission_classes = [AllowAny]  # GET is public, POST requires authentication check
    
    def get(self, request):
        """Get active banners for frontend display"""
        try:
            banner_type = request.query_params.get('type', 'homepage')
            limit = int(request.query_params.get('limit', 5))
            
            # Get active banners
            banners = Banner.objects.filter(
                Q(status='active') | Q(status='scheduled'),
                banner_type=banner_type,
                display_start_date__lte=timezone.now(),
                display_end_date__gte=timezone.now()
            ).order_by('-priority', '-created_at')[:limit]
            
            # Format response
            banner_data = []
            for banner in banners:
                if banner.is_active:
                    banner_data.append({
                        'id': banner.id,
                        'title': banner.title,
                        'description': banner.description,
                        'banner_image': banner.get_optimized_image_url(),
                        'banner_type': banner.banner_type,
                        'click_url': banner.click_url,
                        'priority': banner.priority,
                        'target_audience': banner.target_audience,
                        'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                        'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                        'created_at': banner.created_at.isoformat(),
                    })
            
            return Response({
                'success': True,
                'count': len(banner_data),
                'banner_type': banner_type,
                'banners': banner_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create new banner (admin only)"""
        try:
            # Check if user is authenticated and is admin
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if user has admin privileges (you can customize this check)
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Create banner
            banner_data = request.data.copy()
            banner_data['created_by'] = request.user.id
            
            banner = Banner.objects.create(**banner_data)
            
            return Response({
                'success': True,
                'message': 'Banner created successfully',
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'banner_image': banner.get_optimized_image_url(),
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'target_audience': banner.target_audience,
                    'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                    'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                    'created_at': banner.created_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
            
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
            banner = get_object_or_404(Banner, id=banner_id)
            
            return Response({
                'success': True,
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'banner_image': banner.get_optimized_image_url(),
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'target_audience': banner.target_audience,
                    'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                    'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                    'created_by': banner.created_by.username if banner.created_by else None,
                    'created_at': banner.created_at.isoformat(),
                    'updated_at': banner.updated_at.isoformat(),
                    'is_active': banner.is_active,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, banner_id):
        """Update banner (admin only)"""
        try:
            # Check if user is authenticated and is admin
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            banner = get_object_or_404(Banner, id=banner_id)
            
            # Update banner fields
            for field, value in request.data.items():
                if hasattr(banner, field) and field != 'id':
                    setattr(banner, field, value)
            
            banner.save()
            
            return Response({
                'success': True,
                'message': 'Banner updated successfully',
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'banner_image': banner.get_optimized_image_url(),
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'target_audience': banner.target_audience,
                    'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                    'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                    'created_at': banner.created_at.isoformat(),
                    'updated_at': banner.updated_at.isoformat(),
                    'is_active': banner.is_active,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, banner_id):
        """Delete banner (admin only)"""
        try:
            # Check if user is authenticated and is admin
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            banner = get_object_or_404(Banner, id=banner_id)
            banner_title = banner.title
            banner.delete()
            
            return Response({
                'success': True,
                'message': f'Banner "{banner_title}" deleted successfully'
            }, status=status.HTTP_200_OK)
            
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
            # Check if user is admin
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get query parameters
            banner_type = request.query_params.get('type')
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Build queryset
            queryset = Banner.objects.all().order_by('-priority', '-created_at')
            
            if banner_type:
                queryset = queryset.filter(banner_type=banner_type)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Pagination
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            banners = queryset[start_index:end_index]
            
            # Format response
            banner_data = []
            for banner in banners:
                banner_data.append({
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'banner_image': banner.get_optimized_image_url(),
                    'banner_thumbnail': banner.get_thumbnail_url(),
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'target_audience': banner.target_audience,
                    'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                    'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                    'created_by': banner.created_by.username if banner.created_by else None,
                    'created_at': banner.created_at.isoformat(),
                    'updated_at': banner.updated_at.isoformat(),
                    'is_active': banner.is_active,
                })
            
            return Response({
                'success': True,
                'count': len(banner_data),
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'banners': banner_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

