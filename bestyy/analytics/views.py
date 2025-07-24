from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Avg, F, ExpressionWrapper, DurationField
from datetime import timedelta
from user.models import Order

# Vendor Transaction History and Total Earnings API
class VendorTransactionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'vendor_profile'):
            return Response({"detail": "You do not have a vendor profile. Please register as a vendor to access transactions."}, status=403)
        vendor = user.vendor_profile

        # Get all completed/paid orders for this vendor
        orders = Order.objects.filter(vendor=vendor, payment_confirmed=True).order_by('-created_at')

        # Transaction history: list of dicts
        transactions = [
            {
                "order_id": order.id,
                "amount": float(order.total_price),
                "date": order.created_at.strftime('%Y-%m-%d %H:%M'),
                "status": order.status,
                "customer": str(order.user) if hasattr(order, 'user') else None
            }
            for order in orders
        ]

        # Total earnings
        total_earnings = orders.aggregate(total=Sum('total_price'))['total'] or 0

        return Response({
            "total_earnings": float(total_earnings),
            "transactions": transactions
        })

# Dashboard Analytics API
class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Check if user has a vendor profile
        if not hasattr(user, 'vendor_profile'):
            return Response(
                {"detail": "You do not have a vendor profile. Please register as a vendor to access the dashboard."},
                status=403
            )
        vendor = user.vendor_profile
        
        # Date calculations
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_week_start = today - timedelta(days=7)
        last_week_end = today - timedelta(days=1)
        
        # Filter orders for this vendor
        vendor_orders = Order.objects.filter(vendor=vendor)
        today_orders = vendor_orders.filter(created_at__date=today)
        yesterday_orders = vendor_orders.filter(created_at__date=yesterday)
        
        # Calculate total orders (all time for this vendor)
        total_orders = vendor_orders.count()
        
        # Calculate today's metrics
        todays_order_count = today_orders.count()
        todays_sales = today_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Calculate total sales (all time for this vendor)
        total_sales = vendor_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Calculate pending orders (payment confirmed but user hasn't confirmed receipt)
        pending_orders = vendor_orders.filter(
            payment_confirmed=True,
            user_receipt_confirmed=False,
            status__in=['delivered', 'ready']
        ).count()
        
        # Calculate delivery time (average delivery time for completed orders)
        completed_orders = vendor_orders.filter(
            user_receipt_confirmed=True,
            delivered_at__isnull=False
        )
        # Annotate each order with delivery time in minutes
        completed_orders = completed_orders.annotate(
            delivery_time=ExpressionWrapper(
                F('delivered_at') - F('order_placed_at'),
                output_field=DurationField()
            )
        )
        # Calculate average delivery time in minutes
        avg_delivery_minutes = completed_orders.aggregate(
            avg_time=Avg(ExpressionWrapper(F('delivery_time') / 60, output_field=DurationField()))
        )['avg_time']
        if avg_delivery_minutes is None:
            avg_delivery_minutes = 15  # Default to 15 minutes if no data
        else:
            avg_delivery_minutes = int(avg_delivery_minutes.total_seconds() / 60)
        delivery_time = f"{int(avg_delivery_minutes)}-{int(avg_delivery_minutes + 5)}mins"
        
        # Calculate DAILY percentage changes (today vs yesterday)
        yesterday_order_count = yesterday_orders.count()
        yesterday_sales = yesterday_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Daily order count percentage change
        if yesterday_order_count > 0:
            daily_order_percentage_change = ((todays_order_count - yesterday_order_count) / yesterday_order_count) * 100
        else:
            daily_order_percentage_change = 100 if todays_order_count > 0 else 0
            
        # Daily sales percentage change
        if yesterday_sales > 0:
            daily_sales_percentage_change = ((todays_sales - yesterday_sales) / yesterday_sales) * 100
        else:
            daily_sales_percentage_change = 100 if todays_sales > 0 else 0
            
        # Daily pending orders percentage change
        yesterday_pending = vendor_orders.filter(
            payment_confirmed=True,
            user_receipt_confirmed=False,
            status__in=['delivered', 'ready'],
            created_at__date=yesterday
        ).count()
        
        if yesterday_pending > 0:
            daily_pending_percentage_change = ((pending_orders - yesterday_pending) / yesterday_pending) * 100
        else:
            daily_pending_percentage_change = 100 if pending_orders > 0 else 0
        
        # Calculate WEEKLY percentage changes (this week vs last week)
        # This week (last 7 days including today)
        this_week_start = today - timedelta(days=6)
        this_week_orders = vendor_orders.filter(created_at__date__gte=this_week_start, created_at__date__lte=today)
        this_week_order_count = this_week_orders.count()
        this_week_sales = this_week_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Last week (7 days before this week)
        last_week_orders = vendor_orders.filter(created_at__date__gte=last_week_start, created_at__date__lte=last_week_end)
        last_week_order_count = last_week_orders.count()
        last_week_sales = last_week_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Weekly order count percentage change
        if last_week_order_count > 0:
            weekly_order_percentage_change = ((this_week_order_count - last_week_order_count) / last_week_order_count) * 100
        else:
            weekly_order_percentage_change = 100 if this_week_order_count > 0 else 0
            
        # Weekly sales percentage change
        if last_week_sales > 0:
            weekly_sales_percentage_change = ((this_week_sales - last_week_sales) / last_week_sales) * 100
        else:
            weekly_sales_percentage_change = 100 if this_week_sales > 0 else 0
        
        # Sales chart for current month
        current_month = int(request.GET.get('month', today.month))
        current_year = int(request.GET.get('year', today.year))
        sales_chart = []
        
        # Get number of days in current month
        import calendar
        num_days = calendar.monthrange(current_year, current_month)[1]
        
        for day in range(1, num_days + 1):
            day_orders = vendor_orders.filter(
                created_at__year=current_year,
                created_at__month=current_month,
                created_at__day=day
            )
            day_sales = day_orders.aggregate(total=Sum('total_price'))['total'] or 0
            sales_chart.append({
                "label": f"{day} {calendar.month_abbr[current_month]}",
                "sales": float(day_sales),
                "orders": day_orders.count()
            })

        return Response({
            "total_orders": total_orders,  # Total orders all time
            "todays_order": todays_order_count,  # Orders today
            "total_sales": float(total_sales),  # Total sales all time
            "total_pending": pending_orders,
            "delivery_time": delivery_time,
            "sales_chart": sales_chart,
            "percentage_changes": {
                "orders": {
                    "daily": {
                        "value": daily_order_percentage_change,
                        "direction": "up" if daily_order_percentage_change >= 0 else "down",
                        "text": f"{abs(daily_order_percentage_change):.1f}% {'Up' if daily_order_percentage_change >= 0 else 'Down'} from yesterday"
                    },
                    "weekly": {
                        "value": weekly_order_percentage_change,
                        "direction": "up" if weekly_order_percentage_change >= 0 else "down",
                        "text": f"{abs(weekly_order_percentage_change):.1f}% {'Up' if weekly_order_percentage_change >= 0 else 'Down'} from last week"
                    }
                },
                "sales": {
                    "daily": {
                        "value": daily_sales_percentage_change,
                        "direction": "up" if daily_sales_percentage_change >= 0 else "down",
                        "text": f"{abs(daily_sales_percentage_change):.1f}% {'Up' if daily_sales_percentage_change >= 0 else 'Down'} from yesterday"
                    },
                    "weekly": {
                        "value": weekly_sales_percentage_change,
                        "direction": "up" if weekly_sales_percentage_change >= 0 else "down",
                        "text": f"{abs(weekly_sales_percentage_change):.1f}% {'Up' if weekly_sales_percentage_change >= 0 else 'Down'} from last week"
                    }
                },
                "pending": {
                    "daily": {
                        "value": daily_pending_percentage_change,
                        "direction": "up" if daily_pending_percentage_change >= 0 else "down",
                        "text": f"{abs(daily_pending_percentage_change):.1f}% {'Up' if daily_pending_percentage_change >= 0 else 'Down'} from yesterday"
                    }
                }
            }
        })
