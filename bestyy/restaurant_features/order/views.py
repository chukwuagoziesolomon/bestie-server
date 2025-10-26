"""
Views for the order app.
"""
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination

from user.permissions import IsAdminUser
from .models import Order, OrderStatus
from .serializers import (
    OrderAdminListSerializer, 
    OrderDetailAdminSerializer,
    OrderStatusUpdateSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for order lists."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminOrderListView(ListAPIView):
    """
    API endpoint that lists all orders with search and pagination.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = OrderAdminListSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Order.objects.select_related('customer', 'vendor')
        
        # Apply search filter
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer__first_name__icontains=question) |
                Q(customer__last_name__icontains=question) |
                Q(customer__email__icontains=question) |
                Q(vendor__business_name__icontains=question)
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
                end_date = end_date + timedelta(days=1)  # Include the entire end date
                queryset = queryset.filter(created_at__date__lt=end_date)
            except (ValueError, TypeError):
                pass
        
        return queryset.order_by('-created_at')


class AdminOrderDetailView(RetrieveAPIView):
    """
    API endpoint that retrieves a single order with all details.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = OrderDetailAdminSerializer
    queryset = Order.objects.all()
    lookup_field = 'id'


class AdminOrderStatusUpdateView(UpdateAPIView):
    """
    API endpoint to update order status.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = OrderStatusUpdateSerializer
    queryset = Order.objects.all()
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update order status
        new_status = serializer.validated_data['status']
        instance.status = new_status
        
        # Add notes if provided
        notes = serializer.validated_data.get('notes')
        if notes:
            if instance.notes:
                instance.notes += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
            else:
                instance.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
        
        instance.save()
        
        # Return the updated order
        return Response(OrderDetailAdminSerializer(instance).data)


class OrderStatsView(APIView):
    """
    API endpoint that provides order statistics for the admin dashboard.
    Only accessible by admin users.
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
