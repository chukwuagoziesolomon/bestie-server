"""
Vendor Autocomplete Search API
Fast autocomplete search for restaurants/vendors with smart ranking
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Avg, Case, When, FloatField, Value
from django.db.models.functions import Lower
from bestyy.core_features.user.models import VendorProfile
from bestyy.restaurant_features.product.models import Product
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def vendor_autocomplete(request):
    """
    Fast autocomplete search for vendors/restaurants
    
    GET /api/user/vendors/autocomplete/?q=search_term&limit=10
    
    Query Parameters:
    - q: Search query (required, min 2 characters)
    - limit: Maximum results to return (default: 10, max: 50)
    - location: Filter by location/area (optional)
    - category: Filter by business category (optional)
    
    Returns:
    - Ranked list of vendors matching search
    - Includes: business name, category, address, rating, logo
    """
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)
    location = request.GET.get('location', '').strip()
    category = request.GET.get('category', '').strip()
    
    # Validate query
    if not query:
        return Response({
            'success': False,
            'error': 'Search query is required (parameter: q)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if len(query) < 2:
        return Response({
            'success': False,
            'error': 'Search query must be at least 2 characters'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Base queryset: only approved, non-suspended vendors
        vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        )
        
        # Apply search across multiple fields with ranking
        search_q = Q()
        
        # Exact match (highest priority)
        search_q |= Q(business_name__iexact=query)
        
        # Starts with (high priority)
        search_q |= Q(business_name__istartswith=query)
        
        # Contains (medium priority)
        search_q |= Q(business_name__icontains=query)
        
        # Description and category search (lower priority)
        search_q |= Q(business_description__icontains=query)
        search_q |= Q(business_category__icontains=query)
        search_q |= Q(service_areas__icontains=query)
        
        vendors = vendors.filter(search_q).distinct()
        
        # Apply filters (location filter removed - search by name regardless of location)
        # if location:
        #     vendors = vendors.filter(
        #         Q(business_address__icontains=location) |
        #         Q(service_areas__icontains=location)
        #     )
        
        if category:
            vendors = vendors.filter(business_category__icontains=category)
        
        # Annotate with relevance score
        vendors = vendors.annotate(
            # Exact match score
            exact_match=Case(
                When(business_name__iexact=query, then=Value(100.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Starts with score
            starts_with=Case(
                When(business_name__istartswith=query, then=Value(50.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Calculate total products
            product_count=Count('products', filter=Q(products__is_available=True)),
            # Calculate average rating (from orders if you have that)
            # avg_rating=Avg('vendor_orders__rating')  # Uncomment if you have ratings
        )
        
        # Sort by relevance and popularity
        vendors = vendors.order_by(
            '-exact_match',
            '-starts_with',
            '-product_count',
            Lower('business_name')
        )[:limit]
        
        # Build response
        results = []
        for vendor in vendors:
            # Get logo URL
            logo_url = None
            if vendor.logo:
                logo_url = request.build_absolute_uri(vendor.logo.url)
            
            # Get cover image URL
            cover_url = None
            if vendor.cover_image:
                cover_url = request.build_absolute_uri(vendor.cover_image.url)
            
            results.append({
                'id': vendor.id,
                'business_name': vendor.business_name,
                'category': vendor.business_category,
                'address': vendor.business_address,
                'service_areas': vendor.service_areas,
                'description': vendor.business_description[:100] if vendor.business_description else None,
                'logo': logo_url,
                'cover_image': cover_url,
                'offers_delivery': vendor.offers_delivery,
                'opening_hours': str(vendor.opening_hours) if vendor.opening_hours else None,
                'closing_hours': str(vendor.closing_hours) if vendor.closing_hours else None,
                'product_count': vendor.product_count,
                'phone': vendor.phone,
                # 'rating': float(vendor.avg_rating or 0),  # Uncomment if you have ratings
            })
        
        return Response({
            'success': True,
            'query': query,
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in vendor autocomplete: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while searching',
            'details': str(e) if request.user.is_staff else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def vendor_suggestions(request):
    """
    Get vendor name suggestions for autocomplete (lightweight)
    
    GET /api/user/vendors/suggestions/?q=search_term&limit=5
    
    Query Parameters:
    - q: Search query (required, min 2 characters)
    - limit: Maximum suggestions (default: 5, max: 20)
    
    Returns:
    - Simple list of vendor names for autocomplete dropdown
    """
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 5)), 20)
    
    if not query or len(query) < 2:
        return Response({
            'success': False,
            'error': 'Search query must be at least 2 characters'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get vendor names matching query
        vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        ).filter(
            Q(business_name__istartswith=query) |
            Q(business_name__icontains=query)
        ).values_list('business_name', flat=True).distinct()[:limit]
        
        return Response({
            'success': True,
            'query': query,
            'suggestions': list(vendors)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in vendor suggestions: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while getting suggestions'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def vendor_by_cuisine(request):
    """
    Search vendors by cuisine/food type
    
    GET /api/user/vendors/by-cuisine/?cuisine=Nigerian&limit=10
    
    Query Parameters:
    - cuisine: Cuisine type (required)
    - limit: Maximum results (default: 10, max: 50)
    
    Returns:
    - List of vendors offering specified cuisine
    """
    cuisine = request.GET.get('cuisine', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)
    
    if not cuisine:
        return Response({
            'success': False,
            'error': 'Cuisine parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Search vendors by category or products they offer
        vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        ).filter(
            Q(business_category__icontains=cuisine) |
            Q(business_description__icontains=cuisine) |
            Q(products__name__icontains=cuisine) |
            Q(products__description__icontains=cuisine)
        ).annotate(
            product_count=Count('products', filter=Q(products__is_available=True))
        ).distinct().order_by('-product_count', 'business_name')[:limit]
        
        results = []
        for vendor in vendors:
            logo_url = None
            if vendor.logo:
                logo_url = request.build_absolute_uri(vendor.logo.url)
            
            results.append({
                'id': vendor.id,
                'business_name': vendor.business_name,
                'category': vendor.business_category,
                'address': vendor.business_address,
                'logo': logo_url,
                'offers_delivery': vendor.offers_delivery,
                'product_count': vendor.product_count,
            })
        
        return Response({
            'success': True,
            'cuisine': cuisine,
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in vendor by cuisine: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while searching by cuisine'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
