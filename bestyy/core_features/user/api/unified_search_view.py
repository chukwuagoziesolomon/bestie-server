"""
Unified search endpoint that combines vendor and courier search functionality.
This provides a single endpoint for searching both vendors and couriers with unified filtering.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Q, Avg, Count, F, Case, When, DecimalField
from django.utils import timezone
from typing import List, Dict, Optional
import logging

from bestyy.core_features.user.models import (
    User, VendorProfile, CourierProfile,
    Favorite
)
from bestyy.restaurant_features.order.models import Order

logger = logging.getLogger(__name__)


class UnifiedSearchView(APIView):
    """
    Unified search endpoint for vendors and couriers.

    GET /api/user/search/
    Query Parameters:
    - type: 'vendor', 'courier', or 'all' (default: 'all')
    - q: General text search (name, category, description, address)
    - category: Business category filter (for vendors)
    - cuisine: Cuisine type filter (for vendors)
    - state: State filter
    - city: City filter
    - area: Area filter
    - min_price: Minimum price filter (vendors only)
    - max_price: Maximum price filter (vendors only)
    - min_rating: Minimum rating filter
    - delivery_only: Show only delivery-enabled vendors (true/false)
    - verification_status: Filter by verification status (pending, verified, rejected)
    - is_active: Filter by active status (true/false)
    - page: Page number (default: 1)
    - page_size: Results per page (default: 10)
    """
    permission_classes = [AllowAny]  # Public search functionality

    def get(self, request):
        """Unified search for vendors and couriers"""
        try:
            # Extract search parameters
            search_type = request.query_params.get('type', 'all').lower()
            query = request.query_params.get('q', '').strip()
            category = request.query_params.get('category', '').strip()
            cuisine = request.query_params.get('cuisine', '').strip()
            state = request.query_params.get('state', '').strip()
            city = request.query_params.get('city', '').strip()
            area = request.query_params.get('area', '').strip()
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            min_rating = request.query_params.get('min_rating')
            delivery_only = request.query_params.get('delivery_only', 'false').lower() == 'true'
            verification_status = request.query_params.get('verification_status', '').strip()
            is_active = request.query_params.get('is_active')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))

            # Get user for personalized results
            user = request.user if request.user.is_authenticated else None

            # Perform unified search
            search_results = self._unified_search(
                search_type=search_type,
                query=query,
                category=category,
                cuisine=cuisine,
                state=state,
                city=city,
                area=area,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                delivery_only=delivery_only,
                verification_status=verification_status,
                is_active=is_active,
                user=user,
                page=page,
                page_size=page_size
            )

            return Response({
                'success': True,
                'search_type': search_type,
                'total_results': search_results['total_results'],
                'page': page,
                'page_size': page_size,
                'has_next': search_results['has_next'],
                'has_previous': search_results['has_previous'],
                'search_params': {
                    'query': query,
                    'category': category,
                    'cuisine': cuisine,
                    'state': state,
                    'city': city,
                    'area': area,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_rating': min_rating,
                    'delivery_only': delivery_only,
                    'verification_status': verification_status,
                    'is_active': is_active
                },
                'results': search_results['results']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unified search error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _unified_search(self, search_type, **kwargs):
        """Perform unified search across vendors and couriers"""
        results = {
            'vendors': [],
            'couriers': []
        }
        total_results = 0

        # Search vendors if requested
        if search_type in ['all', 'vendor']:
            vendor_results = self._search_vendors(**kwargs)
            results['vendors'] = vendor_results['vendors']
            total_results += vendor_results['count']

        # Search couriers if requested
        if search_type in ['all', 'courier']:
            courier_results = self._search_couriers(**kwargs)
            results['couriers'] = courier_results['couriers']
            total_results += courier_results['count']

        # Calculate pagination info
        page = kwargs.get('page', 1)
        page_size = kwargs.get('page_size', 10)

        # For unified results, we need to handle pagination across both types
        all_results = results['vendors'] + results['couriers']
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        paginated_results = all_results[start_index:end_index]

        return {
            'results': paginated_results,
            'total_results': total_results,
            'has_next': end_index < total_results,
            'has_previous': page > 1
        }

    def _search_vendors(self, query='', category='', cuisine='', state='', city='', area='',
                       min_price=None, max_price=None, min_rating=None, delivery_only=False,
                       verification_status='', is_active=None, user=None, page=1, page_size=10, **kwargs):
        """Search vendors with filters"""
        # Start with base queryset
        queryset = VendorProfile.objects.filter(
            is_suspended=False
        ).select_related('user').annotate(
            avg_rating=Avg('id'),  # Placeholder
            total_reviews=Count('id'),  # Placeholder
            menu_item_count=Count('menu_items')
        )

        # Apply filters
        queryset = self._apply_vendor_filters(
            queryset, query, category, cuisine, state, city, area,
            min_price, max_price, min_rating, delivery_only, verification_status, is_active
        )

        # Calculate search score
        queryset = queryset.annotate(
            search_score=self._calculate_vendor_search_score(query, user)
        )

        # Order by search relevance
        queryset = queryset.order_by('-search_score', '-avg_rating', '-created_at')

        # Get total count
        total_count = queryset.count()

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        vendors = queryset[start_index:end_index]

        # Format results
        vendor_data = []
        for vendor in vendors:
            vendor_data.append(self._create_vendor_search_dict(vendor, user))

        return {
            'count': len(vendor_data),
            'total_count': total_count,
            'vendors': vendor_data
        }

    def _search_couriers(self, query='', state='', city='', area='', verification_status='',
                        is_active=None, user=None, page=1, page_size=10, **kwargs):
        """Search couriers with filters"""
        # Start with base queryset
        queryset = CourierProfile.objects.select_related('user')

        # Annotate with delivery stats
        queryset = queryset.annotate(
            completed_deliveries=Count(
                Case(
                    When(order__status='delivered', then=1),
                    output_field=Count('id'),
                )
            ),
            rating=Value(0.0, output_field=DecimalField())  # Placeholder
        )

        # Apply filters
        queryset = self._apply_courier_filters(
            queryset, query, state, city, area, verification_status, is_active
        )

        # Calculate search score
        queryset = queryset.annotate(
            search_score=self._calculate_courier_search_score(query, user)
        )

        # Order by search relevance
        queryset = queryset.order_by('-search_score', '-completed_deliveries', '-user__date_joined')

        # Get total count
        total_count = queryset.count()

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        couriers = queryset[start_index:end_index]

        # Format results
        courier_data = []
        for courier in couriers:
            courier_data.append(self._create_courier_search_dict(courier, user))

        return {
            'count': len(courier_data),
            'total_count': total_count,
            'couriers': courier_data
        }

    def _apply_vendor_filters(self, queryset, query, category, cuisine, state, city, area,
                            min_price, max_price, min_rating, delivery_only, verification_status, is_active):
        """Apply filters to vendor queryset"""
        # Text search
        if query:
            queryset = queryset.filter(
                Q(business_name__icontains=query) |
                Q(business_category__icontains=query) |
                Q(business_description__icontains=query) |
                Q(business_address__icontains=query) |
                Q(service_areas__icontains=query)
            )

        # Category and cuisine filters
        if category:
            queryset = queryset.filter(business_category__icontains=category)
        if cuisine:
            queryset = queryset.filter(
                Q(business_category__icontains=cuisine) |
                Q(business_description__icontains=cuisine)
            )

        # Location filters
        location_filters = Q()
        if state:
            location_filters |= Q(business_address__icontains=state) | Q(service_areas__icontains=state)
        if city:
            location_filters |= Q(business_address__icontains=city) | Q(service_areas__icontains=city)
        if area:
            location_filters |= Q(business_address__icontains=area) | Q(service_areas__icontains=area)

        if location_filters:
            queryset = queryset.filter(location_filters)

        # Price filters
        if min_price or max_price:
            price_filter = Q()
            if min_price:
                try:
                    min_price_float = float(min_price)
                    price_filter |= Q(menuitem__price__gte=min_price_float)
                except ValueError:
                    pass
            if max_price:
                try:
                    max_price_float = float(max_price)
                    price_filter |= Q(menuitem__price__lte=max_price_float)
                except ValueError:
                    pass

            if price_filter:
                queryset = queryset.filter(price_filter).distinct()

        # Rating filter
        if min_rating:
            try:
                min_rating_float = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating_float)
            except ValueError:
                pass

        # Delivery filter
        if delivery_only:
            queryset = queryset.filter(offers_delivery=True)

        # Status filters
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)
        if is_active is not None:
            queryset = queryset.filter(user__is_active=is_active)

        return queryset

    def _apply_courier_filters(self, queryset, query, state, city, area, verification_status, is_active):
        """Apply filters to courier queryset"""
        # Text search
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__email__icontains=query) |
                Q(phone__icontains=query) |
                Q(nin_number__icontains=query)
            )

        # Location filters (if available in courier profile)
        # Note: Courier profiles may not have detailed location info like vendors

        # Status filters
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)
        if is_active is not None:
            queryset = queryset.filter(user__is_active=is_active)

        return queryset

    def _calculate_vendor_search_score(self, query: str, user: Optional[User]) -> DecimalField:
        """Calculate search relevance score for vendors"""
        score = Case(
            When(Q(avg_rating__isnull=True) | Q(total_reviews=0), then=5),
            When(avg_rating__gte=4.0, then=F('avg_rating') * 15),
            When(avg_rating__gte=3.0, then=F('avg_rating') * 10),
            When(avg_rating__gte=2.0, then=F('avg_rating') * 5),
            default=F('avg_rating') * -10,
            output_field=DecimalField()
        )

        # Featured vendor boost
        score += Case(
            When(is_featured=True, then=50),
            default=0,
            output_field=DecimalField()
        )

        # Menu items boost
        score = score + Case(
            When(menu_item_count__gt=0, then=F('menu_item_count') * 0.5),
            default=0,
            output_field=DecimalField()
        )

        # Delivery boost
        score = score + Case(
            When(offers_delivery=True, then=10),
            default=0,
            output_field=DecimalField()
        )

        # User-specific boosts
        if user:
            score = score + Case(
                When(orders__user=user, then=20),
                default=0,
                output_field=DecimalField()
            )

            score = score + Case(
                When(favorites__user=user, then=30),
                default=0,
                output_field=DecimalField()
            )

        return score

    def _calculate_courier_search_score(self, query: str, user: Optional[User]) -> DecimalField:
        """Calculate search relevance score for couriers"""
        score = Value(0, output_field=DecimalField())

        # Completed deliveries boost
        score = score + Case(
            When(completed_deliveries__gt=0, then=F('completed_deliveries') * 2),
            default=0,
            output_field=DecimalField()
        )

        # Rating boost (placeholder)
        score = score + Case(
            When(rating__gt=0, then=F('rating') * 10),
            default=5,  # Base score for new couriers
            output_field=DecimalField()
        )

        # Verification status boost
        score = score + Case(
            When(verification_status='verified', then=20),
            When(verification_status='pending', then=5),
            default=0,
            output_field=DecimalField()
        )

        return score

    def _create_vendor_search_dict(self, vendor: VendorProfile, user: Optional[User]) -> Dict:
        """Create vendor dictionary for search results"""
        # Handle Cloudinary URL generation
        logo_url = None
        if vendor.logo:
            try:
                if hasattr(vendor.logo, 'url'):
                    logo_url = vendor.logo.url
                    if 'cloudinary.com' in logo_url:
                        logo_url = logo_url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                else:
                    logo_url = str(vendor.logo)
            except Exception:
                logo_url = None

        # Get price range from menu items
        menu_items = vendor.menuitem_set.all()
        price_range = None
        food_images = []
        if menu_items.exists():
            prices = [item.price for item in menu_items if item.price]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                price_range = {
                    'min': float(min_price),
                    'max': float(max_price),
                    'currency': 'NGN'
                }

            # Get food images from menu items
            for item in menu_items[:5]:  # Get first 5 menu items
                if item.image:
                    try:
                        if hasattr(item.image, 'url'):
                            image_url = item.image.url
                            if 'cloudinary.com' in image_url:
                                # Transform for web optimization
                                image_url = image_url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                            food_images.append({
                                'id': item.id,
                                'dish_name': item.dish_name,
                                'image': image_url,
                                'thumbnail': self._get_cloudinary_thumbnail(image_url) if image_url else None,
                                'price': float(item.price)
                            })
                    except Exception:
                        continue

        return {
            'type': 'vendor',
            'id': vendor.id,
            'business_name': vendor.business_name,
            'business_category': vendor.business_category,
            'business_description': vendor.business_description,
            'business_address': vendor.business_address,
            'logo': logo_url,
            'logo_thumbnail': self._get_cloudinary_thumbnail(logo_url) if logo_url else None,
            'food_images': food_images,  # Add food images from menu items
            'rating': float(vendor.avg_rating or 0),
            'total_reviews': vendor.total_reviews or 0,
            'is_featured': vendor.is_featured,
            'offers_delivery': vendor.offers_delivery,
            'delivery_time': self._estimate_delivery_time(vendor),
            'service_areas': vendor.service_areas.split(',') if vendor.service_areas else [],
            'opening_hours': vendor.opening_hours.strftime('%H:%M') if vendor.opening_hours else None,
            'closing_hours': vendor.closing_hours.strftime('%H:%M') if vendor.closing_hours else None,
            'is_open': self._is_vendor_open(vendor),
            'price_range': price_range,
            'menu_item_count': vendor.menu_item_count or 0,
            'search_score': float(vendor.search_score or 0),
            'distance': None
        }

    def _create_courier_search_dict(self, courier: CourierProfile, user: Optional[User]) -> Dict:
        """Create courier dictionary for search results"""
        # Handle profile image URL generation
        profile_image_url = None
        if courier.profile_image:
            try:
                if hasattr(courier.profile_image, 'url'):
                    profile_image_url = courier.profile_image.url
                    if 'cloudinary.com' in profile_image_url:
                        profile_image_url = profile_image_url.replace('/upload/', '/upload/w_150,h_150,c_fill,f_auto,q_auto/')
                else:
                    profile_image_url = str(courier.profile_image)
            except Exception:
                profile_image_url = None

        return {
            'type': 'courier',
            'id': courier.id,
            'name': f"{courier.user.first_name} {courier.user.last_name}".strip(),
            'email': courier.user.email,
            'phone': courier.phone,
            'profile_image': profile_image_url,
            'completed_deliveries': courier.completed_deliveries or 0,
            'rating': float(courier.rating or 0),
            'verification_status': courier.verification_status,
            'is_active': courier.user.is_active,
            'joined_date': courier.user.date_joined.isoformat(),
            'search_score': float(courier.search_score or 0)
        }

    def _estimate_delivery_time(self, vendor: VendorProfile) -> str:
        """Estimate delivery time based on vendor data"""
        base_time = 30  # Base 30 minutes
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