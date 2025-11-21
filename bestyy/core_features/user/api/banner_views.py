"""
Banner management API views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db.models import Q
from ..models import Banner
import cloudinary.uploader


class BannerListView(APIView):
    """
    GET /api/user/banners/ - Get active banners for frontend
    POST /api/user/banners/ - Create new banner (admin only)
    """
    permission_classes = [AllowAny]  # GET is public, POST requires authentication check
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """Get active banners for frontend display"""
        try:
            # Query parameters
            banner_type = request.query_params.get('type', None)
            limit = int(request.query_params.get('limit', 10))
            
            # Base query - only currently active banners
            now = timezone.now()
            queryset = Banner.objects.filter(
                is_active=True,
                status='active'
            ).filter(
                Q(display_start_date__isnull=True) | Q(display_start_date__lte=now)
            ).filter(
                Q(display_end_date__isnull=True) | Q(display_end_date__gte=now)
            )
            
            # Filter by type if specified
            if banner_type:
                queryset = queryset.filter(banner_type=banner_type)
            
            # Order by priority and limit
            banners = queryset[:limit]
            
            # Serialize with Cloudinary optimization
            banners_data = []
            for banner in banners:
                image_url = banner.banner_image.url if banner.banner_image else None
                
                # Cloudinary optimization for 1180x192 banners
                optimized_url = None
                thumbnail_url = None
                if image_url and 'cloudinary.com' in image_url:
                    # Full banner optimized
                    optimized_url = image_url.replace('/upload/', '/upload/w_1180,h_192,c_fill,f_auto,q_auto/')
                    # Thumbnail for admin preview
                    thumbnail_url = image_url.replace('/upload/', '/upload/w_300,h_46,c_fill,f_auto,q_auto/')
                else:
                    optimized_url = image_url
                    thumbnail_url = image_url
                
                banners_data.append({
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'image_url': optimized_url,
                    'thumbnail_url': thumbnail_url,
                    'banner_type': banner.banner_type,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'created_at': banner.created_at.isoformat() if banner.created_at else None
                })
            
            return Response({
                'success': True,
                'count': len(banners_data),
                'banner_type': banner_type or 'all',
                'banners': banners_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create new banner (admin only)"""
        try:
            # Check admin permission
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate required fields
            if 'banner_image' not in request.FILES:
                return Response({
                    'success': False,
                    'error': 'Banner image is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create banner
            banner = Banner.objects.create(
                title=request.data.get('title', 'Untitled Banner'),
                description=request.data.get('description', ''),
                banner_image=request.FILES['banner_image'],
                banner_type=request.data.get('banner_type', 'homepage'),
                status=request.data.get('status', 'active'),
                priority=int(request.data.get('priority', 0)),
                click_url=request.data.get('click_url', ''),
                is_active=request.data.get('is_active', 'true').lower() == 'true',
                created_by=request.user
            )
            
            # Handle optional date fields
            if request.data.get('display_start_date'):
                banner.display_start_date = request.data.get('display_start_date')
            if request.data.get('display_end_date'):
                banner.display_end_date = request.data.get('display_end_date')
            banner.save()
            
            # Return created banner
            image_url = banner.banner_image.url if banner.banner_image else None
            optimized_url = image_url.replace('/upload/', '/upload/w_1180,h_192,c_fill,f_auto,q_auto/') if image_url and 'cloudinary.com' in image_url else image_url
            
            return Response({
                'success': True,
                'message': 'Banner created successfully',
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'image_url': optimized_url,
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'is_active': banner.is_active,
                    'created_at': banner.created_at.isoformat()
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
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        """Get banner details"""
        try:
            banner = Banner.objects.get(id=pk)
            
            image_url = banner.banner_image.url if banner.banner_image else None
            optimized_url = image_url.replace('/upload/', '/upload/w_1180,h_192,c_fill,f_auto,q_auto/') if image_url and 'cloudinary.com' in image_url else image_url
            thumbnail_url = image_url.replace('/upload/', '/upload/w_300,h_46,c_fill,f_auto,q_auto/') if image_url and 'cloudinary.com' in image_url else image_url
            
            return Response({
                'success': True,
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'image_url': optimized_url,
                    'thumbnail_url': thumbnail_url,
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'display_start_date': banner.display_start_date.isoformat() if banner.display_start_date else None,
                    'display_end_date': banner.display_end_date.isoformat() if banner.display_end_date else None,
                    'is_active': banner.is_active,
                    'created_at': banner.created_at.isoformat() if banner.created_at else None,
                    'updated_at': banner.updated_at.isoformat() if banner.updated_at else None
                }
            }, status=status.HTTP_200_OK)

        except Banner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Banner not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        """Update banner (admin only)"""
        try:
            # Check admin permission
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            banner = Banner.objects.get(id=pk)
            
            # Update fields if provided
            if 'title' in request.data:
                banner.title = request.data['title']
            if 'description' in request.data:
                banner.description = request.data['description']
            if 'banner_image' in request.FILES:
                # Delete old image from cloudinary if exists
                if banner.banner_image:
                    try:
                        public_id = banner.banner_image.name.split('/')[-1].split('.')[0]
                        cloudinary.uploader.destroy(f"banners/{public_id}")
                    except:
                        pass
                banner.banner_image = request.FILES['banner_image']
            if 'banner_type' in request.data:
                banner.banner_type = request.data['banner_type']
            if 'status' in request.data:
                banner.status = request.data['status']
            if 'priority' in request.data:
                banner.priority = int(request.data['priority'])
            if 'click_url' in request.data:
                banner.click_url = request.data['click_url']
            if 'display_start_date' in request.data:
                banner.display_start_date = request.data['display_start_date']
            if 'display_end_date' in request.data:
                banner.display_end_date = request.data['display_end_date']
            if 'is_active' in request.data:
                banner.is_active = request.data['is_active'].lower() == 'true' if isinstance(request.data['is_active'], str) else bool(request.data['is_active'])
            
            banner.save()
            
            image_url = banner.banner_image.url if banner.banner_image else None
            optimized_url = image_url.replace('/upload/', '/upload/w_1180,h_192,c_fill,f_auto,q_auto/') if image_url and 'cloudinary.com' in image_url else image_url
            
            return Response({
                'success': True,
                'message': 'Banner updated successfully',
                'banner': {
                    'id': banner.id,
                    'title': banner.title,
                    'description': banner.description,
                    'image_url': optimized_url,
                    'banner_type': banner.banner_type,
                    'status': banner.status,
                    'priority': banner.priority,
                    'click_url': banner.click_url,
                    'is_active': banner.is_active,
                    'updated_at': banner.updated_at.isoformat()
                }
            }, status=status.HTTP_200_OK)

        except Banner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Banner not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        """Delete banner (admin only)"""
        try:
            # Check admin permission
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:
                return Response({
                    'success': False,
                    'error': 'Admin privileges required'
                }, status=status.HTTP_403_FORBIDDEN)
            
            banner = Banner.objects.get(id=pk)
            
            # Delete image from cloudinary if exists
            if banner.banner_image:
                try:
                    public_id = banner.banner_image.name.split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(f"banners/{public_id}")
                except:
                    pass
            
            banner.delete()
            
            return Response({
                'success': True,
                'message': 'Banner deleted successfully'
            }, status=status.HTTP_200_OK)

        except Banner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Banner not found'
            }, status=status.HTTP_404_NOT_FOUND)

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

