"""
Unified recommendation endpoint that combines all recommendation logic into one endpoint.
This matches the homepage design where there's one main section showing vendors.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db.models import Q, Avg, Count, F, Case, When, DecimalField
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Optional

from bestyy.core_features.user.models import (
    User, VendorProfile,
    Order, Favorite
)
from bestyy.core_features.user.services.popularity_update_service import VendorPopularityUpdateService


class UnifiedVendorRecommendationView(APIView):
    """
    Unified endpoint for vendor recommendations that combines:
    - Featured vendor prioritization
    - Location-based recommendations
    - User preferences and behavior
    - Rating-based sorting
    - Social recommendations
    
    This single endpoint handles all the logic and returns a unified list
    where featured vendors appear first, followed by regular vendors.
    
    GET /api/user/recommendations/
    Query Parameters:
    - category: Business category filter (e.g., 'Food', 'Restaurant')
    - limit: Number of recommendations (default: 20)
    - latitude: User's latitude for location-based recommendations
    - longitude: User's longitude for location-based recommendations
    - city: User's city for location-based recommendations
    
    POST /api/user/recommendations/
    Body: Rate a vendor after ordering
    {
        "vendor_id": 1,
        "rating": 5,
        "review_text": "Excellent service!",
        "order_id": 123
    }
    
    PUT /api/user/recommendations/preferences/
    Body: Update user preferences
    {
        "preferred_locations": ["Lagos", "Abuja"],
        "preferred_categories": ["Food", "Restaurant"],
        "current_city": "Lagos"
    }
    """
    permission_classes = [AllowAny]  # Public recommendations
    
    def get(self, request):
        """Get unified vendor recommendations"""
        try:
            # Extract parameters
            category = request.query_params.get('category', '').strip()
            cuisine = request.query_params.get('cuisine', '').strip()
            limit = int(request.query_params.get('limit', 20))
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            city = request.query_params.get('city', '').strip()
            
            # Get user if authenticated
            user = request.user if request.user.is_authenticated else None
            
            # Build base queryset
            queryset = self._build_base_queryset()
            
            # Apply filters
            queryset = self._apply_filters(queryset, category, cuisine, city)
            
            # Apply location filtering
            user_location = {
                'latitude': latitude,
                'longitude': longitude,
                'city': city
            }
            queryset = self._apply_location_filtering(queryset, user_location, user)
            
            # Get recommendations
            recommendations = self._get_recommendations(queryset, limit, user)
            
            return Response({
                'success': True,
                'recommendations': recommendations,
                'total_count': len(recommendations),
                'filters_applied': {
                    'category': category,
                    'cuisine': cuisine,
                    'city': city,
                    'limit': limit
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Rate a vendor (combines rating functionality) - DISABLED: VendorRating model removed"""
        return Response({
            'success': False,
            'error': 'Rating functionality is currently disabled'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    def put(self, request):
        """Update user preferences - DISABLED: UserPreference model removed"""
        return Response({
            'success': False,
            'error': 'Preference functionality is currently disabled'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    def _build_base_queryset(self):
        """Build the base queryset for vendor recommendations"""
        two_days_ago = timezone.now() - timedelta(days=2)
        return VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False,
            last_menu_update__gte=two_days_ago
        ).select_related('user', 'subscription_plan')
    
    def _apply_filters(self, queryset, category, cuisine, city):
        """Apply category, cuisine, and city filters"""
        if category:
            queryset = queryset.filter(business_category__icontains=category)

        if cuisine:
            queryset = queryset.filter(
                Q(business_category__icontains=cuisine) |
                Q(business_description__icontains=cuisine)
            )
        
        if city:
            queryset = queryset.filter(
                Q(business_address__icontains=city) |
                Q(service_areas__icontains=city)
            )

        return queryset
    
    def _apply_location_filtering(self, queryset, user_location, user):
        """Apply location-based filtering"""
        location_q = Q()
        
        # Filter by user's current city if provided
        if user_location.get('city'):
            city = user_location['city']
            location_q |= Q(business_address__icontains=city) | Q(service_areas__icontains=city)
        
        return queryset.filter(location_q) if location_q else queryset
    
    def _get_recommendations(self, queryset, limit, user):
        """Get vendor recommendations with proper prioritization"""
        # Get featured vendors first (they get priority)
        featured_vendors = self._get_featured_vendors(queryset, limit // 2)
        remaining_limit = limit - len(featured_vendors)
        
        # Get regular vendors for remaining slots
        regular_vendors = self._get_regular_vendors(queryset, remaining_limit, user)
        
        # Combine and return
        all_recommendations = featured_vendors + regular_vendors
        return all_recommendations[:limit]
    
    def _get_featured_vendors(self, queryset, limit: int) -> List[Dict]:
        """Get featured vendors (those with pro subscription) with highest priority"""
        featured_queryset = queryset.filter(
            is_featured=True
        ).order_by('-featured_priority', '-created_at')

        featured_vendors = featured_queryset[:limit]
        return [self._create_vendor_dict(vendor, is_featured=True) for vendor in featured_vendors]
    
    def _get_regular_vendors(
        self,
        queryset,
        limit: int,
        user: Optional[User]
    ) -> List[Dict]:
        """Get regular (non-featured) vendor recommendations"""
        # Exclude featured vendors
        queryset = queryset.exclude(is_featured=True)

        # Order by creation date (newest first) since no rating system exists
        regular_vendors = queryset.order_by('-created_at')[:limit]

        # Convert to list and sort by custom scoring
        vendor_list = list(regular_vendors)
        vendor_list.sort(key=lambda v: self._calculate_simple_score(v, user), reverse=True)

        return [self._create_vendor_dict(vendor, is_featured=False) for vendor in vendor_list]
    
    def _calculate_simple_score(self, vendor, user: Optional[User]) -> float:
        """Calculate improved recommendation score with performance metrics and time-based factors"""
        score = 0.0
        
        # Base score from vendor metrics (40% weight)
        popularity_metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
        score += float(popularity_metrics.get('popularity_score', 0)) * 0.4
        
        # Featured vendor boost (20% weight)
        if vendor.is_featured:
            score += 20
        
        # Subscription plan boost (15% weight)
        if vendor.subscription_plan and vendor.subscription_plan.plan_type == 'pro':
            score += 15
        
        # Improved new vendor boost with gradual decay (10% weight)
        days_since_created = (timezone.now() - vendor.created_at).days
        if days_since_created < 7:
            score += 8  # Strong boost for brand new vendors
        elif days_since_created < 30:
            score += 5  # Moderate boost
        elif days_since_created < 90:
            score += 2  # Small boost
        # No boost after 90 days
        
        # Performance metrics from existing orders (15% weight)
        performance_score = self._calculate_performance_score(vendor)
        score += performance_score * 0.15
        
        # Time-based relevance boost (10% weight)
        time_relevance = self._calculate_time_relevance(vendor)
        score += time_relevance * 0.10
        
        # User preference alignment (5% weight)
        if user:
            # Boost for vendors user has ordered from before
            if Order.objects.filter(user=user, vendor=vendor).exists():
                score += 8
            # Boost for favorited vendors
            if Favorite.objects.filter(user=user, favorite_type='venue', vendor=vendor).exists():
                score += 12
        
        return score
    
    def _calculate_performance_score(self, vendor) -> float:
        """Calculate performance score based on order history"""
        from bestyy.core_features.user.models import Order
        from datetime import timedelta
        
        # Get recent orders (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_orders = Order.objects.filter(
            vendor=vendor,
            created_at__gte=thirty_days_ago
        )
        
        if not recent_orders.exists():
            return 0.0
        
        # Calculate performance metrics
        total_orders = recent_orders.count()
        completed_orders = recent_orders.filter(status='completed').count()
        completion_rate = completed_orders / total_orders if total_orders > 0 else 0
        
        # Calculate average order value
        total_revenue = sum(order.total_price for order in recent_orders if order.total_price)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Performance score (0-100)
        performance_score = 0
        performance_score += completion_rate * 50  # 50 points for completion rate
        performance_score += min(avg_order_value / 1000, 1) * 30  # 30 points for order value (capped at 1000)
        performance_score += min(total_orders / 10, 1) * 20  # 20 points for order volume (capped at 10 orders)
        
        return performance_score
    
    def _calculate_time_relevance(self, vendor) -> float:
        """Calculate time-based relevance score"""
        current_hour = timezone.now().hour
        
        # Define time-based food categories
        time_categories = {
            'morning': (6, 11),    # 6 AM - 11 AM
            'afternoon': (11, 17), # 11 AM - 5 PM
            'evening': (17, 21),   # 5 PM - 9 PM
            'night': (21, 6)       # 9 PM - 6 AM
        }
        
        # Determine current time category
        current_category = None
        for category, (start, end) in time_categories.items():
            if category == 'night':
                if current_hour >= start or current_hour < end:
                    current_category = category
                    break
            else:
                if start <= current_hour < end:
                    current_category = category
                    break
        
        if not current_category:
            return 0.0
        
        # Define food keywords for each time category
        time_food_keywords = {
            'morning': ['breakfast', 'bread', 'tea', 'coffee', 'porridge', 'pancake', 'cereal', 'toast', 'egg', 'milk'],
            'afternoon': ['lunch', 'rice', 'pasta', 'sandwich', 'burger', 'pizza', 'main', 'meal', 'chicken', 'beef'],
            'evening': ['dinner', 'supper', 'heavy', 'traditional', 'jollof', 'fried', 'grilled', 'roasted', 'stew'],
            'night': ['snack', 'soup', 'garri', 'beverage', 'drink', 'light', 'quick', 'late', 'night']
        }
        
        # Check if vendor's business category or description matches current time
        vendor_text = f"{vendor.business_category} {vendor.business_description}".lower()
        relevant_keywords = time_food_keywords.get(current_category, [])
        
        # Calculate relevance score
        relevance_score = 0
        for keyword in relevant_keywords:
            if keyword in vendor_text:
                relevance_score += 10
        
        # Cap the relevance score
        return min(relevance_score, 50)
    
    def _create_vendor_dict(self, vendor: VendorProfile, is_featured: bool = False) -> Dict:
        """Create vendor dictionary for API response with Cloudinary integration"""
        # Get popularity metrics (calculated on-demand)
        popularity_metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
        
        # Handle Cloudinary URL generation
        logo_url = None
        if vendor.logo:
            try:
                # If using Cloudinary, get the optimized URL
                if hasattr(vendor.logo, 'url'):
                    logo_url = vendor.logo.url
                    # Add Cloudinary transformations for optimization
                    if 'cloudinary.com' in logo_url:
                        # Transform for web optimization (auto format, quality, resize)
                        logo_url = logo_url.replace('/upload/', '/upload/w_300,h_300,c_fill,f_auto,q_auto/')
                else:
                    logo_url = str(vendor.logo)
            except Exception as e:
                # Fallback if Cloudinary URL generation fails
                logo_url = None
        
        return {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'business_category': vendor.business_category,
            'business_address': vendor.business_address,
            'logo': logo_url,
            'logo_thumbnail': self._get_cloudinary_thumbnail(logo_url) if logo_url else None,
            'delivery_time': self._estimate_delivery_time(vendor),
            'rating': 0.0,  # No rating system implemented yet
            'total_reviews': 0,  # No review system implemented yet
            'is_featured': is_featured,
            'featured_priority': vendor.featured_priority,
            'subscription_plan': vendor.subscription_plan.plan_type if vendor.subscription_plan else 'free',
            'recommendation_score': float(popularity_metrics.get('popularity_score', 0)),
            'offers_delivery': vendor.offers_delivery,
            'service_areas': vendor.service_areas.split(',') if vendor.service_areas else [],
            'opening_hours': vendor.opening_hours.strftime('%H:%M') if vendor.opening_hours else None,
            'closing_hours': vendor.closing_hours.strftime('%H:%M') if vendor.closing_hours else None,
            'is_open': self._is_vendor_open(vendor),
            'distance': None,  # Can be calculated on frontend with user location
        }
    
    def _get_cloudinary_thumbnail(self, logo_url: str) -> str:
        """Generate thumbnail URL for Cloudinary images"""
        if logo_url and 'cloudinary.com' in logo_url:
            # Create a smaller thumbnail version
            return logo_url.replace('/upload/', '/upload/w_100,h_100,c_fill,f_auto,q_auto/')
        return logo_url
    
    def _estimate_delivery_time(self, vendor: VendorProfile) -> str:
        """Estimate delivery time based on vendor characteristics"""
        base_time = 30  # Base 30 minutes
        
        # Adjust based on vendor metrics
        popularity_metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
        recent_orders = popularity_metrics.get('orders_last_7_days', 0)
        
        if recent_orders > 50:
                base_time += 15
        elif recent_orders > 20:
                base_time += 10
        
        return f"{base_time}-{base_time + 15} min"
    
    def _is_vendor_open(self, vendor: VendorProfile) -> bool:
        """Check if vendor is currently open"""
        if not vendor.opening_hours or not vendor.closing_hours:
            return True  # Assume open if hours not set
        
        now = timezone.now().time()
        return vendor.opening_hours <= now <= vendor.closing_hours