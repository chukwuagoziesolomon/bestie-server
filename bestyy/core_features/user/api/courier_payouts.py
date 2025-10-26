from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta, date
from decimal import Decimal

from bestyy.core_features.user.models import Order
from bestyy.core_features.user.api.serializers import DeliverySerializer

class CourierPayoutHistoryView(APIView):
    """
    API endpoint for courier payout and transaction history.
    
    Query Parameters:
    - period: Time period filter ('today', 'week', 'month', 'year', 'custom')
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - status: Filter by order status ('delivered', 'completed', 'all')
    - page: Page number for pagination
    - page_size: Number of results per page
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
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status', 'all')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
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
            # Default to current month
            start_date = today.replace(day=1)
            end_date = today
        
        # Base queryset for completed deliveries
        base_queryset = Order.objects.filter(
            courier=courier,
            delivered_at__date__range=(start_date, end_date)
        )
        
        # Apply status filter
        if status_filter != 'all':
            base_queryset = base_queryset.filter(status=status_filter)
        else:
            base_queryset = base_queryset.filter(status__in=['delivered', 'completed'])
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(base_queryset, start_date, end_date)
        
        # Get paginated transaction history
        offset = (page - 1) * page_size
        transactions = base_queryset.order_by('-delivered_at')[offset:offset + page_size]
        
        # Serialize transactions
        transaction_data = []
        for order in transactions:
            transaction_data.append({
                'order_id': order.id,
                'order_name': order.order_name or f"Order #{order.id}",
                'amount': float(order.commission) if order.commission else 0.0,
                'delivery_fee': float(order.total_price) if order.total_price else 0.0,
                'date': order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else None,
                'status': order.status,
                'customer': str(order.user) if order.user else None,
                'delivery_address': order.delivery_address,
                'distance_km': order.distance_km,
                'delivery_time_minutes': order.delivery_time_minutes
            })
        
        # Calculate pagination info
        total_transactions = base_queryset.count()
        total_pages = (total_transactions + page_size - 1) // page_size
        
        response_data = {
            'summary': summary_stats,
            'transactions': transaction_data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_transactions': total_transactions,
                'has_next': page < total_pages,
                'has_previous': page > 1
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period_type': period
            }
        }
        
        return Response(response_data)
    
    def _calculate_summary_stats(self, queryset, start_date, end_date):
        """Calculate summary statistics for the given period."""
        # Total earnings from commission
        total_commission = queryset.aggregate(
            total=Sum('commission')
        )['total'] or Decimal('0.00')
        
        # Total delivery fees (if any)
        total_delivery_fees = queryset.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')
        
        # Total deliveries
        total_deliveries = queryset.count()
        
        # Average earnings per delivery
        avg_earnings_per_delivery = 0
        if total_deliveries > 0:
            avg_earnings_per_delivery = float(total_commission / total_deliveries)
        
        # Calculate trend (simple comparison with previous period)
        days_diff = (end_date - start_date).days
        if days_diff > 0:
            previous_start = start_date - timedelta(days=days_diff)
            previous_end = start_date - timedelta(days=1)

            previous_orders = Order.objects.filter(
                courier=queryset.first().courier if queryset.exists() else None,
                delivered_at__date__range=(previous_start, previous_end),
                status__in=['delivered', 'completed']
            )

            previous_commission = previous_orders.aggregate(
                total=Sum('commission')
            )['total'] or Decimal('0.00')

            if previous_commission > 0:
                trend_percentage = ((total_commission - previous_commission) / previous_commission) * 100
            else:
                trend_percentage = 100 if total_commission > 0 else 0
        else:
            trend_percentage = 0
        
        return {
            'total_earnings': float(total_commission),
            'total_delivery_fees': float(total_delivery_fees),
            'total_deliveries': total_deliveries,
            'average_earnings_per_delivery': round(avg_earnings_per_delivery, 2),
            'trend_percentage': round(trend_percentage, 2),
            'period_days': (end_date - start_date).days + 1
        }


class CourierEarningsBreakdownView(APIView):
    """
    API endpoint for detailed courier earnings breakdown by different time periods.
    
    Query Parameters:
    - year: Year for earnings breakdown (default: current year)
    - month: Month for earnings breakdown (1-12, default: current month)
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
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        # Validate month
        if month < 1 or month > 12:
            return Response(
                {'error': 'Invalid month. Must be between 1 and 12.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Calculate earnings from orders for the month
        monthly_orders = Order.objects.filter(
            courier=courier,
            delivered_at__date__range=(start_date, end_date),
            status__in=['delivered', 'completed']
        )

        # Calculate weekly breakdown
        weekly_breakdown = self._calculate_weekly_breakdown(monthly_orders, start_date, end_date)

        # Calculate monthly summary
        monthly_summary = self._calculate_monthly_summary(monthly_orders, start_date, end_date)

        # Get year-to-date summary
        ytd_start = date(year, 1, 1)
        ytd_orders = Order.objects.filter(
            courier=courier,
            delivered_at__date__range=(ytd_start, end_date),
            status__in=['delivered', 'completed']
        )
        ytd_summary = self._calculate_ytd_summary(ytd_orders, ytd_start, end_date)
        
        response_data = {
            'period': {
                'year': year,
                'month': month,
                'month_name': start_date.strftime('%B'),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'monthly_summary': monthly_summary,
            'weekly_breakdown': weekly_breakdown,
            'year_to_date': ytd_summary
        }
        
        return Response(response_data)
    
    def _calculate_weekly_breakdown(self, orders, start_date, end_date):
        """Calculate weekly breakdown of earnings."""
        weekly_data = []
        current_date = start_date

        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            week_end = week_start + timedelta(days=6)

            if week_end > end_date:
                week_end = end_date

            # Get orders for this week
            week_orders = orders.filter(delivered_at__date__range=(week_start, week_end))

            week_earnings = week_orders.aggregate(total=Sum('commission'))['total'] or 0
            week_deliveries = week_orders.count()

            weekly_data.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'week_number': current_date.isocalendar()[1],
                'total_earnings': float(week_earnings),
                'total_deliveries': week_deliveries,
                'average_earnings_per_day': round(float(week_earnings) / 7, 2) if week_earnings > 0 else 0
            })

            current_date = week_end + timedelta(days=1)

        return weekly_data
    
    def _calculate_monthly_summary(self, orders, start_date, end_date):
        """Calculate monthly summary statistics."""
        if not orders:
            return {
                'total_earnings': 0.0,
                'total_deliveries': 0,
                'average_earnings_per_day': 0.0,
                'best_day': None,
                'worst_day': None,
                'total_working_days': 0
            }

        total_earnings = orders.aggregate(total=Sum('commission'))['total'] or 0
        total_deliveries = orders.count()

        # Group by day to find best/worst days
        daily_earnings = {}
        for order in orders:
            day = order.delivered_at.date()
            if day not in daily_earnings:
                daily_earnings[day] = {'earnings': 0, 'deliveries': 0}
            daily_earnings[day]['earnings'] += float(order.commission or 0)
            daily_earnings[day]['deliveries'] += 1

        if daily_earnings:
            # Find best and worst days
            best_day_date = max(daily_earnings.keys(), key=lambda x: daily_earnings[x]['earnings'])
            worst_day_date = min(daily_earnings.keys(), key=lambda x: daily_earnings[x]['earnings'])

            # Count working days (days with earnings)
            working_days = sum(1 for day_data in daily_earnings.values() if day_data['earnings'] > 0)

            return {
                'total_earnings': float(total_earnings),
                'total_deliveries': total_deliveries,
                'average_earnings_per_day': round(float(total_earnings) / (end_date - start_date).days, 2),
                'best_day': {
                    'date': best_day_date.isoformat(),
                    'earnings': daily_earnings[best_day_date]['earnings'],
                    'deliveries': daily_earnings[best_day_date]['deliveries']
                },
                'worst_day': {
                    'date': worst_day_date.isoformat(),
                    'earnings': daily_earnings[worst_day_date]['earnings'],
                    'deliveries': daily_earnings[worst_day_date]['deliveries']
                },
                'total_working_days': working_days,
                'total_calendar_days': (end_date - start_date).days + 1
            }
        else:
            return {
                'total_earnings': 0.0,
                'total_deliveries': 0,
                'average_earnings_per_day': 0.0,
                'best_day': None,
                'worst_day': None,
                'total_working_days': 0,
                'total_calendar_days': (end_date - start_date).days + 1
            }
    
    def _calculate_ytd_summary(self, ytd_orders, ytd_start, end_date):
        """Calculate year-to-date summary."""
        if not ytd_orders:
            return {
                'total_earnings': 0.0,
                'total_deliveries': 0,
                'average_earnings_per_month': 0.0,
                'projected_annual_earnings': 0.0
            }

        total_earnings = ytd_orders.aggregate(total=Sum('commission'))['total'] or 0
        total_deliveries = ytd_orders.count()

        # Calculate months elapsed
        months_elapsed = (end_date.year - ytd_start.year) * 12 + end_date.month - ytd_start.month + 1

        avg_monthly_earnings = float(total_earnings) / months_elapsed if months_elapsed > 0 else 0

        # Project annual earnings
        projected_annual = avg_monthly_earnings * 12

        return {
            'total_earnings': float(total_earnings),
            'total_deliveries': total_deliveries,
            'average_earnings_per_month': round(avg_monthly_earnings, 2),
            'projected_annual_earnings': round(projected_annual, 2),
            'months_elapsed': months_elapsed
        }
