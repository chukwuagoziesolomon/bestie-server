"""
Order summary API for calculating totals with delivery fees
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404

from bestyy.restaurant_features.product.models import Product as MenuItem
from bestyy.core_features.user.models import VendorProfile
from bestyy.core_features.user.services.google_maps_service import GoogleMapsService


class OrderSummaryView(APIView):
    """
    Calculate order summary with delivery fees based on distance

    POST /api/user/order-summary/
    {
        "cart_items": [
            {"menu_item_id": 1, "quantity": 2},
            {"menu_item_id": 3, "quantity": 1}
        ],
        "delivery_address": "123 Lagos Street, Lagos, Nigeria",
        "vendor_id": 1
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Calculate order summary with delivery costs"""
        try:
            data = request.data
            cart_items = data.get('cart_items', [])
            delivery_address = data.get('delivery_address', '').strip()
            vendor_id = data.get('vendor_id')

            if not cart_items:
                return Response({
                    'success': False,
                    'error': 'No items in cart'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not delivery_address:
                return Response({
                    'success': False,
                    'error': 'Delivery address is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not vendor_id:
                return Response({
                    'success': False,
                    'error': 'Vendor ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get vendor
            vendor = get_object_or_404(VendorProfile, id=vendor_id)

            # Validate and get menu items
            menu_item_ids = []
            quantities_by_id = {}
            for item in cart_items:
                try:
                    mid = int(item.get('menu_item_id'))
                    qty = int(item.get('quantity', 1))
                    if qty < 1:
                        continue
                    menu_item_ids.append(mid)
                    quantities_by_id[mid] = qty
                except (ValueError, TypeError):
                    continue

            if not menu_item_ids:
                return Response({
                    'success': False,
                    'error': 'No valid items found'
                }, status=status.HTTP_400_BAD_REQUEST)

            menu_items = list(MenuItem.objects.filter(id__in=menu_item_ids, is_available=True).select_related('vendor'))
            if len(menu_items) == 0:
                return Response({
                    'success': False,
                    'error': 'No valid items found'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Enforce single vendor
            vendor_ids = {mi.vendor.id for mi in menu_items}
            if len(vendor_ids) > 1:
                return Response({
                    'success': False,
                    'error': 'Cart contains items from multiple vendors'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate subtotal
            subtotal = sum(float(mi.price) * quantities_by_id.get(mi.pk, 0) for mi in menu_items)

            # Calculate delivery fee based on distance
            maps_service = GoogleMapsService()
            distance_result = maps_service.get_distance_and_price(vendor.business_address, delivery_address)

            if distance_result:
                delivery_fee = distance_result['delivery_price']
                distance_km = distance_result['distance_km']
                estimated_time = distance_result['duration_text']
                distance_text = distance_result['distance_text']
            else:
                # Fallback values if distance calculation fails
                delivery_fee = 700.0
                distance_km = 0
                estimated_time = "30-45 minutes"
                distance_text = "Unknown"

            # Calculate platform fee (5% of subtotal)
            platform_fee = subtotal * 0.05

            # Calculate grand total
            grand_total = subtotal + delivery_fee + platform_fee

            # Prepare item breakdown
            items_breakdown = []
            for menu_item in menu_items:
                qty = quantities_by_id.get(menu_item.pk, 0)
                if qty > 0:
                    items_breakdown.append({
                        'id': menu_item.pk,
                        'name': getattr(menu_item, 'dish_name', menu_item.name),
                        'price': float(menu_item.price),
                        'quantity': qty,
                        'total': float(menu_item.price) * qty
                    })

            return Response({
                'success': True,
                'summary': {
                    'subtotal': round(subtotal, 2),
                    'delivery_fee': round(delivery_fee, 2),
                    'platform_fee': round(platform_fee, 2),
                    'grand_total': round(grand_total, 2),
                    'currency': 'NGN'
                },
                'delivery_info': {
                    'distance_km': round(distance_km, 2),
                    'distance_text': distance_text,
                    'estimated_time': estimated_time,
                    'vendor_address': vendor.business_address,
                    'delivery_address': delivery_address
                },
                'items': items_breakdown,
                'item_count': len(items_breakdown),
                'vendor': {
                    'id': vendor.id,
                    'name': vendor.business_name,
                    'address': vendor.business_address
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)