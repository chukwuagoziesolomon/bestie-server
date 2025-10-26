from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

from ..models import Order, VendorProfile
from ..serializers.order_serializers import OrderSerializer


class VendorTransactionPagination(PageNumberPagination):
    """Custom pagination for vendor transaction history."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class VendorTransactionHistoryView(generics.ListAPIView):
    """
    Get transaction history for a vendor with filtering and pagination.
    Shows orders, earnings, and payment information.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = VendorTransactionPagination
    
    def get_queryset(self):
        """Get orders/transactions for the authenticated vendor."""
        if not hasattr(self.request.user, 'vendor_profile'):
            return Order.objects.none()
        
        vendor = self.request.user.vendor_profile
        queryset = Order.objects.filter(vendor=vendor).order_by('-created_at')
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        # Payment status filtering
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            if payment_status == 'confirmed':
                queryset = queryset.filter(payment_confirmed=True)
            elif payment_status == 'pending':
                queryset = queryset.filter(payment_confirmed=False)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(user__email__icontains=search) |
                Q(delivery_address__icontains=search)
            )
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_transaction_summary(request):
    """
    Get transaction summary and statistics for a vendor.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get date range from query params (default to last 30 days)
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Base queryset for the date range
    base_queryset = Order.objects.filter(
        vendor=vendor,
        created_at__date__range=[start_date, end_date]
    )
    
    # Calculate summary statistics
    total_orders = base_queryset.count()
    total_revenue = base_queryset.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    # Calculate commission (assuming 10% commission rate)
    commission_rate = 0.10
    total_commission = total_revenue * commission_rate
    net_earnings = total_revenue - total_commission
    
    # Status breakdown
    status_breakdown = base_queryset.values('status').annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('status')
    
    # Payment status breakdown
    payment_breakdown = base_queryset.values('payment_confirmed').annotate(
        count=Count('id'),
        amount=Sum('total_price')
    ).order_by('payment_confirmed')
    
    # Daily revenue for the period
    daily_revenue = base_queryset.extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        orders=Count('id'),
        revenue=Sum('total_price')
    ).order_by('day')
    
    # Average order value
    avg_order_value = base_queryset.aggregate(
        avg=Avg('total_price')
    )['avg'] or 0
    
    # Top customers by order count
    top_customers = base_queryset.values(
        'user__email', 'user__first_name', 'user__last_name'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total_price')
    ).order_by('-order_count')[:5]
    
    return Response({
        'summary': {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'commission_rate': commission_rate,
            'total_commission': float(total_commission),
            'net_earnings': float(net_earnings),
            'average_order_value': float(avg_order_value)
        },
        'status_breakdown': list(status_breakdown),
        'payment_breakdown': list(payment_breakdown),
        'daily_revenue': list(daily_revenue),
        'top_customers': list(top_customers)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_earnings_breakdown(request):
    """
    Get detailed earnings breakdown for a vendor by different time periods.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    period = request.query_params.get('period', 'monthly')  # daily, weekly, monthly, yearly
    
    # Get date range
    end_date = timezone.now().date()
    if period == 'daily':
        start_date = end_date - timedelta(days=30)
        trunc_func = TruncDate('created_at')
    elif period == 'weekly':
        start_date = end_date - timedelta(weeks=12)
        trunc_func = TruncDate('created_at')
    elif period == 'monthly':
        start_date = end_date - timedelta(days=365)
        trunc_func = TruncMonth('created_at')
    elif period == 'yearly':
        start_date = end_date - timedelta(days=365*3)
        trunc_func = TruncYear('created_at')
    else:
        return Response({
            'error': 'Invalid period. Use: daily, weekly, monthly, or yearly'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get earnings data
    earnings_data = Order.objects.filter(
        vendor=vendor,
        created_at__date__range=[start_date, end_date],
        status__in=['completed', 'delivered']  # Only completed orders
    ).annotate(
        period=trunc_func
    ).values('period').annotate(
        orders=Count('id'),
        revenue=Sum('total_price'),
        commission=Sum('commission')  # Assuming commission field exists
    ).order_by('period')
    
    # Calculate totals
    total_revenue = sum(item['revenue'] or 0 for item in earnings_data)
    total_commission = sum(item['commission'] or 0 for item in earnings_data)
    total_orders = sum(item['orders'] for item in earnings_data)
    
    # Calculate percentage changes
    earnings_with_changes = []
    for i, item in enumerate(earnings_data):
        percentage_change = 0
        if i > 0:
            prev_revenue = earnings_data[i-1]['revenue'] or 0
            current_revenue = item['revenue'] or 0
            if prev_revenue > 0:
                percentage_change = ((current_revenue - prev_revenue) / prev_revenue) * 100
        
        earnings_with_changes.append({
            'period': item['period'].isoformat() if item['period'] else None,
            'orders': item['orders'],
            'revenue': float(item['revenue'] or 0),
            'commission': float(item['commission'] or 0),
            'net_earnings': float((item['revenue'] or 0) - (item['commission'] or 0)),
            'percentage_change': round(percentage_change, 2)
        })
    
    return Response({
        'period': period,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'totals': {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'total_commission': float(total_commission),
            'total_net_earnings': float(total_revenue - total_commission)
        },
        'earnings_data': earnings_with_changes
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_payment_history(request):
    """
    Get payment history for a vendor including pending and completed payments.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get payment status breakdown
    payment_status = Order.objects.filter(vendor=vendor).values(
        'payment_confirmed'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('total_price')
    ).order_by('payment_confirmed')
    
    # Get recent payments
    recent_payments = Order.objects.filter(
        vendor=vendor,
        payment_confirmed=True
    ).order_by('-created_at')[:10]
    
    # Calculate pending payments
    pending_payments = Order.objects.filter(
        vendor=vendor,
        payment_confirmed=False
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('total_price')
    )
    
    # Calculate completed payments this month
    current_month = timezone.now().replace(day=1)
    monthly_completed = Order.objects.filter(
        vendor=vendor,
        payment_confirmed=True,
        created_at__gte=current_month
    ).aggregate(
        count=Count('id'),
        total_amount=Sum('total_price')
    )
    
    # Serialize recent payments
    recent_payments_data = []
    for payment in recent_payments:
        recent_payments_data.append({
            'order_id': payment.id,
            'amount': float(payment.total_price),
            'customer_email': payment.user.email,
            'payment_date': payment.created_at.isoformat(),
            'status': payment.status
        })
    
    return Response({
        'payment_status_breakdown': list(payment_status),
        'pending_payments': {
            'count': pending_payments['count'] or 0,
            'total_amount': float(pending_payments['total_amount'] or 0)
        },
        'monthly_completed': {
            'count': monthly_completed['count'] or 0,
            'total_amount': float(monthly_completed['total_amount'] or 0)
        },
        'recent_payments': recent_payments_data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_transaction_analytics(request):
    """
    Get analytics and insights for vendor transactions.
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get current month data
    current_month = timezone.now().replace(day=1)
    current_month_orders = Order.objects.filter(
        vendor=vendor,
        created_at__gte=current_month
    )
    
    # Get previous month data for comparison
    prev_month = (current_month - timedelta(days=1)).replace(day=1)
    prev_month_orders = Order.objects.filter(
        vendor=vendor,
        created_at__gte=prev_month,
        created_at__lt=current_month
    )
    
    # Current month stats
    current_stats = current_month_orders.aggregate(
        orders=Count('id'),
        revenue=Sum('total_price'),
        avg_order_value=Avg('total_price')
    )
    
    # Previous month stats
    prev_stats = prev_month_orders.aggregate(
        orders=Count('id'),
        revenue=Sum('total_price'),
        avg_order_value=Avg('total_price')
    )
    
    # Calculate growth percentages
    orders_growth = 0
    revenue_growth = 0
    avg_order_growth = 0
    
    if prev_stats['orders'] and prev_stats['orders'] > 0:
        orders_growth = ((current_stats['orders'] or 0) - prev_stats['orders']) / prev_stats['orders'] * 100
    
    if prev_stats['revenue'] and prev_stats['revenue'] > 0:
        revenue_growth = ((current_stats['revenue'] or 0) - prev_stats['revenue']) / prev_stats['revenue'] * 100
    
    if prev_stats['avg_order_value'] and prev_stats['avg_order_value'] > 0:
        avg_order_growth = ((current_stats['avg_order_value'] or 0) - prev_stats['avg_order_value']) / prev_stats['avg_order_value'] * 100
    
    # Get top performing days of the week from orders
    current_month_start = timezone.now().replace(day=1)
    day_performance = Order.objects.filter(
        vendor=vendor,
        created_at__gte=current_month_start
    ).extra(
        select={'day_of_week': 'WEEKDAY(created_at)'}
    ).values('day_of_week').annotate(
        orders=Count('id'),
        revenue=Sum('total_price')
    ).order_by('-revenue')
    
    # Map day numbers to names
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_performance_data = []
    for item in day_performance:
        day_num = int(item['day_of_week'])
        if 0 <= day_num <= 6:
            day_performance_data.append({
                'day': day_names[day_num],
                'orders': item['orders'] or 0,
                'revenue': float(item['revenue'] or 0)
            })
    
    return Response({
        'current_month': {
            'orders': current_stats['orders'] or 0,
            'revenue': float(current_stats['revenue'] or 0),
            'avg_order_value': float(current_stats['avg_order_value'] or 0)
        },
        'previous_month': {
            'orders': prev_stats['orders'] or 0,
            'revenue': float(prev_stats['revenue'] or 0),
            'avg_order_value': float(prev_stats['avg_order_value'] or 0)
        },
        'growth': {
            'orders_growth': round(orders_growth, 2),
            'revenue_growth': round(revenue_growth, 2),
            'avg_order_growth': round(avg_order_growth, 2)
        },
        'day_performance': day_performance_data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_order_activity(request):
    """
    Get order activity data for donut chart
    Returns completed vs rejected orders with total count
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get time period (default to current week)
    period = request.query_params.get('period', 'week')
    
    # Calculate date range based on period
    now = timezone.now()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)  # Default to week
    
    # Get orders for the period
    orders = Order.objects.filter(
        vendor=vendor,
        created_at__gte=start_date
    )
    
    # Calculate order status breakdown
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    rejected_orders = orders.filter(status='rejected').count()
    other_orders = total_orders - completed_orders - rejected_orders
    
    # Calculate percentages
    completed_percentage = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    rejected_percentage = (rejected_orders / total_orders * 100) if total_orders > 0 else 0
    other_percentage = (other_orders / total_orders * 100) if total_orders > 0 else 0
    
    return Response({
        'period': period,
        'total_orders': total_orders,
        'breakdown': {
            'completed': {
                'count': completed_orders,
                'percentage': round(completed_percentage, 1)
            },
            'rejected': {
                'count': rejected_orders,
                'percentage': round(rejected_percentage, 1)
            },
            'other': {
                'count': other_orders,
                'percentage': round(other_percentage, 1)
            }
        },
        'chart_data': [
            {
                'label': 'Completed',
                'value': completed_orders,
                'color': '#10B981'  # Green
            },
            {
                'label': 'Rejected',
                'value': rejected_orders,
                'color': '#EF4444'  # Red
            },
            {
                'label': 'Other',
                'value': other_orders,
                'color': '#6B7280'  # Grey
            }
        ]
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_top_dishes(request):
    """
    Get top dishes for vendor dashboard
    Returns popular dishes with prices, order counts, and percentage changes
    """
    if not hasattr(request.user, 'vendor_profile'):
        return Response({
            'error': 'User does not have a vendor profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    vendor = request.user.vendor_profile
    
    # Get time period (default to current week)
    period = request.query_params.get('period', 'week')
    limit = int(request.query_params.get('limit', 5))
    
    # Calculate date range based on period
    now = timezone.now()
    if period == 'week':
        start_date = now - timedelta(days=7)
        prev_start_date = now - timedelta(days=14)
        prev_end_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
        prev_start_date = now - timedelta(days=60)
        prev_end_date = now - timedelta(days=30)
    elif period == 'year':
        start_date = now - timedelta(days=365)
        prev_start_date = now - timedelta(days=730)
        prev_end_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)  # Default to week
        prev_start_date = now - timedelta(days=14)
        prev_end_date = now - timedelta(days=7)
    
    # Get current period orders
    current_orders = Order.objects.filter(
        vendor=vendor,
        created_at__gte=start_date
    )
    
    # Get previous period orders for comparison
    prev_orders = Order.objects.filter(
        vendor=vendor,
        created_at__gte=prev_start_date,
        created_at__lt=prev_end_date
    )
    
    # Get menu items with order counts for current period
    from ..models import MenuItem
    current_dish_stats = MenuItem.objects.filter(
        vendor=vendor,
        order__in=current_orders
    ).annotate(
        order_count=Count('order'),
        total_revenue=Sum('order__total_price')
    ).order_by('-order_count')[:limit]
    
    # Get menu items with order counts for previous period
    prev_dish_stats = MenuItem.objects.filter(
        vendor=vendor,
        order__in=prev_orders
    ).annotate(
        order_count=Count('order')
    )
    
    # Create a dictionary for previous period data
    prev_stats_dict = {item.id: item.order_count for item in prev_dish_stats}
    
    # Build response data
    top_dishes = []
    for dish in current_dish_stats:
        current_count = dish.order_count
        prev_count = prev_stats_dict.get(dish.id, 0)
        
        # Calculate percentage change
        if prev_count > 0:
            percentage_change = ((current_count - prev_count) / prev_count) * 100
        else:
            percentage_change = 100 if current_count > 0 else 0
        
        top_dishes.append({
            'id': dish.id,
            'name': dish.dish_name,
            'price': float(dish.price),
            'order_count': current_count,
            'percentage_change': round(percentage_change, 1),
            'trend': 'up' if percentage_change > 0 else 'down' if percentage_change < 0 else 'stable',
            'image': dish.image.url if dish.image else None
        })
    
    return Response({
        'period': period,
        'top_dishes': top_dishes
    }, status=status.HTTP_200_OK)


