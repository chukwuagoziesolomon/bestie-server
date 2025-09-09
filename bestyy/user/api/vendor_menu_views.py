from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from django.db.models import Q, Count, Min, Max, Avg
from django.http import Http404

from ..models import MenuItem, VendorProfile
from ..serializers.menu_serializers import (
    MenuItemSerializer, 
    MenuItemCreateSerializer, 
    MenuItemUpdateSerializer,
    MenuItemListSerializer,
    MenuCategorySerializer
)


class VendorMenuListView(generics.ListCreateAPIView):
    """
    API endpoint for vendors to list and create menu items.
    
    GET: List all menu items for the authenticated vendor
    POST: Create a new menu item for the authenticated vendor
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MenuItemCreateSerializer
        return MenuItemListSerializer
    
    def get_queryset(self):
        """Get menu items for the authenticated vendor."""
        if not hasattr(self.request.user, 'vendor_profile'):
            return MenuItem.objects.none()
        
        vendor = self.request.user.vendor_profile
        queryset = MenuItem.objects.filter(vendor=vendor).order_by('-created_at')
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        available_only = self.request.query_params.get('available_only')
        if available_only and available_only.lower() == 'true':
            queryset = queryset.filter(available_now=True)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(dish_name__icontains=search) |
                Q(item_description__icontains=search) |
                Q(category__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Create menu item for the authenticated vendor."""
        if not hasattr(self.request.user, 'vendor_profile'):
            raise permissions.PermissionDenied("User must have a vendor profile to create menu items.")
        
        vendor = self.request.user.vendor_profile
        serializer.save(vendor=vendor)


class VendorMenuDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for vendors to retrieve, update, or delete specific menu items.
    
    GET: Retrieve a specific menu item
    PUT/PATCH: Update a specific menu item
    DELETE: Delete a specific menu item
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MenuItemUpdateSerializer
        return MenuItemSerializer
    
    def get_queryset(self):
        """Get menu items for the authenticated vendor only."""
        if not hasattr(self.request.user, 'vendor_profile'):
            return MenuItem.objects.none()
        
        vendor = self.request.user.vendor_profile
        return MenuItem.objects.filter(vendor=vendor)
    
    def perform_update(self, serializer):
        """Update menu item, ensuring vendor can only update their own items."""
        if not hasattr(self.request.user, 'vendor_profile'):
            raise permissions.PermissionDenied("User must have a vendor profile to update menu items.")
        
        vendor = self.request.user.vendor_profile
        if serializer.instance.vendor != vendor:
            raise permissions.PermissionDenied("You can only update your own menu items.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Delete menu item, ensuring vendor can only delete their own items."""
        if not hasattr(self.request.user, 'vendor_profile'):
            raise permissions.PermissionDenied("User must have a vendor profile to delete menu items.")
        
        vendor = self.request.user.vendor_profile
        if instance.vendor != vendor:
            raise permissions.PermissionDenied("You can only delete your own menu items.")
        
        instance.delete()


class VendorMenuCategoriesView(APIView):
    """
    API endpoint for vendors to get menu categories and items grouped by category.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all categories for the vendor's menu with item counts."""
        if not hasattr(request.user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access menu categories."},
                status=403
            )
        
        vendor = request.user.vendor_profile
        
        # Get all categories with item counts
        categories = MenuItem.objects.filter(vendor=vendor).values('category').annotate(
            count=Count('id')
        ).order_by('category')
        
        # Get items for each category
        category_data = []
        for category in categories:
            category_name = category['category']
            items = MenuItem.objects.filter(
                vendor=vendor, 
                category=category_name
            ).order_by('dish_name')
            
            # Serialize items
            item_serializer = MenuItemListSerializer(items, many=True, context={'request': request})
            
            category_data.append({
                'category': category_name,
                'count': category['count'],
                'items': item_serializer.data
            })
        
        return Response({
            'categories': category_data,
            'total_categories': len(category_data),
            'total_items': sum(cat['count'] for cat in category_data)
        })


class VendorMenuStatsView(APIView):
    """
    API endpoint for vendors to get menu statistics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get menu statistics for the vendor."""
        if not hasattr(request.user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access menu stats."},
                status=403
            )
        
        vendor = request.user.vendor_profile
        
        # Get menu statistics
        total_items = MenuItem.objects.filter(vendor=vendor).count()
        available_items = MenuItem.objects.filter(vendor=vendor, available_now=True).count()
        unavailable_items = total_items - available_items
        
        # Get category statistics
        categories = MenuItem.objects.filter(vendor=vendor).values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get price range
        price_stats = MenuItem.objects.filter(vendor=vendor).aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price')
        )
        
        # Get items with low quantity (less than 5)
        low_quantity_items = MenuItem.objects.filter(
            vendor=vendor, 
            quantity__lt=5, 
            quantity__gt=0
        ).count()
        
        out_of_stock_items = MenuItem.objects.filter(
            vendor=vendor, 
            quantity=0
        ).count()
        
        return Response({
            'total_items': total_items,
            'available_items': available_items,
            'unavailable_items': unavailable_items,
            'low_quantity_items': low_quantity_items,
            'out_of_stock_items': out_of_stock_items,
            'categories': list(categories),
            'price_range': {
                'min_price': float(price_stats['min_price']) if price_stats['min_price'] else 0,
                'max_price': float(price_stats['max_price']) if price_stats['max_price'] else 0,
                'avg_price': float(price_stats['avg_price']) if price_stats['avg_price'] else 0
            }
        })


class VendorMenuBulkUpdateView(APIView):
    """
    API endpoint for vendors to perform bulk operations on menu items.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request):
        """Bulk update menu items (e.g., mark as available/unavailable, update prices)."""
        if not hasattr(request.user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to perform bulk operations."},
                status=403
            )
        
        vendor = request.user.vendor_profile
        item_ids = request.data.get('item_ids', [])
        updates = request.data.get('updates', {})
        
        if not item_ids:
            return Response(
                {"detail": "item_ids is required for bulk update."},
                status=400
            )
        
        # Validate that all items belong to the vendor
        items = MenuItem.objects.filter(id__in=item_ids, vendor=vendor)
        if items.count() != len(item_ids):
            return Response(
                {"detail": "Some items do not belong to your vendor profile or do not exist."},
                status=400
            )
        
        # Apply updates
        updated_count = items.update(**updates)
        
        return Response({
            'message': f'Successfully updated {updated_count} menu items.',
            'updated_count': updated_count
        })
    
    def delete(self, request):
        """Bulk delete menu items."""
        if not hasattr(request.user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to perform bulk operations."},
                status=403
            )
        
        vendor = request.user.vendor_profile
        item_ids = request.data.get('item_ids', [])
        
        if not item_ids:
            return Response(
                {"detail": "item_ids is required for bulk delete."},
                status=400
            )
        
        # Validate that all items belong to the vendor
        items = MenuItem.objects.filter(id__in=item_ids, vendor=vendor)
        if items.count() != len(item_ids):
            return Response(
                {"detail": "Some items do not belong to your vendor profile or do not exist."},
                status=400
            )
        
        # Delete items
        deleted_count, _ = items.delete()
        
        return Response({
            'message': f'Successfully deleted {deleted_count} menu items.',
            'deleted_count': deleted_count
        })
