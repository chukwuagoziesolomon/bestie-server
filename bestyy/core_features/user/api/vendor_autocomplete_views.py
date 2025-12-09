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
    food = request.GET.get('food', '').strip()
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
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
        # Vendor name, description, category, service area
        if query:
            search_q |= Q(business_name__iexact=query)
            search_q |= Q(business_name__istartswith=query)
            search_q |= Q(business_name__icontains=query)
            search_q |= Q(business_description__icontains=query)
            search_q |= Q(business_category__icontains=query)
            search_q |= Q(service_areas__icontains=query)

        # Location filter (city/state/area)
        if location:
            search_q |= Q(business_address__icontains=location)
            search_q |= Q(service_areas__icontains=location)

        # Category filter
        if category:
            search_q &= Q(business_category__icontains=category)

        # Initial vendor filter
        vendors = vendors.filter(search_q).distinct()

        # If food or price filters are present, join with Product
        product_filters = Q()
        if food:
            product_filters &= Q(name__icontains=food)
        if min_price:
            try:
                min_price_val = float(min_price)
                product_filters &= Q(price__gte=min_price_val)
            except:
                pass
        if max_price:
            try:
                max_price_val = float(max_price)
                product_filters &= Q(price__lte=max_price_val)
            except:
                pass

        # If any product filter, get vendors with matching products
        matching_vendor_ids = None
        matching_products = {}
        if food or min_price or max_price:
            products = Product.objects.filter(product_filters, vendor__in=vendors, is_available=True)
            matching_vendor_ids = set(products.values_list('vendor_id', flat=True))
            # Map vendor_id to list of matching products
            for p in products:
                if p.vendor_id not in matching_products:
                    matching_products[p.vendor_id] = []
                matching_products[p.vendor_id].append({
                    'id': p.id,
                    'name': p.name,
                    'price': float(p.price),
                    'description': p.description,
                })
            # Filter vendors to only those with matching products
            vendors = vendors.filter(id__in=matching_vendor_ids)

        # Annotate with relevance score
        vendors = vendors.annotate(
            exact_match=Case(
                When(business_name__iexact=query, then=Value(100.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            starts_with=Case(
                When(business_name__istartswith=query, then=Value(50.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            product_count=Count('products', filter=Q(products__is_available=True)),
        )

        vendors = vendors.order_by(
            '-exact_match',
            '-starts_with',
            '-product_count',
            Lower('business_name')
        )[:limit]

        # Build response
        results = []
        for vendor in vendors:
            logo_url = None
            if vendor.logo:
                logo_url = request.build_absolute_uri(vendor.logo.url)
            cover_url = None
            if vendor.cover_image:
                cover_url = request.build_absolute_uri(vendor.cover_image.url)

            vendor_data = {
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
            }
            # If product filters, include matching products
            if matching_products and vendor.id in matching_products:
                vendor_data['matching_products'] = matching_products[vendor.id]
            results.append(vendor_data)

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
