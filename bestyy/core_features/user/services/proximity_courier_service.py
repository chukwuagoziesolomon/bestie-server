"""
Proximity-based Courier Selection Service
Finds the closest available courier to a vendor location
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db.models import Q
from ..models import CourierProfile, VendorProfile
from bestyy.restaurant_features.order.models import Order
from .ai_memory_service import AIMemoryService

logger = logging.getLogger(__name__)


class ProximityCourierService:
    """
    Service for finding the closest available courier to a vendor
    """
    
    def __init__(self):
        self.memory_service = AIMemoryService()
        self.max_search_radius = 50  # km
        self.default_search_radius = 10  # km
        
    def find_closest_courier(self, 
                           vendor_id: int,
                           order_id: int = None,
                           search_radius: float = None,
                           max_couriers: int = 5) -> Dict:
        """
        Find the closest available courier to a vendor
        
        Args:
            vendor_id: Vendor ID
            order_id: Order ID (optional)
            search_radius: Search radius in km (optional)
            max_couriers: Maximum number of couriers to return
            
        Returns:
            Dictionary with closest couriers and their details
        """
        try:
            # Get vendor information
            vendor = VendorProfile.objects.get(id=vendor_id)
            vendor_location = self._get_vendor_location(vendor)
            
            if not vendor_location:
                return {
                    'success': False,
                    'error': 'Vendor location not found',
                    'vendor_id': vendor_id
                }
            
            # Get available couriers
            available_couriers = self._get_available_couriers()
            
            if not available_couriers:
                return {
                    'success': False,
                    'error': 'No available couriers found',
                    'vendor_id': vendor_id,
                    'vendor_location': vendor_location
                }
            
            # Calculate distances and filter by radius
            courier_distances = []
            search_radius = search_radius or self.default_search_radius
            
            for courier in available_couriers:
                courier_location = self._get_courier_location(courier)
                if courier_location:
                    distance = self._calculate_distance(
                        vendor_location, 
                        courier_location
                    )
                    
                    if distance <= search_radius:
                        courier_distances.append({
                            'courier': courier,
                            'distance': distance,
                            'location': courier_location
                        })
            
            # Sort by distance
            courier_distances.sort(key=lambda x: x['distance'])
            
            # Limit results
            closest_couriers = courier_distances[:max_couriers]
            
            # Prepare response
            result = {
                'success': True,
                'vendor_id': vendor_id,
                'vendor_location': vendor_location,
                'search_radius': search_radius,
                'total_available_couriers': len(available_couriers),
                'couriers_in_radius': len(courier_distances),
                'closest_couriers': []
            }
            
            for courier_data in closest_couriers:
                courier = courier_data['courier']
                courier_info = self._prepare_courier_info(courier, courier_data)
                result['closest_couriers'].append(courier_info)
            
            # Store selection as memory
            self._store_courier_selection_memory(
                vendor_id=vendor_id,
                order_id=order_id,
                selection_result=result
            )
            
            return result
            
        except VendorProfile.DoesNotExist:
            return {
                'success': False,
                'error': 'Vendor not found',
                'vendor_id': vendor_id
            }
        except Exception as e:
            logger.error(f"Error finding closest courier: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'vendor_id': vendor_id
            }
    
    def get_courier_contact_info(self, courier_id: int) -> Dict:
        """
        Get comprehensive contact information for a courier
        
        Args:
            courier_id: Courier ID
            
        Returns:
            Dictionary with contact information
        """
        try:
            courier = CourierProfile.objects.get(id=courier_id)
            
            contact_info = {
                'courier_id': courier.id,
                'name': f"{courier.user.first_name} {courier.user.last_name}".strip(),
                'phone_number': courier.phone_number,
                'email': courier.user.email,
                'whatsapp_number': courier.phone_number,  # Same as phone for WhatsApp
                'preferred_contact_method': courier.preferred_contact_method or 'whatsapp',
                'availability_status': courier.availability_status,
                'service_areas': courier.service_areas,
                'vehicle_type': courier.vehicle_type,
                'rating': courier.rating,
                'total_deliveries': courier.total_deliveries,
                'last_active': courier.last_active.isoformat() if courier.last_active else None
            }
            
            return {
                'success': True,
                'contact_info': contact_info
            }
            
        except CourierProfile.DoesNotExist:
            return {
                'success': False,
                'error': 'Courier not found',
                'courier_id': courier_id
            }
        except Exception as e:
            logger.error(f"Error getting courier contact info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'courier_id': courier_id
            }
    
    def get_vendor_contact_info(self, vendor_id: int) -> Dict:
        """
        Get comprehensive contact information for a vendor
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            Dictionary with contact information
        """
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            
            contact_info = {
                'vendor_id': vendor.id,
                'business_name': vendor.business_name,
                'contact_person': f"{vendor.user.first_name} {vendor.user.last_name}".strip(),
                'phone_number': vendor.phone_number,
                'email': vendor.user.email,
                'whatsapp_number': vendor.phone_number,  # Same as phone for WhatsApp
                'business_address': vendor.business_address,
                'business_type': vendor.business_type,
                'operating_hours': vendor.operating_hours,
                'preferred_contact_method': vendor.preferred_contact_method or 'whatsapp',
                'verification_status': vendor.verification_status,
                'rating': vendor.rating,
                'total_orders': vendor.total_orders
            }
            
            return {
                'success': True,
                'contact_info': contact_info
            }
            
        except VendorProfile.DoesNotExist:
            return {
                'success': False,
                'error': 'Vendor not found',
                'vendor_id': vendor_id
            }
        except Exception as e:
            logger.error(f"Error getting vendor contact info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'vendor_id': vendor_id
            }
    
    def notify_closest_courier(self, 
                             vendor_id: int,
                             order_id: int,
                             notification_type: str = 'delivery_assignment',
                             custom_message: str = None) -> Dict:
        """
        Notify the closest courier about a delivery assignment
        
        Args:
            vendor_id: Vendor ID
            order_id: Order ID
            notification_type: Type of notification
            custom_message: Custom message (optional)
            
        Returns:
            Dictionary with notification results
        """
        try:
            # Find closest courier
            courier_selection = self.find_closest_courier(
                vendor_id=vendor_id,
                order_id=order_id,
                max_couriers=1
            )
            
            if not courier_selection['success']:
                return courier_selection
            
            if not courier_selection['closest_couriers']:
                return {
                    'success': False,
                    'error': 'No couriers found within search radius',
                    'vendor_id': vendor_id,
                    'order_id': order_id
                }
            
            # Get closest courier
            closest_courier = courier_selection['closest_couriers'][0]
            courier_id = closest_courier['courier_id']
            
            # Get contact information
            courier_contact = self.get_courier_contact_info(courier_id)
            vendor_contact = self.get_vendor_contact_info(vendor_id)
            
            if not courier_contact['success'] or not vendor_contact['success']:
                return {
                    'success': False,
                    'error': 'Failed to get contact information',
                    'vendor_id': vendor_id,
                    'courier_id': courier_id
                }
            
            # Prepare notification data
            notification_data = {
                'courier_contact': courier_contact['contact_info'],
                'vendor_contact': vendor_contact['contact_info'],
                'order_id': order_id,
                'distance': closest_courier['distance'],
                'notification_type': notification_type,
                'custom_message': custom_message,
                'vendor_location': courier_selection['vendor_location'],
                'courier_location': closest_courier['location']
            }
            
            # Send notifications
            notification_result = self._send_courier_notifications(notification_data)
            
            # Store notification as memory
            self._store_notification_memory(
                vendor_id=vendor_id,
                courier_id=courier_id,
                order_id=order_id,
                notification_data=notification_data,
                notification_result=notification_result
            )
            
            return {
                'success': True,
                'courier_selected': closest_courier,
                'notification_result': notification_result,
                'contact_info': {
                    'courier': courier_contact['contact_info'],
                    'vendor': vendor_contact['contact_info']
                }
            }
            
        except Exception as e:
            logger.error(f"Error notifying closest courier: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'vendor_id': vendor_id,
                'order_id': order_id
            }
    
    def _get_vendor_location(self, vendor: VendorProfile) -> Optional[Dict]:
        """
        Get vendor location coordinates
        """
        try:
            # Try to get coordinates from vendor profile
            if hasattr(vendor, 'latitude') and hasattr(vendor, 'longitude'):
                if vendor.latitude and vendor.longitude:
                    return {
                        'latitude': float(vendor.latitude),
                        'longitude': float(vendor.longitude),
                        'address': vendor.business_address
                    }
            
            # Fallback: Use geocoding service
            # In production, integrate with Google Maps API or similar
            return self._geocode_address(vendor.business_address)
            
        except Exception as e:
            logger.error(f"Error getting vendor location: {str(e)}")
            return None
    
    def _get_courier_location(self, courier: CourierProfile) -> Optional[Dict]:
        """
        Get courier location coordinates
        """
        try:
            # Try to get coordinates from courier profile
            if hasattr(courier, 'latitude') and hasattr(courier, 'longitude'):
                if courier.latitude and courier.longitude:
                    return {
                        'latitude': float(courier.latitude),
                        'longitude': float(courier.longitude),
                        'address': courier.current_location or 'Current Location'
                    }
            
            # Fallback: Use service area center
            if courier.service_areas:
                return self._get_service_area_center(courier.service_areas)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting courier location: {str(e)}")
            return None
    
    def _get_available_couriers(self) -> List[CourierProfile]:
        """
        Get list of available couriers
        """
        try:
            # Filter available couriers
            available_couriers = CourierProfile.objects.filter(
                Q(availability_status='available') | Q(availability_status='busy'),
                is_active=True,
                verification_status='approved'
            ).order_by('-rating', '-total_deliveries')
            
            return list(available_couriers)
            
        except Exception as e:
            logger.error(f"Error getting available couriers: {str(e)}")
            return []
    
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
    
    def _prepare_courier_info(self, courier: CourierProfile, courier_data: Dict) -> Dict:
        """
        Prepare courier information for response
        """
        try:
            return {
                'courier_id': courier.id,
                'name': f"{courier.user.first_name} {courier.user.last_name}".strip(),
                'phone_number': courier.phone_number,
                'email': courier.user.email,
                'whatsapp_number': courier.phone_number,
                'distance': courier_data['distance'],
                'location': courier_data['location'],
                'availability_status': courier.availability_status,
                'vehicle_type': courier.vehicle_type,
                'rating': courier.rating,
                'total_deliveries': courier.total_deliveries,
                'service_areas': courier.service_areas,
                'preferred_contact_method': courier.preferred_contact_method or 'whatsapp',
                'last_active': courier.last_active.isoformat() if courier.last_active else None
            }
            
        except Exception as e:
            logger.error(f"Error preparing courier info: {str(e)}")
            return {}
    
    def _geocode_address(self, address: str) -> Optional[Dict]:
        """
        Geocode address to coordinates (placeholder implementation)
        """
        # Placeholder: In production, integrate with Google Maps API
        # For now, return None to indicate geocoding needed
        logger.warning(f"Geocoding needed for address: {address}")
        return None
    
    def _get_service_area_center(self, service_areas: List[str]) -> Optional[Dict]:
        """
        Get center coordinates of service areas
        """
        # Placeholder: In production, calculate center of service areas
        # For now, return None
        logger.warning(f"Service area center calculation needed for: {service_areas}")
        return None
    
    def _send_courier_notifications(self, notification_data: Dict) -> Dict:
        """
        Send notifications to courier
        """
        try:
            courier_contact = notification_data['courier_contact']
            vendor_contact = notification_data['vendor_contact']
            
            # Prepare notification message
            message = self._prepare_courier_notification_message(notification_data)
            
            # Send WhatsApp notification
            whatsapp_result = self._send_whatsapp_notification(
                phone_number=courier_contact['whatsapp_number'],
                message=message
            )
            
            # Send email notification
            email_result = self._send_email_notification(
                email=courier_contact['email'],
                subject=f"New Delivery Assignment - Order #{notification_data['order_id']}",
                message=message
            )
            
            return {
                'whatsapp_sent': whatsapp_result['success'],
                'email_sent': email_result['success'],
                'whatsapp_result': whatsapp_result,
                'email_result': email_result,
                'message_sent': message
            }
            
        except Exception as e:
            logger.error(f"Error sending courier notifications: {str(e)}")
            return {
                'whatsapp_sent': False,
                'email_sent': False,
                'error': str(e)
            }
    
    def _prepare_courier_notification_message(self, notification_data: Dict) -> str:
        """
        Prepare notification message for courier
        """
        try:
            courier_contact = notification_data['courier_contact']
            vendor_contact = notification_data['vendor_contact']
            order_id = notification_data['order_id']
            distance = notification_data['distance']
            
            message = f"""🚚 *NEW DELIVERY ASSIGNMENT*

