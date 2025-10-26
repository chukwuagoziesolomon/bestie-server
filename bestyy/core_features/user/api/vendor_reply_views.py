"""
Vendor automatic reply management API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from bestyy.core_features.user.models import Order, VendorProfile
from bestyy.core_features.user.services.notification_service import AutomaticVendorReplyService


class VendorReplyManagementView(APIView):
    """
    Manage automatic replies for vendors
    
    POST /api/user/vendor/replies/send/
    GET /api/user/vendor/replies/history/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send automatic reply to vendor"""
        try:
            order_id = request.data.get('order_id')
            reply_type = request.data.get('reply_type', 'order_confirmation')
            vendor_id = request.data.get('vendor_id')
            
            if not order_id:
                return Response({
                    'success': False,
                    'error': 'Order ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get order
            order = get_object_or_404(Order, id=order_id)
            
            # Check if user is the vendor or admin
            if not (request.user == order.vendor.user or request.user.is_staff):
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Prepare order data
            order_data = {
                'vendor': order.vendor,
                'order': order,
                'order_items': self._get_order_items_data(order),
                'customer': {
                    'name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'email': order.user.email,
                    'phone': getattr(order.user, 'phone', 'Not provided')
                },
                'total_amount': float(order.total_price)
            }
            
            # Send automatic reply
            results = AutomaticVendorReplyService.send_automatic_reply(order_data, reply_type)
            
            return Response({
                'success': True,
                'message': f'Automatic reply sent successfully',
                'reply_type': reply_type,
                'order_id': order.id,
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Get automatic reply history for vendor"""
        try:
            # Get vendor's orders with reply history
            vendor = request.user.vendor if hasattr(request.user, 'vendor') else None
            if not vendor:
                return Response({
                    'success': False,
                    'error': 'User is not a vendor'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get recent orders
            orders = Order.objects.filter(
                vendor=vendor
            ).order_by('-created_at')[:20]  # Last 20 orders
            
            reply_history = []
            for order in orders:
                reply_history.append({
                    'order_id': order.id,
                    'order_number': f"#{order.id}",
                    'customer_name': f"{order.user.first_name} {order.user.last_name}".strip(),
                    'total_amount': float(order.total_price),
                    'status': order.status,
                    'order_date': order.created_at.isoformat(),
                    'reply_sent': True,  # Assuming reply was sent when order was placed
                    'reply_type': 'order_confirmation'
                })
            
            return Response({
                'success': True,
                'reply_history': reply_history,
                'vendor': {
                    'id': vendor.id,
                    'business_name': vendor.business_name,
                    'whatsapp_number': getattr(vendor, 'whatsapp_number', 'Not set'),
                    'contact_email': vendor.user.email if vendor.user else 'Not set'
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_order_items_data(self, order):
        """Get order items data for notifications"""
        order_items = []
        
        if hasattr(order, 'items'):
            for item in order.items.all():
                order_items.append({
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'base_price': float(item.base_price),
                    'variants': item.variants,
                    'special_instructions': item.special_instructions,
                    'total_price': float(item.total_price)
                })
        
        return order_items


class VendorReplySettingsView(APIView):
    """
    Manage vendor reply settings
    
    GET /api/user/vendor/replies/settings/
    PUT /api/user/vendor/replies/settings/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get vendor reply settings"""
        try:
            vendor = request.user.vendor if hasattr(request.user, 'vendor') else None
            if not vendor:
                return Response({
                    'success': False,
                    'error': 'User is not a vendor'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get vendor settings (you might want to create a VendorSettings model)
            settings = {
                'auto_reply_enabled': True,
                'whatsapp_notifications': bool(getattr(vendor, 'whatsapp_number', None)),
                'websocket_notifications': True,
                'reply_types': {
                    'order_confirmation': True,
                    'order_reminder': True,
                    'order_update': True
                },
                'reminder_interval_minutes': 15,
                'business_hours': {
                    'start': '08:00',
                    'end': '22:00'
                }
            }
            
            return Response({
                'success': True,
                'settings': settings,
                'vendor': {
                    'id': vendor.id,
                    'business_name': vendor.business_name,
                    'whatsapp_number': getattr(vendor, 'whatsapp_number', None),
                    'contact_email': vendor.user.email if vendor.user else None
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        """Update vendor reply settings"""
        try:
            vendor = request.user.vendor if hasattr(request.user, 'vendor') else None
            if not vendor:
                return Response({
                    'success': False,
                    'error': 'User is not a vendor'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Update vendor settings
            whatsapp_number = request.data.get('whatsapp_number')
            if whatsapp_number:
                vendor.whatsapp_number = whatsapp_number
                vendor.save()
            
            return Response({
                'success': True,
                'message': 'Settings updated successfully',
                'updated_fields': ['whatsapp_number'] if whatsapp_number else []
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






