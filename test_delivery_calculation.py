#!/usr/bin/env python
"""
Test script to calculate delivery price from:
- Origin: No 5 Onwe Close, Gariki, Enugu
- Destination: No 3 Chief Samuel Ugwu Street, Monarch, Enugu
"""

import os
import sys
import django

# Add the bestyy directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bestyy'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.core_features.user.services.google_maps_service import GoogleMapsService

def test_delivery_calculation():
    """Test delivery price calculation between two addresses in Enugu."""

    # Initialize the service
    maps_service = GoogleMapsService()

    # Define addresses
    origin = "No 5 Onwe Close, Gariki, Enugu"
    destination = "No 3 Chief Samuel Ugwu Street, Monarch, Enugu"

    print("Testing Delivery Price Calculation")
    print("=" * 50)
    print(f"Origin: {origin}")
    print(f"Destination: {destination}")
    print()

    try:
        # Get distance and price
        result = maps_service.get_distance_and_price(origin, destination)

        if result:
            print("SUCCESS: Calculation completed!")
            print(f"Distance: {result['distance_km']:.2f} km")
            print(f"Delivery Price: NGN {result['delivery_price']:.2f}")
            print(f"Duration: {result['duration_text']}")
            print()
            print("Breakdown:")
            print(f"   - Base fare: NGN {result['pricing_details']['base_price']:.2f}")
            print(f"   - Distance charge: NGN {(result['distance_km'] * result['pricing_details']['price_per_km']):.2f}")
            print(f"   - Total: NGN {result['delivery_price']:.2f}")
        else:
            print("FAILED: Calculation failed!")
            print("Error: Could not calculate distance and price")

    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_delivery_calculation()