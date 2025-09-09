"""
Courier Dashboard API endpoints.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Sum, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from ...models import Order


def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)

class CourierDashboardView(APIView):
    """
    API view for courier dashboard statistics.
    Returns total deliveries, total earnings, and average delivery time.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated courier
        courier = request.user
        
        if not hasattr(courier, 'courier_profile'):
            return Response(
                {"error": "User is not a courier"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate time periods
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        
        # Previous periods for trend analysis
        yesterday = today - timedelta(days=1)
        last_week_start = start_of_week - timedelta(weeks=1)
        last_week_end = start_of_week - timedelta(days=1)
        last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        last_month_end = start_of_month - timedelta(days=1)
        
        # Base queryset for delivered and completed orders
        delivered_orders = Order.objects.filter(
            courier=courier,
            status__in=['delivered', 'completed'],
            delivered_at__isnull=False
        )
        
        # Total deliveries
        total_deliveries = delivered_orders.count()
        
        # Weekly deliveries
        weekly_deliveries = delivered_orders.filter(
            delivered_at__date__gte=start_of_week
        ).count()
        
        # Monthly deliveries
        monthly_deliveries = delivered_orders.filter(
            delivered_at__date__gte=start_of_month
        ).count()
        
        # Calculate earnings (assuming delivery fee is stored in the order)
        # Adjust the field name according to your model
        total_earnings = delivered_orders.aggregate(
            total_earnings=Sum('delivery_fee')
        )['total_earnings'] or 0
        
        # Calculate average delivery time in minutes
        # Only consider orders with both order_ready_at and delivered_at timestamps
        avg_delivery_time = delivered_orders.exclude(
            order_ready_at__isnull=True
        ).annotate(
            delivery_time=ExpressionWrapper(
                F('delivered_at') - F('order_ready_at'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_delivery_time=Avg('delivery_time')
        )['avg_delivery_time']
        
        # Convert timedelta to minutes if not None
        avg_delivery_minutes = round(avg_delivery_time.total_seconds() / 60) if avg_delivery_time else 0
        
        # Get metrics for current and previous periods
        today_metrics = self._get_metrics_for_period(courier, today, today + timedelta(days=1))
        yesterday_metrics = self._get_metrics_for_period(courier, yesterday, today)
        
        this_week_metrics = self._get_metrics_for_period(courier, start_of_week, today + timedelta(days=1))
        last_week_metrics = self._get_metrics_for_period(courier, last_week_start, last_week_end + timedelta(days=1))
        
        this_month_metrics = self._get_metrics_for_period(courier, start_of_month, today + timedelta(days=1))
        last_month_metrics = self._get_metrics_for_period(courier, last_month_start, last_month_end + timedelta(days=1))
        
        # Calculate trends
        today_trend = {
            'deliveries': calculate_percentage_change(today_metrics['deliveries'], yesterday_metrics['deliveries']),
            'earnings': calculate_percentage_change(today_metrics['earnings'], yesterday_metrics['earnings']),
            'average_delivery_time': calculate_percentage_change(
                yesterday_metrics['average_delivery_time_minutes'],
                today_metrics['average_delivery_time_minutes']
            )
        }
        
        weekly_trend = {
            'deliveries': calculate_percentage_change(this_week_metrics['deliveries'], last_week_metrics['deliveries']),
            'earnings': calculate_percentage_change(this_week_metrics['earnings'], last_week_metrics['earnings']),
            'average_delivery_time': calculate_percentage_change(
                last_week_metrics['average_delivery_time_minutes'],
                this_week_metrics['average_delivery_time_minutes']
            )
        }
        
        monthly_trend = {
            'deliveries': calculate_percentage_change(this_month_metrics['deliveries'], last_month_metrics['deliveries']),
            'earnings': calculate_percentage_change(this_month_metrics['earnings'], last_month_metrics['earnings']),
            'average_delivery_time': calculate_percentage_change(
                last_month_metrics['average_delivery_time_minutes'],
                this_month_metrics['average_delivery_time_minutes']
            )
        }
        
        # Response data
        data = {
            'total_deliveries': total_deliveries,
            'weekly_deliveries': weekly_deliveries,
            'monthly_deliveries': monthly_deliveries,
            'total_earnings': float(total_earnings),
            'average_delivery_time_minutes': avg_delivery_minutes,
            'trends': {
                'daily': today_trend,
                'weekly': weekly_trend,
                'monthly': monthly_trend
            },
            'metrics': {
                'today': today_metrics,
                'this_week': this_week_metrics,
                'this_month': this_month_metrics,
                'yesterday': yesterday_metrics,
                'last_week': last_week_metrics,
                'last_month': last_month_metrics
            }
        }
        
        return Response(data)
    
    def _get_metrics_for_period(self, courier, start_date, end_date):
        """Helper method to get metrics for a specific time period."""
        orders = Order.objects.filter(
            courier=courier,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(start_date, end_date)
        )
        
        total_earnings = orders.aggregate(
            total=Sum('delivery_fee')
        )['total'] or 0
        
        avg_delivery = orders.exclude(
            order_ready_at__isnull=True,
            delivered_at__isnull=True
        ).annotate(
            delivery_time=ExpressionWrapper(
                F('delivered_at') - F('order_ready_at'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_delivery=Avg('delivery_time')
        )['avg_delivery']
        
        avg_delivery_minutes = round(avg_delivery.total_seconds() / 60) if avg_delivery else 0
        
        # Calculate delivery success rate
        total_attempted_orders = Order.objects.filter(
            courier=courier,
            status__in=['delivered', 'completed', 'cancelled'],
            created_at__date__range=(start_date, end_date)
        ).count()
        
        success_rate = 0
        if total_attempted_orders > 0:
            success_rate = round((orders.count() / total_attempted_orders) * 100, 1)
        
        return {
            'deliveries': orders.count(),
            'earnings': float(total_earnings),
            'average_delivery_time_minutes': avg_delivery_minutes,
            'success_rate': success_rate,
            'total_attempted_orders': total_attempted_orders,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
