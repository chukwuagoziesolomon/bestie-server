"""
Service to find nearby couriers based on location for order assignment.
This service uses latitude/longitude coordinates to find couriers close to
the delivery location or vendor location.
"""
import math
from typing import List, Optional, Tuple
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from bestyy.core_features.user.models import CourierProfile
import logging

logger = logging.getLogger(__name__)


class CourierLocationService:
    """
    Service for finding nearby couriers based on location coordinates.
    """

    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth using the Haversine formula.

        Args:
            lat1, lon1: Latitude and longitude of first point (in degrees)
            lat2, lon2: Latitude and longitude of second point (in degrees)

        Returns:
            Distance in kilometers
        """
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return CourierLocationService.EARTH_RADIUS_KM * c

    @staticmethod
    def find_nearby_couriers(
        latitude: float,
        longitude: float,
        max_distance_km: float = 10.0,
        max_results: int = 10,
        require_active: bool = True,
        require_verified: bool = True
    ) -> List[Tuple[CourierProfile, float]]:
        """
        Find couriers near a specific location.

        Args:
            latitude: Target latitude
            longitude: Target longitude
            max_distance_km: Maximum distance in kilometers (default: 10km)
            max_results: Maximum number of results to return (default: 10)
            require_active: Only include active couriers (default: True)
            require_verified: Only include verified couriers (default: True)

        Returns:
            List of tuples: (CourierProfile, distance_in_km)
        """
        try:
            # Build base queryset
            queryset = CourierProfile.objects.select_related('user')

            # Apply filters
            if require_active:
                queryset = queryset.filter(is_active=True, is_suspended=False)

            if require_verified:
                queryset = queryset.filter(verification_status='approved')

            # Only include couriers with location data
            queryset = queryset.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )

            # Filter by recent location updates (within last 2 hours)
            two_hours_ago = timezone.now() - timedelta(hours=2)
            queryset = queryset.filter(last_location_update__gte=two_hours_ago)

            # Get all potential couriers
            couriers = list(queryset)

            # Calculate distances and filter by max distance
            nearby_couriers = []
            for courier in couriers:
                # Ensure coordinates are not None
                if courier.latitude is None or courier.longitude is None:
                    continue

                distance = CourierLocationService.haversine_distance(
                    latitude, longitude,
                    float(courier.latitude), float(courier.longitude)
                )

                if distance <= max_distance_km:
                    nearby_couriers.append((courier, distance))

            # Sort by distance (closest first)
            nearby_couriers.sort(key=lambda x: x[1])

            # Return top results
            return nearby_couriers[:max_results]

        except Exception as e:
            logger.error(f"Error finding nearby couriers: {str(e)}")
            return []

    @staticmethod
    def find_best_couriers_for_order(
        order_latitude: float,
        order_longitude: float,
        vendor_latitude: Optional[float] = None,
        vendor_longitude: Optional[float] = None,
        max_distance_km: float = 15.0,
        max_results: int = 5
    ) -> List[Tuple[CourierProfile, float, str]]:
        """
        Find the best couriers for an order, considering both delivery location and vendor location.

        Args:
            order_latitude: Delivery location latitude
            order_longitude: Delivery location longitude
            vendor_latitude: Vendor location latitude (optional)
            vendor_longitude: Vendor location longitude (optional)
            max_distance_km: Maximum distance in kilometers
            max_results: Maximum number of results

        Returns:
            List of tuples: (CourierProfile, distance_to_order, location_type)
            where location_type is 'order' or 'vendor'
        """
        try:
            # Find couriers near the delivery location
            order_nearby = CourierLocationService.find_nearby_couriers(
                order_latitude, order_longitude,
                max_distance_km, max_results * 2,  # Get more candidates
                require_active=True, require_verified=True
            )

            # If vendor location is provided, also find couriers near vendor
            vendor_nearby = []
            if vendor_latitude and vendor_longitude:
                vendor_nearby = CourierLocationService.find_nearby_couriers(
                    vendor_latitude, vendor_longitude,
                    max_distance_km, max_results * 2,
                    require_active=True, require_verified=True
                )

            # Combine and prioritize
            courier_scores = {}

            # Score couriers based on proximity to order location (primary)
            for courier, distance in order_nearby:
                courier_id = courier.id
                if courier_id not in courier_scores:
                    courier_scores[courier_id] = {
                        'courier': courier,
                        'order_distance': distance,
                        'vendor_distance': float('inf'),
                        'best_location': 'order'
                    }
                courier_scores[courier_id]['order_distance'] = min(
                    courier_scores[courier_id]['order_distance'], distance
                )

            # Score couriers based on proximity to vendor location (secondary)
            for courier, distance in vendor_nearby:
                courier_id = courier.id
                if courier_id not in courier_scores:
                    courier_scores[courier_id] = {
                        'courier': courier,
                        'order_distance': float('inf'),
                        'vendor_distance': distance,
                        'best_location': 'vendor'
                    }
                courier_scores[courier_id]['vendor_distance'] = min(
                    courier_scores[courier_id]['vendor_distance'], distance
                )

                # Update best location if vendor is closer
                if distance < courier_scores[courier_id]['order_distance']:
                    courier_scores[courier_id]['best_location'] = 'vendor'

            # Convert to list and sort by combined score
            scored_couriers = []
            for courier_data in courier_scores.values():
                # Calculate combined score (weighted average)
                order_dist = courier_data['order_distance']
                vendor_dist = courier_data['vendor_distance']

                # Weight: 70% for order distance, 30% for vendor distance
                if vendor_dist == float('inf'):
                    combined_score = order_dist  # Only order distance matters
                else:
                    combined_score = (order_dist * 0.7) + (vendor_dist * 0.3)

                scored_couriers.append((
                    courier_data['courier'],
                    combined_score,
                    courier_data['best_location']
                ))

            # Sort by combined score (lowest = best)
            scored_couriers.sort(key=lambda x: x[1])

            return scored_couriers[:max_results]

        except Exception as e:
            logger.error(f"Error finding best couriers for order: {str(e)}")
            return []

    @staticmethod
    def update_courier_location(courier_id: int, latitude: float, longitude: float) -> bool:
        """
        Update a courier's current location.

        Args:
            courier_id: CourierProfile ID
            latitude: New latitude
            longitude: New longitude

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            courier = CourierProfile.objects.get(id=courier_id)
            courier.latitude = Decimal(str(latitude))
            courier.longitude = Decimal(str(longitude))
            courier.last_location_update = timezone.now()
            courier.save()

            logger.info(f"Updated location for courier {courier_id}: {latitude}, {longitude}")
            return True

        except CourierProfile.DoesNotExist:
            logger.warning(f"Courier {courier_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating courier location: {str(e)}")
            return False

    @staticmethod
    def get_courier_service_areas() -> dict:
        """
        Get a summary of courier distribution by service areas.

        Returns:
            Dictionary with service area statistics
        """
        try:
            # Group couriers by service areas
            couriers = CourierProfile.objects.filter(
                is_active=True,
                verification_status='approved',
                latitude__isnull=False,
                longitude__isnull=False
            )

            areas = {}
            for courier in couriers:
                area = courier.service_areas.strip() if courier.service_areas else 'Unknown'
                if area not in areas:
                    areas[area] = 0
                areas[area] += 1

            return {
                'total_couriers': len(couriers),
                'areas': areas,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting courier service areas: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """
        Validate that coordinates are within valid ranges.

        Args:
            latitude: Latitude to validate
            longitude: Longitude to validate

        Returns:
            True if valid, False otherwise
        """
        return (
            -90 <= latitude <= 90 and
            -180 <= longitude <= 180 and
            latitude != 0 and longitude != 0  # Not null island
        )