Hello {courier_contact['name']},

You have been assigned a new delivery:

📦 *Order ID:* #{order_id}
🏪 *Vendor:* {vendor_contact['business_name']}
📍 *Pickup Location:* {vendor_contact['business_address']}
📞 *Vendor Contact:* {vendor_contact['phone_number']}
📧 *Vendor Email:* {vendor_contact['email']}
📏 *Distance:* {distance} km

*Vendor Details:*
• Business: {vendor_contact['business_name']}
• Contact Person: {vendor_contact['contact_person']}
• Phone: {vendor_contact['phone_number']}
• Email: {vendor_contact['email']}

Please contact the vendor to confirm pickup and get delivery details.

Thank you for your service! 🙏

---
*Bestyy Delivery Team*"""
            
            return message
            
        except Exception as e:
            logger.error(f"Error preparing courier notification message: {str(e)}")
            return "New delivery assignment available. Please check your dashboard for details."
    
    def _send_whatsapp_notification(self, phone_number: str, message: str) -> Dict:
        """
        Send WhatsApp notification (placeholder implementation)
        """
        # Placeholder: In production, integrate with WhatsApp API
        logger.info(f"WhatsApp notification sent to {phone_number}")
        return {
            'success': True,
            'phone_number': phone_number,
            'message_id': f"wa_{timezone.now().timestamp()}"
        }
    
    def _send_email_notification(self, email: str, subject: str, message: str) -> Dict:
        """
        Send email notification (placeholder implementation)
        """
        # Placeholder: In production, integrate with email service
        logger.info(f"Email notification sent to {email}")
        return {
            'success': True,
            'email': email,
            'message_id': f"email_{timezone.now().timestamp()}"
        }
    
    def _store_courier_selection_memory(self, 
                                      vendor_id: int,
                                      order_id: int,
                                      selection_result: Dict) -> str:
        """
        Store courier selection as episodic memory
        """
        try:
            memory_id = self.memory_service.store_episodic_memory(
                memory_type='system_event',
                title=f"Courier Selection for Order #{order_id}",
                description=f"Selected closest courier for vendor {vendor_id}",
                content={
                    'vendor_id': vendor_id,
                    'order_id': order_id,
                    'selection_result': selection_result,
                    'selection_timestamp': timezone.now().isoformat()
                },
                importance_score=0.7,
                tags=['courier_selection', 'proximity', f'order_{order_id}']
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing courier selection memory: {str(e)}")
            return None
    
    def _store_notification_memory(self,
                                 vendor_id: int,
                                 courier_id: int,
                                 order_id: int,
                                 notification_data: Dict,
                                 notification_result: Dict) -> str:
        """
        Store notification as episodic memory
        """
        try:
            memory_id = self.memory_service.store_episodic_memory(
                memory_type='system_event',
                title=f"Courier Notification for Order #{order_id}",
                description=f"Notified courier {courier_id} about order {order_id}",
                content={
                    'vendor_id': vendor_id,
                    'courier_id': courier_id,
                    'order_id': order_id,
                    'notification_data': notification_data,
                    'notification_result': notification_result,
                    'notification_timestamp': timezone.now().isoformat()
                },
                importance_score=0.8,
                tags=['courier_notification', 'delivery_assignment', f'order_{order_id}']
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing notification memory: {str(e)}")
            return None
