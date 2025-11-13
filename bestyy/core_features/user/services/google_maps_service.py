import logging
from typing import Optional, Dict, Any, List

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


class GoogleMapsService:
    """
    Google Maps based service for geocoding and distance calculation.
    Uses Geocoding API and Distance Matrix API.
    """

    def __init__(self) -> None:
        self.api_key: Optional[str] = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not self.api_key:
            logger.warning("Google Maps API key not configured")

    def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Convert an address string to latitude/longitude using Google Geocoding API.
        Returns dict with latitude, longitude and formatted_address or None.
        """
        # Already coordinates?
        if ',' in address:
            try:
                lat_str, lng_str = [p.strip() for p in address.split(',', 1)]
                lat, lng = float(lat_str), float(lng_str)
                return {
                    'latitude': lat,
                    'longitude': lng,
                    'formatted_address': address,
                    'raw_result': {'coordinates': [lng, lat]},
                }
            except Exception:
                pass

        if not self.api_key:
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": address, "key": self.api_key}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get('status') != 'OK' or not data.get('results'):
                logger.warning(f"No Google geocode results for: {address} (status={data.get('status')})")
                return None
            result = data['results'][0]
            loc = result['geometry']['location']  # {'lat':..., 'lng':...}
            return {
                'latitude': loc['lat'],
                'longitude': loc['lng'],
                'formatted_address': result.get('formatted_address', address),
                'raw_result': result,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error in Google geocoding for '{address}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error in Google geocoding for '{address}': {str(e)}")
            return None

    def calculate_distance(self, origin: str, destination: str, mode: str = 'driving') -> Optional[Dict[str, Any]]:
        """
        Calculate distance and duration using Google Distance Matrix API.
        origin/destination can be addresses or "lat,lng" strings.
        """
        if not self.api_key:
            return None
        try:
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": origin,
                "destinations": destination,
                "mode": mode,  # driving|walking|bicycling|transit
                "key": self.api_key,
            }
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if data.get('status') != 'OK':
                logger.error(f"Distance Matrix error: status={data.get('status')} error_message={data.get('error_message')}")
                return None

            rows = data.get('rows') or []
            if not rows or not rows[0].get('elements'):
                logger.error("No rows/elements in Distance Matrix response")
                return None
            elem = rows[0]['elements'][0]
            if elem.get('status') != 'OK':
                logger.error(f"Element status not OK: {elem.get('status')}")
                return None

            distance_meters = int(elem['distance']['value'])
            duration_seconds = int(elem['duration']['value'])
            distance_km = distance_meters / 1000.0

            # Duration text
            hours, remainder = divmod(duration_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            duration_text = f"{hours} hour {minutes} mins" if hours > 0 else f"{minutes} mins"

            # Distance text
            distance_text = f"{distance_meters:.0f} m" if distance_km < 1 else f"{distance_km:.1f} km"

            return {
                'distance_text': distance_text,
                'distance_value': distance_meters,
                'duration_text': duration_text,
                'duration_value': duration_seconds,
                'origin': origin,
                'destination': destination,
                'mode': mode,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error calculating distance: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return None

    def calculate_delivery_price(self, distance_km: float, base_price: float = 700.0, price_per_km: float = 120.0, minimum_price: float = 600.0) -> float:
        calculated_price = base_price + (distance_km * price_per_km)
        final_price = max(calculated_price, minimum_price)
        return round(final_price, 2)

    def get_distance_and_price(self, origin: str, destination: str, base_price: float = 700.0, price_per_km: float = 120.0, minimum_price: float = 600.0, mode: str = 'driving') -> Optional[Dict[str, Any]]:
        distance_info = self.calculate_distance(origin, destination, mode=mode)
        if not distance_info:
            return None
        distance_km = distance_info['distance_value'] / 1000.0
        delivery_price = self.calculate_delivery_price(distance_km, base_price, price_per_km, minimum_price)
        result = distance_info.copy()
        result.update({
            'distance_km': round(distance_km, 2),
            'delivery_price': delivery_price,
            'pricing_details': {
                'base_price': base_price,
                'price_per_km': price_per_km,
                'minimum_price': minimum_price,
            }
        })
        return result

    def validate_and_correct_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Validate an address and suggest corrections using Google Maps
        Returns corrected address info or None if invalid
        """
        if not self.api_key:
            return None

        try:
            # First, try to geocode the original address
            geocode_result = self.geocode_address(address)
            if geocode_result:
                return {
                    'original_address': address,
                    'corrected_address': geocode_result['formatted_address'],
                    'coordinates': {
                        'latitude': geocode_result['latitude'],
                        'longitude': geocode_result['longitude']
                    },
                    'place_id': geocode_result.get('raw_result', {}).get('place_id'),
                    'is_valid': True,
                    'confidence': 'high' if geocode_result['formatted_address'] != address else 'exact'
                }

            # If geocoding fails, try to find similar addresses using Places API
            places_result = self._find_similar_addresses(address)
            if places_result:
                return {
                    'original_address': address,
                    'suggestions': places_result,
                    'is_valid': False,
                    'confidence': 'low'
                }

            return {
                'original_address': address,
                'is_valid': False,
                'error': 'Address not found',
                'confidence': 'none'
            }

        except Exception as e:
            logger.error(f"Error validating address '{address}': {str(e)}")
            return None

    def _find_similar_addresses(self, address: str) -> Optional[List[Dict[str, Any]]]:
        """
        Find similar addresses using Google Places API text search
        """
        if not self.api_key:
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                "query": address,
                "key": self.api_key,
                "region": "ng"  # Nigeria region bias
            }
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('status') == 'OK' and data.get('results'):
                suggestions = []
                for result in data['results'][:3]:  # Top 3 suggestions
                    suggestions.append({
                        'formatted_address': result.get('formatted_address'),
                        'place_id': result.get('place_id'),
                        'coordinates': {
                            'latitude': result['geometry']['location']['lat'],
                            'longitude': result['geometry']['location']['lng']
                        },
                        'types': result.get('types', [])
                    })
                return suggestions

            return None

        except Exception as e:
            logger.error(f"Error finding similar addresses for '{address}': {str(e)}")
            return None

    def calculate_delivery_route(self, origin: str, destination: str, waypoints: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Calculate optimal delivery route with optional waypoints
        """
        if not self.api_key:
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin,
                "destination": destination,
                "mode": "driving",
                "key": self.api_key,
                "region": "ng",  # Nigeria region bias
                "alternatives": "false"  # Get only the best route
            }

            if waypoints:
                params["waypoints"] = "|".join(f"place_id:{wp}" for wp in waypoints if wp)

            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if data.get('status') == 'OK' and data.get('routes'):
                route = data['routes'][0]
                leg = route['legs'][0]  # Assuming single destination

                return {
                    'distance_text': leg['distance']['text'],
                    'distance_value': leg['distance']['value'],
                    'duration_text': leg['duration']['text'],
                    'duration_value': leg['duration']['value'],
                    'polyline': route.get('overview_polyline', {}).get('points'),
                    'steps': [
                        {
                            'instruction': step['html_instructions'],
                            'distance': step['distance']['text'],
                            'duration': step['duration']['text']
                        }
                        for step in leg['steps']
                    ],
                    'bounds': route.get('bounds'),
                    'warnings': route.get('warnings', [])
                }

            return None

        except Exception as e:
            logger.error(f"Error calculating delivery route: {str(e)}")
            return None

    def track_delivery_progress(self, order_id: str, courier_location: Dict[str, float], destination: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Track delivery progress and provide ETA updates
        """
        if not self.api_key:
            return None

        try:
            origin = f"{courier_location['latitude']},{courier_location['longitude']}"
            destination_str = f"{destination['latitude']},{destination['longitude']}"

            # Get current distance and time to destination
            distance_result = self.calculate_distance(origin, destination_str)
            if not distance_result:
                return None

            # Calculate progress percentage (this would need historical data in production)
            # For now, return current status
            return {
                'order_id': order_id,
                'current_distance_km': round(distance_result['distance_value'] / 1000, 2),
                'estimated_time_remaining': distance_result['duration_text'],
                'estimated_time_seconds': distance_result['duration_value'],
                'courier_location': courier_location,
                'destination': destination,
                'last_updated': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error tracking delivery progress for order {order_id}: {str(e)}")
            return None

    def get_address_suggestions(self, input_text: str, location_bias: Optional[Dict[str, float]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get address autocomplete suggestions using Google Places API
        """
        if not self.api_key:
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
            params = {
                "input": input_text,
                "key": self.api_key,
                "types": "address",
                "components": "country:ng",  # Nigeria only
                "language": "en"
            }

            if location_bias:
                params["location"] = f"{location_bias['latitude']},{location_bias['longitude']}"
                params["radius"] = "50000"  # 50km radius

            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('status') == 'OK' and data.get('predictions'):
                suggestions = []
                for prediction in data['predictions'][:5]:  # Top 5 suggestions
                    suggestions.append({
                        'description': prediction.get('description'),
                        'place_id': prediction.get('place_id'),
                        'types': prediction.get('types', []),
                        'structured_formatting': prediction.get('structured_formatting', {})
                    })
                return suggestions

            return []

        except Exception as e:
            logger.error(f"Error getting address suggestions for '{input_text}': {str(e)}")
            return None

    def validate_address_for_delivery(self, address: str, vendor_location: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Validate if an address is suitable for delivery from a vendor location
        """
        if not self.api_key:
            return None

        try:
            # First geocode the delivery address
            geocode_result = self.geocode_address(address)
            if not geocode_result:
                return {
                    'is_valid': False,
                    'error': 'Address not found',
                    'suggestions': []
                }

            delivery_coords = {
                'latitude': geocode_result['latitude'],
                'longitude': geocode_result['longitude']
            }

            # Calculate distance from vendor
            origin = f"{vendor_location['latitude']},{vendor_location['longitude']}"
            destination = f"{delivery_coords['latitude']},{delivery_coords['longitude']}"

            distance_result = self.calculate_distance(origin, destination)
            if not distance_result:
                return {
                    'is_valid': False,
                    'error': 'Cannot calculate delivery distance',
                    'coordinates': delivery_coords
                }

            distance_km = distance_result['distance_value'] / 1000.0

            # Check if within reasonable delivery distance (configurable)
            from decimal import Decimal
            from bestyy.core_features.user.models import SystemSettings
            max_delivery_distance = SystemSettings.get_setting('max_delivery_distance_km', Decimal('50.0'))

            if max_delivery_distance and distance_km > float(max_delivery_distance):
                return {
                    'is_valid': False,
                    'error': f'Delivery address is too far ({distance_km:.1f}km > {max_delivery_distance}km)',
                    'distance_km': distance_km,
                    'coordinates': delivery_coords
                }

            # Calculate delivery fee
            delivery_fee = self.calculate_delivery_price(distance_km)

            return {
                'is_valid': True,
                'coordinates': delivery_coords,
                'formatted_address': geocode_result['formatted_address'],
                'distance_km': round(distance_km, 2),
                'estimated_duration': distance_result['duration_text'],
                'delivery_fee': delivery_fee,
                'place_id': geocode_result.get('raw_result', {}).get('place_id')
            }

        except Exception as e:
            logger.error(f"Error validating delivery address '{address}': {str(e)}")
            return None



