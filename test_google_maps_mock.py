#!/usr/bin/env python
import os
import django

# Ensure Django settings are available for the service import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

import unittest
from unittest.mock import patch, Mock

from user.services.google_maps_service import GoogleMapsService


class TestGoogleMapsServiceMocked(unittest.TestCase):
    def setUp(self):
        # Pretend we have an API key so the service does not early-return
        from django.conf import settings
        settings.GOOGLE_MAPS_API_KEY = 'fake-key-for-tests'
        self.service = GoogleMapsService()

    @patch('user.services.google_maps_service.requests.get')
    def test_geocode_address_success(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'formatted_address': '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
                    'geometry': {
                        'location': {'lat': 37.4224764, 'lng': -122.0842499}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.service.geocode_address('Googleplex')
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['latitude'], 37.4224764)
        self.assertAlmostEqual(result['longitude'], -122.0842499)
        self.assertIn('formatted_address', result)

    @patch('user.services.google_maps_service.requests.get')
    def test_geocode_address_failure_status(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {'status': 'ZERO_RESULTS', 'results': []}
        mock_get.return_value = mock_response

        result = self.service.geocode_address('unknown place')
        self.assertIsNone(result)

    @patch('user.services.google_maps_service.requests.get')
    def test_calculate_distance_success(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'rows': [
                {
                    'elements': [
                        {
                            'status': 'OK',
                            'distance': {'text': '12.3 km', 'value': 12345},
                            'duration': {'text': '25 mins', 'value': 1500}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.service.calculate_distance('A', 'B', mode='driving')
        self.assertIsNotNone(result)
        self.assertEqual(result['distance_value'], 12345)
        self.assertEqual(result['duration_value'], 1500)
        self.assertEqual(result['mode'], 'driving')

    @patch('user.services.google_maps_service.requests.get')
    def test_get_distance_and_price_pipeline(self, mock_get):
        # Mock Distance Matrix for pipeline; geocode is not used by get_distance_and_price
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'rows': [
                {
                    'elements': [
                        {
                            'status': 'OK',
                            'distance': {'text': '10.0 km', 'value': 10000},
                            'duration': {'text': '20 mins', 'value': 1200}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.service.get_distance_and_price('Origin', 'Destination', base_price=700.0, price_per_km=120.0, minimum_price=600.0)
        self.assertIsNotNone(result)
        # 10 km -> 700 + 10*120 = 1900
        self.assertEqual(result['delivery_price'], 1900.0)
        self.assertEqual(result['distance_km'], 10.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)








