"""
Admin API views for dashboard KPI statistics.
These endpoints provide data for the admin dashboard stat cards.
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
from user.models import Order, Payment, VendorProfile, CourierProfile
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminDashboardStatsView(APIView):
    """
    API endpoint that provides KPI statistics for admin dashboard stat cards.
    Returns data for Total Orders, Total Revenue, Pending Verification, and Active Couriers.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `period` (string, optional): Time period for comparison. 
      Options: 'today', 'week', 'month'. Default: 'week'
    
    ## Response Format
    ```json
    {
        "total_orders": {
            "value": 90,
            "trend": "up",
            "change_percentage": 1.3,
            "comparison_text": "Up from past week",
            "icon": "package"
        },
        "total_revenue": {
            "value": 200000.00,
            "formatted_value": "N200,000",
            "trend": "down",
            "change_percentage": -4.3,
            "comparison_text": "Down from yesterday",
            "icon": "trending-up"
        },
        "pending_verification": {
            "value": 10,
            "trend": "up",
            "change_percentage": 1.8,
            "comparison_text": "Up from yesterday",
            "icon": "check-circle"
        },
        "active_couriers": {
            "value": 8,
            "trend": "up",
            "change_percentage": 1.8,
            "comparison_text": "Up from yesterday",
            "icon": "truck"
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            period = request.query_params.get('period', 'week')
            
            # Calculate date ranges based on period
            date_ranges = self._calculate_date_ranges(period)
            
            # Get KPI data
            total_orders = self._get_total_orders_stats(date_ranges)
            total_revenue = self._get_total_revenue_stats(date_ranges)
            pending_verification = self._get_pending_verification_stats(date_ranges)
            active_couriers = self._get_active_couriers_stats(date_ranges)
            
            response_data = {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "pending_verification": pending_verification,
                "active_couriers": active_couriers
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in AdminDashboardStatsView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch dashboard statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_date_ranges(self, period):
        """Calculate date ranges for current and comparison periods."""
        now = timezone.now()
        today = now.date()
        
        if period == 'today':
            # Compare with yesterday
            current_start = today
            current_end = today
            comparison_start = today - timedelta(days=1)
            comparison_end = today - timedelta(days=1)
            comparison_text = "yesterday"
        elif period == 'week':
            # Compare with previous week
            current_start = today - timedelta(days=7)
            current_end = today
            comparison_start = today - timedelta(days=14)
            comparison_end = today - timedelta(days=7)
            comparison_text = "past week"
        else:  # month
            # Compare with previous month
            current_start = today - timedelta(days=30)
            current_end = today
            comparison_start = today - timedelta(days=60)
            comparison_end = today - timedelta(days=30)
            comparison_text = "past month"
        
        return {
            'current': {
                'start': current_start,
                'end': current_end
            },
            'comparison': {
                'start': comparison_start,
                'end': comparison_end
            },
            'comparison_text': comparison_text
        }
    
    def _get_total_orders_stats(self, date_ranges):
        """Get total orders statistics."""
        # Current period orders
        current_orders = Order.objects.filter(
            created_at__date__gte=date_ranges['current']['start'],
            created_at__date__lte=date_ranges['current']['end'],
            payment_confirmed=True
        ).count()
        
        # Comparison period orders
        comparison_orders = Order.objects.filter(
            created_at__date__gte=date_ranges['comparison']['start'],
            created_at__date__lte=date_ranges['comparison']['end'],
            payment_confirmed=True
        ).count()
        
        # Calculate percentage change
        change_percentage = self._calculate_percentage_change(current_orders, comparison_orders)
        trend = "up" if change_percentage >= 0 else "down"
        
        return {
            "value": current_orders,
            "trend": trend,
            "change_percentage": abs(change_percentage),
            "comparison_text": f"{'Up' if trend == 'up' else 'Down'} from {date_ranges['comparison_text']}",
            "icon": "package"
        }
    
    def _get_total_revenue_stats(self, date_ranges):
        """Get total revenue statistics."""
        # Current period revenue
        current_revenue = Order.objects.filter(
            created_at__date__gte=date_ranges['current']['start'],
            created_at__date__lte=date_ranges['current']['end'],
            payment_confirmed=True
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        # Comparison period revenue
        comparison_revenue = Order.objects.filter(
            created_at__date__gte=date_ranges['comparison']['start'],
            created_at__date__lte=date_ranges['comparison']['end'],
            payment_confirmed=True
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        # Calculate percentage change
        change_percentage = self._calculate_percentage_change(float(current_revenue), float(comparison_revenue))
        trend = "up" if change_percentage >= 0 else "down"
        
        # Format revenue value
        formatted_value = self._format_currency(float(current_revenue))
        
        return {
            "value": float(current_revenue),
            "formatted_value": formatted_value,
            "trend": trend,
            "change_percentage": abs(change_percentage),
            "comparison_text": f"{'Up' if trend == 'up' else 'Down'} from {date_ranges['comparison_text']}",
            "icon": "trending-up"
        }
    
    def _get_pending_verification_stats(self, date_ranges):
        """Get pending verification statistics."""
        # Current pending verifications
        current_pending = (
            VendorProfile.objects.filter(verification_status='pending').count() +
            CourierProfile.objects.filter(verification_status='pending').count()
        )
        
        # Get comparison data (pending verifications from comparison period)
        # This is a bit tricky - we'll look at how many were pending at the end of comparison period
        comparison_pending = (
            VendorProfile.objects.filter(
                verification_status='pending',
                created_at__date__lte=date_ranges['comparison']['end']
            ).count() +
            CourierProfile.objects.filter(
                verification_status='pending',
                created_at__date__lte=date_ranges['comparison']['end']
            ).count()
        )
        
        # Calculate percentage change
        change_percentage = self._calculate_percentage_change(current_pending, comparison_pending)
        trend = "up" if change_percentage >= 0 else "down"
        
        return {
            "value": current_pending,
            "trend": trend,
            "change_percentage": abs(change_percentage),
            "comparison_text": f"{'Up' if trend == 'up' else 'Down'} from {date_ranges['comparison_text']}",
            "icon": "check-circle"
        }
    
    def _get_active_couriers_stats(self, date_ranges):
        """Get active couriers statistics."""
        # Current active couriers (logged in within last 7 days and verified)
        current_active = CourierProfile.objects.filter(
            verification_status='approved',
            user__last_login__date__gte=date_ranges['current']['start'] - timedelta(days=7),
            is_active=True
        ).count()
        
        # Comparison active couriers
        comparison_active = CourierProfile.objects.filter(
            verification_status='approved',
            user__last_login__date__gte=date_ranges['comparison']['start'] - timedelta(days=7),
            user__last_login__date__lte=date_ranges['comparison']['end'],
            is_active=True
        ).count()
        
        # Calculate percentage change
        change_percentage = self._calculate_percentage_change(current_active, comparison_active)
        trend = "up" if change_percentage >= 0 else "down"
        
        return {
            "value": current_active,
            "trend": trend,
            "change_percentage": abs(change_percentage),
            "comparison_text": f"{'Up' if trend == 'up' else 'Down'} from {date_ranges['comparison_text']}",
            "icon": "truck"
        }
    
    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between current and previous values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)
    
    def _format_currency(self, amount):
        """Format currency amount for display."""
        if amount >= 1000000:
            return f"N{amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"N{amount/1000:.0f}K"
        else:
            return f"N{amount:,.0f}"


class AdminRevenueBreakdownView(APIView):
    """
    API endpoint that provides detailed revenue breakdown for specific periods.
    Returns revenue data for particular days, weeks, or months.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `date` (date, optional): Specific date for breakdown (YYYY-MM-DD). Default: today
    - `period` (string, optional): Period type. Options: 'day', 'week', 'month'. Default: 'day'
    - `breakdown_type` (string, optional): Type of breakdown. 
      Options: 'hourly', 'daily', 'by_vendor', 'by_status', 'by_payment_method'. Default: 'hourly'
    
    ## Response Format
    ```json
    {
        "period": {
            "date": "2025-09-08",
            "period_type": "day",
            "breakdown_type": "hourly"
        },
        "summary": {
            "total_revenue": 25000.00,
            "total_orders": 45,
            "average_order_value": 555.56
        },
        "breakdown": [
            {
                "time": "09:00",
                "revenue": 2500.00,
                "orders": 5,
                "percentage": 10.0
            },
            {
                "time": "10:00",
                "revenue": 3200.00,
                "orders": 7,
                "percentage": 12.8
            }
        ],
        "top_performers": [
            {
                "vendor_id": 1,
                "vendor_name": "Tasty Bites",
                "revenue": 5000.00,
                "orders": 10,
                "percentage": 20.0
            }
        ]
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            date_str = request.query_params.get('date')
            period = request.query_params.get('period', 'day')
            breakdown_type = request.query_params.get('breakdown_type', 'hourly')
            
            # Parse date
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                target_date = timezone.now().date()
            
            # Get breakdown data
            breakdown_data = self._get_breakdown_data(target_date, period, breakdown_type)
            summary = self._get_period_summary(target_date, period)
            top_performers = self._get_top_performers(target_date, period)
            
            response_data = {
                "period": {
                    "date": target_date.isoformat(),
                    "period_type": period,
                    "breakdown_type": breakdown_type
                },
                "summary": summary,
                "breakdown": breakdown_data,
                "top_performers": top_performers
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in AdminRevenueBreakdownView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch revenue breakdown'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_breakdown_data(self, target_date, period, breakdown_type):
        """Get breakdown data based on type."""
        if breakdown_type == 'hourly' and period == 'day':
            return self._get_hourly_breakdown(target_date)
        elif breakdown_type == 'daily' and period == 'week':
            return self._get_daily_breakdown(target_date)
        elif breakdown_type == 'by_vendor':
            return self._get_vendor_breakdown(target_date, period)
        elif breakdown_type == 'by_status':
            return self._get_status_breakdown(target_date, period)
        elif breakdown_type == 'by_payment_method':
            return self._get_payment_method_breakdown(target_date, period)
        else:
            return self._get_hourly_breakdown(target_date)
    
    def _get_hourly_breakdown(self, target_date):
        """Get hourly revenue breakdown for a specific day."""
        orders = Order.objects.filter(
            created_at__date=target_date,
            payment_confirmed=True
        )
        
        hourly_data = []
        total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        for hour in range(24):
            hour_orders = orders.filter(created_at__hour=hour)
            hour_revenue = hour_orders.aggregate(total=Sum('total_price'))['total'] or 0
            hour_count = hour_orders.count()
            percentage = (float(hour_revenue) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            
            hourly_data.append({
                "time": f"{hour:02d}:00",
                "revenue": float(hour_revenue),
                "orders": hour_count,
                "percentage": round(percentage, 1)
            })
        
        return hourly_data
    
    def _get_daily_breakdown(self, target_date):
        """Get daily revenue breakdown for a week."""
        week_start = target_date - timedelta(days=target_date.weekday())
        daily_data = []
        
        total_revenue = Order.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_start + timedelta(days=6),
            payment_confirmed=True
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        for day in range(7):
            current_date = week_start + timedelta(days=day)
            day_orders = Order.objects.filter(
                created_at__date=current_date,
                payment_confirmed=True
            )
            day_revenue = day_orders.aggregate(total=Sum('total_price'))['total'] or 0
            day_count = day_orders.count()
            percentage = (float(day_revenue) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            
            daily_data.append({
                "time": current_date.strftime('%A'),
                "revenue": float(day_revenue),
                "orders": day_count,
                "percentage": round(percentage, 1)
            })
        
        return daily_data
    
    def _get_vendor_breakdown(self, target_date, period):
        """Get revenue breakdown by vendor."""
        date_range = self._get_date_range(target_date, period)
        
        vendor_data = Order.objects.filter(
            created_at__date__gte=date_range['start'],
            created_at__date__lte=date_range['end'],
            payment_confirmed=True
        ).values(
            'vendor__id',
            'vendor__business_name'
        ).annotate(
            revenue=Sum('total_price'),
            orders=Count('id')
        ).order_by('-revenue')[:10]
        
        total_revenue = sum(item['revenue'] for item in vendor_data)
        
        breakdown = []
        for vendor in vendor_data:
            percentage = (float(vendor['revenue']) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            breakdown.append({
                "time": vendor['vendor__business_name'],
                "revenue": float(vendor['revenue']),
                "orders": vendor['orders'],
                "percentage": round(percentage, 1)
            })
        
        return breakdown
    
    def _get_status_breakdown(self, target_date, period):
        """Get revenue breakdown by order status."""
        date_range = self._get_date_range(target_date, period)
        
        status_data = Order.objects.filter(
            created_at__date__gte=date_range['start'],
            created_at__date__lte=date_range['end'],
            payment_confirmed=True
        ).values('status').annotate(
            revenue=Sum('total_price'),
            orders=Count('id')
        ).order_by('-revenue')
        
        total_revenue = sum(item['revenue'] for item in status_data)
        
        breakdown = []
        for status_item in status_data:
            percentage = (float(status_item['revenue']) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            breakdown.append({
                "time": status_item['status'].title(),
                "revenue": float(status_item['revenue']),
                "orders": status_item['orders'],
                "percentage": round(percentage, 1)
            })
        
        return breakdown
    
    def _get_payment_method_breakdown(self, target_date, period):
        """Get revenue breakdown by payment method."""
        date_range = self._get_date_range(target_date, period)
        
        payment_data = Payment.objects.filter(
            created_at__date__gte=date_range['start'],
            created_at__date__lte=date_range['end'],
            status='successful'
        ).values('payment_method').annotate(
            revenue=Sum('amount'),
            orders=Count('id')
        ).order_by('-revenue')
        
        total_revenue = sum(item['revenue'] for item in payment_data)
        
        breakdown = []
        for payment_item in payment_data:
            percentage = (float(payment_item['revenue']) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            breakdown.append({
                "time": payment_item['payment_method'].title(),
                "revenue": float(payment_item['revenue']),
                "orders": payment_item['orders'],
                "percentage": round(percentage, 1)
            })
        
        return breakdown
    
    def _get_period_summary(self, target_date, period):
        """Get summary statistics for the period."""
        date_range = self._get_date_range(target_date, period)
        
        orders = Order.objects.filter(
            created_at__date__gte=date_range['start'],
            created_at__date__lte=date_range['end'],
            payment_confirmed=True
        )
        
        total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
        total_orders = orders.count()
        avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0
        
        return {
            "total_revenue": float(total_revenue),
            "total_orders": total_orders,
            "average_order_value": round(avg_order_value, 2)
        }
    
    def _get_top_performers(self, target_date, period):
        """Get top performing vendors for the period."""
        date_range = self._get_date_range(target_date, period)
        
        top_vendors = Order.objects.filter(
            created_at__date__gte=date_range['start'],
            created_at__date__lte=date_range['end'],
            payment_confirmed=True
        ).values(
            'vendor__id',
            'vendor__business_name'
        ).annotate(
            revenue=Sum('total_price'),
            orders=Count('id')
        ).order_by('-revenue')[:5]
        
        total_revenue = sum(vendor['revenue'] for vendor in top_vendors)
        
        performers = []
        for vendor in top_vendors:
            percentage = (float(vendor['revenue']) / float(total_revenue)) * 100 if total_revenue > 0 else 0
            performers.append({
                "vendor_id": vendor['vendor__id'],
                "vendor_name": vendor['vendor__business_name'],
                "revenue": float(vendor['revenue']),
                "orders": vendor['orders'],
                "percentage": round(percentage, 1)
            })
        
        return performers
    
    def _get_date_range(self, target_date, period):
        """Get date range based on period type."""
        if period == 'day':
            return {'start': target_date, 'end': target_date}
        elif period == 'week':
            week_start = target_date - timedelta(days=target_date.weekday())
            return {'start': week_start, 'end': week_start + timedelta(days=6)}
        else:  # month
            month_start = target_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
            return {'start': month_start, 'end': month_end}


class AdminTopVendorsView(APIView):
    """
    API endpoint for Top Vendors dashboard section.
    Returns vendor performance data with order counts and percentage changes.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        period = request.query_params.get('period', 'week')  # 'today', 'week', 'month'
        
        now = timezone.now()
        
        # Calculate date ranges
        if period == 'today':
            current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_start = current_start - timedelta(days=1)
            previous_end = current_start
        elif period == 'month':
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_start = (current_start - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_end = current_start
        else:  # Default to 'week'
            current_start = now - timedelta(days=now.weekday())  # Start of current week (Monday)
            current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_start = current_start - timedelta(weeks=1)
            previous_end = current_start

        # Get top vendors for current period
        current_vendors = Order.objects.filter(
            created_at__gte=current_start,
            status__in=['completed', 'delivered']
        ).values('vendor__business_name', 'vendor_id').annotate(
            order_count=Count('id')
        ).order_by('-order_count')[:10]

        # Get vendor data for previous period for comparison
        previous_vendors = Order.objects.filter(
            created_at__gte=previous_start,
            created_at__lt=previous_end,
            status__in=['completed', 'delivered']
        ).values('vendor__business_name', 'vendor_id').annotate(
            order_count=Count('id')
        ).order_by('-order_count')

        # Create a dictionary for quick lookup of previous period data
        previous_data = {vendor['vendor_id']: vendor['order_count'] for vendor in previous_vendors}

        # Build response data
        top_vendors = []
        for vendor in current_vendors:
            vendor_id = vendor['vendor_id']
            current_orders = vendor['order_count']
            previous_orders = previous_data.get(vendor_id, 0)
            
            # Calculate percentage change
            if previous_orders == 0:
                change_percentage = 100.0 if current_orders > 0 else 0.0
            else:
                change_percentage = round(((current_orders - previous_orders) / previous_orders) * 100, 1)
            
            # Get vendor details
            try:
                vendor_profile = VendorProfile.objects.get(id=vendor_id)
                business_name = vendor_profile.business_name
                # Get top menu item for this vendor
                top_item = self._get_top_menu_item(vendor_id, current_start, now)
            except VendorProfile.DoesNotExist:
                business_name = f"Vendor {vendor_id}"
                top_item = "Unknown Item"

            top_vendors.append({
                'vendor_id': vendor_id,
                'business_name': business_name,
                'top_item': top_item,
                'orders': current_orders,
                'change_percentage': change_percentage,
                'trend': 'up' if change_percentage >= 0 else 'down',
                'change_color': '#10B981' if change_percentage >= 0 else '#EF4444'
            })

        response_data = {
            'period': period,
            'date_range': {
                'current_start': current_start.isoformat(),
                'current_end': now.isoformat(),
                'previous_start': previous_start.isoformat(),
                'previous_end': previous_end.isoformat()
            },
            'top_vendors': top_vendors,
            'summary': {
                'total_vendors': len(top_vendors),
                'total_orders': sum(vendor['orders'] for vendor in top_vendors)
            }
        }

        return Response(response_data)

    def _get_top_menu_item(self, vendor_id, start_date, end_date):
        """Get the top-selling menu item for a vendor in the given period."""
        try:
            from menu.models import MenuItem, OrderItem
            
            # Get top menu item for this vendor in the period
            top_item = OrderItem.objects.filter(
                order__vendor_id=vendor_id,
                order__created_at__gte=start_date,
                order__created_at__lte=end_date,
                order__status__in=['completed', 'delivered']
            ).values('menu_item__dish_name').annotate(
                total_quantity=Sum('quantity')
            ).order_by('-total_quantity').first()
            
            if top_item:
                return top_item['menu_item__dish_name']
            else:
                return "No orders"
        except Exception:
            return "Unknown Item"


class AdminOrderActivityView(APIView):
    """
    API endpoint for Order Activity donut chart.
    Returns order status breakdown with counts and percentages.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        period = request.query_params.get('period', 'week')  # 'today', 'week', 'month'
        
        now = timezone.now()
        
        # Calculate date range
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # Default to 'week'
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get order status breakdown
        orders_qs = Order.objects.filter(created_at__gte=start_date)
        
        status_breakdown = orders_qs.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        # Calculate total orders
        total_orders = orders_qs.count()
        
        # Define status colors and labels
        status_config = {
            'completed': {'label': 'Completed', 'color': '#10B981'},
            'delivered': {'label': 'Delivered', 'color': '#10B981'},
            'pending': {'label': 'Pending', 'color': '#F59E0B'},
            'processing': {'label': 'Processing', 'color': '#3B82F6'},
            'cancelled': {'label': 'Cancelled', 'color': '#EF4444'},
            'rejected': {'label': 'Rejected', 'color': '#6B7280'},
            'in_progress': {'label': 'In Progress', 'color': '#8B5CF6'},
        }

        # Build chart data
        chart_data = []
        for status_data in status_breakdown:
            status = status_data['status']
            count = status_data['count']
            percentage = round((count / total_orders) * 100, 1) if total_orders > 0 else 0
            
            config = status_config.get(status, {'label': status.title(), 'color': '#6B7280'})
            
            chart_data.append({
                'status': status,
                'label': config['label'],
                'count': count,
                'percentage': percentage,
                'color': config['color']
            })

        # Sort by count (descending)
        chart_data.sort(key=lambda x: x['count'], reverse=True)

        # Calculate summary statistics
        completed_orders = sum(item['count'] for item in chart_data if item['status'] in ['completed', 'delivered'])
        pending_orders = sum(item['count'] for item in chart_data if item['status'] in ['pending', 'processing', 'in_progress'])
        rejected_orders = sum(item['count'] for item in chart_data if item['status'] in ['rejected', 'cancelled'])

        response_data = {
            'period': period,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': now.isoformat()
            },
            'total_orders': total_orders,
            'chart_data': chart_data,
            'summary': {
                'completed': completed_orders,
                'pending': pending_orders,
                'rejected': rejected_orders,
                'completion_rate': round((completed_orders / total_orders) * 100, 1) if total_orders > 0 else 0
            }
        }

        return Response(response_data)
