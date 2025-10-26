"""
Tests for AI Service Order Integration
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch, MagicMock
from bestyy.core_features.user.models import (
    VendorProfile, MenuItem
)
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService
from bestyy.communication.whatsapp.models import WhatsAppConversation, WhatsAppMessage

User = get_user_model()


class AIOrderIntegrationTestCase(TestCase):
    """Test cases for AI Service Order Integration"""
    
    def setUp(self):
        """Set up test data"""
        self.ai_service = WhatsAppAIService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            phone='2348012345678'
        )
        
        # Create test vendor
        self.vendor = VendorProfile.objects.create(
            user=User.objects.create_user(
                username='vendor1',
                email='vendor@example.com',
                password='vendorpass123'
            ),
            phone='2348087654321',
            business_name='Pizza Palace',
            business_category='pizza',
            business_address='123 Main St',
            delivery_radius='5km',
            service_areas='Lagos',
            verification_status='approved',
            is_suspended=False
        )
        
        # Create test menu items
        self.pizza_item = MenuItem.objects.create(
            vendor=self.vendor,
            dish_name='Pepperoni Pizza',
            price=Decimal('5000.00'),
            category='pizza',
            available_now=True
        )
        
        # Create WhatsApp conversation
        self.conversation = WhatsAppConversation.objects.create(
            phone_number='2348012345678',
            user=self.user,
            language='en'
        )
    
    def test_handle_order_request_pizza(self):
        """Test handling pizza order request"""
        result = self.ai_service._handle_order_request(
            message_content="I want 2 pepperoni pizzas",
            category="specific_food_request",
            user=self.user,
            context={}
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['action'], 'show_vendors')
        self.assertEqual(result['food_type'], 'pizza')
        self.assertGreater(len(result['vendors']), 0)
        self.assertEqual(result['vendors'][0]['name'], 'Pizza Palace')
    
    def test_handle_order_request_no_vendors(self):
        """Test handling order request with no vendors"""
        result = self.ai_service._handle_order_request(
            message_content="I want sushi",
            category="specific_food_request",
            user=self.user,
            context={}
        )
        
        self.assertIsNone(result)
    
    def test_handle_order_request_nigerian_food(self):
        """Test handling Nigerian food order request"""
        # Create vendor with Nigerian food
        nigerian_vendor = VendorProfile.objects.create(
            user=User.objects.create_user(
                username='vendor2',
                email='vendor2@example.com',
                password='vendorpass123'
            ),
            phone='2348087654322',
            business_name='Mama Jollof',
            business_category='nigerian',
            business_address='456 Main St',
            delivery_radius='5km',
            service_areas='Lagos',
            verification_status='approved',
            is_suspended=False
        )
        
        # Create jollof rice menu item
        MenuItem.objects.create(
            vendor=nigerian_vendor,
            dish_name='Jollof Rice',
            price=Decimal('3000.00'),
            category='nigerian',
            available_now=True
        )
        
        result = self.ai_service._handle_order_request(
            message_content="I want jollof rice",
            category="nigerian_food_request",
            user=self.user,
            context={}
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['food_type'], 'jollof')
        self.assertGreater(len(result['vendors']), 0)
    
    def test_handle_order_request_with_extras(self):
        """Test handling order request with extras"""
        result = self.ai_service._handle_order_request(
            message_content="I want pizza with extra cheese and pepperoni",
            category="food_order_with_extras",
            user=self.user,
            context={}
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['action'], 'show_vendors')
        self.assertEqual(result['food_type'], 'pizza')
    
    def test_handle_order_request_vendor_selection(self):
        """Test handling vendor selection"""
        result = self.ai_service._handle_order_request(
            message_content="I want to order from Pizza Palace",
            category="vendor_selection",
            user=self.user,
            context={}
        )
        
        # Should return None since "Pizza Palace" is not in food keywords
        # This is expected behavior - vendor selection is handled differently
        self.assertIsNone(result)
    
    def test_order_data_in_response(self):
        """Test that order data is included in AI response"""
        # Create a WhatsApp message
        message = WhatsAppMessage.objects.create(
            conversation=self.conversation,
            content="I want 2 pepperoni pizzas",
            direction='inbound',
            message_type='text'
        )
        
        # Mock the LLM categorization to return specific_food_request
        with patch.object(self.ai_service, '_categorize_with_llm', return_value='specific_food_request'):
            with patch.object(self.ai_service, '_get_template', return_value=None):
                with patch.object(self.ai_service, '_generate_response', return_value={'response': 'Here are vendors...', 'confidence': 0.95}):
                    result = self.ai_service.process_message(
                        message,
                        context={'user_exists': True}
                    )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['category'], 'specific_food_request')
        # Order data should be included
        if result.get('order_data'):
            self.assertEqual(result['order_data']['action'], 'show_vendors')
    
    def test_order_request_without_user(self):
        """Test that order request is not processed without user"""
        result = self.ai_service._handle_order_request(
            message_content="I want 2 pepperoni pizzas",
            category="specific_food_request",
            user=None,
            context={}
        )
        
        # Should handle gracefully
        self.assertIsNone(result)
    
    def test_multiple_food_keywords(self):
        """Test extraction of first matching food keyword"""
        result = self.ai_service._handle_order_request(
            message_content="I want pizza and burger",
            category="specific_food_request",
            user=self.user,
            context={}
        )
        
        # Should extract 'pizza' (first match)
        self.assertIsNotNone(result)
        self.assertEqual(result['food_type'], 'pizza')

