"""
API views for vendor menu items - allows users to view menu items for a specific vendor
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Count, Avg
from rest_framework.permissions import IsAuthenticated
from bestyy.core_features.user.permissions import IsVerifiedVendor

from bestyy.restaurant_features.product.models import Product as MenuItem, Category
from bestyy.core_features.user.models import VendorProfile
from bestyy.restaurant_features.vendor.models import Vendor


class VendorMenuItemsView(APIView):
    """
    Get all menu items for a specific vendor
    GET /api/user/vendor/{vendor_id}/menu/
    """
    permission_classes = [AllowAny]  # Public access to view menus

    def get(self, request, vendor_id):
        """Get all menu items for a vendor"""
        try:
            # Get the vendor profile
            vendor_profile = get_object_or_404(VendorProfile, id=vendor_id, is_suspended=False)

            # Get the corresponding Vendor instance - create if it doesn't exist
            try:
                vendor = Vendor.objects.get(user=vendor_profile.user)
            except Vendor.DoesNotExist:
                # Create Vendor instance if it doesn't exist
                vendor = Vendor.objects.create(
                    user=vendor_profile.user,
                    business_name=vendor_profile.business_name,
                    business_address=vendor_profile.business_address,
                    phone_number=vendor_profile.phone,
                    is_verified=vendor_profile.verification_status == 'approved'
                )

            # Get all menu items for this vendor
            menu_items = MenuItem.objects.filter(vendor=vendor_profile).order_by('category', 'name')

            # Format menu items
            menu_data = []
            for item in menu_items:
                # Handle image URL
                image_url = None
                if item.image:
                    try:
                        # If it's already a string URL (Cloudinary), return it directly
                        if isinstance(item.image, str):
                            if 'cloudinary.com' in item.image:
                                # Transform for web optimization
                                image_url = item.image.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                            else:
                                image_url = item.image
                        # If it's a Django ImageField/FileField, get the URL
                        elif hasattr(item.image, 'url'):
                            image_url = item.image.url
                            if 'cloudinary.com' in image_url:
                                # Transform for web optimization
                                image_url = image_url.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                            else:
                                # For local images, construct full URL
                                image_url = f"{settings.MEDIA_URL}{image_url}"
                        # Handle case where image might be a field that has a name attribute (Cloudinary URL stored as string)
                        elif hasattr(item.image, 'name') and isinstance(item.image.name, str):
                            if 'cloudinary.com' in item.image.name:
                                # Transform for web optimization
                                image_url = item.image.name.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                            else:
                                image_url = item.image.name
                    except Exception:
                        image_url = None

                # Handle video URL
                video_url = None
                if hasattr(item, 'video') and item.video:
                    try:
                        # If it's already a string URL (Cloudinary), return it directly
                        if isinstance(item.video, str):
                            if 'cloudinary.com' in item.video:
                                # Keep original video URL
                                video_url = item.video
                            else:
                                video_url = item.video
                        # If it's a Django ImageField/FileField, get the URL
                        elif hasattr(item.video, 'url'):
                            video_url = item.video.url
                            if 'cloudinary.com' in video_url:
                                # Keep original video URL
                                pass
                            else:
                                # For local videos, construct full URL
                                video_url = f"{settings.MEDIA_URL}{video_url}"
                    except Exception:
                        video_url = None

                menu_data.append({
                    'id': item.id,
                    'dish_name': item.name,
                    'item_description': item.description,
                    'price': float(item.price),
                    'category': item.category.name if item.category else None,
                    'image': image_url,
                    'video': video_url,
                    'available_now': item.is_available,
                    'quantity': item.stock_quantity,
                    'created_at': item.created_at.isoformat()
                })

            # Group by category for better frontend display
            categories = {}
            for item in menu_data:
                category = item['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)

            # Get vendor basic info
            vendor_info = {
                'id': vendor_profile.id,
                'business_name': vendor_profile.business_name,
                'business_category': vendor_profile.business_category,
                'business_description': vendor_profile.business_description,
                'logo': self._get_vendor_logo_url(vendor_profile),
                'cover_image': self._get_vendor_cover_url(vendor_profile),
                'is_featured': getattr(vendor_profile, 'is_featured', False),
                'offers_delivery': vendor_profile.offers_delivery,
                'opening_hours': vendor_profile.opening_hours.strftime('%H:%M') if vendor_profile.opening_hours else None,
                'closing_hours': vendor_profile.closing_hours.strftime('%H:%M') if vendor_profile.closing_hours else None,
                'is_open': self._is_vendor_open(vendor_profile),
                'phone': vendor_profile.phone,
                'business_address': vendor_profile.business_address,
                'service_areas': vendor_profile.service_areas.split(',') if vendor_profile.service_areas else [],
                'delivery_radius': vendor_profile.delivery_radius,
                'verification_status': vendor_profile.verification_status,
                'created_at': vendor_profile.created_at.isoformat(),
                'updated_at': vendor_profile.updated_at.isoformat()
            }

            return Response({
                'success': True,
                'vendor': vendor_info,
                'menu_items': menu_data,
                'categories': categories,
                'total_items': len(menu_data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_vendor_logo_url(self, vendor):
        """Get vendor logo URL"""
        if vendor.logo:
            try:
                # Since logo is now URLField (string), handle it directly
                logo_url = vendor.logo
                if isinstance(logo_url, str) and 'cloudinary.com' in logo_url:
                    # Add Cloudinary transformations for optimized display
                    logo_url = logo_url.replace('/upload/', '/upload/w_200,h_200,c_fill,f_auto,q_auto/')
                return logo_url
            except Exception:
                pass
        return None

    def _get_vendor_cover_url(self, vendor):
        """Get vendor cover image URL"""
        if hasattr(vendor, 'cover_image') and vendor.cover_image:
            try:
                # Since cover_image is now URLField (string), handle it directly
                cover_url = vendor.cover_image
                if isinstance(cover_url, str) and 'cloudinary.com' in cover_url:
                    # Add Cloudinary transformations for optimized display
                    cover_url = cover_url.replace('/upload/', '/upload/w_800,h_400,c_fill,f_auto,q_auto/')
                return cover_url
            except Exception:
                pass
        return None

    def _is_vendor_open(self, vendor):
        """Check if vendor is currently open"""
        if not vendor.opening_hours or not vendor.closing_hours:
            return True  # Assume open if hours not set

        from datetime import datetime
        current_time = datetime.now().time()
        return vendor.opening_hours <= current_time <= vendor.closing_hours


class VendorMenuListView(APIView):
    """
    List and create menu items for a vendor
    GET /api/user/vendors/menu/ - List vendor's menu items
    POST /api/user/vendors/menu/ - Create new menu item
    """
    permission_classes = [IsVerifiedVendor]

    def get(self, request):
        """List all menu items for the authenticated vendor"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Get query parameters for filtering
            category = request.query_params.get('category')
            available_only = request.query_params.get('available_only', 'false').lower() == 'true'

            # Build queryset
            queryset = MenuItem.objects.filter(vendor=vendor)

            if category:
                queryset = queryset.filter(category__icontains=category)

            if available_only:
                queryset = queryset.filter(available_now=True)

            menu_items = queryset.order_by('category', 'name')

            # Format response
            items_data = []
            for item in menu_items:
                items_data.append({
                    'id': item.id,
                    'dish_name': item.name,
                    'item_description': item.description,
                    'price': float(item.price),
                    'category': item.category.name if item.category else None,
                    'available_now': item.is_available,
                    'quantity': item.stock_quantity,
                    'image': self._get_image_url(item.image) if hasattr(item, 'image') else None,
                    'video': self._get_image_url(item.video) if hasattr(item, 'video') else None,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat()
                })

            return Response({
                'success': True,
                'count': len(items_data),
                'menu_items': items_data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create a new menu item"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Validate required fields
            required_fields = ['dish_name', 'price', 'category']
            for field in required_fields:
                if field not in request.data:
                    return Response({
                        'success': False,
                        'error': f'{field} is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Handle image upload to Cloudinary
            image_url = None
            if 'image' in request.FILES:
                from utils.cloudinary_utils import upload_to_cloudinary
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['image'],
                        folder=f"menu_items/{vendor.id}",
                        resource_type='image'
                    )
                    image_url = upload_response['secure_url']
                except Exception as e:
                    # Log the error but don't fail the request - allow menu item creation without image
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Failed to upload image: {str(e)}')
                    # Continue without image
            elif 'image' in request.data and isinstance(request.data['image'], str):
                # Handle Cloudinary URL directly
                image_url = request.data['image']

            # Handle video upload to Cloudinary
            video_url = None
            if 'video' in request.FILES:
                from utils.cloudinary_utils import upload_to_cloudinary
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['video'],
                        folder=f"menu_items/{vendor.id}",
                        resource_type='video'
                    )
                    video_url = upload_response['secure_url']
                except Exception as e:
                    # Log the error but don't fail the request - allow menu item creation without video
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Failed to upload video: {str(e)}')
                    # Continue without video
            elif 'video' in request.data and isinstance(request.data['video'], str):
                # Handle Cloudinary URL directly
                video_url = request.data['video']

            # Get or create category
            category_name = request.data['category']
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'{category_name} category'}
            )

            # Create menu item
            menu_item = MenuItem.objects.create(
                vendor=vendor,
                name=request.data['dish_name'],
                description=request.data.get('item_description', ''),
                price=request.data['price'],
                category=category,
                is_available=self._parse_boolean(request.data.get('available_now', True)),
                stock_quantity=request.data.get('quantity', 0)
            )

            # Set image and video if provided
            if image_url:
                menu_item.image = image_url
            if video_url:
                menu_item.video = video_url
            menu_item.save()

            return Response({
                'success': True,
                'message': 'Menu item created successfully',
                'menu_item': {
                    'id': menu_item.id,
                    'dish_name': menu_item.name,
                    'item_description': menu_item.description,
                    'price': float(menu_item.price),
                    'category': menu_item.category.name if menu_item.category else None,
                    'available_now': menu_item.is_available,
                    'quantity': menu_item.stock_quantity,
                    'image': self._get_image_url(menu_item.image) if hasattr(menu_item, 'image') else None,
                    'video': self._get_image_url(menu_item.video) if hasattr(menu_item, 'video') else None,
                    'created_at': menu_item.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_image_url(self, image_field):
        """Get image URL"""
        if image_field:
            try:
                # If it's already a string URL (Cloudinary), return it directly
                if isinstance(image_field, str):
                    if 'cloudinary.com' in image_field:
                        return image_field.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                    return image_field
                # If it's a Django ImageField/FileField, get the URL
                elif hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                    else:
                        return f"{settings.MEDIA_URL}{url}"
                # Handle case where image_field might be a field that has a name attribute (Cloudinary URL stored as string)
                elif hasattr(image_field, 'name') and isinstance(image_field.name, str):
                    if 'cloudinary.com' in image_field.name:
                        return image_field.name.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                    return image_field.name
            except Exception:
                pass
        return None

    def _parse_boolean(self, value):
        """Parse boolean value from string or return as is"""
        if isinstance(value, str):
            return value.lower() == 'true'
        return bool(value)


class VendorMenuDetailView(APIView):
    """
    Retrieve, update, or delete a specific menu item
    GET /api/user/vendors/menu/{pk}/ - Get menu item details
    PUT /api/user/vendors/menu/{pk}/ - Update menu item
    DELETE /api/user/vendors/menu/{pk}/ - Delete menu item
    """
    permission_classes = [IsVerifiedVendor]

    def get(self, request, pk):
        """Get specific menu item"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile
            menu_item = get_object_or_404(MenuItem, id=pk, vendor=vendor)

            return Response({
                'success': True,
                'menu_item': {
                    'id': menu_item.id,
                    'dish_name': menu_item.dish_name,
                    'item_description': menu_item.item_description,
                    'price': float(menu_item.price),
                    'category': menu_item.category.name if menu_item.category else None,
                    'available_now': menu_item.available_now,
                    'quantity': menu_item.quantity,
                    'image': self._get_image_url(menu_item.image) if hasattr(menu_item, 'image') else None,
                    'video': self._get_image_url(menu_item.video) if hasattr(menu_item, 'video') else None,
                    'created_at': menu_item.created_at.isoformat(),
                    'updated_at': menu_item.updated_at.isoformat()
                }
            })

        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        """Update menu item"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile
            menu_item = get_object_or_404(MenuItem, id=pk, vendor=vendor)

            # Update fields
            if 'dish_name' in request.data:
                menu_item.name = request.data['dish_name']
            if 'item_description' in request.data:
                menu_item.description = request.data['item_description']
            if 'price' in request.data:
                menu_item.price = request.data['price']
            if 'category' in request.data:
                # Get or create category
                category_name = request.data['category']
                category, created = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'description': f'{category_name} category'}
                )
                menu_item.category = category
            if 'available_now' in request.data:
                menu_item.is_available = self._parse_boolean(request.data['available_now'])
            if 'quantity' in request.data:
                menu_item.stock_quantity = request.data['quantity']

            # Handle image upload to Cloudinary
            if 'image' in request.FILES:
                from utils.cloudinary_utils import upload_to_cloudinary
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['image'],
                        folder=f"menu_items/{vendor.id}",
                        resource_type='image'
                    )
                    menu_item.image = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload image: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'image' in request.data and isinstance(request.data['image'], str):
                # Handle Cloudinary URL directly
                menu_item.image = request.data['image']

            # Handle video upload to Cloudinary
            if 'video' in request.FILES:
                from utils.cloudinary_utils import upload_to_cloudinary
                try:
                    upload_response = upload_to_cloudinary(
                        request.FILES['video'],
                        folder=f"menu_items/{vendor.id}",
                        resource_type='video'
                    )
                    menu_item.video = upload_response['secure_url']
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Failed to upload video: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif 'video' in request.data and isinstance(request.data['video'], str):
                # Handle Cloudinary URL directly
                menu_item.video = request.data['video']

            menu_item.save()

            return Response({
                'success': True,
                'message': 'Menu item updated successfully',
                'menu_item': {
                    'id': menu_item.id,
                    'dish_name': menu_item.name,
                    'item_description': menu_item.description,
                    'price': float(menu_item.price),
                    'category': menu_item.category.name if menu_item.category else None,
                    'available_now': menu_item.is_available,
                    'quantity': menu_item.stock_quantity,
                    'image': self._get_image_url(menu_item.image) if hasattr(menu_item, 'image') else None,
                    'video': self._get_image_url(menu_item.video) if hasattr(menu_item, 'video') else None,
                    'updated_at': menu_item.updated_at.isoformat()
                }
            })

        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        """Delete menu item"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile
            menu_item = get_object_or_404(MenuItem, id=pk, vendor=vendor)

            menu_item.delete()

            return Response({
                'success': True,
                'message': 'Menu item deleted successfully'
            })

        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_image_url(self, image_field):
        """Get image URL"""
        if image_field:
            try:
                # Handle both URLField (string) and old ImageField objects
                if isinstance(image_field, str):
                    url = image_field
                elif hasattr(image_field, 'url'):
                    url = image_field.url
                else:
                    url = str(image_field)
                
                if 'cloudinary.com' in url:
                    return url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                return url
            except Exception:
                pass
        return None


class VendorMenuCategoriesView(APIView):
    """
    Get menu categories and statistics for a vendor
    GET /api/user/vendors/menu/categories/
    """
    permission_classes = [IsVerifiedVendor]

    def get(self, request):
        """Get menu categories with item counts"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Get categories with counts
            categories = MenuItem.objects.filter(vendor=vendor).values('category').annotate(
                item_count=Count('id'),
                available_count=Count('id', filter={'available_now': True})
            ).order_by('category')

            # Format response
            categories_data = []
            for cat in categories:
                categories_data.append({
                    'category': cat['category'] or 'Uncategorized',
                    'total_items': cat['item_count'],
                    'available_items': cat['available_count']
                })

            return Response({
                'success': True,
                'categories': categories_data,
                'total_categories': len(categories_data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorMenuStatsView(APIView):
    """
    Get menu statistics for a vendor
    GET /api/user/vendors/menu/stats/
    """
    permission_classes = [IsVerifiedVendor]

    def get(self, request):
        """Get menu statistics"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Get basic stats
            total_items = MenuItem.objects.filter(vendor=vendor).count()
            available_items = MenuItem.objects.filter(vendor=vendor, available_now=True).count()
            categories_count = MenuItem.objects.filter(vendor=vendor).values('category').distinct().count()

            # Price statistics
            price_stats = MenuItem.objects.filter(vendor=vendor).aggregate(
                avg_price=Avg('price'),
                min_price=Avg('price'),  # Using Avg as placeholder, should be Min/Max
                max_price=Avg('price')
            )

            # Get actual min/max prices
            prices = MenuItem.objects.filter(vendor=vendor).values_list('price', flat=True)
            if prices:
                min_price = min(prices)
                max_price = max(prices)
            else:
                min_price = max_price = 0

            return Response({
                'success': True,
                'stats': {
                    'total_menu_items': total_items,
                    'available_menu_items': available_items,
                    'unavailable_menu_items': total_items - available_items,
                    'total_categories': categories_count,
                    'price_range': {
                        'min': float(min_price),
                        'max': float(max_price),
                        'currency': 'NGN'
                    },
                    'availability_percentage': (available_items / total_items * 100) if total_items > 0 else 0
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorMenuBulkUpdateView(APIView):
    """
    Bulk update menu items
    PATCH /api/user/vendors/menu/bulk/
    """
    permission_classes = [IsVerifiedVendor]

    def patch(self, request):
        """Bulk update menu items"""
        try:
            if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile:
                return Response({
                    'success': False,
                    'error': 'Vendor profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

            vendor = request.user.vendor_profile

            # Get item IDs and update data
            item_ids = request.data.get('item_ids', [])
            update_data = request.data.get('update_data', {})

            if not item_ids:
                return Response({
                    'success': False,
                    'error': 'item_ids is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not update_data:
                return Response({
                    'success': False,
                    'error': 'update_data is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate item_ids belong to vendor
            menu_items = MenuItem.objects.filter(id__in=item_ids, vendor=vendor)
            if len(menu_items) != len(item_ids):
                return Response({
                    'success': False,
                    'error': 'Some menu items not found or do not belong to this vendor'
                }, status=status.HTTP_404_NOT_FOUND)

            # Update items
            updated_count = menu_items.update(**update_data)

            return Response({
                'success': True,
                'message': f'Successfully updated {updated_count} menu items',
                'updated_count': updated_count
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicVendorMenuItemsView(APIView):
    """
    Public view for vendor menu items (consumer-facing)
    GET /api/user/vendors/{vendor_id}/menu-items/
    """
    permission_classes = [AllowAny]

    def get(self, request, vendor_id):
        """Get public menu items for a vendor"""
        try:
            vendor = get_object_or_404(VendorProfile, id=vendor_id, verification_status='approved')

            # Get available menu items
            menu_items = MenuItem.objects.filter(
                vendor=vendor,
                available_now=True
            ).order_by('category', 'dish_name')

            # Format response
            items_data = []
            for item in menu_items:
                items_data.append({
                    'id': item.id,
                    'dish_name': item.dish_name,
                    'item_description': item.item_description,
                    'price': float(item.price),
                    'category': item.category,
                    'image': self._get_image_url(item.image),
                    'video': self._get_image_url(item.video)
                })

            return Response({
                'success': True,
                'vendor_id': vendor_id,
                'vendor_name': vendor.business_name,
                'menu_items': items_data,
                'total_items': len(items_data)
            })

        except VendorProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Vendor not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_image_url(self, image_field):
        """Get image URL"""
        if image_field:
            try:
                # Handle both URLField (string) and old ImageField objects
                if isinstance(image_field, str):
                    url = image_field
                elif hasattr(image_field, 'url'):
                    url = image_field.url
                else:
                    url = str(image_field)
                
                if 'cloudinary.com' in url:
                    return url.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                return url
            except Exception:
                pass
        return None
