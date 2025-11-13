"""
Order grouping and splitting service for multi-vendor orders
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Set
from django.db.models import Q, F, Sum
from ..models import MenuItem, VendorProfile, Cart, OrderItem

logger = logging.getLogger(__name__)


class OrderGroupingService:
    """
    Service for intelligently grouping cart items by vendor and optimizing delivery
    """

    def __init__(self):
        self.max_vendors_per_group = 3  # Maximum vendors in one delivery group
        self.max_delivery_radius = 10.0  # Maximum delivery radius in km
        self.delivery_fee_per_vendor = Decimal('300.00')  # Base delivery fee per vendor

    def group_cart_items(self, cart: Cart, delivery_address_coords: Optional[Dict] = None) -> Dict:
        """
        Group cart items by optimal vendor combinations
        """
        cart_items = list(cart.items.all().select_related('menu_item__vendor'))

        if not cart_items:
            return {'groups': [], 'total_cost': 0, 'delivery_fee': 0}

        # Group items by vendor
        vendor_groups = self._group_by_vendor(cart_items)

        # If only one vendor, no need for complex grouping
        if len(vendor_groups) == 1:
            return self._create_single_vendor_group(vendor_groups, delivery_address_coords)

        # For multiple vendors, find optimal grouping
        optimal_groups = self._find_optimal_vendor_groups(vendor_groups, delivery_address_coords)

        return {
            'groups': optimal_groups,
            'total_cost': sum(group['subtotal'] for group in optimal_groups),
            'delivery_fee': self._calculate_grouped_delivery_fee(optimal_groups),
            'grouping_strategy': 'multi_vendor_optimized'
        }

    def _group_by_vendor(self, cart_items: List[OrderItem]) -> Dict[int, List[OrderItem]]:
        """
        Group cart items by their vendor
        """
        vendor_groups = {}
        for item in cart_items:
            vendor_id = item.menu_item.vendor.id
            if vendor_id not in vendor_groups:
                vendor_groups[vendor_id] = []
            vendor_groups[vendor_id].append(item)

        return vendor_groups

    def _create_single_vendor_group(self, vendor_groups: Dict, delivery_coords: Optional[Dict]) -> Dict:
        """
        Create group structure for single vendor order
        """
        vendor_id, items = list(vendor_groups.items())[0]
        vendor = items[0].menu_item.vendor

        subtotal = sum(item.price * item.quantity for item in items)

        group = {
            'vendor_id': vendor_id,
            'vendor_name': vendor.business_name,
            'items': [{
                'id': item.id,
                'menu_item_id': item.menu_item.id,
                'name': item.menu_item.dish_name,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.price * item.quantity)
            } for item in items],
            'subtotal': float(subtotal),
            'delivery_fee': float(self.delivery_fee_per_vendor),
            'estimated_delivery_time': self._estimate_delivery_time(vendor, delivery_coords),
            'vendor_location': {
                'lat': vendor.business_latitude,
                'lng': vendor.business_longitude
            } if vendor.business_latitude else None
        }

        return {
            'groups': [group],
            'total_cost': float(subtotal),
            'delivery_fee': float(self.delivery_fee_per_vendor),
            'grouping_strategy': 'single_vendor'
        }

    def _find_optimal_vendor_groups(self, vendor_groups: Dict[int, List[OrderItem]],
                                  delivery_coords: Optional[Dict]) -> List[Dict]:
        """
        Find optimal grouping of vendors for delivery efficiency
        """
        vendors = []
        for vendor_id, items in vendor_groups.items():
            vendor = items[0].menu_item.vendor
            subtotal = sum(item.price * item.quantity for item in items)

            vendor_data = {
                'id': vendor_id,
                'name': vendor.business_name,
                'items': items,
                'subtotal': subtotal,
                'location': {
                    'lat': vendor.business_latitude,
                    'lng': vendor.business_longitude
                } if vendor.business_latitude else None,
                'delivery_radius': vendor.delivery_radius or 5.0
            }
            vendors.append(vendor_data)

        # Strategy 1: Group by proximity (if location data available)
        if delivery_coords and all(v.get('location') for v in vendors):
            return self._group_by_proximity(vendors, delivery_coords)

        # Strategy 2: Group by delivery radius compatibility
        return self._group_by_delivery_compatibility(vendors)

    def _group_by_proximity(self, vendors: List[Dict], delivery_coords: Dict) -> List[Dict]:
        """
        Group vendors based on proximity to delivery address and each other
        """
        # Calculate distances from delivery address
        for vendor in vendors:
            if vendor['location']:
                distance = self._calculate_distance(
                    delivery_coords['lat'], delivery_coords['lng'],
                    vendor['location']['lat'], vendor['location']['lng']
                )
                vendor['distance_to_delivery'] = distance
            else:
                vendor['distance_to_delivery'] = float('inf')

        # Sort by distance
        vendors.sort(key=lambda x: x['distance_to_delivery'])

        # Create groups starting with closest vendor
        groups = []
        remaining_vendors = vendors.copy()

        while remaining_vendors:
            # Start new group with closest vendor
            current_group = [remaining_vendors.pop(0)]
            group_center = current_group[0]['location']

            # Add compatible vendors to group
            i = 0
            while i < len(remaining_vendors) and len(current_group) < self.max_vendors_per_group:
                vendor = remaining_vendors[i]
                if vendor['location']:
                    # Check if vendor is within reasonable distance from group center
                    distance_from_group = self._calculate_distance(
                        group_center['lat'], group_center['lng'],
                        vendor['location']['lat'], vendor['location']['lng']
                    )

                    # If within 3km of group center, add to group
                    if distance_from_group <= 3.0:
                        current_group.append(remaining_vendors.pop(i))
                        # Recalculate group center (simple average)
                        group_center = self._calculate_group_center(current_group)
                        continue

                i += 1

            # Create group structure
            groups.append(self._create_vendor_group(current_group))

        return groups

    def _group_by_delivery_compatibility(self, vendors: List[Dict]) -> List[Dict]:
        """
        Group vendors based on delivery radius compatibility
        """
        groups = []
        remaining_vendors = vendors.copy()

        while remaining_vendors:
            current_group = [remaining_vendors.pop(0)]

            # Try to add compatible vendors
            i = 0
            while i < len(remaining_vendors) and len(current_group) < self.max_vendors_per_group:
                vendor = remaining_vendors[i]

                # Check if vendor's delivery radius is compatible
                # (simplified - in production would check actual delivery areas)
                if vendor['delivery_radius'] >= 3.0:  # Can deliver reasonably far
                    current_group.append(remaining_vendors.pop(i))
                    continue

                i += 1

            groups.append(self._create_vendor_group(current_group))

        return groups

    def _create_vendor_group(self, vendors_in_group: List[Dict]) -> Dict:
        """
        Create a delivery group from a list of vendors
        """
        all_items = []
        total_subtotal = 0

        for vendor_data in vendors_in_group:
            for item in vendor_data['items']:
                all_items.append({
                    'id': item.id,
                    'menu_item_id': item.menu_item.id,
                    'name': item.menu_item.dish_name,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.price * item.quantity),
                    'vendor_id': vendor_data['id'],
                    'vendor_name': vendor_data['name']
                })
            total_subtotal += vendor_data['subtotal']

        # Calculate delivery fee for group (shared fee)
        delivery_fee = self._calculate_group_delivery_fee(len(vendors_in_group))

        return {
            'vendors': [{
                'id': v['id'],
                'name': v['name'],
                'location': v['location'],
                'subtotal': float(v['subtotal'])
            } for v in vendors_in_group],
            'items': all_items,
            'subtotal': float(total_subtotal),
            'delivery_fee': float(delivery_fee),
            'total_with_delivery': float(total_subtotal + delivery_fee),
            'vendor_count': len(vendors_in_group),
            'estimated_delivery_time': self._estimate_group_delivery_time(vendors_in_group)
        }

    def _calculate_group_delivery_fee(self, vendor_count: int) -> Decimal:
        """
        Calculate delivery fee for a group (economies of scale)
        """
        if vendor_count == 1:
            return self.delivery_fee_per_vendor
        elif vendor_count == 2:
            return self.delivery_fee_per_vendor * Decimal('1.5')  # 50% more for 2 vendors
        else:
            return self.delivery_fee_per_vendor * Decimal('2.0')  # Double fee for 3+ vendors

    def _calculate_grouped_delivery_fee(self, groups: List[Dict]) -> Decimal:
        """
        Calculate total delivery fee for all groups
        """
        return sum(Decimal(str(group['delivery_fee'])) for group in groups)

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate approximate distance between two points (in km)
        """
        # Simplified Haversine formula approximation
        # In production, use a proper geolocation library
        lat_diff = abs(lat1 - lat2)
        lng_diff = abs(lng1 - lng2)

        # Rough approximation: 1 degree lat/lng ≈ 111 km
        distance = ((lat_diff * 111) ** 2 + (lng_diff * 111) ** 2) ** 0.5
        return distance

    def _calculate_group_center(self, vendors: List[Dict]) -> Dict:
        """
        Calculate center point of vendor group
        """
        if not vendors:
            return {'lat': 0, 'lng': 0}

        total_lat = sum(v['location']['lat'] for v in vendors if v.get('location'))
        total_lng = sum(v['location']['lng'] for v in vendors if v.get('location'))

        vendor_count = len([v for v in vendors if v.get('location')])

        if vendor_count == 0:
            return {'lat': 0, 'lng': 0}

        return {
            'lat': total_lat / vendor_count,
            'lng': total_lng / vendor_count
        }

    def _estimate_delivery_time(self, vendor: VendorProfile, delivery_coords: Optional[Dict]) -> str:
        """
        Estimate delivery time for a vendor
        """
        base_time = 30  # Base 30 minutes

        if delivery_coords and vendor.business_latitude:
            distance = self._calculate_distance(
                delivery_coords['lat'], delivery_coords['lng'],
                vendor.business_latitude, vendor.business_longitude
            )
            # Add 2 minutes per km
            base_time += int(distance * 2)

        return f"{base_time}-{base_time + 15} min"

    def _estimate_group_delivery_time(self, vendors: List[Dict]) -> str:
        """
        Estimate delivery time for a vendor group
        """
        if len(vendors) == 1:
            return vendors[0].get('estimated_delivery_time', '30-45 min')

        # For multiple vendors, take the longest delivery time
        max_time = 45
        for vendor in vendors:
            time_str = vendor.get('estimated_delivery_time', '30-45 min')
            # Extract max time from range
            try:
                max_from_range = int(time_str.split('-')[1].split()[0])
                max_time = max(max_time, max_from_range)
            except (IndexError, ValueError):
                continue

        return f"{max_time}-{max_time + 15} min"

    def validate_grouping_feasibility(self, groups: List[Dict], delivery_coords: Optional[Dict]) -> Dict:
        """
        Validate if the grouping is feasible for delivery
        """
        issues = []

        for group in groups:
            vendor_count = group.get('vendor_count', 1)

            # Check vendor count limit
            if vendor_count > self.max_vendors_per_group:
                issues.append(f"Group has {vendor_count} vendors, exceeds maximum of {self.max_vendors_per_group}")

            # Check delivery radius if coordinates available
            if delivery_coords:
                for vendor in group.get('vendors', []):
                    if vendor.get('location'):
                        distance = self._calculate_distance(
                            delivery_coords['lat'], delivery_coords['lng'],
                            vendor['location']['lat'], vendor['location']['lng']
                        )
                        if distance > self.max_delivery_radius:
                            issues.append(f"Vendor {vendor['name']} is {distance:.1f}km away, exceeds {self.max_delivery_radius}km limit")

        return {
            'feasible': len(issues) == 0,
            'issues': issues,
            'recommendations': self._generate_grouping_recommendations(issues, groups)
        }

    def _generate_grouping_recommendations(self, issues: List[str], groups: List[Dict]) -> List[str]:
        """
        Generate recommendations to fix grouping issues
        """
        recommendations = []

        if any('vendor count' in issue.lower() for issue in issues):
            recommendations.append("Consider splitting large orders into separate deliveries")

        if any('distance' in issue.lower() or 'radius' in issue.lower() for issue in issues):
            recommendations.append("Some vendors are too far for combined delivery - consider separate orders")

        if not recommendations:
            recommendations.append("Grouping looks good for delivery")

        return recommendations