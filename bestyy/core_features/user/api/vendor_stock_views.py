from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404

from ..models import MenuItem, VendorProfile
from ..serializers.menu_serializers import MenuItemSerializer


class VendorStockPagination(PageNumberPagination):
    """Custom pagination for vendor stock management."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class VendorStockListView(generics.ListAPIView):
    """
    Get all menu items for a vendor with stock/availability information.
    Allows filtering by availability status and category.
    """
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = VendorStockPagination
    
    def get_queryset(self):
        """Get menu items for the authenticated vendor."""
        if not hasattr(self.request.user, 'vendor_profile'):
            return MenuItem.objects.none()
        
        vendor = self.request.user.vendor_profile
        queryset = MenuItem.objects.filter(vendor=vendor).order_by('-created_at')
        
        # Apply filters
        availability = self.request.query_params.get('availability')
        if availability is not None:
            if availability.lower() == 'true':
                queryset = queryset.filter(available_now=True)
            elif availability.lower() == 'false':
                queryset = queryset.filter(available_now=False)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by stock status
        stock_status = self.request.query_params.get('stock_status')
        if stock_status:
            if stock_status == 'in_stock':
                queryset = queryset.filter(quantity__gt=0)
            elif stock_status == 'out_of_stock':
                queryset = queryset.filter(quantity=0)
            elif stock_status == 'low_stock':
                queryset = queryset.filter(quantity__gt=0, quantity__lte=10)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(dish_name__icontains=search) |
                Q(item_description__icontains=search) |
                Q(category__icontains=search)
            )
        
        return queryset


class VendorStockDetailView(generics.RetrieveUpdateAPIView):
    """
    Get, update, or toggle availability of a specific menu item.
    """
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get menu items for the authenticated vendor."""
        if not hasattr(self.request.user, 'vendor_profile'):
            return MenuItem.objects.none()
        
        vendor = self.request.user.vendor_profile
        return MenuItem.objects.filter(vendor=vendor)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_item_availability(request, item_id):
    """
    Toggle the availability status of a menu item.
    This is a quick way to mark items as finished/not available.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    try:
        menu_item = get_object_or_404(MenuItem, id=item_id, vendor=vendor)
        
        # Toggle availability
        menu_item.available_now = not menu_item.available_now
        menu_item.save()
        
        serializer = MenuItemSerializer(menu_item)
        
        return Response({
            'message': f'Item {"made available" if menu_item.available_now else "marked as unavailable"}',
            'item': serializer.data
        }, status=status.HTTP_200_OK)
        
    except MenuItem.DoesNotExist:
        return Response({
            'error': 'Menu item not found or does not belong to this vendor'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def bulk_toggle_availability(request):
    """
    Bulk toggle availability for multiple menu items.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    item_ids = request.data.get('item_ids', [])
    availability = request.data.get('availability')
    
    if not item_ids:
        return Response({
            'error': 'item_ids is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if availability is None:
        return Response({
            'error': 'availability (true/false) is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Update multiple items
        updated_count = MenuItem.objects.filter(
            id__in=item_ids,
            vendor=vendor
        ).update(available_now=availability)
        
        return Response({
            'message': f'Updated availability for {updated_count} items',
            'updated_count': updated_count,
            'availability': availability
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to update items: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_summary(request):
    """
    Get a summary of stock status for the vendor.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get stock statistics
    total_items = MenuItem.objects.filter(vendor=vendor).count()
    available_items = MenuItem.objects.filter(vendor=vendor, available_now=True).count()
    unavailable_items = MenuItem.objects.filter(vendor=vendor, available_now=False).count()
    in_stock_items = MenuItem.objects.filter(vendor=vendor, quantity__gt=0).count()
    out_of_stock_items = MenuItem.objects.filter(vendor=vendor, quantity=0).count()
    low_stock_items = MenuItem.objects.filter(vendor=vendor, quantity__gt=0, quantity__lte=10).count()
    
    # Get category breakdown
    categories = MenuItem.objects.filter(vendor=vendor).values('category').distinct()
    category_stats = []
    
    for category in categories:
        cat_name = category['category']
        cat_total = MenuItem.objects.filter(vendor=vendor, category=cat_name).count()
        cat_available = MenuItem.objects.filter(vendor=vendor, category=cat_name, available_now=True).count()
        cat_out_of_stock = MenuItem.objects.filter(vendor=vendor, category=cat_name, quantity=0).count()
        
        category_stats.append({
            'category': cat_name,
            'total_items': cat_total,
            'available_items': cat_available,
            'out_of_stock_items': cat_out_of_stock
        })
    
    return Response({
        'summary': {
            'total_items': total_items,
            'available_items': available_items,
            'unavailable_items': unavailable_items,
            'in_stock_items': in_stock_items,
            'out_of_stock_items': out_of_stock_items,
            'low_stock_items': low_stock_items
        },
        'category_breakdown': category_stats
    }, status=status.HTTP_200_OK)


