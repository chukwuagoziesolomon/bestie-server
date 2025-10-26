"""
Vendor profile API for displaying vendor details and menu items
This is used when users click on a vendor to view their profile and order
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Q, Avg, Count, F, Case, When, DecimalField
from django.utils import timezone
from django.shortcuts import get_object_or_404
from typing import List, Dict, Optional

from bestyy.core_features.user.models import (
    User, VendorProfile, UserPreference, 
    Order, Favorite, MenuItem
)


class VendorProfileDetailView(APIView):
    """
    Get complete vendor profile with menu items for the vendor profile page
    This is used when users click on a vendor to view their details and order
    
    GET /api/user/vendors/{vendor_id}/profile/
    """
    permission_classes = [AllowAny]  # Public access for vendor profiles
    
    def get(self, request, vendor_id):
        """Get vendor profile with all details and menu items"""
        try:
            # Get vendor
            vendor = get_object_or_404(VendorProfile, id=vendor_id, verification_status='approved')
            
            # Get user for personalized data
            user = request.user if request.user.is_authenticated else None
            
            # Get vendor details
            vendor_details = self._get_vendor_details(vendor, user)
            
            # Get menu items organized by categories
            menu_categories = self._get_menu_categories(vendor)
            
            # Get vendor reviews
            reviews = self._get_vendor_reviews(vendor)
            
            # Get vendor statistics
            stats = self._get_vendor_stats(vendor)
            
            return Response({
                'success': True,
                'vendor': vendor_details,
                'menu_categories': menu_categories,
                'reviews': reviews,
                'stats': stats
            }, status=status.HTTP_200_OK)
            
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
    
    def _get_vendor_details(self, vendor: VendorProfile, user: Optional[User]) -> Dict:
        """Get vendor basic details"""
        # Popularity metrics can be derived from recent orders without a separate model
        
        # Handle Cloudinary URL generation for images
        logo_url = self._get_optimized_image_url(vendor.logo)
        banner_url = self._get_optimized_image_url(getattr(vendor, 'banner_image', None))
        
        # Check if user has favorited this vendor
        is_favorited = False
        if user:
            is_favorited = Favorite.objects.filter(
                user=user, 
                vendor=vendor, 
                favorite_type='venue'
            ).exists()
        
        # Check if vendor is open
        is_open = self._is_vendor_open(vendor)
        
        # Get price range from menu items
        price_range = self._get_vendor_price_range(vendor)
        
        return {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'business_category': vendor.business_category,
            'business_description': vendor.business_description,
            'business_address': vendor.business_address,
            'logo': logo_url,
            'banner_image': banner_url,
            'rating': self._get_vendor_avg_rating(vendor),
            'total_reviews': 0,
            'is_featured': bool(getattr(vendor, 'is_featured', False)),
            'offers_delivery': vendor.offers_delivery,
            'delivery_time': self._estimate_delivery_time(vendor),
            'service_areas': vendor.service_areas.split(',') if vendor.service_areas else [],
            'opening_hours': vendor.opening_hours.strftime('%H:%M') if vendor.opening_hours else None,
            'closing_hours': vendor.closing_hours.strftime('%H:%M') if vendor.closing_hours else None,
            'is_open': is_open,
            'price_range': price_range,
            'contact_phone': getattr(vendor, 'contact_phone', None),
            'contact_email': getattr(vendor, 'contact_email', None),
            'website': getattr(vendor, 'website', None),
            'social_media': {
                'facebook': getattr(vendor, 'facebook_url', None),
                'instagram': getattr(vendor, 'instagram_url', None),
                'twitter': getattr(vendor, 'twitter_url', None),
            },
            'is_favorited': is_favorited,
            'created_at': vendor.created_at.isoformat(),
            'verification_date': vendor.verification_date.isoformat() if vendor.verification_date else None,
        }
    
    def _get_menu_categories(self, vendor: VendorProfile) -> List[Dict]:
        """Get menu items organized by categories"""
        # Get all menu items for this vendor
        menu_items = MenuItem.objects.filter(
            vendor=vendor,
            available_now=True
        ).order_by('category', 'dish_name')
        
        # Group by categories
        categories = {}
        for item in menu_items:
            category = item.category or 'Other'
            if category not in categories:
                categories[category] = []
            
            # Handle Cloudinary URL for item images
            item_image = self._get_optimized_image_url(item.image)
            
            categories[category].append({
                'id': item.id,
                'name': item.dish_name,
                'description': item.item_description,
                'price': float(item.price),
                'currency': 'NGN',
                'image': item_image,
                'is_available': item.available_now,
                'preparation_time': None,  # Field not available in current model
                'ingredients': [],  # Field not available in current model
                'allergens': [],  # Field not available in current model
                'is_vegetarian': False,  # Field not available in current model
                'is_spicy': False,  # Field not available in current model
                'calories': None,  # Field not available in current model
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            })
        
        # Convert to list format
        category_list = []
        for category_name, items in categories.items():
            category_list.append({
                'category': category_name,
                'item_count': len(items),
                'items': items
            })
        
        return category_list
    
    def _get_vendor_reviews(self, vendor: VendorProfile, limit: int = 10) -> Dict:
        """Get recent vendor reviews"""
        return {
            'recent_reviews': [],
            'total_reviews': 0,
            'average_rating': float(getattr(vendor, 'rating', 0) or 0),
            'rating_breakdown': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        }
    
    def _get_rating_breakdown(self, vendor: VendorProfile) -> Dict:
        """Get rating breakdown (5 stars, 4 stars, etc.)"""
        return {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    
    def _get_vendor_stats(self, vendor: VendorProfile) -> Dict:
        """Get vendor statistics"""
        # Get recent orders count
        recent_orders = Order.objects.filter(
            vendor=vendor,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        return {
            'recent_orders_last_30_days': recent_orders,
            'popularity_score': recent_orders,
            'member_since': vendor.created_at.date().isoformat(),
        }
    
    def _calculate_years_in_business(self, vendor: VendorProfile) -> int:
        """Calculate years in business"""
        if vendor.created_at:
            delta = timezone.now() - vendor.created_at
            return max(0, delta.days // 365)
        return 0
    
    def _get_optimized_image_url(self, image_field) -> Optional[str]:
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        # Optimize for web display
                        return url.replace('/upload/', '/upload/w_400,h_400,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None
    
    def _get_vendor_price_range(self, vendor: VendorProfile) -> Optional[Dict]:
        """Get vendor price range from menu items"""
        menu_items = MenuItem.objects.filter(
            vendor=vendor,
            available_now=True,
            price__isnull=False
        )
        
        if menu_items.exists():
            prices = [item.price for item in menu_items]
            return {
                'min': float(min(prices)),
                'max': float(max(prices)),
                'currency': 'NGN'
            }
        return None
    
    def _estimate_delivery_time(self, vendor: VendorProfile) -> str:
        """Estimate delivery time based on vendor data"""
        base_time = 30  # Base 30 minutes
        
        if hasattr(vendor, 'popularity'):
            if vendor.popularity.orders_last_7_days > 50:
                base_time += 15
            elif vendor.popularity.orders_last_7_days > 20:
                base_time += 10
        
        return f"{base_time}-{base_time + 10} min"
    
    def _is_vendor_open(self, vendor: VendorProfile) -> bool:
        """Check if vendor is currently open"""
        if not vendor.opening_hours or not vendor.closing_hours:
            return True
        
        from datetime import datetime
        current_time = datetime.now().time()
        
        if vendor.closing_hours <= vendor.opening_hours:
            return current_time >= vendor.opening_hours or current_time <= vendor.closing_hours
        else:
            return vendor.opening_hours <= current_time <= vendor.closing_hours
    
    def _get_vendor_avg_rating(self, vendor: VendorProfile) -> float:
        """Calculate average rating for vendor"""
        from django.db.models import Avg
        avg_rating = vendor.ratings.aggregate(avg=Avg('rating'))['avg']
        return float(avg_rating) if avg_rating else 0.0


class VendorMenuItemsView(APIView):
    """
    Get vendor menu items with filtering and search
    
    GET /api/user/vendors/{vendor_id}/menu/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, vendor_id):
        """Get vendor menu items with optional filtering"""
        try:
            vendor = get_object_or_404(VendorProfile, id=vendor_id, verification_status='approved')
            
            # Get query parameters
            category = request.query_params.get('category')
            search = request.query_params.get('search', '').strip()
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            vegetarian_only = request.query_params.get('vegetarian_only', 'false').lower() == 'true'
            
            # Build queryset
            queryset = MenuItem.objects.filter(
                vendor=vendor,
                available_now=True
            )
            
            # Apply filters
            if category:
                queryset = queryset.filter(category__icontains=category)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(ingredients__icontains=search)
                )
            
            if min_price:
                try:
                    queryset = queryset.filter(price__gte=float(min_price))
                except ValueError:
                    pass
            
            if max_price:
                try:
                    queryset = queryset.filter(price__lte=float(max_price))
                except ValueError:
                    pass
            
            if vegetarian_only:
                queryset = queryset.filter(is_vegetarian=True)
            
            # Order by category and name
            menu_items = queryset.order_by('category', 'name')
            
            # Format response
            items_data = []
            for item in menu_items:
                items_data.append({
                    'id': item.id,
                    'name': item.dish_name,
                    'description': item.item_description,
                    'price': float(item.price),
                    'currency': 'NGN',
                    'image': self._get_optimized_image_url(item.image),
                    'category': item.category,
                    'preparation_time': None,  # Field not available in current model
                    'ingredients': [],  # Field not available in current model
                    'allergens': [],  # Field not available in current model
                    'is_vegetarian': False,  # Field not available in current model
                    'is_spicy': False,  # Field not available in current model
                    'calories': None,  # Field not available in current model
                })
            
            return Response({
                'success': True,
                'count': len(items_data),
                'vendor_id': vendor_id,
                'vendor_name': vendor.business_name,
                'filters_applied': {
                    'category': category,
                    'search': search,
                    'min_price': min_price,
                    'max_price': max_price,
                    'vegetarian_only': vegetarian_only,
                },
                'menu_items': items_data
            }, status=status.HTTP_200_OK)
            
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
    
    def _get_optimized_image_url(self, image_field) -> Optional[str]:
        """Get optimized Cloudinary URL for images"""
        if image_field:
            try:
                if hasattr(image_field, 'url'):
                    url = image_field.url
                    if 'cloudinary.com' in url:
                        return url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                    return url
                else:
                    return str(image_field)
            except Exception:
                return None
        return None
