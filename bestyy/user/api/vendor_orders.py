from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, timedelta

from user.models import Order


class VendorOrdersPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class VendorOrdersView(APIView):
    """
    API endpoint for vendors to view their own orders with pagination and search.
    
    Query Parameters:
    - search: Search in order ID, customer name, or customer email
    - status: Filter by order status (pending, confirmed, preparing, ready, out_for_delivery, delivered, completed, cancelled, failed, refunded)
    - start_date: Filter orders from this date (YYYY-MM-DD)
    - end_date: Filter orders until this date (YYYY-MM-DD)
    - page: Page number for pagination (default: 1)
    - page_size: Number of items per page (default: 20, max: 100)
    - sort_by: Sort field (created_at, total_price, status) (default: created_at)
    - sort_order: Sort order (asc, desc) (default: desc)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check if user has a vendor profile
        if not hasattr(user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access orders."},
                status=403
            )
        
        vendor = user.vendor_profile
        
        # Get query parameters
        search = request.query_params.get('search', '').strip()
        status = request.query_params.get('status', '').strip()
        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        page = int(request.query_params.get('page', 1))
        page_size = min(100, int(request.query_params.get('page_size', 20)))
        
        # Validate sort parameters
        valid_sort_fields = ['created_at', 'total_price', 'status']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        # Build queryset
        queryset = Order.objects.filter(vendor=vendor).select_related('user')
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(delivery_address__icontains=search)
            )
        
        # Apply status filter
        if status:
            queryset = queryset.filter(status=status)
        
        # Apply date range filter
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date_obj)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Add one day to include the entire end date
                end_date_obj = end_date_obj + timedelta(days=1)
                queryset = queryset.filter(created_at__date__lt=end_date_obj)
            except (ValueError, TypeError):
                pass
        
        # Apply sorting
        sort_prefix = '-' if sort_order == 'desc' else ''
        queryset = queryset.order_by(f'{sort_prefix}{sort_by}')
        
        # Paginate results
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Serialize orders
        orders_data = []
        for order in page_obj:
            # Get customer name
            customer_name = order.user.get_full_name() if order.user else "Unknown Customer"
            if not customer_name.strip():
                customer_name = order.user.email if order.user else "Unknown Customer"
            
            # Get delivery address (first 100 characters)
            delivery_address = order.delivery_address[:100] + "..." if order.delivery_address and len(order.delivery_address) > 100 else order.delivery_address or "No address"
            
            orders_data.append({
                "id": order.id,
                "name": customer_name,
                "address": delivery_address,
                "date": order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "total_amount": float(order.total_price or 0),
                "status": order.status,
                "customer_email": order.user.email if order.user else None,
                "customer_phone": getattr(order.user, 'phone', None) if order.user else None,
                "payment_confirmed": order.payment_confirmed,
                "user_receipt_confirmed": order.user_receipt_confirmed,
                "delivered_at": order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else None,
                "order_placed_at": order.order_placed_at.strftime('%Y-%m-%d %H:%M:%S') if order.order_placed_at else None
            })
        
        # Prepare response
        response_data = {
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "page_size": page_size,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "results": orders_data,
            "filters_applied": {
                "search": search,
                "status": status,
                "start_date": start_date,
                "end_date": end_date,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        return Response(response_data)


class VendorOrderDetailView(APIView):
    """
    API endpoint for vendors to view detailed information about a specific order.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        user = request.user
        
        # Check if user has a vendor profile
        if not hasattr(user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access orders."},
                status=403
            )
        
        vendor = user.vendor_profile
        
        try:
            order = Order.objects.select_related('user', 'vendor').get(id=order_id, vendor=vendor)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found or you don't have permission to view this order."},
                status=404
            )
        
        # Get customer name
        customer_name = order.user.get_full_name() if order.user else "Unknown Customer"
        if not customer_name.strip():
            customer_name = order.user.email if order.user else "Unknown Customer"
        
        # Serialize order details
        order_data = {
            "id": order.id,
            "customer": {
                "id": order.user.id if order.user else None,
                "name": customer_name,
                "email": order.user.email if order.user else None,
                "phone": getattr(order.user, 'phone', None) if order.user else None
            },
            "vendor": {
                "id": order.vendor.id,
                "name": order.vendor.business_name,
                "address": order.vendor.business_address
            },
            "order_details": {
                "total_amount": float(order.total_price or 0),
                "status": order.status,
                "payment_confirmed": order.payment_confirmed,
                "user_receipt_confirmed": order.user_receipt_confirmed,
                "delivery_address": order.delivery_address,
                "delivery_date": order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
                "order_name": order.order_name
            },
            "timestamps": {
                "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "order_placed_at": order.order_placed_at.strftime('%Y-%m-%d %H:%M:%S') if order.order_placed_at else None,
                "delivered_at": order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else None
            },
            "items": []  # You can add order items here if needed
        }
        
        return Response(order_data)


