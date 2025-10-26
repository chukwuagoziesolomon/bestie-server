"""
Tests for Fallback Categorization
Tests the keyword-based categorization when LLM API fails
"""
from django.test import TestCase
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService


class FallbackCategorizationTestCase(TestCase):
    """Test cases for fallback categorization"""
    
    def setUp(self):
        """Set up test data"""
        self.ai_service = WhatsAppAIService()
    
    def test_nigerian_food_request_eba(self):
        """Test Nigerian food request - eba"""
        result = self.ai_service._fallback_categorize("i want to order eba")
        self.assertEqual(result, 'nigerian_food_request')
    
    def test_nigerian_food_request_jollof(self):
        """Test Nigerian food request - jollof rice"""
        result = self.ai_service._fallback_categorize("i want jollof rice")
        self.assertEqual(result, 'nigerian_food_request')
    
    def test_nigerian_food_request_egusi(self):
        """Test Nigerian food request - egusi soup"""
        result = self.ai_service._fallback_categorize("i want egusi soup")
        self.assertEqual(result, 'nigerian_food_request')
    
    def test_nigerian_food_request_pounded_yam(self):
        """Test Nigerian food request - pounded yam"""
        result = self.ai_service._fallback_categorize("i want pounded yam")
        self.assertEqual(result, 'nigerian_food_request')
    
    def test_food_order_with_extras_pizza(self):
        """Test food order with extras - pizza"""
        result = self.ai_service._fallback_categorize("i want pizza with extra cheese")
        self.assertEqual(result, 'food_order_with_extras')
    
    def test_food_order_with_extras_eba(self):
        """Test food order with extras - eba with chicken"""
        result = self.ai_service._fallback_categorize("i want eba with chicken")
        self.assertEqual(result, 'food_order_with_extras')
    
    def test_specific_food_request_pizza(self):
        """Test specific food request - pizza"""
        result = self.ai_service._fallback_categorize("i want 2 pepperoni pizzas")
        self.assertEqual(result, 'specific_food_request')
    
    def test_specific_food_request_burger(self):
        """Test specific food request - burger"""
        result = self.ai_service._fallback_categorize("i want a burger")
        self.assertEqual(result, 'specific_food_request')
    
    def test_specific_food_request_chicken(self):
        """Test specific food request - chicken"""
        result = self.ai_service._fallback_categorize("i want chicken")
        self.assertEqual(result, 'specific_food_request')
    
    def test_greeting_hi(self):
        """Test greeting - hi"""
        result = self.ai_service._fallback_categorize("hi")
        self.assertEqual(result, 'greeting')
    
    def test_greeting_hello(self):
        """Test greeting - hello"""
        result = self.ai_service._fallback_categorize("hello")
        self.assertEqual(result, 'greeting')
    
    def test_greeting_good_morning(self):
        """Test greeting - good morning"""
        result = self.ai_service._fallback_categorize("good morning")
        self.assertEqual(result, 'greeting')
    
    def test_delivery_status_where(self):
        """Test delivery status - where is my order"""
        result = self.ai_service._fallback_categorize("where is my order")
        self.assertEqual(result, 'delivery_status')
    
    def test_delivery_status_track(self):
        """Test delivery status - track my delivery"""
        result = self.ai_service._fallback_categorize("track my delivery")
        self.assertEqual(result, 'delivery_status')
    
    def test_payment_help_payment(self):
        """Test payment help - payment issue"""
        result = self.ai_service._fallback_categorize("i have a payment problem")
        self.assertEqual(result, 'payment_help')
    
    def test_payment_help_card(self):
        """Test payment help - card issue"""
        result = self.ai_service._fallback_categorize("my card is not working")
        self.assertEqual(result, 'payment_help')
    
    def test_complaint_wrong(self):
        """Test complaint - wrong order"""
        result = self.ai_service._fallback_categorize("i got the wrong order")
        self.assertEqual(result, 'complaint')
    
    def test_complaint_late(self):
        """Test complaint - late delivery"""
        result = self.ai_service._fallback_categorize("my order is late")
        self.assertEqual(result, 'complaint')
    
    def test_menu_request(self):
        """Test menu request"""
        result = self.ai_service._fallback_categorize("what do you have on the menu")
        self.assertEqual(result, 'menu_request')
    
    def test_order_inquiry_general(self):
        """Test general order inquiry"""
        result = self.ai_service._fallback_categorize("i want to order something")
        self.assertEqual(result, 'order_inquiry')
    
    def test_case_insensitive(self):
        """Test case insensitivity"""
        result1 = self.ai_service._fallback_categorize("I WANT EBA")
        result2 = self.ai_service._fallback_categorize("i want eba")
        result3 = self.ai_service._fallback_categorize("I Want Eba")
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
        self.assertEqual(result1, 'nigerian_food_request')
    
    def test_default_general_info(self):
        """Test default to general_info"""
        result = self.ai_service._fallback_categorize("random text that doesn't match anything")
        self.assertEqual(result, 'general_info')
    
    def test_multiple_keywords(self):
        """Test message with multiple keywords"""
        result = self.ai_service._fallback_categorize("hello, i want to order eba with chicken")
        # Should prioritize order over greeting
        self.assertEqual(result, 'food_order_with_extras')
    
    def test_nigerian_food_priority(self):
        """Test that Nigerian food is detected correctly"""
        result = self.ai_service._fallback_categorize("i want afang soup")
        self.assertEqual(result, 'nigerian_food_request')
    
    def test_extras_detection(self):
        """Test extras detection"""
        result = self.ai_service._fallback_categorize("i want rice without onions")
        self.assertEqual(result, 'food_order_with_extras')
    
    def test_spicy_detection(self):
        """Test spicy detection as extra"""
        result = self.ai_service._fallback_categorize("i want extra spicy chicken")
        self.assertEqual(result, 'food_order_with_extras')

