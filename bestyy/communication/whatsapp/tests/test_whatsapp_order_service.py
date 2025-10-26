"""
Tests for WhatsApp Order Processing Service
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from bestyy.core_features.user.models import (
    VendorProfile, MenuItem, Cart, Order, Address
)
from bestyy.communication.whatsapp.whatsapp_order_service import WhatsAppOrderService

User = get_user_model()


class WhatsAppOrderServiceTestCase(TestCase):
    """Test cases for WhatsApp Order Service"""
    
    def setUp(self):
        """Set up test data"""
        self.order_service = WhatsAppOrderService()
        
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
        
        self.coke_item = MenuItem.objects.create(
            vendor=self.vendor,
            dish_name='Coca Cola',
            price=Decimal('500.00'),
            category='beverage',
            available_now=True
        )
    
    def test_search_vendors_by_food(self):
        """Test vendor search by food type"""
        result = self.order_service.search_vendors_by_food('pizza', limit=3)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['vendors']), 1)
        self.assertEqual(result['vendors'][0]['name'], 'Pizza Palace')
        self.assertIn('menu_items', result['vendors'][0])
    
    def test_search_vendors_no_results(self):
        """Test vendor search with no results"""
        result = self.order_service.search_vendors_by_food('sushi', limit=3)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['vendors']), 0)
    
    def test_create_order_from_whatsapp(self):
        """Test order creation from WhatsApp"""
        items_data = [
            {'menu_item_id': self.pizza_item.id, 'quantity': 2},
            {'menu_item_id': self.coke_item.id, 'quantity': 1}
        ]
        
        result = self.order_service.create_order_from_whatsapp(
            user=self.user,
            vendor_id=self.vendor.id,
            items_data=items_data,
            delivery_address_text='123 Test Street, Lagos',
            payment_method='cash'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('order', result)
        
        order_data = result['order']
        self.assertEqual(order_data['vendor'], 'Pizza Palace')
        self.assertEqual(len(order_data['items']), 2)
        self.assertEqual(
            order_data['total_amount'],
            float(Decimal('5000.00') * 2 + Decimal('500.00'))
        )
        self.assertEqual(order_data['payment_method'], 'cash')
        self.assertIsNone(order_data['payment_link'])  # Cash payment has no link
    
    def test_create_order_with_card_payment(self):
        """Test order creation with card payment"""
        items_data = [
            {'menu_item_id': self.pizza_item.id, 'quantity': 1}
        ]
        
        result = self.order_service.create_order_from_whatsapp(
            user=self.user,
            vendor_id=self.vendor.id,
            items_data=items_data,
            delivery_address_text='123 Test Street, Lagos',
            payment_method='card'
        )
        
        self.assertTrue(result['success'])
        order_data = result['order']
        self.assertEqual(order_data['payment_method'], 'card')
        # Payment link may be None if Paystack is not configured
    
    def test_get_order_status(self):
        """Test getting order status"""
        # Create an order first
        order = Order.objects.create(
            user=self.user,
            vendor=self.vendor,
            delivery_address='123 Test Street',
            total_price=Decimal('5000.00'),
            status='pending'
        )
        
        result = self.order_service.get_order_status(order.id, self.user)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['order']['id'], order.id)
        self.assertEqual(result['order']['status'], 'pending')
        self.assertEqual(result['order']['vendor'], 'Pizza Palace')
    
    def test_get_order_status_not_found(self):
        """Test getting status for non-existent order"""
        result = self.order_service.get_order_status(9999, self.user)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_cart_creation(self):
        """Test that cart is created correctly"""
        items_data = [
            {'menu_item_id': self.pizza_item.id, 'quantity': 1}
        ]
        
        result = self.order_service.create_order_from_whatsapp(
            user=self.user,
            vendor_id=self.vendor.id,
            items_data=items_data,
            delivery_address_text='123 Test Street, Lagos',
            payment_method='cash'
        )
        
        # Verify cart was created
        carts = Cart.objects.filter(user=self.user, vendor=self.vendor)
        self.assertEqual(carts.count(), 1)
        
        cart = carts.first()
        self.assertFalse(cart.is_active)  # Cart should be deactivated after order
        self.assertEqual(cart.total_price, Decimal('5000.00'))
    
    def test_address_creation(self):
        """Test that address is created correctly"""
        items_data = [
            {'menu_item_id': self.pizza_item.id, 'quantity': 1}
        ]
        
        address_text = '456 New Street, Lekki'
        result = self.order_service.create_order_from_whatsapp(
            user=self.user,
            vendor_id=self.vendor.id,
            items_data=items_data,
            delivery_address_text=address_text,
            payment_method='cash'
        )
        
        # Verify address was created
        addresses = Address.objects.filter(
            user=self.user,
            street_address=address_text
        )
        self.assertEqual(addresses.count(), 1)
        
        address = addresses.first()
        self.assertEqual(address.city, 'Lagos')
        self.assertEqual(address.state, 'Lagos')

