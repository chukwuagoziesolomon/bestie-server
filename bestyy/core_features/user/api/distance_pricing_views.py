from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from user.services.google_maps_service import GoogleMapsService
import logging

logger = logging.getLogger(__name__)

class DistancePricingView(APIView):
    """
    API endpoint to calculate distance and delivery pricing between two locations
    """
    permission_classes = [AllowAny]  # Allow anyone to calculate pricing

    def post(self, request):
        """
        Calculate distance and pricing for delivery

        Expected request data:
        {
            "origin": "Lagos, Nigeria",  # or lat,lng format
            "destination": "Ikeja, Lagos, Nigeria",  # or lat,lng format
            "mode": "driving",  # optional: 'driving', 'walking', 'bicycling', 'transit'
            "base_price": 500.0,  # optional: base delivery fee in NGN
            "price_per_km": 50.0,  # optional: additional price per km in NGN
            "minimum_price": 300.0  # optional: minimum delivery price in NGN
        }
        """
        # Extract parameters from request
        origin = request.data.get('origin')
        destination = request.data.get('destination')
        mode = request.data.get('mode', 'driving')

        # Pricing parameters with defaults (tuned for Nigeria inner-city)
        base_price = float(request.data.get('base_price', 700.0))
        price_per_km = float(request.data.get('price_per_km', 120.0))
        minimum_price = float(request.data.get('minimum_price', 600.0))

        # Validate required parameters
        if not origin or not destination:
            return Response(
                {
                    'error': 'Both origin and destination are required',
                    'example': {
                        'origin': 'Lagos, Nigeria',
                        'destination': 'Ikeja, Lagos, Nigeria'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate Google Maps mode
        google_modes = ['driving', 'walking', 'bicycling', 'transit']
        if mode not in google_modes:
            return Response(
                {
                    'error': f'Invalid mode. Must be one of: {", ".join(google_modes)}',
                    'valid_modes': google_modes
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if Google Maps API key is configured
        if not getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
            return Response(
                {
                    'error': 'Google Maps API key not configured',
                    'message': 'Distance calculation service is currently unavailable. Please configure GOOGLE_MAPS_API_KEY in settings.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            # Initialize Google Maps service
            maps_service = GoogleMapsService()

            # Calculate distance and pricing
            result = maps_service.get_distance_and_price(
                origin=origin,
                destination=destination,
                base_price=base_price,
                price_per_km=price_per_km,
                minimum_price=minimum_price,
                mode=mode  # Use Google mode directly (driving, walking, bicycling, transit)
            )

            if not result:
                return Response(
                    {
                        'error': 'Unable to calculate distance',
                        'message': 'Please check the addresses and try again'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Return successful response
            return Response({
                'success': True,
                'data': result,
                'pricing_breakdown': {
                    'base_fee': base_price,
                    'distance_fee': round((result['distance_km'] * price_per_km), 2),
                    'total': result['delivery_price']
                }
            })

        except Exception as e:
            logger.error(f"Error in distance pricing calculation: {str(e)}")
            return Response(
                {
                    'error': 'Internal server error',
                    'message': 'Unable to process distance calculation request'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GeocodeAddressView(APIView):
    """
    API endpoint to geocode an address (convert address to coordinates)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Convert an address to latitude and longitude coordinates

        Expected request data:
        {
            "address": "Lagos, Nigeria"
        }
        """
        address = request.data.get('address')

        if not address:
            return Response(
                {
                    'error': 'Address is required',
                    'example': {'address': 'Lagos, Nigeria'}
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if Google Maps API key is configured
        if not getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
            return Response(
                {
                    'error': 'Google Maps API key not configured',
                    'message': 'Geocoding service is currently unavailable. Please configure GOOGLE_MAPS_API_KEY in settings.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            maps_service = GoogleMapsService()
            result = maps_service.geocode_address(address)

            if not result:
                return Response(
                    {
                        'error': 'Unable to geocode address',
                        'message': 'Please check the address and try again'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'success': True,
                'data': result
            })

        except Exception as e:
            logger.error(f"Error in address geocoding: {str(e)}")
            return Response(
                {
                    'error': 'Internal server error',
                    'message': 'Unable to process geocoding request'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )