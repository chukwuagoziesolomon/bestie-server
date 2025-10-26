"""
Vendor search API with advanced filtering capabilities
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Q, Avg, Count, F, Case, When, DecimalField
from django.utils import timezone
from typing import List, Dict, Optional

from bestyy.core_features.user.models import (
    User, VendorProfile,
    Order, Favorite
)


class VendorSearchView(APIView):
    """
    Advanced vendor search with multiple filters:
    - Text search (business name, category, description)
    - Location filtering (state, city, area)
    - Food type/cuisine filtering
    - Price range filtering
    - Rating filtering
    - Delivery options
    - Distance filtering (if coordinates provided)
    
    GET /api/user/search/vendors/
    """
    permission_classes = [AllowAny]  # Public search functionality
    
    def get(self, request):
        """Search vendors with advanced filtering"""
        try:
            # Extract search parameters
            query = request.query_params.get('q', '').strip()
            state = request.query_params.get('state', '').strip()
            city = request.query_params.get('city', '').strip()
            area = request.query_params.get('area', '').strip()
            cuisine = request.query_params.get('cuisine', '').strip()
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            min_rating = request.query_params.get('min_rating')
            delivery_only = request.query_params.get('delivery_only', 'false').lower() == 'true'
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 5))
            
            # Get user for personalized results
            user = request.user if request.user.is_authenticated else None
            
            # Build search results
            search_results = self._search_vendors(
                query=query,
                state=state,
                city=city,
                area=area,
                cuisine=cuisine,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                delivery_only=delivery_only,
                user=user,
                page=page,
                page_size=page_size
            )
            
            return Response({
                'success': True,
                'count': search_results['count'],
                'total_count': search_results['total_count'],
                'page': page,
                'page_size': page_size,
                'total_pages': search_results['total_pages'],
                'has_next': search_results['has_next'],
                'has_previous': search_results['has_previous'],
                'search_params': {
                    'query': query,
                    'state': state,
                    'city': city,
                    'area': area,
                    'cuisine': cuisine,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_rating': min_rating,
                    'delivery_only': delivery_only
                },
                'vendors': search_results['vendors']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _search_vendors(
        self,
        query: str = '',
        state: str = '',
        city: str = '',
        area: str = '',
        cuisine: str = '',
        min_price: str = None,
        max_price: str = None,
        min_rating: str = None,
        delivery_only: bool = False,
        user: Optional[User] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """Perform vendor search with filters"""

        # Start with base queryset - only include vendors with fresh menus
        from django.utils import timezone
        from datetime import timedelta

        two_days_ago = timezone.now() - timedelta(days=2)

        queryset = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        ).select_related('user', 'subscription_plan').annotate(
            # No rating system implemented yet
            avg_rating=Avg('id'),  # Placeholder
            total_reviews=Count('id'),  # Placeholder
            menu_item_count=Count('menu_items')
        )
        
        # Apply text search
        if query:
            queryset = queryset.filter(
                Q(business_name__icontains=query) |
                Q(business_category__icontains=query) |
                Q(business_description__icontains=query) |
                Q(business_address__icontains=query) |
                Q(service_areas__icontains=query)
            )
        
        # Apply location filters
        location_filters = Q()
        if state:
            location_filters |= Q(business_address__icontains=state) | Q(service_areas__icontains=state)
        if city:
            location_filters |= Q(business_address__icontains=city) | Q(service_areas__icontains=city)
        if area:
            location_filters |= Q(business_address__icontains=area) | Q(service_areas__icontains=area)
        
        if location_filters:
            queryset = queryset.filter(location_filters)
        
        # Apply cuisine/food type filter
        if cuisine:
            queryset = queryset.filter(
                Q(business_category__icontains=cuisine) |
                Q(business_description__icontains=cuisine)
            )
        
        # Apply price range filter (based on menu items)
        if min_price or max_price:
            price_filter = Q()
            if min_price:
                try:
                    min_price_float = float(min_price)
                    price_filter |= Q(menu_items__price__gte=min_price_float)
                except ValueError:
                    pass
            if max_price:
                try:
                    max_price_float = float(max_price)
                    price_filter |= Q(menu_items__price__lte=max_price_float)
                except ValueError:
                    pass
            
            if price_filter:
                queryset = queryset.filter(price_filter).distinct()
        
        # Apply rating filter
        if min_rating:
            try:
                min_rating_float = float(min_rating)
                queryset = queryset.filter(ratings__rating__gte=min_rating_float).distinct()
            except ValueError:
                pass
        
        # Apply delivery filter
        if delivery_only:
            queryset = queryset.filter(offers_delivery=True)
        
        # Calculate search relevance score with rating penalties
        queryset = queryset.annotate(
            search_score=self._calculate_search_score(query, user)
        )
        
        # Order by search relevance, then by rating, then by creation date
        queryset = queryset.order_by('-search_score', '-avg_rating', '-created_at')
        
        # Get total count
        total_count = queryset.count()
        
        # Apply pagination
        total_pages = (total_count + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        vendors = queryset[start_index:end_index]
        
        # Format vendor data
        vendor_data = []
        for vendor in vendors:
            vendor_data.append(self._create_vendor_search_dict(vendor, user))
        
        return {
            'count': len(vendor_data),
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1,
            'vendors': vendor_data
        }
    
    def _calculate_search_score(self, query: str, user: Optional[User]) -> DecimalField:
        """Calculate search relevance score with rating penalties"""
        # Rating score with boost for new vendors and penalties for low ratings
        score = Case(
            When(Q(avg_rating__isnull=True) | Q(total_reviews=0), then=5),  # Boost for new/unrated vendors
            When(avg_rating__gte=4.0, then=F('avg_rating') * 15),  # Excellent ratings
            When(avg_rating__gte=3.0, then=F('avg_rating') * 10),  # Good ratings
            When(avg_rating__gte=2.0, then=F('avg_rating') * 5),   # Average ratings
            default=F('avg_rating') * -10,  # Penalty for poor ratings (< 2.0)
            output_field=DecimalField()
        )
        
        # No popularity model - skip popularity score
        
        # Boost for featured vendors (pro subscription)
        score += Case(
            When(subscription_plan__plan_type='pro', then=50),
            default=0,
            output_field=DecimalField()
        )
        
        # Boost for vendors with more menu items
        score = score + Case(
            When(menu_item_count__gt=0, then=F('menu_item_count') * 0.5),
            default=0,
            output_field=DecimalField()
        )
        
        # Boost for delivery options
        score = score + Case(
            When(offers_delivery=True, then=10),
            default=0,
            output_field=DecimalField()
        )
        
        # User-specific boosts
        if user:
            # Boost for vendors user has ordered from before
            score = score + Case(
                When(orders__user=user, then=20),
                default=0,
                output_field=DecimalField()
            )
            
            # Boost for vendors in user's favorites
            score = score + Case(
                When(favorites__user=user, then=30),
                default=0,
                output_field=DecimalField()
            )
        
        return score
    
    def _create_vendor_search_dict(self, vendor: VendorProfile, user: Optional[User]) -> Dict:
        """Create vendor dictionary for search results"""
        # Compute lightweight popularity metrics without separate model
        recent_orders = Order.objects.filter(
            vendor=vendor
        ).count()
        
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
        menu_items = vendor.menu_items.all()
        price_range = None
        if menu_items.exists():
            prices = [item.price for item in menu_items if item.price]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                price_range = {
                    'min': float(min_price),
                    'max': float(max_price),
                    'currency': 'NGN'  # Nigerian Naira
                }
        
        return {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'business_category': vendor.business_category,
            'business_description': vendor.business_description,
            'business_address': vendor.business_address,
            'logo': logo_url,
            'rating': float(vendor.avg_rating or 0),
            'total_reviews': vendor.total_reviews or 0,
            'is_featured': vendor.subscription_plan.plan_type == 'pro' if vendor.subscription_plan else False,
            'offers_delivery': vendor.offers_delivery,
            'delivery_time': self._estimate_delivery_time(vendor),
            'service_areas': vendor.service_areas.split(',') if vendor.service_areas else [],
            'opening_hours': vendor.opening_hours.strftime('%H:%M') if vendor.opening_hours else None,
            'closing_hours': vendor.closing_hours.strftime('%H:%M') if vendor.closing_hours else None,
            'is_open': self._is_vendor_open(vendor),
            'price_range': price_range,
            'menu_item_count': vendor.menu_item_count or 0,
            'search_score': float(vendor.search_score or 0),
            'distance': None,  # Can be calculated on frontend with user coordinates
        }
    
    def _estimate_delivery_time(self, vendor: VendorProfile) -> str:
        """Estimate delivery time based on vendor data"""
        base_time = 30  # Base 30 minutes
        
        # No popularity model - use base time
        
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


class SearchFiltersView(APIView):
    """
    Get available search filters and options
    
    GET /api/user/search/filters/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get available search filters"""
        try:
            # Get unique states from vendor addresses
            states = VendorProfile.objects.filter(
                verification_status='approved',
                business_address__isnull=False
            ).exclude(business_address='').values_list('business_address', flat=True)
            
            # Extract states from addresses (simple extraction)
            unique_states = set()
            for address in states:
                # Simple state extraction - you might want to improve this
                parts = address.split(',')
                if len(parts) > 1:
                    state = parts[-1].strip()
                    if state:
                        unique_states.add(state)
            
            # Get unique cities
            cities = VendorProfile.objects.filter(
                verification_status='approved',
                business_address__isnull=False
            ).exclude(business_address='').values_list('business_address', flat=True)
            
            unique_cities = set()
            for address in cities:
                parts = address.split(',')
                if len(parts) > 0:
                    city = parts[0].strip()
                    if city:
                        unique_cities.add(city)
            
            # Get unique cuisine types
            cuisines = VendorProfile.objects.filter(
                verification_status='approved'
            ).exclude(business_category='').values_list('business_category', flat=True)
            
            unique_cuisines = set()
            for category in cuisines:
                if category:
                    # Split by common separators
                    categories = category.replace(',', '|').replace(';', '|').split('|')
                    for cat in categories:
                        cat = cat.strip()
                        if cat:
                            unique_cuisines.add(cat)
            
            # Get price ranges from menu items
            from bestyy.core_features.user.models import MenuItem
            prices = MenuItem.objects.filter(
                vendor__verification_status='approved'
            ).values_list('price', flat=True).order_by('price')
            
            price_ranges = []
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                
                # Create price ranges
                price_ranges = [
                    {'label': 'Under ₦500', 'min': 0, 'max': 500},
                    {'label': '₦500 - ₦1,000', 'min': 500, 'max': 1000},
                    {'label': '₦1,000 - ₦2,000', 'min': 1000, 'max': 2000},
                    {'label': '₦2,000 - ₦5,000', 'min': 2000, 'max': 5000},
                    {'label': 'Above ₦5,000', 'min': 5000, 'max': None},
                ]
            
            return Response({
                'success': True,
                'filters': {
                    'states': sorted(list(unique_states)),
                    'cities': sorted(list(unique_cities)),
                    'cuisines': sorted(list(unique_cuisines)),
                    'price_ranges': price_ranges,
                    'rating_options': [
                        {'label': '4+ Stars', 'value': 4},
                        {'label': '3+ Stars', 'value': 3},
                        {'label': '2+ Stars', 'value': 2},
                        {'label': '1+ Stars', 'value': 1},
                    ],
                    'delivery_options': [
                        {'label': 'Delivery Available', 'value': True},
                        {'label': 'Pickup Only', 'value': False},
                    ]
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

