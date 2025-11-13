from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta, date
from decimal import Decimal
import logging

from bestyy.restaurant_features.order.models import Order

# Set up logging
logger = logging.getLogger(__name__)

class CourierDeliveryActivityView(APIView):
    """
    API endpoint for courier delivery activity tracking with pie chart data.
    
    Query Parameters:
    - period: Time period filter ('today', 'week', 'month', 'year', 'custom')
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - include_graph: Whether to include graph data (default: true)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated courier
        if not hasattr(request.user, 'courier_profile'):
            return Response(
                {'error': 'User does not have a courier profile. Only couriers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        courier = request.user.courier_profile
        
        # Get query parameters
        period = request.query_params.get('period', 'week')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        include_graph = request.query_params.get('include_graph', 'true').lower() == 'true'
        
        # Calculate date range based on period
        today = timezone.now().date()
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif period == 'custom' and start_date and end_date:
            try:
                start_date = date.fromisoformat(start_date)
                end_date = date.fromisoformat(end_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Default to current week
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        
        # Get delivery statistics
        delivery_stats = self._get_delivery_statistics(courier, start_date, end_date)
        
        # Prepare response data
        response_data = {
            'summary': {
                'total_deliveries': delivery_stats['total_deliveries'],
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'period_type': period
                }
            },
            'delivery_breakdown': delivery_stats['breakdown'],
            'activity_metrics': delivery_stats['metrics']
        }
        
        # Include graph data if requested
        if include_graph:
            response_data['graph_data'] = self._prepare_graph_data(delivery_stats)
        
        return Response(response_data)
    
    def _get_delivery_statistics(self, courier, start_date, end_date):
        """Get comprehensive delivery statistics for the courier."""
        # Get all orders for the courier in the date range
        orders = Order.objects.filter(
            courier=courier,
            created_at__date__range=(start_date, end_date)
        )
        
        # Count orders by status
        status_counts = orders.values('status').annotate(count=Count('id'))
        
        # Initialize counters
        completed_count = 0
        rejected_count = 0
        pending_count = 0
        in_progress_count = 0
        cancelled_count = 0
        failed_count = 0
        
        # Count by status
        for status_item in status_counts:
            status = status_item['status']
            count = status_item['count']
            
            if status in ['delivered', 'completed']:
                completed_count += count
            elif status == 'rejected':
                rejected_count += count
            elif status == 'pending':
                pending_count += count
            elif status in ['out_for_delivery', 'picked_up']:
                in_progress_count += count
            elif status == 'cancelled':
                cancelled_count += count
            elif status == 'failed':
                failed_count += count
        
        total_deliveries = orders.count()
        
        # Calculate percentages
        completed_percentage = round((completed_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        rejected_percentage = round((rejected_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        pending_percentage = round((pending_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        in_progress_percentage = round((in_progress_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        
        # Prepare breakdown data (matching the UI legend)
        breakdown = [
            {
                'status': 'completed',
                'label': 'Completed',
                'count': completed_count,
                'percentage': completed_percentage,
                'color': '#4CAF50',  # Green for completed
                'icon': 'check-circle'
            },
            {
                'status': 'rejected',
                'label': 'Rejected',
                'count': rejected_count,
                'percentage': rejected_percentage,
                'color': '#F44336',  # Red for rejected
                'icon': 'x-circle'
            }
        ]
        
        # Add other statuses if they exist
        if pending_count > 0:
            breakdown.append({
                'status': 'pending',
                'label': 'Pending',
                'count': pending_count,
                'percentage': pending_percentage,
                'color': '#FF9800',  # Orange for pending
                'icon': 'clock'
            })
        
        if in_progress_count > 0:
            breakdown.append({
                'status': 'in_progress',
                'label': 'In Progress',
                'count': in_progress_count,
                'percentage': in_progress_percentage,
                'color': '#2196F3',  # Blue for in progress
                'icon': 'truck'
            })
        
        if cancelled_count > 0:
            breakdown.append({
                'status': 'cancelled',
                'label': 'Cancelled',
                'count': cancelled_count,
                'percentage': round((cancelled_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0,
                'color': '#9E9E9E',  # Gray for cancelled
                'icon': 'ban'
            })
        
        if failed_count > 0:
            breakdown.append({
                'status': 'failed',
                'label': 'Failed',
                'count': failed_count,
                'percentage': round((failed_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0,
                'color': '#D32F2F',  # Dark red for failed
                'icon': 'alert-triangle'
            })
        
        # Calculate additional metrics
        success_rate = round((completed_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        rejection_rate = round((rejected_count / total_deliveries * 100), 1) if total_deliveries > 0 else 0
        
        # Get earnings for completed deliveries
        completed_orders = orders.filter(status__in=['delivered', 'completed'])
        total_earnings = completed_orders.aggregate(
            total=Sum('commission')
        )['total'] or Decimal('0.00')
        
        # Calculate average delivery time for completed orders
        delivery_times = []
        for order in completed_orders:
            if order.delivered_at and order.order_placed_at:
                delivery_time = (order.delivered_at - order.order_placed_at).total_seconds() / 60
                delivery_times.append(delivery_time)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        metrics = {
            'success_rate': success_rate,
            'rejection_rate': rejection_rate,
            'total_earnings': float(total_earnings),
            'average_delivery_time_minutes': round(avg_delivery_time, 1),
            'total_completed': completed_count,
            'total_rejected': rejected_count,
            'total_pending': pending_count,
            'total_in_progress': in_progress_count
        }
        
        return {
            'total_deliveries': total_deliveries,
            'breakdown': breakdown,
            'metrics': metrics
        }
    
    def _prepare_graph_data(self, delivery_stats):
        """Prepare graph data for the delivery activity pie chart."""
        breakdown = delivery_stats['breakdown']
        
        # Prepare pie chart data (matching the UI donut chart)
        pie_chart_data = {
            'labels': [item['label'] for item in breakdown],
            'datasets': [
                {
                    'data': [item['count'] for item in breakdown],
                    'backgroundColor': [item['color'] for item in breakdown],
                    'borderColor': '#ffffff',
                    'borderWidth': 2,
                    'hoverBorderWidth': 3
                }
            ]
        }
        
        # Prepare donut chart data (alternative to pie chart)
        donut_chart_data = {
            'labels': [item['label'] for item in breakdown],
            'datasets': [
                {
                    'data': [item['count'] for item in breakdown],
                    'backgroundColor': [item['color'] for item in breakdown],
                    'borderColor': '#ffffff',
                    'borderWidth': 3,
                    'cutout': '60%'  # Creates donut effect
                }
            ]
        }
        
        # Prepare bar chart for comparison
        bar_chart_data = {
            'labels': [item['label'] for item in breakdown],
            'datasets': [
                {
                    'label': 'Number of Deliveries',
                    'data': [item['count'] for item in breakdown],
                    'backgroundColor': [item['color'] for item in breakdown],
                    'borderColor': [item['color'] for item in breakdown],
                    'borderWidth': 1
                }
            ]
        }
        
        # Chart options for better visualization
        chart_options = {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'position': 'bottom',
                    'labels': {
                        'padding': 20,
                        'usePointStyle': True,
                        'pointStyle': 'circle'
                    }
                },
                'tooltip': {
                    'callbacks': {
                        'label': 'function(context) { return context.label + ": " + context.parsed + " deliveries"; }'
                    }
                }
            }
        }
        
        return {
            'pie_chart': pie_chart_data,
            'donut_chart': donut_chart_data,
            'bar_chart': bar_chart_data,
            'chart_options': chart_options,
            'color_scheme': {
                item['status']: item['color'] for item in breakdown
            }
        }


class CourierDeliveryTrendsView(APIView):
    """
    API endpoint for courier delivery trends over time.
    
    Query Parameters:
    - period: Time period filter ('week', 'month', 'year')
    - metric: Metric to track ('deliveries', 'earnings', 'success_rate')
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated courier
        if not hasattr(request.user, 'courier_profile'):
            return Response(
                {'error': 'User does not have a courier profile. Only couriers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        courier = request.user.courier_profile
        
        # Get query parameters
        period = request.query_params.get('period', 'week')
        metric = request.query_params.get('metric', 'deliveries')
        
        # Calculate date range
        today = timezone.now().date()
        if period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = today - timedelta(days=7)
            end_date = today
        
        # Get trend data
        trend_data = self._get_trend_data(courier, start_date, end_date, metric)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period_type': period
            },
            'metric': metric,
            'trend_data': trend_data
        })
    
    def _get_trend_data(self, courier, start_date, end_date, metric):
        """Get trend data for the specified metric."""
        current_date = start_date
        trend_points = []
        
        while current_date <= end_date:
            # Get orders for this specific date
            daily_orders = Order.objects.filter(
                courier=courier,
                created_at__date=current_date
            )
            
            if metric == 'deliveries':
                value = daily_orders.count()
            elif metric == 'earnings':
                completed_orders = daily_orders.filter(status__in=['delivered', 'completed'])
                value = float(completed_orders.aggregate(
                    total=Sum('commission')
                )['total'] or 0)
            elif metric == 'success_rate':
                total_orders = daily_orders.count()
                completed_orders = daily_orders.filter(status__in=['delivered', 'completed'])
                value = round((completed_orders.count() / total_orders * 100), 1) if total_orders > 0 else 0
            else:
                value = 0
            
            trend_points.append({
                'date': current_date.isoformat(),
                'value': value,
                'day': current_date.strftime('%A')[:3]  # Short day name
            })
            
            current_date += timedelta(days=1)
        
        return trend_points
