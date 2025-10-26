#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from user.services.google_maps_service import GoogleMapsService

def test_google_maps():
    print("Testing Google Maps Service...")
    service = GoogleMapsService()
    
    # Test addresses
    test_addresses = [
        ("Gariki, Enugu, Nigeria", "New Heaven, Enugu, Nigeria"),
        ("Topland, Enugu, Nigeria", "Monarch Ugwuaji, Enugu, Nigeria"),
        ("No 5 Onwe Close, Gariki Topland, Gariki, Enugu, Nigeria", "No 3 Chief Samuel Ugwu Street, Ugwuaji, Enugu, Nigeria")
    ]
    
    for origin, destination in test_addresses:
        print(f"\n--- Testing: {origin} -> {destination} ---")
        
        # Test geocoding first
        print("Testing geocoding...")
        origin_geocode = service.geocode_address(origin)
        dest_geocode = service.geocode_address(destination)
        
        if origin_geocode:
            print(f"Origin coords: {origin_geocode['latitude']}, {origin_geocode['longitude']}")
        else:
            print("Origin geocoding failed")
            
        if dest_geocode:
            print(f"Destination coords: {dest_geocode['latitude']}, {dest_geocode['longitude']}")
        else:
            print("Destination geocoding failed")
        
        # Test distance calculation
        print("Testing distance calculation...")
        result = service.get_distance_and_price(origin, destination)
        
        if result:
            print(f"Distance: {result['distance_text']}")
            print(f"Duration: {result['duration_text']}")
            print(f"Price: ₦{result['delivery_price']}")
        else:
            print("Distance calculation failed")

if __name__ == "__main__":
    test_google_maps()













