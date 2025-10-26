"""
Courier location service for finding nearby couriers based on vendor location
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
from django.db.models import Q
from ..models import CourierProfile, VendorProfile
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import requests

logger = logging.getLogger(__name__)


class CourierLocationService:
    """
    Service for finding nearby couriers based on vendor location and service areas
    """
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="bestyy_courier_service")
        self.google_maps_api_key = None  # Add Google Maps API key if available
    
    def find_nearby_couriers(self, vendor, max_distance_km: float = 10.0, limit: int = 5) -> List[Dict]:
        """
        Find couriers near a vendor's location
        
        Args:
            vendor: VendorProfile instance
            max_distance_km: Maximum distance in kilometers
            limit: Maximum number of couriers to return
            
        Returns:
            List of courier dictionaries with distance and availability info
        """
        try:
            # Get vendor location coordinates
            vendor_coords = self._get_coordinates(vendor.business_address)
            if not vendor_coords:
                logger.error(f"Could not get coordinates for vendor {vendor.id}")
                return []
            
            # Get all active couriers
            active_couriers = CourierProfile.objects.filter(
                is_active=True,
                is_suspended=False,
                verification_status='approved'
            ).select_related('user')
            
            nearby_couriers = []
            
            for courier in active_couriers:
                # Check if courier is available (within working hours)
                if not self._is_courier_available(courier):
                    continue
                
                # Check if courier serves this area
                if not self._courier_serves_area(courier, vendor.business_address):
                    continue
                
                # Get courier's service area coordinates
                courier_coords = self._get_courier_location(courier)
                if not courier_coords:
                    continue
                
                # Calculate distance
                distance = geodesic(vendor_coords, courier_coords).kilometers
                
                if distance <= max_distance_km:
                    nearby_couriers.append({
                        'courier': courier,
                        'distance_km': round(distance, 2),
                        'estimated_earnings': self._calculate_estimated_earnings(distance),
                        'estimated_delivery_time': self._calculate_delivery_time(distance),
                        'service_areas': courier.service_areas,
                        'vehicle_type': courier.vehicle_type,
                        'phone': courier.phone,
                        'is_available': True
                    })
            
            # Sort by distance and return top results
            nearby_couriers.sort(key=lambda x: x['distance_km'])
            return nearby_couriers[:limit]
            
        except Exception as e:
            logger.error(f"Error finding nearby couriers: {str(e)}")
            return []
    
    def find_couriers_by_service_area(self, vendor_address: str, limit: int = 5) -> List[Dict]:
        """
        Find couriers by service area matching (fallback method)
        
        Args:
            vendor_address: Vendor's business address
            limit: Maximum number of couriers to return
            
        Returns:
            List of courier dictionaries
        """
        try:
            # Extract city/area from vendor address
            vendor_area = self._extract_area_from_address(vendor_address)
            if not vendor_area:
                return []
            
            # Find couriers whose service areas contain the vendor's area
            couriers = CourierProfile.objects.filter(
                is_active=True,
                is_suspended=False,
                verification_status='approved',
                service_areas__icontains=vendor_area
            ).select_related('user')[:limit]
            
            result = []
            for courier in couriers:
                if self._is_courier_available(courier):
                    result.append({
                        'courier': courier,
                        'distance_km': 'N/A',
                        'estimated_earnings': 500,  # Default estimate
                        'estimated_delivery_time': '30-45 min',
                        'service_areas': courier.service_areas,
                        'vehicle_type': courier.vehicle_type,
                        'phone': courier.phone,
                        'is_available': True
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error finding couriers by service area: {str(e)}")
            return []
    
    def _get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for an address using geocoding
        """
        try:
            if not address:
                return None
            
            # Try Google Maps Geocoding API first if available
            if self.google_maps_api_key:
                coords = self._get_google_coordinates(address)
                if coords:
                    return coords
            
            # Fallback to Nominatim
            location = self.geocoder.geocode(address, timeout=10)
            if location:
                return (location.latitude, location.longitude)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting coordinates for {address}: {str(e)}")
            return None
    
    def _get_google_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates using Google Maps Geocoding API
        """
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.google_maps_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return (location['lat'], location['lng'])
            
            return None
            
        except Exception as e:
            logger.error(f"Google Maps geocoding error: {str(e)}")
            return None
    
    def _get_courier_location(self, courier: CourierProfile) -> Optional[Tuple[float, float]]:
        """
        Get courier's current location (for now, use service area center)
        """
        try:
            # For now, use the first service area as courier location
            # In a real implementation, you'd track courier's real-time location
            service_areas = courier.service_areas.split(',')
            if service_areas:
                first_area = service_areas[0].strip()
                return self._get_coordinates(first_area)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting courier location: {str(e)}")
            return None
    
    def _is_courier_available(self, courier: CourierProfile) -> bool:
        """
        Check if courier is currently available (within working hours)
        """
        try:
            from django.utils import timezone
            now = timezone.now().time()
            
            # Check if current time is within courier's working hours
            return courier.opening_hours <= now <= courier.closing_hours
            
        except Exception as e:
            logger.error(f"Error checking courier availability: {str(e)}")
            return False
    
    def _courier_serves_area(self, courier: CourierProfile, vendor_address: str) -> bool:
        """
        Check if courier serves the vendor's area
        """
        try:
            if not courier.service_areas or not vendor_address:
                return False
            
            # Extract area from vendor address
            vendor_area = self._extract_area_from_address(vendor_address)
            if not vendor_area:
                return False
            
            # Check if vendor area is in courier's service areas
            service_areas = [area.strip().lower() for area in courier.service_areas.split(',')]
            return vendor_area.lower() in service_areas
            
        except Exception as e:
            logger.error(f"Error checking courier service area: {str(e)}")
            return False
    
    def _extract_area_from_address(self, address: str) -> Optional[str]:
        """
        Extract city/area name from address string
        """
        try:
            if not address:
                return None
            
            # Common Nigerian cities/areas
            nigerian_areas = [
                'lagos', 'abuja', 'kano', 'ibadan', 'port harcourt', 'benin city',
                'maiduguri', 'zaria', 'aba', 'jos', 'ilorin', 'oyo', 'enugu',
                'abeokuta', 'sokoto', 'onitsha', 'calabar', 'katsina', 'akure',
                'victoria island', 'lekki', 'ikeja', 'surulere', 'yaba', 'gbagada',
                'magodo', 'banana island', 'ikoyi', 'v.i', 'vi'
            ]
            
            address_lower = address.lower()
            
            # Look for Nigerian areas in the address
            for area in nigerian_areas:
                if area in address_lower:
                    return area.title()
            
            # If no specific area found, try to extract the last part of the address
            parts = address.split(',')
            if len(parts) > 1:
                return parts[-1].strip()
            
            return address.strip()
            
        except Exception as e:
            logger.error(f"Error extracting area from address: {str(e)}")
            return None
    
    def _calculate_estimated_earnings(self, distance_km: float) -> float:
        """
        Calculate estimated earnings based on distance
        """
        try:
            # Base rate
            base_rate = 200  # ₦200 base rate
            
            # Distance rate (₦50 per km)
            distance_rate = distance_km * 50
            
            # Minimum earnings
            min_earnings = 300
            
            estimated = base_rate + distance_rate
            return max(estimated, min_earnings)
            
        except Exception as e:
            logger.error(f"Error calculating estimated earnings: {str(e)}")
            return 300  # Default minimum
    
    def _calculate_delivery_time(self, distance_km: float) -> str:
        """
        Calculate estimated delivery time based on distance
        """
        try:
            # Base time: 15 minutes
            base_time = 15
            
            # Additional time: 2 minutes per km
            additional_time = distance_km * 2
            
            total_minutes = base_time + additional_time
            
            if total_minutes < 30:
                return "15-30 min"
            elif total_minutes < 45:
                return "30-45 min"
            elif total_minutes < 60:
                return "45-60 min"
            else:
                return "60+ min"
                
        except Exception as e:
            logger.error(f"Error calculating delivery time: {str(e)}")
            return "30-45 min"  # Default
    
    def assign_courier_to_order(self, order, vendor, customer_data: Dict) -> Optional[Dict]:
        """
        Find and assign the best courier for an order
        
        Args:
            order: Order instance
            vendor: VendorProfile instance
            customer_data: Customer information dictionary
            
        Returns:
            Dictionary with courier assignment details or None if no courier found
        """
        try:
            # First try to find nearby couriers
            nearby_couriers = self.find_nearby_couriers(vendor, max_distance_km=15.0, limit=3)
            
            if not nearby_couriers:
                # Fallback to service area matching
                nearby_couriers = self.find_couriers_by_service_area(vendor.business_address, limit=3)
            
            if not nearby_couriers:
                logger.warning(f"No available couriers found for vendor {vendor.id}")
                return None
            
            # Select the best courier (closest available)
            best_courier = nearby_couriers[0]
            courier = best_courier['courier']
            
            # Prepare order data for courier notification
            order_data = {
                'order': {
                    'id': order.id,
                    'created_at': order.order_placed_at,
                    'total_price': order.total_price,
                    'delivery_address': order.delivery_address
                },
                'vendor': {
                    'id': vendor.id,
                    'business_name': vendor.business_name,
                    'business_address': vendor.business_address,
                    'contact_phone': vendor.contact_phone
                },
                'customer': customer_data,
                'pickup_location': vendor.business_address,
                'delivery_location': order.delivery_address,
                'estimated_distance': best_courier['distance_km'],
                'estimated_earnings': best_courier['estimated_earnings'],
                'estimated_delivery_time': best_courier['estimated_delivery_time'],
                'timestamp': order.order_placed_at.isoformat()
            }
            
            return {
                'courier': courier,
                'order_data': order_data,
                'assignment_details': best_courier
            }
            
        except Exception as e:
            logger.error(f"Error assigning courier to order: {str(e)}")
            return None
