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
    Favorite
)
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.services.popularity_update_service import VendorPopularityUpdateService
from django.conf import settings


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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"UnifiedVendorRecommendationView.get called with URL: {request.path}")
        logger.info(f"Query params: {dict(request.GET)}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")

        try:
            # Extract parameters - handle both DRF query_params and Django GET
            if hasattr(request, 'query_params'):
                category = request.query_params.get('category', '').strip()
                cuisine = request.query_params.get('cuisine', '').strip()
                limit = int(request.query_params.get('limit', 20))
                latitude = request.query_params.get('latitude')
                longitude = request.query_params.get('longitude')
                city = request.query_params.get('city', '').strip()
                include_slideshow = request.query_params.get('slideshow', 'true').lower() == 'true'
                include_vendor_benefits = request.query_params.get('vendor_benefits', 'false').lower() == 'true'
            else:
                # Fallback for Django request objects
                category = request.GET.get('category', '').strip()
                cuisine = request.GET.get('cuisine', '').strip()
                limit = int(request.GET.get('limit', 20))
                latitude = request.GET.get('latitude')
                longitude = request.GET.get('longitude')
                city = request.GET.get('city', '').strip()
                include_slideshow = request.GET.get('slideshow', 'true').lower() == 'true'
                include_vendor_benefits = request.GET.get('vendor_benefits', 'false').lower() == 'true'
            
            # Get user if authenticated - handle both DRF and Django request objects
            if hasattr(request, 'user'):
                user = request.user if request.user.is_authenticated else None
            else:
                # For Django request objects without user attribute
                user = None
            
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
            
            # Get recommendations with slideshow and vendor benefits options
            recommendations = self._get_recommendations(queryset, limit, user, include_slideshow, include_vendor_benefits)
            
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
        """Build the base queryset for vendor recommendations - open gates for launch"""
        # Remove all restrictions - show all active vendors for maximum discovery
        return VendorProfile.objects.filter(
            is_suspended=False
        ).select_related('user')
    
    def _apply_filters(self, queryset, category, cuisine, city):
        """Apply category, cuisine, and city filters - optional for launch"""
        # For launch, make all filters optional and less restrictive
        if category:
            queryset = queryset.filter(business_category__icontains=category)

        if cuisine:
            queryset = queryset.filter(
                Q(business_category__icontains=cuisine) |
                Q(business_description__icontains=cuisine)
            )

        # City filtering is now optional - don't restrict by location for broader discovery
        # if city:
        #     queryset = queryset.filter(
        #         Q(business_address__icontains=city) |
        #         Q(service_areas__icontains=city)
        #     )

        return queryset
    
    def _apply_location_filtering(self, queryset, user_location, user):
        """Apply location-based filtering - made optional for better discovery"""
        location_q = Q()

        # Filter by user's current city if provided, but don't be too strict
        if user_location.get('city'):
            city = user_location['city']
            # Use a more flexible approach - only filter if explicitly requested
            # For now, we'll skip strict city filtering to allow broader discovery
            pass

        return queryset  # Return all vendors for better discovery
    
    def _get_recommendations(self, queryset, limit, user, include_slideshow=True, include_vendor_benefits=False):
        """Get vendor recommendations with featured priority for launch"""
        # For launch: Featured vendors get priority, then all others
        featured_vendors = self._get_featured_vendors(queryset, limit // 2, include_slideshow, include_vendor_benefits)  # Featured get half the slots
        remaining_limit = limit - len(featured_vendors)

        # Get all remaining vendors (no restrictions)
        regular_vendors = self._get_regular_vendors(queryset, remaining_limit, user, include_slideshow, include_vendor_benefits)

        # Combine and return
        all_recommendations = featured_vendors + regular_vendors
        return all_recommendations[:limit]
    
    def _get_featured_vendors(self, queryset, limit: int, include_slideshow=True, include_vendor_benefits=False) -> List[Dict]:
        """Get featured vendors (those with pro subscription) with highest priority"""
        # For now, return empty list since subscription model is not available
        # TODO: Implement featured vendor logic when subscription model is restored
        return []
    
    def _get_regular_vendors(
        self,
        queryset,
        limit: int,
        user: Optional[User],
        include_slideshow=True,
        include_vendor_benefits=False
    ) -> List[Dict]:
        """Get regular (non-featured) vendor recommendations - open gates for launch"""
        # For launch: Get all available vendors, no complex scoring needed
        regular_vendors = queryset.order_by('-created_at')[:limit]

        # Return all vendors without complex scoring
        return [self._create_vendor_dict(vendor, is_featured=False, include_slideshow=include_slideshow, include_vendor_benefits=include_vendor_benefits) for vendor in regular_vendors]
    
    def _calculate_simple_score(self, vendor, user: Optional[User]) -> float:
        """Calculate improved recommendation score with performance metrics and time-based factors"""
        score = 0.0
        
        # Base score from vendor metrics (40% weight)
        popularity_metrics = VendorPopularityUpdateService.get_vendor_metrics(vendor)
        score += float(popularity_metrics.get('popularity_score', 0)) * 0.4
        
        # Featured vendor boost (20% weight)
        # TODO: Implement when subscription model is restored
        # if getattr(vendor, 'is_featured', False):
        #     score += 20

        # Subscription plan boost (15% weight) - subscription model removed
        # No subscription boost applied
        
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
            if Order.objects.filter(customer=user, vendor=vendor).exists():
                score += 8
            # Boost for favorited vendors
            if Favorite.objects.filter(user=user, favorite_type='venue', vendor=vendor).exists():
                score += 12
        
            return score

    def _get_vendor_slideshow(self, vendor: VendorProfile, menu_data: Dict) -> Dict:
        """Generate slideshow data with multiple food images and transitions"""
        from bestyy.restaurant_features.product.models import Product as MenuItem
        import random
        
        slideshow_items = []
        
        # Get all items with images (not just meal-specific)
        menu_items = getattr(vendor, 'products', None)
        if menu_items:
            items_with_images = menu_items.filter(
                is_available=True, 
                image__isnull=False
            ).exclude(image__exact='')[:12]  # Get up to 12 items
            
            for item in items_with_images:
                if item.image:
                    try:
                        # Multiple image sizes for different uses
                        base_url = item.image if isinstance(item.image, str) else str(item.image)
                        if 'cloudinary.com' in base_url:
                            slideshow_items.append({
                                'id': item.id,
                                'name': item.name,
                                'description': item.description[:80] + '...' if len(item.description) > 80 else item.description,
                                'price': float(item.price),
                                'currency': 'NGN',
                                'category': item.category.name if item.category else 'Food',
                                'images': {
                                    'slideshow': base_url.replace('/upload/', '/upload/w_600,h_400,c_fill,f_auto,q_80/'),
                                    'thumbnail': base_url.replace('/upload/', '/upload/w_150,h_150,c_fill,f_auto,q_auto/'),
                                    'detail': base_url.replace('/upload/', '/upload/w_800,h_600,c_fill,f_auto,q_90/')
                                },
                                'slide_duration': 4000,  # 4 seconds per slide
                                'transition': 'fade'  # smooth fade transition
                            })
                    except Exception:
                        continue
        
        # Add vendor's cover image as first slide if available
        cover_image = self._get_cover_image_url(vendor)
        if cover_image:
            slideshow_items.insert(0, {
                'id': f'cover_{vendor.id}',
                'name': f"Welcome to {vendor.business_name}",
                'description': vendor.business_description[:100] + '...' if vendor.business_description and len(vendor.business_description) > 100 else vendor.business_description or f"Delicious food from {vendor.business_name}",
                'price': None,
                'currency': 'NGN',
                'category': 'Restaurant',
                'images': {
                    'slideshow': cover_image,
                    'thumbnail': cover_image.replace('/upload/', '/upload/w_150,h_150,c_fill,f_auto,q_auto/') if 'cloudinary.com' in cover_image else cover_image,
                    'detail': cover_image
                },
                'slide_duration': 5000,  # 5 seconds for intro slide
                'transition': 'fade'
            })
        
        # Shuffle for variety (except first slide)
        if len(slideshow_items) > 1:
            first_slide = slideshow_items[0]
            rest_slides = slideshow_items[1:]
            random.shuffle(rest_slides)
            slideshow_items = [first_slide] + rest_slides[:8]  # Limit to 9 total slides
        
        return {
            'items': slideshow_items,
            'total_slides': len(slideshow_items),
            'auto_play': True,
            'loop': True,
            'transition_duration': 800,  # 0.8 seconds transition
            'pause_on_hover': True,
            'show_indicators': True,
            'show_arrows': len(slideshow_items) > 1
        }

    def _calculate_performance_score(self, vendor) -> float:
        """Calculate performance score based on order history"""
        from bestyy.restaurant_features.order.models import Order
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
        total_revenue = sum(order.total_amount for order in recent_orders if order.total_amount)
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
    
    def _create_vendor_dict(self, vendor: VendorProfile, is_featured: bool = False, include_slideshow: bool = True, include_vendor_benefits: bool = False) -> Dict:
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
                    # Add high-quality Cloudinary transformations
                    if 'cloudinary.com' in logo_url:
                        # Clean existing transformations and add high-quality parameters
                        if '/upload/' in logo_url:
                            parts = logo_url.split('/upload/')
                            clean_url = f"{parts[0]}/upload/{parts[1]}"
                        else:
                            clean_url = logo_url
                        logo_url = clean_url.replace('/upload/', '/upload/c_fill,w_400,h_400,q_90,f_auto,dpr_auto/')
                else:
                    logo_url = str(vendor.logo)
            except Exception as e:
                # Fallback if Cloudinary URL generation fails
                logo_url = None

        # Get categorized menu items based on current meal time
        categorized_menu_items = self._get_meal_categorized_items(vendor)

        # Get slideshow data for this vendor
        slideshow_data = self._get_vendor_slideshow(vendor, categorized_menu_items)
        
        # Get vendor attraction metrics
        attraction_metrics = self._get_vendor_attraction_metrics(vendor, popularity_metrics)

        # Determine primary image - prioritize slideshow over logo
        primary_image = None
        fallback_logo = logo_url
        
        if slideshow_data and slideshow_data.get('images'):
            # Use first slideshow image as primary
            primary_image = slideshow_data['images'][0]['url']
            fallback_logo = slideshow_data['images'][0]['thumbnail']
        elif logo_url:
            # Fall back to logo if no slideshow
            primary_image = logo_url
        
        return {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'business_category': vendor.business_category,
            'business_address': vendor.business_address,
            # Primary image prioritizes slideshow content over static logo
            'primary_image': primary_image,
            'logo': fallback_logo,  # Logo as fallback or thumbnail
            'cover_image': self._get_cover_image_url(vendor),
            'logo_thumbnail': self._get_cloudinary_thumbnail(logo_url) if logo_url else None,
            'menu_items': categorized_menu_items,  # Categorized menu items based on meal time
            'slideshow': slideshow_data,  # Enhanced slideshow for visual appeal - THIS IS THE MAIN VISUAL
            'attraction_metrics': attraction_metrics,  # Metrics to attract new vendors
            'delivery_time': self._estimate_delivery_time(vendor),
            'rating': attraction_metrics.get('estimated_rating', 0.0),
            'total_reviews': attraction_metrics.get('social_proof_count', 0),
            'is_featured': is_featured,
            'featured_priority': getattr(vendor, 'featured_priority', 0),
            'subscription_plan': 'free',  # TODO: Implement when subscription model is restored
            'recommendation_score': float(popularity_metrics.get('popularity_score', 0)),
            'offers_delivery': vendor.offers_delivery,
            'service_areas': vendor.service_areas.split(',') if vendor.service_areas else [],
            'opening_hours': vendor.opening_hours.strftime('%H:%M') if vendor.opening_hours else None,
            'closing_hours': vendor.closing_hours.strftime('%H:%M') if vendor.closing_hours else None,
            'is_open': self._is_vendor_open(vendor),
            'distance': None,  # Can be calculated on frontend with user location
            'vendor_benefits': self._get_vendor_benefits(vendor),  # Benefits for joining platform
            # Frontend guidance: Use 'slideshow' for main display, 'primary_image' as fallback
            'display_priority': 'slideshow' if slideshow_data and slideshow_data.get('images') else 'logo'
        }
    
    def _get_cloudinary_thumbnail(self, logo_url: str) -> str:
        """Generate high-quality thumbnail URL for Cloudinary images"""
        if logo_url and 'cloudinary.com' in logo_url:
            # Clean existing transformations and add high-quality thumbnail parameters
            if '/upload/' in logo_url:
                parts = logo_url.split('/upload/')
                clean_url = f"{parts[0]}/upload/{parts[1]}"
            else:
                clean_url = logo_url
            return clean_url.replace('/upload/', '/upload/c_fill,w_200,h_200,q_90,f_auto,dpr_auto/')
        return logo_url

    def _get_cover_image_url(self, vendor) -> Optional[str]:
        """Get high-quality vendor cover image URL"""
        if hasattr(vendor, 'cover_image') and vendor.cover_image:
            try:
                if hasattr(vendor.cover_image, 'url'):
                    cover_url = vendor.cover_image.url
                    if 'cloudinary.com' in cover_url:
                        # Clean existing transformations and add high-quality parameters
                        if '/upload/' in cover_url:
                            parts = cover_url.split('/upload/')
                            clean_url = f"{parts[0]}/upload/{parts[1]}"
                        else:
                            clean_url = cover_url
                        cover_url = clean_url.replace('/upload/', '/upload/c_fill,w_1000,h_500,q_90,f_auto,dpr_auto/')
                    else:
                        cover_url = f"{settings.MEDIA_URL}{cover_url}"
                    return cover_url
            except Exception:
                pass
        return None
    
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

    def _get_meal_categorized_items(self, vendor: VendorProfile) -> Dict:
        """Get menu items categorized by meal types based on current time and keywords"""
        from bestyy.restaurant_features.product.models import Product as MenuItem
        
        # Get current hour to determine meal preference
        current_hour = timezone.now().hour
        
        # Define meal time periods and preferred categories
        meal_preferences = {
            'breakfast': {
                'time_range': (6, 11),  # 6 AM - 11 AM
                'keywords': ['breakfast', 'bread', 'tea', 'coffee', 'porridge', 'pancake', 'cereal', 'toast', 'egg', 'milk', 'oat', 'juice'],
                'categories': ['breakfast', 'beverages', 'snacks']
            },
            'lunch': {
                'time_range': (11, 16),  # 11 AM - 4 PM
                'keywords': ['lunch', 'rice', 'pasta', 'sandwich', 'burger', 'pizza', 'chicken', 'beef', 'jollof', 'fried rice', 'main'],
                'categories': ['nigerian', 'burgers', 'pizza', 'rice', 'main course', 'pasta']
            },
            'dinner': {
                'time_range': (16, 22),  # 4 PM - 10 PM  
                'keywords': ['dinner', 'soup', 'stew', 'heavy', 'traditional', 'pounded yam', 'eba', 'fufu', 'amala', 'egusi', 'pepper soup'],
                'categories': ['nigerian', 'soup', 'traditional', 'main course']
            },
            'snacks': {
                'time_range': (22, 6),  # 10 PM - 6 AM (night snacks)
                'keywords': ['snacks', 'light', 'quick', 'chips', 'popcorn', 'meat pie', 'chin chin', 'biscuit'],
                'categories': ['snacks', 'beverages', 'light meals']
            }
        }
        
        # Determine current meal time
        current_meal = 'lunch'  # default
        for meal, config in meal_preferences.items():
            start, end = config['time_range']
            if start <= end:  # Normal time range (e.g., 6-11)
                if start <= current_hour < end:
                    current_meal = meal
                    break
            else:  # Overnight range (e.g., 22-6)
                if current_hour >= start or current_hour < end:
                    current_meal = meal
                    break
        
        # Get vendor's menu items
        menu_items = getattr(vendor, 'products', None)
        if not menu_items:
            return {'meal_type': current_meal, 'items': []}
        
        # Filter available items with images
        available_items = menu_items.filter(is_available=True)
        
        # Get current meal preferences
        current_preferences = meal_preferences[current_meal]
        
        # Score and filter items based on relevance to current meal
        relevant_items = []
        for item in available_items[:30]:  # Limit for performance
            score = self._calculate_meal_relevance_score(item, current_preferences)
            if score > 0:
                try:
                    # Get image URL
                    image_url = None
                    if item.image:
                        if isinstance(item.image, str) and item.image.startswith('http'):
                            image_url = item.image
                            # Add Cloudinary optimization
                            if 'cloudinary.com' in image_url:
                                image_url = image_url.replace('/upload/', '/upload/w_400,h_300,c_fill,f_auto,q_auto/')
                    
                    relevant_items.append({
                        'id': item.id,
                        'name': item.name,
                        'description': item.description[:100] + '...' if len(item.description) > 100 else item.description,
                        'price': float(item.price),
                        'currency': 'NGN',
                        'category': item.category.name if item.category else 'Other',
                        'image': image_url,
                        'relevance_score': score
                    })
                except Exception:
                    continue
        
        # Sort by relevance and limit to top 6 items
        relevant_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return {
            'meal_type': current_meal,
            'meal_time': f"{current_preferences['time_range'][0]:02d}:00-{current_preferences['time_range'][1]:02d}:00",
            'items': relevant_items[:6],  # Show top 6 most relevant items
            'total_available': len(relevant_items)
        }
    
    def _calculate_meal_relevance_score(self, item, meal_preferences) -> int:
        """Calculate how relevant a menu item is for the current meal time"""
        score = 0
        item_text = f"{item.name} {item.description}".lower()
        item_category = item.category.name.lower() if item.category else ''
        
        # Check keywords in name/description (higher weight)
        for keyword in meal_preferences['keywords']:
            if keyword in item_text:
                score += 15
        
        # Check category match (lower weight)
        for category in meal_preferences['categories']:
            if category in item_category:
                score += 10
        
        # Bonus for items with images (visual appeal)
        if item.image:
            score += 5
            
        return score
    
    def _get_vendor_attraction_metrics(self, vendor, popularity_metrics):
        """Get vendor attraction metrics for startup growth"""
        try:
            # Base metrics from popularity
            base_score = float(popularity_metrics.get('popularity_score', 0))
            total_orders = popularity_metrics.get('total_orders', 0)
            
            # Calculate partnership score (0-100)
            partnership_score = min(100, base_score + (total_orders * 0.1))
            
            # Revenue potential estimation
            avg_order_value = 2500  # Average Nigerian food order
            potential_monthly = total_orders * avg_order_value * 0.3  # Conservative estimate
            revenue_range = f"₦{potential_monthly:,.0f} - ₦{potential_monthly * 1.5:,.0f}/month"
            
            return {
                "partnership_score": round(partnership_score, 1),
                "revenue_potential": revenue_range,
                "commission_rate": "12%",
                "onboarding_incentives": [
                    "Zero commission for first month",
                    "Free professional food photography",
                    "Premium listing placement"
                ],
                "marketing_support": {
                    "social_media_promotion": True,
                    "featured_vendor_opportunities": True,
                    "email_marketing_inclusion": True,
                    "app_banner_placement": True
                },
                "growth_indicators": {
                    "market_demand": "High" if total_orders > 50 else "Medium",
                    "competition_level": "Medium",
                    "customer_retention": "85%",
                    "order_frequency": f"{max(1.0, total_orders / 30):.1f} orders/week"
                },
                "support_benefits": {
                    "dedicated_account_manager": True,
                    "24_7_technical_support": True,
                    "business_analytics_dashboard": True,
                    "inventory_management_tools": True
                },
                "estimated_rating": round(base_score / 20, 1),  # Convert to 5-star scale
                "social_proof_count": max(5, total_orders // 5)  # Estimated review count
            }
        except Exception:
            # Return default metrics
            return {
                "partnership_score": 75.0,
                "revenue_potential": "₦25,000 - ₦50,000/month",
                "commission_rate": "12%",
                "estimated_rating": 4.0,
                "social_proof_count": 15
            }
    
    def _get_vendor_slideshow(self, vendor, categorized_menu_items):
        """Generate slideshow data for vendor"""
        try:
            from bestyy.restaurant_features.product.models import Product
            
            # Get menu items for slideshow
            menu_items = Product.objects.filter(vendor=vendor, is_available=True)[:6]
            slideshow_images = []
            
            for item in menu_items:
                if item.image:
                    image_url = item.image
                    if hasattr(item.image, 'url'):
                        image_url = item.image.url
                    
                    # High-quality Cloudinary optimization for frontend display
                    if 'cloudinary.com' in str(image_url):
                        base_url = str(image_url)
                        # Remove existing transformations and add high-quality ones
                        if '/upload/' in base_url:
                            parts = base_url.split('/upload/')
                            clean_url = f"{parts[0]}/upload/{parts[1]}"
                        else:
                            clean_url = base_url
                            
                        slideshow_images.append({
                            "url": clean_url.replace('/upload/', '/upload/c_fill,w_800,h_500,q_90,f_auto,dpr_auto/'),
                            "thumbnail": clean_url.replace('/upload/', '/upload/c_fill,w_200,h_150,q_85,f_auto,dpr_auto/'),
                            "detail": clean_url.replace('/upload/', '/upload/c_fill,w_1200,h_800,q_95,f_auto,dpr_auto/'),
                            "mobile": clean_url.replace('/upload/', '/upload/c_fill,w_400,h_300,q_85,f_auto,dpr_auto/'),
                            "title": item.name,
                            "description": item.description[:100] + '...' if len(item.description or '') > 100 else item.description or '',
                            "price": float(item.price),
                            "meal_category": categorized_menu_items.get('meal_type', 'lunch'),
                            "relevance_score": 85.0
                        })
                    else:
                        # Fallback for non-Cloudinary images
                        full_url = f"{settings.MEDIA_URL}{image_url}" if not str(image_url).startswith('http') else str(image_url)
                        slideshow_images.append({
                            "url": full_url,
                            "thumbnail": full_url,
                            "detail": full_url,
                            "mobile": full_url,
                            "title": item.name,
                            "description": item.description[:100] + '...' if len(item.description or '') > 100 else item.description or '',
                            "price": float(item.price),
                            "meal_category": categorized_menu_items.get('meal_type', 'lunch'),
                            "relevance_score": 85.0
                        })
            
            return {
                "images": slideshow_images,
                "total_items": menu_items.count(),
                "meal_specific_items": len(slideshow_images)
            }
        except Exception:
            return {"images": [], "total_items": 0, "meal_specific_items": 0}
    
    def _estimate_delivery_time(self, vendor):
        """Estimate delivery time for vendor"""
        # Simple estimation based on vendor location and current time
        base_time = 25  # minutes
        return f"{base_time}-{base_time + 10} mins"
    
    def _is_vendor_open(self, vendor):
        """Check if vendor is currently open"""
        try:
            current_time = timezone.now().time()
            if vendor.opening_hours and vendor.closing_hours:
                return vendor.opening_hours <= current_time <= vendor.closing_hours
        except Exception:
            pass
        return True  # Default to open
    
    def _get_vendor_benefits(self, vendor):
        """Get benefits for vendors joining the platform"""
        return {
            "commission_free_period": "30 days",
            "marketing_support": True,
            "analytics_dashboard": True,
            "customer_support": "24/7"
        }