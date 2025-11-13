"""
Google Maps location services for checkout and delivery
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings

from bestyy.core_features.user.services.google_maps_service import GoogleMapsService
from bestyy.core_features.user.models import VendorProfile


class AddressGeocodeView(APIView):
    """
    Geocode an address to get coordinates

    POST /api/user/location/geocode/
    {
        "address": "123 Lagos Street, Lagos, Nigeria"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Geocode an address"""
        address = request.data.get('address', '').strip()

        if not address:
            return Response({
                'success': False,
                'error': 'Address is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        service = GoogleMapsService()
        result = service.geocode_address(address)

        if result:
            return Response({
                'success': True,
                'location': {
                    'latitude': result['latitude'],
                    'longitude': result['longitude'],
                    'formatted_address': result['formatted_address'],
                    'place_id': result.get('raw_result', {}).get('place_id')
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Address not found or geocoding service unavailable'
            }, status=status.HTTP_400_BAD_REQUEST)


class AddressSuggestionsView(APIView):
    """
    Get address autocomplete suggestions (proxy for frontend to avoid CORS)

    GET /api/user/location/suggestions/?input=lagos&location=6.5244,3.3792
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Get address suggestions via backend proxy"""
        input_text = request.query_params.get('input', '').strip()
        location = request.query_params.get('location')  # "lat,lng"

        if not input_text:
            return Response({
                'success': False,
                'error': 'Input text is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse location bias
        location_bias = None
        if location:
            try:
                lat_str, lng_str = location.split(',')
                location_bias = {
                    'latitude': float(lat_str.strip()),
                    'longitude': float(lng_str.strip())
                }
            except (ValueError, AttributeError):
                pass

        service = GoogleMapsService()
        suggestions = service.get_address_suggestions(input_text, location_bias)

        if suggestions is not None:
            return Response({
                'success': True,
                'suggestions': suggestions
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Address suggestion service unavailable'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DeliveryValidationView(APIView):
    """
    Validate delivery address and calculate delivery cost

    POST /api/user/location/validate-delivery/
    {
        "address": "123 Lagos Street, Lagos, Nigeria",
        "vendor_id": 1
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate delivery address for a vendor"""
        address = request.data.get('address', '').strip()
        vendor_id = request.data.get('vendor_id')

        if not address:
            return Response({
                'success': False,
                'error': 'Address is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not vendor_id:
            return Response({
                'success': False,
                'error': 'Vendor ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get vendor
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        # Get vendor location (you might want to add lat/lng fields to VendorProfile)
        # For now, geocode the vendor address
        service = GoogleMapsService()

        # Geocode vendor address
        vendor_geocode = service.geocode_address(vendor.business_address)
        if not vendor_geocode:
            return Response({
                'success': False,
                'error': 'Unable to locate vendor address'
            }, status=status.HTTP_400_BAD_REQUEST)

        vendor_location = {
            'latitude': vendor_geocode['latitude'],
            'longitude': vendor_geocode['longitude']
        }

        # Validate delivery address
        validation_result = service.validate_address_for_delivery(address, vendor_location)

        if validation_result:
            return Response({
                'success': True,
                'validation': validation_result
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Delivery validation failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class DistanceCalculationView(APIView):
    """
    Calculate distance and delivery cost between two addresses

    POST /api/user/location/distance/
    {
        "origin": "Vendor Address, Lagos",
        "destination": "Customer Address, Lagos"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Calculate distance and delivery cost"""
        origin = request.data.get('origin', '').strip()
        destination = request.data.get('destination', '').strip()

        if not origin or not destination:
            return Response({
                'success': False,
                'error': 'Both origin and destination addresses are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        service = GoogleMapsService()
        result = service.get_distance_and_price(origin, destination)

        if result:
            return Response({
                'success': True,
                'distance': {
                    'text': result['distance_text'],
                    'value': result['distance_value'],
                    'km': result['distance_km']
                },
                'duration': {
                    'text': result['duration_text'],
                    'value': result['duration_value']
                },
                'delivery_price': result['delivery_price'],
                'pricing_details': result['pricing_details']
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Distance calculation failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class LocationServiceStatusView(APIView):
    """
    Check Google Maps service status

    GET /api/user/location/status/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Check service status"""
        service = GoogleMapsService()
        api_key_configured = service.api_key is not None

        # Test with a simple geocode
        test_result = None
        if api_key_configured:
            test_result = service.geocode_address("Lagos, Nigeria")

        return Response({
            'success': True,
            'status': {
                'api_key_configured': api_key_configured,
                'service_available': test_result is not None,
                'test_location': test_result['formatted_address'] if test_result else None
            }
        }, status=status.HTTP_200_OK)