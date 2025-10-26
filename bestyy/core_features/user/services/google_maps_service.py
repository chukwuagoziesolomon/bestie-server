import logging
from typing import Optional, Dict, Any

import requests
from django.conf import settings


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



