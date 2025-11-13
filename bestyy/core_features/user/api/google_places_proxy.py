"""
Google Places API proxy to handle CORS issues for frontend autocomplete
"""
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse


class GooglePlacesProxyView(APIView):
    """
    Proxy for Google Places Autocomplete API to avoid CORS issues

    GET /api/user/google-places/autocomplete/?input=lagos
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Proxy Google Places Autocomplete requests"""
        try:
            # Get parameters from request
            input_text = request.GET.get('input', '')
            types = request.GET.get('types', 'address')
            components = request.GET.get('components', 'country:ng')
            language = request.GET.get('language', 'en')

            # Validate required parameters
            if not input_text:
                return Response({
                    'error': 'Input parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Use API key from server environment (secure)
            api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
            if not api_key:
                return Response({
                    'error': 'Google Maps API key not configured on server'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Use Google Places API (New) - POST with JSON body
            google_url = "https://places.googleapis.com/v1/places:autocomplete"

            # Build request body for Places API (New)
            request_body = {
                'input': input_text
            }

            # Add location bias if provided (new API format)
            if request.GET.get('location'):
                try:
                    lat_str, lng_str = request.GET['location'].split(',')
                    lat, lng = float(lat_str.strip()), float(lng_str.strip())
                    request_body['locationBias'] = {
                        'circle': {
                            'center': {
                                'latitude': lat,
                                'longitude': lng
                            },
                            'radius': 50000.0  # 50km radius
                        }
                    }
                except (ValueError, AttributeError):
                    pass

            # Add region code for Nigeria if components include country:ng
            if components and 'country:ng' in components:
                request_body['regionCode'] = 'NG'

            # Add language code
            if language:
                request_body['languageCode'] = language

            # Make request to Google Places API (New)
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'suggestions.placePrediction.placeId,suggestions.placePrediction.text,suggestions.placePrediction.structuredFormat'
            }

            response = requests.post(google_url, json=request_body, headers=headers, timeout=10)
            response.raise_for_status()

            google_data = response.json()

            # Transform Places API (New) response to legacy format for frontend compatibility
            transformed_response = {
                'status': 'OK' if 'suggestions' in google_data and google_data['suggestions'] else 'ZERO_RESULTS',
                'predictions': []
            }

            # Convert new API format to legacy format
            if 'suggestions' in google_data:
                for suggestion in google_data['suggestions']:
                    if 'placePrediction' in suggestion:
                        prediction = suggestion['placePrediction']
                        legacy_prediction = {
                            'description': prediction.get('text', {}).get('text', ''),
                            'place_id': prediction.get('placeId', ''),
                            'structured_formatting': {
                                'main_text': prediction.get('structuredFormat', {}).get('mainText', {}).get('text', ''),
                                'secondary_text': prediction.get('structuredFormat', {}).get('secondaryText', {}).get('text', '')
                            }
                        }
                        transformed_response['predictions'].append(legacy_prediction)

            return JsonResponse(transformed_response)

        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'Google Places API request failed: {str(e)}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GooglePlacesDetailsProxyView(APIView):
    """
    Proxy for Google Places Details API (Legacy)

    GET /api/user/google-places/details/?place_id=PLACE_ID
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Proxy Google Places Details requests"""
        try:
            place_id = request.GET.get('place_id', '')
            language = request.GET.get('language', 'en')

            if not place_id:
                return Response({
                    'error': 'place_id parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Use API key from server environment (secure)
            api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
            if not api_key:
                return Response({
                    'error': 'Google Maps API key not configured on server'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Use Google Places API (New) for place details - GET request with headers
            google_url = f"https://places.googleapis.com/v1/places/{place_id}"

            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'id,displayName,formattedAddress,location,types'
            }

            # Make GET request to Google Places API (New) - no params, just headers
            response = requests.get(google_url, headers=headers, timeout=10)
            response.raise_for_status()

            google_data = response.json()

            # Transform Places API (New) response to legacy format for frontend compatibility
            transformed_response = {
                'status': 'OK',
                'result': {
                    'place_id': google_data.get('id', ''),
                    'formatted_address': google_data.get('formattedAddress', ''),
                    'name': google_data.get('displayName', {}).get('text', ''),
                    'geometry': {
                        'location': {
                            'lat': google_data.get('location', {}).get('latitude', 0),
                            'lng': google_data.get('location', {}).get('longitude', 0)
                        }
                    },
                    'types': google_data.get('types', [])
                }
            }

            return JsonResponse(transformed_response)

        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'Google Places Details API request failed: {str(e)}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)