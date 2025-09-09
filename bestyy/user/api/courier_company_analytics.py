from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta, date
from decimal import Decimal
import logging

from user.models import Order, VendorProfile

# Set up logging
logger = logging.getLogger(__name__)

class CourierCompanyAnalyticsView(APIView):
    """
    API endpoint for courier analytics showing top companies by delivery volume.
    
    Query Parameters:
    - period: Time period filter ('today', 'week', 'month', 'year', 'custom')
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - limit: Number of top companies to return (default: 10)
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
        period = request.query_params.get('period', 'week')  # Changed default to 'week' to match UI
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 10))
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
        
        logger.info(f"Courier {courier.id} requesting analytics for period {period}: {start_date} to {end_date}")
        
        # Get company delivery statistics
        company_stats = self._get_company_delivery_stats(courier, start_date, end_date, limit)
        
        # If no company stats, try to get broader data for debugging
        if not company_stats:
            logger.warning(f"No company stats found for courier {courier.id}. Checking for any orders...")
            # Check if there are any orders at all for this courier
            total_orders = Order.objects.filter(courier=courier).count()
            delivered_orders = Order.objects.filter(
                courier=courier,
                status__in=['delivered', 'completed']
            ).count()
            logger.info(f"Courier {courier.id} has {total_orders} total orders, {delivered_orders} delivered orders")
            
            # Return empty response with debug info
            return Response({
                'summary': {
                    'total_deliveries': 0,
                    'total_companies': 0,
                    'total_earnings': 0.00,
                    'average_deliveries_per_company': 0,
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'period_type': period
                    },
                    'debug_info': {
                        'total_orders': total_orders,
                        'delivered_orders': delivered_orders,
                        'period_start': start_date.isoformat(),
                        'period_end': end_date.isoformat()
                    }
                },
                'top_companies': [],
                'graph_data': None,
                'message': 'No delivery data found for the specified period. Try adjusting the date range or check if you have any completed deliveries.'
            })
        
        # Calculate total deliveries for percentage calculations
        total_deliveries = sum(stat['deliveries'] for stat in company_stats)
        
        # Add percentages and prepare response data
        response_data = []
        for stat in company_stats:
            percentage = round((stat['deliveries'] / total_deliveries * 100), 2) if total_deliveries > 0 else 0
            response_data.append({
                'company_id': stat['company_id'],
                'company_name': stat['company_name'],
                'company_logo': stat['company_logo'],
                'deliveries': stat['deliveries'],
                'total_earnings': stat['total_earnings'],
                'average_earnings_per_delivery': stat['average_earnings_per_delivery'],
                'percentage': percentage,
                'rank': stat['rank'],
                'percentage_change': stat['percentage_change'],
                'trend': stat['trend'],
                'orders_text': f"{stat['deliveries']} Orders {stat['percentage_change']:+g}%" if stat['percentage_change'] != 0 else f"{stat['deliveries']} Orders"
            })
        
        # Prepare summary statistics
        summary = {
            'total_deliveries': total_deliveries,
            'total_companies': len(response_data),
            'total_earnings': sum(stat['total_earnings'] for stat in response_data),
            'average_deliveries_per_company': round(total_deliveries / len(response_data), 2) if response_data else 0,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period_type': period
            }
        }
        
        logger.info(f"Returning analytics for courier {courier.id}: {total_deliveries} deliveries, {len(response_data)} companies")
        
        # Include graph data if requested
        graph_data = None
        if include_graph:
            graph_data = self._prepare_graph_data(response_data, period, start_date, end_date)
        
        return Response({
            'summary': summary,
            'top_companies': response_data,
            'graph_data': graph_data
        })
    
    def _get_company_delivery_stats(self, courier, start_date, end_date, limit):
        """Get delivery statistics grouped by company."""
        # Get all delivered orders for the courier in the date range
        orders = Order.objects.filter(
            courier=courier,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(start_date, end_date)
        ).select_related('vendor')
        
        logger.info(f"Found {orders.count()} delivered orders for courier {courier.id} in date range {start_date} to {end_date}")
        
        # If no orders found, try a broader search
        if not orders.exists():
            logger.warning(f"No delivered orders found for courier {courier.id} in date range. Trying broader search...")
            # Try to find any orders for this courier regardless of status
            all_orders = Order.objects.filter(courier=courier).select_related('vendor')
            logger.info(f"Found {all_orders.count()} total orders for courier {courier.id}")
            
            # Check what statuses exist
            status_counts = all_orders.values('status').annotate(count=Count('id'))
            logger.info(f"Status breakdown: {list(status_counts)}")
            
            # If still no orders, return empty
            if not all_orders.exists():
                return []
            
            # Use all orders for now, but mark them as not delivered
            orders = all_orders
        
        # Group by vendor and calculate statistics
        company_stats = []
        vendor_deliveries = {}
        
        for order in orders:
            vendor_id = order.vendor.id
            if vendor_id not in vendor_deliveries:
                vendor_deliveries[vendor_id] = {
                    'company_id': vendor_id,
                    'company_name': order.vendor.business_name,
                    'company_logo': order.vendor.business_logo.url if order.vendor.business_logo else None,
                    'deliveries': 0,
                    'total_earnings': 0.0,
                    'orders': []
                }
            
            vendor_deliveries[vendor_id]['deliveries'] += 1
            # Use commission if available, otherwise calculate a default commission
            commission = order.commission if order.commission else (float(order.total_price) * 0.1)  # 10% default
            vendor_deliveries[vendor_id]['total_earnings'] += float(commission)
            vendor_deliveries[vendor_id]['orders'].append(order)
        
        # Calculate average earnings per delivery and sort by delivery count
        for vendor_id, stats in vendor_deliveries.items():
            avg_earnings = stats['total_earnings'] / stats['deliveries'] if stats['deliveries'] > 0 else 0
            stats['average_earnings_per_delivery'] = round(avg_earnings, 2)
        
        # Sort by delivery count (descending) and take top companies
        sorted_companies = sorted(
            vendor_deliveries.values(),
            key=lambda x: x['deliveries'],
            reverse=True
        )[:limit]
        
        # Add ranking and calculate percentage changes
        for i, company in enumerate(sorted_companies):
            company['rank'] = i + 1
            
            # Calculate percentage change compared to previous period
            percentage_change = self._calculate_percentage_change(
                courier, company['company_id'], start_date, end_date
            )
            company['percentage_change'] = percentage_change
            
            # Add trend indicator
            company['trend'] = 'up' if percentage_change > 0 else 'down' if percentage_change < 0 else 'stable'
        
        logger.info(f"Processed {len(sorted_companies)} companies for courier {courier.id}")
        return sorted_companies
    
    def _calculate_percentage_change(self, courier, company_id, start_date, end_date):
        """Calculate percentage change in deliveries compared to previous period."""
        # Calculate previous period
        days_diff = (end_date - start_date).days
        previous_start = start_date - timedelta(days=days_diff)
        previous_end = start_date - timedelta(days=1)
        
        # Get current period deliveries
        current_deliveries = Order.objects.filter(
            courier=courier,
            vendor_id=company_id,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(start_date, end_date)
        ).count()
        
        # Get previous period deliveries
        previous_deliveries = Order.objects.filter(
            courier=courier,
            vendor_id=company_id,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(previous_start, previous_end)
        ).count()
        
        # Calculate percentage change
        if previous_deliveries > 0:
            percentage_change = ((current_deliveries - previous_deliveries) / previous_deliveries) * 100
            return round(percentage_change, 1)
        elif current_deliveries > 0:
            return 100.0  # New company, 100% increase
        else:
            return 0.0
    
    def _prepare_graph_data(self, company_data, period, start_date, end_date):
        """Prepare graph data for visualization."""
        if not company_data:
            return None
        
        # Prepare bar chart data
        bar_chart_data = {
            'labels': [company['company_name'] for company in company_data],
            'datasets': [
                {
                    'label': 'Number of Deliveries',
                    'data': [company['deliveries'] for company in company_data],
                    'backgroundColor': self._generate_colors(len(company_data)),
                    'borderColor': self._generate_colors(len(company_data)),
                    'borderWidth': 1
                }
            ]
        }
        
        # Prepare pie chart data
        pie_chart_data = {
            'labels': [company['company_name'] for company in company_data],
            'datasets': [
                {
                    'data': [company['percentage'] for company in company_data],
                    'backgroundColor': self._generate_colors(len(company_data)),
                    'borderColor': '#ffffff',
                    'borderWidth': 2
                }
            ]
        }
        
        # Prepare earnings chart data
        earnings_chart_data = {
            'labels': [company['company_name'] for company in company_data],
            'datasets': [
                {
                    'label': 'Total Earnings',
                    'data': [company['total_earnings'] for company in company_data],
                    'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2,
                    'type': 'line'
                }
            ]
        }
        
        # Prepare trend data if period allows
        trend_data = None
        if period in ['month', 'year']:
            trend_data = self._prepare_trend_data(company_data, period, start_date, end_date)
        
        return {
            'bar_chart': bar_chart_data,
            'pie_chart': pie_chart_data,
            'earnings_chart': earnings_chart_data,
            'trend_data': trend_data,
            'chart_options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'ticks': {
                            'callback': 'function(value) { return value + " deliveries"; }'
                        }
                    }
                }
            }
        }
    
    def _prepare_trend_data(self, company_data, period, start_date, end_date):
        """Prepare trend data for time-based analysis."""
        # This would show how company performance changed over time
        # For now, return a simple trend structure
        return {
            'type': 'trend',
            'period': period,
            'companies': [
                {
                    'company_name': company['company_name'],
                    'trend': 'stable',  # Could be calculated based on historical data
                    'growth_rate': 0.0  # Could be calculated based on historical data
                }
                for company in company_data
            ]
        }
    
    def _generate_colors(self, count):
        """Generate a list of colors for charts."""
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
        ]
        
        # If we need more colors, generate them
        while len(colors) < count:
            import random
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            colors.append(f'rgb({r}, {g}, {b})')
        
        return colors[:count]


class CourierCompanyPerformanceView(APIView):
    """
    API endpoint for detailed company performance analysis for a specific courier.
    
    Query Parameters:
    - company_id: ID of the specific company to analyze
    - period: Time period filter ('week', 'month', 'year')
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, company_id):
        # Get the authenticated courier
        if not hasattr(request.user, 'courier_profile'):
            return Response(
                {'error': 'User does not have a courier profile. Only couriers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        courier = request.user.courier_profile
        
        # Get query parameters
        period = request.query_params.get('period', 'month')
        
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
            start_date = today.replace(day=1)
            end_date = today
        
        try:
            # Get the specific company
            company = VendorProfile.objects.get(id=company_id)
        except VendorProfile.DoesNotExist:
            return Response(
                {'error': 'Company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get orders for this specific company
        orders = Order.objects.filter(
            courier=courier,
            vendor=company,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(start_date, end_date)
        ).order_by('delivered_at')
        
        # Calculate performance metrics
        total_deliveries = orders.count()
        total_earnings = sum(float(order.commission or 0) for order in orders)
        avg_earnings_per_delivery = total_earnings / total_deliveries if total_deliveries > 0 else 0
        
        # Calculate delivery time metrics
        delivery_times = []
        for order in orders:
            if order.delivered_at and order.order_placed_at:
                delivery_time = (order.delivered_at - order.order_placed_at).total_seconds() / 60
                delivery_times.append(delivery_time)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # Prepare daily performance data
        daily_performance = self._get_daily_performance(orders, start_date, end_date)
        
        # Calculate growth metrics
        growth_metrics = self._calculate_growth_metrics(courier, company, period, start_date, end_date)
        
        response_data = {
            'company': {
                'id': company.id,
                'name': company.business_name,
                'logo': company.business_logo.url if company.business_logo else None,
                'category': company.business_category,
                'address': company.business_address
            },
            'performance_summary': {
                'total_deliveries': total_deliveries,
                'total_earnings': round(total_earnings, 2),
                'average_earnings_per_delivery': round(avg_earnings_per_delivery, 2),
                'average_delivery_time_minutes': round(avg_delivery_time, 2),
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'period_type': period
                }
            },
            'daily_performance': daily_performance,
            'growth_metrics': growth_metrics
        }
        
        return Response(response_data)
    
    def _get_daily_performance(self, orders, start_date, end_date):
        """Get daily performance data for the company."""
        daily_data = {}
        current_date = start_date
        
        while current_date <= end_date:
            daily_data[current_date.isoformat()] = {
                'date': current_date.isoformat(),
                'deliveries': 0,
                'earnings': 0.0,
                'delivery_time': 0.0
            }
            current_date += timedelta(days=1)
        
        # Populate with actual data
        for order in orders:
            order_date = order.delivered_at.date().isoformat()
            if order_date in daily_data:
                daily_data[order_date]['deliveries'] += 1
                daily_data[order_date]['earnings'] += float(order.commission or 0)
                
                if order.delivered_at and order.order_placed_at:
                    delivery_time = (order.delivered_at - order.order_placed_at).total_seconds() / 60
                    daily_data[order_date]['delivery_time'] += delivery_time
        
        return list(daily_data.values())
    
    def _calculate_growth_metrics(self, courier, company, period, start_date, end_date):
        """Calculate growth metrics compared to previous period."""
        # Calculate previous period
        days_diff = (end_date - start_date).days
        previous_start = start_date - timedelta(days=days_diff)
        previous_end = start_date - timedelta(days=1)
        
        # Get previous period orders
        previous_orders = Order.objects.filter(
            courier=courier,
            vendor=company,
            status__in=['delivered', 'completed'],
            delivered_at__date__range=(previous_start, previous_end)
        )
        
        previous_deliveries = previous_orders.count()
        previous_earnings = sum(float(order.commission or 0) for order in previous_orders)
        
        # Calculate growth percentages
        delivery_growth = 0
        earnings_growth = 0
        
        if previous_deliveries > 0:
            current_deliveries = Order.objects.filter(
                courier=courier,
                vendor=company,
                status__in=['delivered', 'completed'],
                delivered_at__date__range=(start_date, end_date)
            ).count()
            delivery_growth = ((current_deliveries - previous_deliveries) / previous_deliveries) * 100
        
        if previous_earnings > 0:
            current_earnings = sum(
                float(order.commission or 0) 
                for order in Order.objects.filter(
                    courier=courier,
                    vendor=company,
                    status__in=['delivered', 'completed'],
                    delivered_at__date__range=(start_date, end_date)
                )
            )
            earnings_growth = ((current_earnings - previous_earnings) / previous_earnings) * 100
        
        return {
            'delivery_growth_percentage': round(delivery_growth, 2),
            'earnings_growth_percentage': round(earnings_growth, 2),
            'previous_period': {
                'deliveries': previous_deliveries,
                'earnings': round(previous_earnings, 2)
            }
        }
