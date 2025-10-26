"""
Simple Location Service for Nigerian GPS-based proximity matching
Uses external GPS services and mandatory location data
"""
import logging
import math
import requests
from typing import Dict, List, Optional, Tuple
from django.db.models import Q
from django.conf import settings
from ..models import VendorProfile, CourierProfile

logger = logging.getLogger(__name__)


class SimpleLocationService:
    """
    Simple location service using GPS coordinates and external services
    """
    
    def __init__(self):
        # Nigerian states for validation
        self.nigerian_states = [
            'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa',
            'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo',
            'Ekiti', 'Enugu', 'FCT', 'Gombe', 'Imo', 'Jigawa', 'Kaduna',
            'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa',
            'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers',
            'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
        ]
        
        # Major Nigerian cities with approximate coordinates for validation
        self.major_cities = {
            'Lagos': {'lat': 6.5244, 'lng': 3.3792, 'state': 'Lagos'},
            'Abuja': {'lat': 9.0765, 'lng': 7.3986, 'state': 'FCT'},
            'Kano': {'lat': 12.0022, 'lng': 8.5920, 'state': 'Kano'},
            'Ibadan': {'lat': 7.3776, 'lng': 3.9470, 'state': 'Oyo'},
            'Port Harcourt': {'lat': 4.8156, 'lng': 7.0498, 'state': 'Rivers'},
            'Benin City': {'lat': 6.3350, 'lng': 5.6037, 'state': 'Edo'},
            'Kaduna': {'lat': 10.5200, 'lng': 7.4382, 'state': 'Kaduna'},
            'Maiduguri': {'lat': 11.8333, 'lng': 13.1500, 'state': 'Borno'},
            'Zaria': {'lat': 11.0667, 'lng': 7.7000, 'state': 'Kaduna'},
            'Aba': {'lat': 5.1167, 'lng': 7.3667, 'state': 'Abia'},
            'Jos': {'lat': 9.9167, 'lng': 8.9000, 'state': 'Plateau'},
            'Ilorin': {'lat': 8.5000, 'lng': 4.5500, 'state': 'Kwara'},
            'Oyo': {'lat': 7.8500, 'lng': 3.9333, 'state': 'Oyo'},
            'Enugu': {'lat': 6.4500, 'lng': 7.5000, 'state': 'Enugu'},
            'Abeokuta': {'lat': 7.1500, 'lng': 3.3500, 'state': 'Ogun'},
            'Sokoto': {'lat': 13.0667, 'lng': 5.2333, 'state': 'Sokoto'},
            'Onitsha': {'lat': 6.1667, 'lng': 6.7833, 'state': 'Anambra'},
            'Warri': {'lat': 5.5167, 'lng': 5.7500, 'state': 'Delta'},
            'Akure': {'lat': 7.2500, 'lng': 5.2000, 'state': 'Ondo'},
        }
    
    def validate_nigerian_location(self, latitude: float, longitude: float) -> Dict:
        """
        Validate if coordinates are within Nigeria
        """
        try:
            # Nigeria's approximate boundaries
            min_lat, max_lat = 4.0, 14.0
            min_lng, max_lng = 2.5, 15.0
            
            if not (min_lat <= latitude <= max_lat and min_lng <= longitude <= max_lng):
                return {
                    'valid': False,
                    'error': 'Coordinates are outside Nigeria'
                }
            
            # Find nearest major city for reference
            nearest_city = self._find_nearest_city(latitude, longitude)
            
            return {
                'valid': True,
                'latitude': latitude,
                'longitude': longitude,
                'nearest_city': nearest_city
            }
            
        except Exception as e:
            logger.error(f"Error validating location: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def get_address_from_coordinates(self, latitude: float, longitude: float) -> Dict:
        """
        Get address from coordinates using external service (Google Maps API or OpenStreetMap)
        """
        try:
            # Using OpenStreetMap Nominatim (free) as fallback
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
            headers = {
                'User-Agent': 'BestyyApp/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('display_name', '')
                
                # Extract components
                address_components = data.get('address', {})
                
                return {
                    'success': True,
                    'address': address,
                    'components': {
                        'state': address_components.get('state', ''),
                        'city': address_components.get('city') or address_components.get('town', ''),
                        'area': address_components.get('suburb') or address_components.get('neighbourhood', ''),
                        'street': address_components.get('road', ''),
                        'postcode': address_components.get('postcode', '')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to get address from coordinates'
                }
                
        except Exception as e:
            logger.error(f"Error getting address from coordinates: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_closest_couriers_to_vendor(self, vendor_id: int, max_distance_km: float = 50) -> List[Dict]:
        """
        Find closest available couriers to a vendor
        """
        try:
            # Get vendor location
            vendor = VendorProfile.objects.get(id=vendor_id)
            if not vendor.latitude or not vendor.longitude:
                return []
            
            vendor_location = {
                'latitude': float(vendor.latitude),
                'longitude': float(vendor.longitude)
            }
            
            # Get available couriers in same state
            available_couriers = CourierProfile.objects.filter(
                Q(availability_status='available') | Q(availability_status='busy'),
                is_active=True,
                verification_status='approved',
                state=vendor.state,  # Same state first
                latitude__isnull=False,
                longitude__isnull=False
            ).order_by('-rating', '-total_deliveries')
            
            courier_distances = []
            
            for courier in available_couriers:
                courier_location = {
                    'latitude': float(courier.latitude),
                    'longitude': float(courier.longitude)
                }
                
                distance = self._calculate_distance(vendor_location, courier_location)
                
                if distance <= max_distance_km:
                    # Check if courier's service area covers vendor location
                    if self._is_in_service_area(vendor_location, courier):
                        courier_distances.append({
                            'courier': courier,
                            'distance_km': distance,
                            'estimated_time_minutes': self._estimate_delivery_time(distance, courier.vehicle_type)
                        })
            
            # Sort by distance
            courier_distances.sort(key=lambda x: x['distance_km'])
            
            return courier_distances[:10]  # Top 10 closest
            
        except Exception as e:
            logger.error(f"Error finding closest couriers: {str(e)}")
            return []
    
    def validate_vendor_location_for_order(self, vendor_id: int) -> Dict:
        """
        Validate vendor location when accepting order
        """
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            
            if not vendor.latitude or not vendor.longitude:
                return {
                    'valid': False,
                    'error': 'Vendor location not provided. Please enable GPS and update location.',
                    'action_required': 'location_update'
                }
            
            # Validate coordinates are in Nigeria
            location_validation = self.validate_nigerian_location(
                float(vendor.latitude), 
                float(vendor.longitude)
            )
            
            if not location_validation['valid']:
                return {
                    'valid': False,
                    'error': location_validation['error'],
                    'action_required': 'location_update'
                }
            
            # Check if there are available couriers nearby
            nearby_couriers = self.find_closest_couriers_to_vendor(vendor_id, 30)  # 30km radius
            
            if not nearby_couriers:
                return {
                    'valid': False,
                    'error': 'No available couriers in your area. Please try again later.',
                    'action_required': 'wait'
                }
            
            return {
                'valid': True,
                'vendor_location': {
                    'latitude': float(vendor.latitude),
                    'longitude': float(vendor.longitude),
                    'address': vendor.business_address,
                    'state': vendor.state,
                    'city': vendor.city,
                    'area': vendor.area
                },
                'nearby_couriers_count': len(nearby_couriers),
                'closest_courier_distance': nearby_couriers[0]['distance_km'] if nearby_couriers else None
            }
            
        except Exception as e:
            logger.error(f"Error validating vendor location: {str(e)}")
            return {
                'valid': False,
                'error': str(e),
                'action_required': 'contact_support'
            }
    
    def update_courier_location(self, courier_id: int, latitude: float, longitude: float) -> Dict:
        """
        Update courier's current location
        """
        try:
            courier = CourierProfile.objects.get(id=courier_id)
            
            # Validate location
            location_validation = self.validate_nigerian_location(latitude, longitude)
            if not location_validation['valid']:
                return {
                    'success': False,
                    'error': location_validation['error']
                }
            
            # Update location
            courier.latitude = latitude
            courier.longitude = longitude
            courier.save()
            
            return {
                'success': True,
                'message': 'Location updated successfully',
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating courier location: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_distance(self, location1: Dict, location2: Dict) -> float:
        """
        Calculate distance between two locations using Haversine formula
        """
        try:
            lat1, lon1 = location1['latitude'], location1['longitude']
            lat2, lon2 = location2['latitude'], location2['longitude']
            
            # Haversine formula
            R = 6371  # Earth's radius in kilometers
            
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            
            a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                 math.sin(dlon/2) * math.sin(dlon/2))
            
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c
            
            return round(distance, 2)
            
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return float('inf')
    
    def _find_nearest_city(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Find nearest major city
        """
        try:
            min_distance = float('inf')
            nearest_city = None
            
            for city_name, city_data in self.major_cities.items():
                distance = self._calculate_distance(
                    {'latitude': latitude, 'longitude': longitude},
                    {'latitude': city_data['lat'], 'longitude': city_data['lng']}
                )
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_city = {
                        'name': city_name,
                        'state': city_data['state'],
                        'distance_km': distance
                    }
            
            return nearest_city
            
        except Exception as e:
            logger.error(f"Error finding nearest city: {str(e)}")
            return None
    
    def _is_in_service_area(self, location: Dict, courier: CourierProfile) -> bool:
        """
        Check if location is within courier's service area
        """
        try:
            if not courier.latitude or not courier.longitude:
                return False
            
            courier_location = {
                'latitude': float(courier.latitude),
                'longitude': float(courier.longitude)
            }
            
            distance = self._calculate_distance(location, courier_location)
            
            # Parse delivery radius (assuming it's in km)
            try:
                radius_km = float(courier.delivery_radius.replace('km', '').strip())
            except:
                radius_km = 20  # Default 20km radius
            
            return distance <= radius_km
            
        except Exception as e:
            logger.error(f"Error checking service area: {str(e)}")
            return False
    
    def _estimate_delivery_time(self, distance_km: float, vehicle_type: str) -> int:
        """
        Estimate delivery time based on distance and vehicle type
        """
        try:
            # Base speeds (km/h) for different vehicle types
            speeds = {
                'bike': 25,  # 25 km/h average in city traffic
                'car': 35,   # 35 km/h average in city traffic
                'van': 30,   # 30 km/h average in city traffic
                'other': 20  # 20 km/h default
            }
            
            speed = speeds.get(vehicle_type, 20)
            time_hours = distance_km / speed
            time_minutes = int(time_hours * 60)
            
            # Add buffer time for pickup and delivery
            buffer_minutes = 15
            total_minutes = time_minutes + buffer_minutes
            
            return min(total_minutes, 120)  # Cap at 2 hours
            
        except Exception as e:
            logger.error(f"Error estimating delivery time: {str(e)}")
            return 60  # Default 1 hour
