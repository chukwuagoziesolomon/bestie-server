from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, F
from bestyy.user.models import Order, MenuItem
from .serializers import DashboardAnalyticsSerializer

def percent_change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)

class DashboardAnalyticsView(APIView):
    def get(self, request):
        now = timezone.now()
        start_this_week = now - timedelta(days=now.weekday())
        start_last_week = start_this_week - timedelta(days=7)
        end_last_week = start_this_week

        # Orders this week and last week
        orders_this_week = Order.objects.filter(order_placed_at__gte=start_this_week)
        orders_last_week = Order.objects.filter(order_placed_at__gte=start_last_week, order_placed_at__lt=end_last_week)

        completed_this = orders_this_week.filter(status='completed').count()
        completed_last = orders_last_week.filter(status='completed').count()
        rejected_this = orders_this_week.filter(status='rejected').count()
        rejected_last = orders_last_week.filter(status='rejected').count()
        total_revenue = orders_this_week.aggregate(total=Sum('total_price'))['total'] or 0

        # Top dishes this week
        top_dishes_qs = (
            MenuItem.objects
            .filter(order__in=orders_this_week)
            .annotate(orders=Count('order'), revenue=Sum('order__total_price'))
            .order_by('-orders')[:3]
        )

        # Top dishes last week for % change
        last_week_dishes = (
            MenuItem.objects
            .filter(order__in=orders_last_week)
            .annotate(orders=Count('order'))
        )
        last_week_dish_map = {d.dish_name: d.orders for d in last_week_dishes}

        top_dishes = []
        for dish in top_dishes_qs:
            name = dish.dish_name
            orders = dish.orders
            revenue = dish.revenue or 0
            last_orders = last_week_dish_map.get(name, 0)
            change_pct = percent_change(orders, last_orders)
            top_dishes.append({
                'dish_name': name,
                'orders': orders,
                'revenue': revenue,
                'change_pct': change_pct,
            })

        data = {
            'order_activity': {
                'total': orders_this_week.count(),
                'completed': completed_this,
                'rejected': rejected_this,
                'total_revenue': total_revenue,
                'completed_change_pct': percent_change(completed_this, completed_last),
                'rejected_change_pct': percent_change(rejected_this, rejected_last),
            },
            'top_dishes': top_dishes,
        }
        serializer = DashboardAnalyticsSerializer(data)
        return Response(serializer.data)
