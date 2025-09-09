from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from datetime import timedelta

from user.models import Order
from user.api.serializers import DeliverySerializer

class CourierDeliveriesView(APIView):
    """
    API endpoint to list all deliveries for the authenticated courier.
    
    Query Parameters:
    - status: Filter by order status (e.g., 'pending', 'out_for_delivery', 'delivered', 'completed')
    - date: Filter by delivery date (YYYY-MM-DD)
    - limit: Number of results to return (default: 10)
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
        status_filter = request.query_params.get('status')
        date_filter = request.query_params.get('date')
        limit = int(request.query_params.get('limit', 10))
        
        # Base queryset
        deliveries = Order.objects.filter(courier=courier)
        
        # Apply filters
        if status_filter:
            deliveries = deliveries.filter(status=status_filter)
            
        if date_filter:
            deliveries = deliveries.filter(delivered_at__date=date_filter)
        
        # Order by most recent first
        deliveries = deliveries.order_by('-created_at')
        
        # Calculate additional metrics BEFORE applying limit
        total_deliveries = deliveries.count()
        total_earnings = sum(delivery.total_price for delivery in deliveries if delivery.total_price)
        
        # Calculate average delivery time for completed deliveries BEFORE applying limit
        completed_deliveries = deliveries.filter(
            status__in=['delivered', 'completed'],
            delivered_at__isnull=False,
            created_at__isnull=False
        )
        
        # Apply limit AFTER calculating metrics
        deliveries = deliveries[:limit]
        
        avg_delivery_time = None
        if completed_deliveries.exists():
            total_seconds = sum(
                (d.delivered_at - d.created_at).total_seconds()
                for d in completed_deliveries
                if d.delivered_at and d.created_at
            )
            avg_delivery_time = total_seconds / completed_deliveries.count() / 60  # in minutes
        
        # Serialize the data
        serializer = DeliverySerializer(deliveries, many=True)
        
        # Prepare response
        response_data = {
            'count': total_deliveries,
            'total_earnings': float(total_earnings) if total_earnings else 0,
            'average_delivery_time_minutes': round(avg_delivery_time, 2) if avg_delivery_time else None,
            'deliveries': serializer.data
        }
        
        return Response(response_data)
