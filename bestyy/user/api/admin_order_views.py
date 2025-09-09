"""
Admin API views for order management.
These endpoints are protected and only accessible by admin users.
"""
from datetime import datetime, timedelta
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from user.permissions import IsAdminUser
from order.models import Order, OrderItem
from order.serializers import OrderAdminSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminOrderListView(ListAPIView):
    """
    API endpoint that lists all orders with search and pagination.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)
    
    ## Query Parameters
    - `search` (string, optional): Search in vendor name, customer name, or order ID
    - `status` (string, optional): Filter by order status
    - `vendor_id` (integer, optional): Filter by specific vendor
    - `start_date` (date, optional): Filter orders from this date (YYYY-MM-DD)
    - `end_date` (date, optional): Filter orders until this date (YYYY-MM-DD)
    - `page` (integer, optional): Page number for pagination. Default: 1
    - `page_size` (integer, optional): Number of items per page. Default: 20, Max: 100
    
    ## Response Format
    ```json
    {
        "count": 150,
        "total_pages": 8,
        "current_page": 1,
        "results": [
            {
                "id": "ORD-123456",
                "order_date": "2023-10-15T14:30:00Z",
                "status": "completed",
                "total_amount": 125.99,
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "vendor_name": "Best Foods",
                "vendor_id": 5,
                "delivery_address": {
                    "street": "123 Main St",
                    "city": "Lagos",
                    "state": "Lagos",
                    "postal_code": "100001",
                    "country": "Nigeria"
                },
                "items_count": 3
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = OrderAdminSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Order.objects.select_related('vendor', 'customer')
        
        # Apply search filter
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(vendor__business_name__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__email__icontains=search)
            )
        
        # Apply status filter
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Apply vendor filter
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        # Apply date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except (ValueError, TypeError):
                pass
                
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Add one day to include the entire end date
                end_date = end_date + timedelta(days=1)
                queryset = queryset.filter(created_at__date__lt=end_date)
            except (ValueError, TypeError):
                pass
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get paginated data
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # If no pagination, return all results (not recommended for large datasets)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderStatsView(APIView):
    """
    API endpoint that provides order statistics for the admin dashboard.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)
    
    ## Query Parameters
    - `timeframe` (string, optional): Time period for statistics. 
      Options: 'today', 'week', 'month', 'year'. Default: 'month'
    - `vendor_id` (integer, optional): Filter by specific vendor
    
    ## Response Format
    ```json
    {
        "total_orders": 150,
        "total_revenue": 12500.50,
        "average_order_value": 83.34,
        "status_counts": {
            "pending": 10,
            "processing": 25,
            "shipped": 30,
            "delivered": 80,
            "cancelled": 5
        },
        "top_vendors": [
            {
                "id": 5,
                "business_name": "Best Foods",
                "order_count": 45,
                "total_revenue": 4500.00
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Get time period
        timeframe = request.query_params.get('timeframe', 'month')
        now = timezone.now()
        
        # Set time period filter
        if timeframe == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'week':
            start_date = now - timedelta(days=7)
        elif timeframe == 'year':
            start_date = now - timedelta(days=365)
        else:  # month (default)
            start_date = now - timedelta(days=30)
        
        # Base queryset
        queryset = Order.objects.filter(created_at__gte=start_date)
        
        # Apply vendor filter if specified
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        # Calculate basic stats
        total_orders = queryset.count()
        total_revenue = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate average order value
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
        
        # Get order counts by status
        status_counts = dict(queryset.values_list('status').annotate(count=Count('id')))
        
        # Get top vendors by order count and revenue
        from django.db.models import F
        top_vendors = queryset.values(
            'vendor__id', 
            'vendor__business_name'
        ).annotate(
            order_count=Count('id'),
            total_revenue=Sum('total_amount')
        ).order_by('-order_count')[:5]  # Top 5 vendors
        
        # Format the response
        response_data = {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'average_order_value': avg_order_value,
            'status_counts': status_counts,
            'top_vendors': [
                {
                    'id': vendor['vendor__id'],
                    'business_name': vendor['vendor__business_name'],
                    'order_count': vendor['order_count'],
                    'total_revenue': float(vendor['total_revenue'] or 0)
                }
                for vendor in top_vendors
            ]
        }
        
        return Response(response_data)
