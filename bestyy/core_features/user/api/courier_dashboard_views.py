from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import numpy as np
from scipy import stats

from bestyy.core_features.user.models import CourierProfile, Order
from .serializers import DeliverySerializer

def calculate_trend_line(x_data, y_data):
    """Calculate trend line using linear regression"""
    if len(x_data) < 2:
        return None
    
    try:
        # Convert to numpy arrays
        x = np.array(range(len(x_data)))
        y = np.array(y_data)
        
        # Check for valid data (no NaN or inf values)
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            return None
        
        # Calculate linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Check for valid regression results
        if np.isnan(slope) or np.isnan(intercept) or np.isnan(r_value):
            return None
        
        # Generate trend line points
        trend_y = slope * x + intercept
        
        # Convert NumPy types to Python native types for JSON serialization
        return {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_value ** 2),
            'trend_points': [float(val) for val in trend_y.tolist()]
        }
    except Exception:
        # If any error occurs, return None
        return None

def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 0 if current == 0 else 100
    return round(((current - previous) / previous) * 100, 1)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """Main dashboard analytics endpoint"""
    user = request.user
    if not hasattr(user, 'courier_profile'):
        return Response({'error': 'Courier profile not found'}, status=404)
    
    courier = user.courier_profile
    
    # Get time period from query params (default: last 30 days)
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Current period metrics
    current_orders = Order.objects.filter(
        courier=courier,
        status__in=['delivered', 'completed'],
        delivered_at__date__gte=start_date,
        delivered_at__date__lte=end_date
    )
    
    # Previous period for comparison
    previous_start = start_date - timedelta(days=days)
    previous_end = start_date - timedelta(days=1)
    
    previous_orders = Order.objects.filter(
        courier=courier,
        status__in=['delivered', 'completed'],
        delivered_at__date__gte=previous_start,
        delivered_at__date__lte=previous_end
    )
    
    # Calculate current metrics
    total_deliveries = current_orders.count()
    total_earnings = current_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # Calculate average delivery time in minutes
    avg_delivery_time = current_orders.exclude(
        order_ready_at__isnull=True
    ).annotate(
        delivery_time=ExpressionWrapper(
            F('delivered_at') - F('order_ready_at'),
            output_field=DurationField()
        )
    ).aggregate(
        avg_time=Avg('delivery_time')
    )['avg_time']
    
    avg_delivery_minutes = round(avg_delivery_time.total_seconds() / 60) if avg_delivery_time else 0
    
    # Calculate previous metrics for comparison
    prev_total_deliveries = previous_orders.count()
    prev_total_earnings = previous_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    prev_avg_delivery_time = previous_orders.exclude(
        order_ready_at__isnull=True
    ).annotate(
        delivery_time=ExpressionWrapper(
            F('delivered_at') - F('order_ready_at'),
            output_field=DurationField()
        )
    ).aggregate(
        avg_time=Avg('delivery_time')
    )['avg_time']
    
    prev_avg_minutes = round(prev_avg_delivery_time.total_seconds() / 60) if prev_avg_delivery_time else 0
    
    # Calculate percentage changes
    delivery_change = calculate_percentage_change(total_deliveries, prev_total_deliveries)
    earnings_change = calculate_percentage_change(float(total_earnings), float(prev_total_earnings))
    time_change = calculate_percentage_change(avg_delivery_minutes, prev_avg_minutes)
    
    # Get yesterday's metrics for daily comparison
    yesterday = end_date - timedelta(days=1)
    yesterday_earnings = Order.objects.filter(
        courier=courier,
        status__in=['delivered', 'completed'],
        delivered_at__date=yesterday
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    day_before_yesterday = yesterday - timedelta(days=1)
    day_before_earnings = Order.objects.filter(
        courier=courier,
        status__in=['delivered', 'completed'],
        delivered_at__date=day_before_yesterday
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    daily_earnings_change = calculate_percentage_change(
        float(yesterday_earnings), 
        float(day_before_earnings)
    )
    
    response_data = {
        'total_deliveries': total_deliveries,
        'total_earnings': f"₦{float(total_earnings):,.0f}",
        'avg_delivery_time': f"{int(avg_delivery_minutes)}mins",
        'changes': {
            'deliveries': {
                'value': f"{delivery_change:+.1f}%",
                'type': 'up' if delivery_change > 0 else 'down',
                'period': f'from past {days} days'
            },
            'earnings': {
                'value': f"{daily_earnings_change:+.1f}%",
                'type': 'down' if daily_earnings_change < 0 else 'up',
                'period': 'from yesterday'
            },
            'delivery_time': {
                'value': f"{time_change:+.1f}%",
                'type': 'up' if time_change > 0 else 'down',
                'period': 'from yesterday'
            }
        }
    }
    
    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_chart_data(request):
    """Get earnings data for chart with trend line"""
    user = request.user
    if not hasattr(user, 'courier_profile'):
        return Response({'error': 'Courier profile not found'}, status=404)
    
    courier = user.courier_profile
    
    # Get month from query params (default: current month)
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # Get date range for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get daily stats from orders
    daily_stats = []
    current_date = start_date

    while current_date <= end_date:
        # Get orders for this day
        day_orders = Order.objects.filter(
            courier=courier,
            status__in=['delivered', 'completed'],
            delivered_at__date=current_date
        )

        total_earnings = day_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        total_deliveries = day_orders.count()

        # Calculate average delivery time
        avg_delivery_time = day_orders.exclude(
            order_ready_at__isnull=True
        ).annotate(
            delivery_time=ExpressionWrapper(
                F('delivered_at') - F('order_ready_at'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_time=Avg('delivery_time')
        )['avg_time']

        avg_time_minutes = round(avg_delivery_time.total_seconds() / 60) if avg_delivery_time else 0

        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day': current_date.day,
            'earnings': float(total_earnings),
            'deliveries': total_deliveries,
            'avg_time': avg_time_minutes
        })
        current_date += timedelta(days=1)
    
    # Prepare data for chart
    chart_data = []
    earnings_values = []
    
    for i, stat in enumerate(daily_stats):
        # Create data points every 5 days for cleaner chart
        if i % 5 == 0 or i == len(daily_stats) - 1:
            chart_data.append({
                'x': f"{stat['day']}k" if stat['day'] <= 10 else f"{stat['day']}k",
                'y': stat['earnings']
            })
        earnings_values.append(stat['earnings'])
    
    # Calculate trend line
    trend_analysis = calculate_trend_line(range(len(earnings_values)), earnings_values) if earnings_values else None
    
    # Ensure all values are Python native types for JSON serialization
    peak_earnings = float(max(earnings_values)) if earnings_values else 0.0
    peak_day = int(daily_stats[earnings_values.index(max(earnings_values))]['day']) if earnings_values else 0
    total_month_earnings = float(sum(earnings_values)) if earnings_values else 0.0
    average_daily_earnings = float(sum(earnings_values) / len(earnings_values)) if earnings_values else 0.0
    
    response_data = {
        'chart_data': chart_data,
        'trend_analysis': trend_analysis,
        'peak_earnings': peak_earnings,
        'peak_day': peak_day,
        'total_month_earnings': total_month_earnings,
        'average_daily_earnings': average_daily_earnings
    }
    
    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_deliveries(request):
    """Get recent deliveries list"""
    user = request.user
    if not hasattr(user, 'courier_profile'):
        return Response({'error': 'Courier profile not found'}, status=404)
    
    courier = user.courier_profile
    limit = int(request.GET.get('limit', 10))
    status_param = request.GET.get('status')
    
    # Build base queryset
    queryset = Order.objects.filter(courier=courier)
    
    # Apply status filter if provided
    if status_param:
        queryset = queryset.filter(status=status_param)
    
    # Get most recent deliveries
    recent_deliveries = queryset.order_by('-created_at')[:limit]
    
    # Serialize the data
    serializer = DeliverySerializer(recent_deliveries, many=True)
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_delivery_status(request, order_id):
    """Update order status and recalculate stats"""
    user = request.user
    if not hasattr(user, 'courier_profile'):
        return Response({'error': 'Courier profile not found'}, status=404)
    
    try:
        order = Order.objects.get(id=order_id, courier=user.courier_profile)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)
    
    new_status = request.data.get('status')
    valid_statuses = [choice[0] for choice in Order.OrderStatus.choices]
    
    if new_status not in valid_statuses:
        return Response({'error': 'Invalid status'}, status=400)
    
    # Update timestamps based on status
    now = timezone.now()
    if new_status == 'out_for_delivery' and not order.out_for_delivery_at:
        order.out_for_delivery_at = now
    elif new_status == 'delivered' and not order.delivered_at:
        order.delivered_at = now
    
    order.status = new_status
    order.save()
    
    # Daily stats are now calculated on-demand from orders
    
    serializer = DeliverySerializer(order)
    return Response(serializer.data)
