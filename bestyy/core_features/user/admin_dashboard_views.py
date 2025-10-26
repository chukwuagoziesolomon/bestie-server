"""
Views for admin dashboard functionality.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from bestyy.core_features.user.models import User, CourierProfile, VendorProfile, Order

class AdminDashboardMetricsView(APIView):
    """
    API endpoint to get metrics for the admin dashboard.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        # Get date range for metrics (default: last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # User metrics
        total_users = User.objects.count()
        new_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
        
        # Courier metrics
        total_couriers = CourierProfile.objects.count()
        verified_couriers = CourierProfile.objects.filter(verification_status='verified').count()
        pending_couriers = CourierProfile.objects.filter(verification_status='pending').count()
        
        # Vendor metrics
        total_vendors = VendorProfile.objects.count()
        verified_vendors = VendorProfile.objects.filter(verification_status='verified').count()
        pending_vendors = VendorProfile.objects.filter(verification_status='pending').count()
        
        # Order metrics
        total_orders = Order.objects.count()
        recent_orders = Order.objects.filter(created_at__date__range=[start_date, end_date]).count()
        
        # Active users (users who logged in the last 7 days)
        active_users = User.objects.filter(
            last_login__date__gte=timezone.now().date() - timedelta(days=7)
        ).count()
        
        # Prepare response data
        data = {
            'users': {
                'total': total_users,
                'new': new_users,
                'active': active_users,
            },
            'couriers': {
                'total': total_couriers,
                'verified': verified_couriers,
                'pending': pending_couriers,
            },
            'vendors': {
                'total': total_vendors,
                'verified': verified_vendors,
                'pending': pending_vendors,
            },
            'orders': {
                'total': total_orders,
                'recent': recent_orders,
            },
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)
