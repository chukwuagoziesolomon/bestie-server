"""
Admin API views for revenue analytics and tracking.
These endpoints provide detailed revenue data for admin dashboard graphs.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Q, Count, Sum, F, Avg
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from user.permissions import IsAdminUser
from user.models import Order, Payment
from order.models import Order as OrderModel

logger = logging.getLogger(__name__)


class AdminRevenueAnalyticsView(APIView):
    """
    API endpoint that provides comprehensive revenue analytics for admin dashboard.
    Returns data suitable for revenue graphs and charts.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `period` (string, optional): Time period for analytics. 
      Options: 'today', 'week', 'month', 'quarter', 'year', 'custom'. Default: 'month'
    - `start_date` (date, optional): Start date for custom period (YYYY-MM-DD)
    - `end_date` (date, optional): End date for custom period (YYYY-MM-DD)
    - `granularity` (string, optional): Data granularity for time series.
      Options: 'hour', 'day', 'week', 'month'. Default: 'day'
    - `currency` (string, optional): Currency for revenue data. Default: 'NGN'
    
    ## Response Format
    ```json
    {
        "summary": {
            "total_revenue": 128700.00,
            "total_orders": 1250,
            "average_order_value": 102.96,
            "growth_percentage": 3.4,
            "previous_period_revenue": 124500.00
        },
        "time_series": [
            {
                "date": "2025-07-29T00:00:00Z",
                "revenue": 220342.76,
                "orders": 45,
                "average_order_value": 4896.51
            }
        ],
        "breakdown": {
            "by_status": {
                "completed": 125000.00,
                "pending": 2500.00,
                "cancelled": 1200.00
            },
            "by_payment_method": {
                "card": 85000.00,
                "bank_transfer": 43700.00
            },
            "top_vendors": [
                {
                    "id": 1,
                    "business_name": "Tasty Bites",
                    "revenue": 25000.00,
                    "orders": 150,
                    "percentage": 19.4
                }
            ]
        },
        "period": {
            "start_date": "2025-07-01T00:00:00Z",
            "end_date": "2025-07-31T23:59:59Z",
            "granularity": "day"
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            # Get query parameters
            period = request.query_params.get('period', 'month')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            granularity = request.query_params.get('granularity', 'day')
            currency = request.query_params.get('currency', 'NGN')
            
            # Calculate date range
            date_range = self._calculate_date_range(period, start_date, end_date)
            
            # Get revenue data
            revenue_data = self._get_revenue_data(date_range, granularity)
            
            # Get summary statistics
            summary = self._get_summary_stats(date_range)
            
            # Get breakdown data
            breakdown = self._get_breakdown_data(date_range)
            
            # Format response
            response_data = {
                'summary': summary,
                'time_series': revenue_data['time_series'],
                'breakdown': breakdown,
                'period': {
                    'start_date': date_range['start'].isoformat(),
                    'end_date': date_range['end'].isoformat(),
                    'granularity': granularity
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in AdminRevenueAnalyticsView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch revenue analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_date_range(self, period, start_date, end_date):
        """Calculate the date range based on period or custom dates."""
        now = timezone.now()
        
        if period == 'custom' and start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                return {
                    'start': timezone.make_aware(datetime.combine(start, datetime.min.time())),
                    'end': timezone.make_aware(datetime.combine(end, datetime.max.time()))
                }
            except ValueError:
                pass
        
        # Default periods
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'week':
            start = now - timedelta(days=7)
            end = now
        elif period == 'quarter':
            start = now - timedelta(days=90)
            end = now
        elif period == 'year':
            start = now - timedelta(days=365)
            end = now
        else:  # month (default)
            start = now - timedelta(days=30)
            end = now
        
        return {'start': start, 'end': end}
    
    def _get_revenue_data(self, date_range, granularity):
        """Get time series revenue data."""
        # Use the main Order model from user app
        orders = Order.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lte=date_range['end'],
            payment_confirmed=True  # Only confirmed payments
        )
        
        # Group by time period
        if granularity == 'hour':
            time_format = '%Y-%m-%d %H:00:00'
            time_trunc = 'hour'
        elif granularity == 'week':
            time_format = '%Y-%m-%d'
            time_trunc = 'week'
        elif granularity == 'month':
            time_format = '%Y-%m-01'
            time_trunc = 'month'
        else:  # day (default)
            time_format = '%Y-%m-%d'
            time_trunc = 'day'
        
        # Aggregate data by time period
        time_series_data = []
        
        if granularity == 'day':
            # Daily aggregation
            daily_data = orders.extra(
                select={'date': "DATE(created_at)"}
            ).values('date').annotate(
                revenue=Sum('total_price'),
                orders=Count('id'),
                avg_order_value=Avg('total_price')
            ).order_by('date')
            
            for item in daily_data:
                time_series_data.append({
                    'date': f"{item['date']}T00:00:00Z",
                    'revenue': float(item['revenue'] or 0),
                    'orders': item['orders'],
                    'average_order_value': float(item['avg_order_value'] or 0)
                })
        
        elif granularity == 'hour':
            # Hourly aggregation
            hourly_data = orders.extra(
                select={'hour': "DATE_FORMAT(created_at, '%Y-%m-%d %H:00:00')"}
            ).values('hour').annotate(
                revenue=Sum('total_price'),
                orders=Count('id'),
                avg_order_value=Avg('total_price')
            ).order_by('hour')
            
            for item in hourly_data:
                time_series_data.append({
                    'date': f"{item['hour']}Z",
                    'revenue': float(item['revenue'] or 0),
                    'orders': item['orders'],
                    'average_order_value': float(item['avg_order_value'] or 0)
                })
        
        else:
            # For week/month, use a simpler approach
            current_date = date_range['start']
            while current_date <= date_range['end']:
                if granularity == 'week':
                    period_end = current_date + timedelta(days=7)
                else:  # month
                    if current_date.month == 12:
                        period_end = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        period_end = current_date.replace(month=current_date.month + 1)
                
                period_orders = orders.filter(
                    created_at__gte=current_date,
                    created_at__lt=period_end
                )
                
                revenue = period_orders.aggregate(total=Sum('total_price'))['total'] or 0
                order_count = period_orders.count()
                avg_value = float(revenue / order_count) if order_count > 0 else 0
                
                time_series_data.append({
                    'date': current_date.isoformat(),
                    'revenue': float(revenue),
                    'orders': order_count,
                    'average_order_value': avg_value
                })
                
                current_date = period_end
        
        return {'time_series': time_series_data}
    
    def _get_summary_stats(self, date_range):
        """Get summary statistics for the period."""
        # Current period data
        current_orders = Order.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lte=date_range['end'],
            payment_confirmed=True
        )
        
        total_revenue = current_orders.aggregate(total=Sum('total_price'))['total'] or 0
        total_orders = current_orders.count()
        avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0
        
        # Previous period data for growth calculation
        period_duration = date_range['end'] - date_range['start']
        prev_start = date_range['start'] - period_duration
        prev_end = date_range['start']
        
        previous_orders = Order.objects.filter(
            created_at__gte=prev_start,
            created_at__lt=prev_end,
            payment_confirmed=True
        )
        
        previous_revenue = previous_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Calculate growth percentage
        if previous_revenue > 0:
            growth_percentage = round(((float(total_revenue) - float(previous_revenue)) / float(previous_revenue)) * 100, 1)
        else:
            growth_percentage = 0.0
        
        return {
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'average_order_value': round(avg_order_value, 2),
            'growth_percentage': growth_percentage,
            'previous_period_revenue': float(previous_revenue)
        }
    
    def _get_breakdown_data(self, date_range):
        """Get breakdown data by status, payment method, and top vendors."""
        orders = Order.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lte=date_range['end'],
            payment_confirmed=True
        )
        
        # Breakdown by status
        status_breakdown = {}
        for status_choice in Order._meta.get_field('status').choices:
            status_value = status_choice[0]
            status_orders = orders.filter(status=status_value)
            status_revenue = status_orders.aggregate(total=Sum('total_price'))['total'] or 0
            status_breakdown[status_value] = float(status_revenue)
        
        # Breakdown by payment method (from Payment model)
        payment_breakdown = {}
        payments = Payment.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lte=date_range['end'],
            status='successful'
        )
        
        for method_choice in Payment.PAYMENT_METHODS:
            method_value = method_choice[0]
            method_payments = payments.filter(payment_method=method_value)
            method_revenue = method_payments.aggregate(total=Sum('amount'))['total'] or 0
            payment_breakdown[method_value] = float(method_revenue)
        
        # Top vendors
        vendor_data = orders.values(
            'vendor__id',
            'vendor__business_name'
        ).annotate(
            revenue=Sum('total_price'),
            orders=Count('id')
        ).order_by('-revenue')[:10]
        
        total_revenue = sum(item['revenue'] for item in vendor_data)
        top_vendors = []
        
        for vendor in vendor_data:
            percentage = round((float(vendor['revenue']) / float(total_revenue)) * 100, 1) if total_revenue > 0 else 0
            top_vendors.append({
                'id': vendor['vendor__id'],
                'business_name': vendor['vendor__business_name'],
                'revenue': float(vendor['revenue']),
                'orders': vendor['orders'],
                'percentage': percentage
            })
        
        return {
            'by_status': status_breakdown,
            'by_payment_method': payment_breakdown,
            'top_vendors': top_vendors
        }


class AdminRevenueChartView(APIView):
    """
    API endpoint that provides revenue data specifically formatted for charts.
    Optimized for frontend chart libraries like Chart.js, D3.js, etc.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `chart_type` (string, optional): Type of chart data needed.
      Options: 'line', 'bar', 'pie', 'area'. Default: 'line'
    - `period` (string, optional): Time period. Default: 'month'
    - `granularity` (string, optional): Data granularity. Default: 'day'
    
    ## Response Format
    ```json
    {
        "chart_type": "line",
        "labels": ["2025-07-29", "2025-07-30", "2025-07-31"],
        "datasets": [
            {
                "label": "Revenue (NGN)",
                "data": [220342.76, 185432.10, 198765.43],
                "borderColor": "#10B981",
                "backgroundColor": "rgba(16, 185, 129, 0.1)"
            }
        ],
        "options": {
            "responsive": true,
            "scales": {
                "y": {
                    "beginAtZero": true,
                    "ticks": {
                        "callback": "function(value) { return '₦' + value.toLocaleString(); }"
                    }
                }
            }
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            chart_type = request.query_params.get('chart_type', 'line')
            period = request.query_params.get('period', 'month')
            granularity = request.query_params.get('granularity', 'day')
            
            # Get base revenue data
            revenue_view = AdminRevenueAnalyticsView()
            date_range = revenue_view._calculate_date_range(period, None, None)
            revenue_data = revenue_view._get_revenue_data(date_range, granularity)
            
            # Format for chart
            chart_data = self._format_for_chart(revenue_data['time_series'], chart_type)
            
            return Response(chart_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in AdminRevenueChartView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch chart data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _format_for_chart(self, time_series_data, chart_type):
        """Format time series data for chart libraries."""
        labels = []
        revenue_data = []
        order_data = []
        
        for item in time_series_data:
            # Format date for display
            date_obj = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
            if 'T00:00:00' in item['date']:
                labels.append(date_obj.strftime('%b %d'))
            else:
                labels.append(date_obj.strftime('%b %d %H:%M'))
            
            revenue_data.append(item['revenue'])
            order_data.append(item['orders'])
        
        # Chart configuration based on type
        if chart_type == 'line':
            datasets = [
                {
                    'label': 'Revenue (₦)',
                    'data': revenue_data,
                    'borderColor': '#10B981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }
            ]
        elif chart_type == 'bar':
            datasets = [
                {
                    'label': 'Revenue (₦)',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(16, 185, 129, 0.8)',
                    'borderColor': '#10B981',
                    'borderWidth': 1
                }
            ]
        elif chart_type == 'area':
            datasets = [
                {
                    'label': 'Revenue (₦)',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(16, 185, 129, 0.3)',
                    'borderColor': '#10B981',
                    'fill': True
                }
            ]
        else:  # pie or default
            datasets = [
                {
                    'label': 'Revenue Distribution',
                    'data': revenue_data,
                    'backgroundColor': [
                        '#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6',
                        '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
                    ]
                }
            ]
        
        return {
            'chart_type': chart_type,
            'labels': labels,
            'datasets': datasets,
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'ticks': {
                            'callback': 'function(value) { return "₦" + value.toLocaleString(); }'
                        }
                    }
                },
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    },
                    'tooltip': {
                        'callbacks': {
                            'label': 'function(context) { return "₦" + context.parsed.y.toLocaleString(); }'
                        }
                    }
                }
            }
        }
