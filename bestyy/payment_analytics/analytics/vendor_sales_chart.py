from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta, date
import calendar

from bestyy.restaurant_features.order.models import Order


class VendorSalesChartView(APIView):
    """
    API endpoint for vendor sales chart line graph data.
    Provides data in the format needed for the sales details chart.
    
    Query Parameters:
    - month: Month number (1-12, default: current month)
    - year: Year (default: current year)
    - period: 'daily', 'weekly', 'monthly' (default: 'daily')
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check if user has a vendor profile
        if not hasattr(user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access the sales chart."},
                status=403
            )
        
        vendor = getattr(user, 'vendor_profile', None)
        if not vendor:
            return Response(
                {"detail": "Vendor profile not found."},
                status=404
            )
        
        # Get query parameters
        month = int(request.query_params.get('month', timezone.now().month))
        year = int(request.query_params.get('year', timezone.now().year))
        period = request.query_params.get('period', 'daily')
        
        # Validate month and year
        if month < 1 or month > 12:
            return Response(
                {"detail": "Invalid month. Must be between 1 and 12."},
                status=400
            )
        
        if year < 2020 or year > 2030:
            return Response(
                {"detail": "Invalid year. Must be between 2020 and 2030."},
                status=400
            )
        
        # Get date range for the specified month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Filter orders for this vendor in the specified month
        vendor_orders = Order.objects.filter(
            vendor=vendor,
            created_at__date__range=(start_date, end_date)
        )
        
        # Generate chart data based on period
        if period == 'daily':
            chart_data = self._get_daily_chart_data(vendor_orders, start_date, end_date)
        elif period == 'weekly':
            chart_data = self._get_weekly_chart_data(vendor_orders, start_date, end_date)
        elif period == 'monthly':
            chart_data = self._get_monthly_chart_data(vendor_orders, year)
        else:
            return Response(
                {"detail": "Invalid period. Must be 'daily', 'weekly', or 'monthly'."},
                status=400
            )
        
        # Calculate summary statistics
        total_sales = vendor_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders = vendor_orders.count()
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Calculate percentage change from previous period
        percentage_change = self._calculate_percentage_change(vendor, start_date, end_date, period)
        
        # Get month name for display
        month_name = calendar.month_name[month]
        
        return Response({
            "chart_data": chart_data,
            "summary": {
                "total_sales": float(total_sales),
                "total_orders": total_orders,
                "average_order_value": round(avg_order_value, 2),
                "period": period,
                "month": month_name,
                "year": year
            },
            "percentage_change": percentage_change,
            "chart_config": {
                "x_axis_label": "Sales Volume" if period == 'daily' else "Week" if period == 'weekly' else "Month",
                "y_axis_label": "Sales Value (%)",
                "chart_type": "line",
                "show_tooltip": True,
                "show_grid": True
            }
        })
    
    def _get_daily_chart_data(self, vendor_orders, start_date, end_date):
        """Generate daily chart data for the month."""
        chart_data = []
        current_date = start_date
        
        # Get all sales values for percentage calculation
        all_sales = []
        daily_sales_map = {}
        
        while current_date <= end_date:
            day_orders = vendor_orders.filter(created_at__date=current_date)
            day_sales = day_orders.aggregate(total=Sum('total_amount'))['total'] or 0
            daily_sales_map[current_date.day] = float(day_sales)
            all_sales.append(float(day_sales))
            current_date += timedelta(days=1)
        
        # Calculate max sales for percentage calculation
        max_sales = max(all_sales) if all_sales else 1
        
        # Generate chart data points
        current_date = start_date
        while current_date <= end_date:
            day_sales = daily_sales_map.get(current_date.day, 0)
            percentage = (day_sales / max_sales * 100) if max_sales > 0 else 0
            
            chart_data.append({
                "x": f"{current_date.day}k",  # Format as "5k", "10k", etc.
                "y": round(percentage, 1),  # Percentage value
                "value": day_sales,  # Actual sales value
                "date": current_date.isoformat(),
                "day": current_date.day
            })
            current_date += timedelta(days=1)
        
        return chart_data
    
    def _get_weekly_chart_data(self, vendor_orders, start_date, end_date):
        """Generate weekly chart data for the month."""
        chart_data = []
        
        # Calculate weeks in the month
        current_date = start_date
        week_number = 1
        
        while current_date <= end_date:
            # Calculate week end date (7 days from start or end of month)
            week_end = min(current_date + timedelta(days=6), end_date)
            
            # Get orders for this week
            week_orders = vendor_orders.filter(
                created_at__date__range=(current_date, week_end)
            )
            week_sales = week_orders.aggregate(total=Sum('total_amount'))['total'] or 0
            
            chart_data.append({
                "x": f"Week {week_number}",
                "y": float(week_sales),
                "value": float(week_sales),
                "week_start": current_date.isoformat(),
                "week_end": week_end.isoformat(),
                "week_number": week_number
            })
            
            current_date = week_end + timedelta(days=1)
            week_number += 1
        
        return chart_data
    
    def _get_monthly_chart_data(self, vendor_orders, year):
        """Generate monthly chart data for the year."""
        chart_data = []
        
        for month in range(1, 13):
            # Get date range for the month
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            
            # Get orders for this month
            month_orders = vendor_orders.filter(
                created_at__date__range=(month_start, month_end)
            )
            month_sales = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
            
            chart_data.append({
                "x": calendar.month_abbr[month],
                "y": float(month_sales),
                "value": float(month_sales),
                "month": month,
                "month_name": calendar.month_name[month]
            })
        
        return chart_data
    
    def _calculate_percentage_change(self, vendor, start_date, end_date, period):
        """Calculate percentage change from previous period."""
        if period == 'daily':
            # Compare with previous month
            if start_date.month == 1:
                prev_start = date(start_date.year - 1, 12, 1)
                prev_end = date(start_date.year, 1, 1) - timedelta(days=1)
            else:
                prev_start = date(start_date.year, start_date.month - 1, 1)
                if start_date.month - 1 == 12:
                    prev_end = date(start_date.year, 1, 1) - timedelta(days=1)
                else:
                    prev_end = date(start_date.year, start_date.month, 1) - timedelta(days=1)
        
        elif period == 'weekly':
            # Compare with previous month
            if start_date.month == 1:
                prev_start = date(start_date.year - 1, 12, 1)
                prev_end = date(start_date.year, 1, 1) - timedelta(days=1)
            else:
                prev_start = date(start_date.year, start_date.month - 1, 1)
                if start_date.month - 1 == 12:
                    prev_end = date(start_date.year, 1, 1) - timedelta(days=1)
                else:
                    prev_end = date(start_date.year, start_date.month, 1) - timedelta(days=1)
        
        else:  # monthly
            # Compare with previous year
            prev_start = date(start_date.year - 1, start_date.month, 1)
            if start_date.month == 12:
                prev_end = date(start_date.year, 1, 1) - timedelta(days=1)
            else:
                prev_end = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        
        # Get previous period sales
        prev_orders = Order.objects.filter(
            vendor=vendor,
            created_at__date__range=(prev_start, prev_end)
        )
        prev_sales = prev_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Get current period sales
        current_orders = Order.objects.filter(
            vendor=vendor,
            created_at__date__range=(start_date, end_date)
        )
        current_sales = current_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate percentage change
        if prev_sales > 0:
            percentage_change = ((current_sales - prev_sales) / prev_sales) * 100
        elif current_sales > 0:
            percentage_change = 100.0  # New sales, 100% increase
        else:
            percentage_change = 0.0
        
        return {
            "value": round(percentage_change, 1),
            "direction": "up" if percentage_change > 0 else "down" if percentage_change < 0 else "stable",
            "text": f"{abs(percentage_change):.1f}% {'Up' if percentage_change > 0 else 'Down' if percentage_change < 0 else 'No Change'} from previous {period}",
            "previous_period_sales": float(prev_sales),
            "current_period_sales": float(current_sales)
        }


