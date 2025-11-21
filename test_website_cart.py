"""
Test JWT-Based Cart System
Works across ALL browsers without cookies
"""
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from bestyy.core_features.user.models import AnonymousCart, WebsiteCartItem, VendorProfile
from bestyy.restaurant_features.product.models import Product

User = get_user_model()


class WebsiteCartTestCase(TestCase):
    """Test JWT-based cart system"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test vendor
        self.vendor = VendorProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            phone='+2341234567890',
            business_category='Restaurant',
            business_address='123 Test St',
            delivery_radius='5km',
            service_areas='Lagos'
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            name='Jollof Rice',
            description='Delicious jollof rice',
            price=1500.00,
            vendor=self.vendor,
            stock_quantity=100,
            is_available=True
        )
        
        self.product2 = Product.objects.create(
            name='Fried Rice',
            description='Tasty fried rice',
            price=2000.00,
            vendor=self.vendor,
            stock_quantity=50,
            is_available=True
        )
    
    def test_add_to_cart_anonymous(self):
        """Test adding product to cart as anonymous user"""
        response = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIsNotNone(response.data['cart_token'])  # CRITICAL
        self.assertEqual(response.data['total_items'], 2)
        self.assertEqual(response.data['product']['id'], self.product1.id)
        
        # Verify cart exists in database
        cart_token = response.data['cart_token']
        self.assertTrue(AnonymousCart.objects.filter(cart_token=cart_token).exists())
        
        # Verify item exists
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.product, self.product1)
        self.assertEqual(item.quantity, 2)
    
    def test_add_to_cart_with_existing_token(self):
        """Test adding product with existing cart_token"""
        # First add
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 1
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Second add with same token (different product)
        response2 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product2.id,
            'quantity': 3,
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data['cart_token'], cart_token)  # Same token
        self.assertEqual(response2.data['total_items'], 4)  # 1 + 3
    
    def test_update_cart_quantity(self):
        """Test updating product quantity in cart"""
        # Add product
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Add same product again (should increase quantity)
        response2 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 3,
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['product']['quantity'], 5)  # 2 + 3
    
    def test_list_cart_items(self):
        """Test retrieving cart items"""
        # Add products
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product2.id,
            'quantity': 1,
            'cart_token': cart_token
        }, format='json')
        
        # Get cart list
        response = self.client.get(f'/api/user/website-cart/?cart_token={cart_token}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['products']), 2)
        self.assertEqual(response.data['total_items'], 3)  # 2 + 1
    
    def test_update_cart_item_quantity(self):
        """Test updating cart item quantity"""
        # Add product
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Update quantity
        response = self.client.post('/api/user/website-cart/update/', {
            'product_id': self.product1.id,
            'quantity': 5,
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product']['quantity'], 5)
    
    def test_remove_from_cart(self):
        """Test removing product from cart"""
        # Add product
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Remove product
        response = self.client.post('/api/user/website-cart/remove/', {
            'product_id': self.product1.id,
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify item removed
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        self.assertEqual(cart.items.count(), 0)
    
    def test_clear_cart(self):
        """Test clearing entire cart"""
        # Add products
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product2.id,
            'quantity': 1,
            'cart_token': cart_token
        }, format='json')
        
        # Clear cart
        response = self.client.post('/api/user/website-cart/clear/', {
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all items removed
        cart = AnonymousCart.objects.get(cart_token=cart_token)
        self.assertEqual(cart.items.count(), 0)
    
    def test_cart_summary(self):
        """Test getting cart summary"""
        # Add products
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product2.id,
            'quantity': 1,
            'cart_token': cart_token
        }, format='json')
        
        # Get summary
        response = self.client.get(f'/api/user/website-cart/summary/?cart_token={cart_token}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 3)
        self.assertEqual(response.data['total_amount'], 5000.00)  # (1500*2) + (2000*1)
    
    def test_authenticated_user_cart(self):
        """Test cart for authenticated user (no cart_token needed)"""
        # Login
        self.client.force_authenticate(user=self.user)
        
        # Add product (no cart_token)
        response = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['cart_token'])  # No token for auth users
        
        # Verify item linked to user
        self.assertEqual(WebsiteCartItem.objects.filter(user=self.user).count(), 1)
    
    def test_merge_carts_on_login(self):
        """Test merging anonymous cart into user cart on login"""
        # Add to anonymous cart
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Login
        self.client.force_authenticate(user=self.user)
        
        # Merge cart
        response = self.client.post('/api/user/website-cart/merge/', {
            'cart_token': cart_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 2)
        
        # Verify items transferred to user
        self.assertEqual(WebsiteCartItem.objects.filter(user=self.user).count(), 1)
        
        # Verify anonymous cart deleted
        self.assertFalse(AnonymousCart.objects.filter(cart_token=cart_token).exists())
    
    def test_stock_validation(self):
        """Test stock quantity validation"""
        # Try to add more than available stock
        response = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product2.id,
            'quantity': 100  # Only 50 in stock
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('available in stock', response.data['error'].lower())
    
    def test_cart_token_header(self):
        """Test passing cart_token in header"""
        # Add product
        response1 = self.client.post('/api/user/website-cart/add/', {
            'product_id': self.product1.id,
            'quantity': 2
        }, format='json')
        
        cart_token = response1.data['cart_token']
        
        # Get cart with token in header
        response = self.client.get(
            '/api/user/website-cart/',
            HTTP_X_CART_TOKEN=cart_token
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 2)


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
    django.setup()
    
    from django.test.utils import get_runner
    TestRunner = get_runner(django.conf.settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['test_website_cart'])
