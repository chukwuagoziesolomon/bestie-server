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

from bestyy.core_features.user.permissions import IsAdminUser
from bestyy.core_features.user.models import VendorProfile, CourierProfile
from bestyy.restaurant_features.order.models import Order
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
        """Helper method to calculate date ranges for statistics."""
        now = timezone.now()
        if period == 'today':
            current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            previous_start = current_start - timedelta(days=1)
            previous_end = current_start
        elif period == 'week':
            current_start = now - timedelta(days=now.weekday())
            current_end = now
            previous_start = current_start - timedelta(weeks=1)
            previous_end = current_start
        else:  # month
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            # Go to first day of previous month
            if current_start.month == 1:
                previous_start = current_start.replace(year=current_start.year-1, month=12)
            else:
                previous_start = current_start.replace(month=current_start.month-1)
            previous_end = current_start
        
        return {
            'current': {'start': current_start, 'end': current_end},
            'previous': {'start': previous_start, 'end': previous_end}
        }
    
    def _get_total_orders_stats(self, date_ranges):
        """Calculate order statistics for the given time periods."""
        current_orders = Order.objects.filter(
            created_at__gte=date_ranges['current']['start'],
            created_at__lte=date_ranges['current']['end']
        ).count()
        
        previous_orders = Order.objects.filter(
            created_at__gte=date_ranges['previous']['start'],
            created_at__lte=date_ranges['previous']['end']
        ).count()
        
        change = self._calculate_change(current_orders, previous_orders)
        
        return {
            "value": current_orders,
            "trend": "up" if change >= 0 else "down",
            "change_percentage": abs(change),
            "comparison_text": f"{'Up' if change >= 0 else 'Down'} from previous period",
            "icon": "package"
        }
    
    def _get_total_revenue_stats(self, date_ranges):
        """Calculate revenue statistics for the given time periods."""
        current_revenue = Order.objects.filter(
            created_at__gte=date_ranges['current']['start'],
            created_at__lte=date_ranges['current']['end'],
            payment_confirmed=True
        ).aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')

        previous_revenue = Order.objects.filter(
            created_at__gte=date_ranges['previous']['start'],
            created_at__lte=date_ranges['previous']['end'],
            payment_confirmed=True
        ).aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')

        change = self._calculate_change(float(current_revenue), float(previous_revenue))

        return {
            "value": float(current_revenue),
            "formatted_value": f"N{float(current_revenue):,.2f}",
            "trend": "up" if change >= 0 else "down",
            "change_percentage": abs(change),
            "comparison_text": f"{'Up' if change >= 0 else 'Down'} from previous period",
            "icon": "trending-up"
        }
    
    def _get_pending_verification_stats(self, date_ranges):
        """Calculate verification statistics for the given time periods."""
        current_pending = (
            VendorProfile.objects.filter(
                verification_status='pending',
                created_at__gte=date_ranges['current']['start'],
                created_at__lte=date_ranges['current']['end']
            ).count() +
            CourierProfile.objects.filter(
                verification_status='pending',
                created_at__gte=date_ranges['current']['start'],
                created_at__lte=date_ranges['current']['end']
            ).count()
        )
        
        previous_pending = (
            VendorProfile.objects.filter(
                verification_status='pending',
                created_at__gte=date_ranges['previous']['start'],
                created_at__lte=date_ranges['previous']['end']
            ).count() +
            CourierProfile.objects.filter(
                verification_status='pending',
                created_at__gte=date_ranges['previous']['start'],
                created_at__lte=date_ranges['previous']['end']
            ).count()
        )
        
        change = self._calculate_change(current_pending, previous_pending)
        
        return {
            "value": current_pending,
            "trend": "up" if change >= 0 else "down",
            "change_percentage": abs(change),
            "comparison_text": f"{'Up' if change >= 0 else 'Down'} from previous period",
            "icon": "check-circle"
        }
    
    def _get_active_couriers_stats(self, date_ranges):
        """Calculate active courier statistics for the given time periods."""
        current_active = CourierProfile.objects.filter(
            is_active=True,
            created_at__lte=date_ranges['current']['end']
        ).count()
        
        previous_active = CourierProfile.objects.filter(
            is_active=True,
            created_at__lte=date_ranges['previous']['end']
        ).count()
        
        change = self._calculate_change(current_active, previous_active)
        
        return {
            "value": current_active,
            "trend": "up" if change >= 0 else "down",
            "change_percentage": abs(change),
            "comparison_text": f"{'Up' if change >= 0 else 'Down'} from previous period",
            "icon": "truck"
        }
    
    def _calculate_change(self, current, previous):
        """Calculate percentage change between current and previous values."""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
            

class AdminRevenueBreakdownView(APIView):
    """
    API endpoint that provides revenue breakdown by vendor category.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `period` (string, optional): Time period for data range.
      Options: 'today', 'week', 'month', 'year'. Default: 'month'
    
    ## Response Format
    ```json
    {
        "categories": [
            {
                "category": "Restaurant",
                "total_revenue": 50000.00,
                "percentage": 45,
                "color": "#FF6B6B"
            },
            {
                "category": "Grocery",
                "total_revenue": 30000.00,
                "percentage": 27,
                "color": "#4ECDC4"
            },
            ...
        ],
        "total": 110000.00
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            period = request.query_params.get('period', 'month')
            date_range = self._get_date_range(period)
            
            # Get all completed orders in the date range
            orders = Order.objects.filter(
                payment_confirmed=True,
                created_at__gte=date_range['start'],
                created_at__lte=date_range['end']
            ).select_related('vendor')

            # Group orders by vendor category and calculate totals
            category_totals = {}
            total_revenue = Decimal('0.00')

            for order in orders:
                if not order.vendor:
                    continue

                category = order.vendor.business_category
                if category not in category_totals:
                    category_totals[category] = Decimal('0.00')
                category_totals[category] += order.total_price
                total_revenue += order.total_price
            
            # Calculate percentages and format response
            categories = []
            colors = self._get_category_colors()
            
            for category, amount in category_totals.items():
                percentage = round((amount / total_revenue * 100) if total_revenue else 0, 1)
                categories.append({
                    "category": category,
                    "total_revenue": float(amount),
                    "formatted_revenue": f"N{float(amount):,.2f}",
                    "percentage": percentage,
                    "color": colors.get(category, "#808080")  # Default gray if no color defined
                })
            
            # Sort by revenue (highest first)
            categories.sort(key=lambda x: x['total_revenue'], reverse=True)
            
            response_data = {
                "categories": categories,
                "total": float(total_revenue),
                "formatted_total": f"N{float(total_revenue):,.2f}"
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in AdminRevenueBreakdownView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch revenue breakdown'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_date_range(self, period):
        """Helper method to calculate date range based on period."""
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=now.weekday())
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # month (default)
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return {
            'start': start_date,
            'end': now
        }
    
    def _get_category_colors(self):
        """Define colors for different business categories."""
        return {
            "Restaurant": "#FF6B6B",
            "Grocery": "#4ECDC4",
            "Fast Food": "#45B7D1",
            "Cafe": "#96CEB4",
            "Bakery": "#FFEEAD",
            "Other": "#808080"
        }