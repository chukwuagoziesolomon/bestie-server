"""
Django management command to populate database with test vendors and menu items
Usage: python manage.py populate_test_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from decimal import Decimal
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from bestyy.core_features.user.models import VendorProfile, MenuItem, SubscriptionPlan, VendorRating

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with test vendors and menu items'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database population...'))

        # Create test vendors
        vendors = self._create_vendors()

        # Create menu items for each vendor
        for vendor in vendors:
            self._create_menu_items(vendor)

        # Add ratings to vendors
        self._add_vendor_ratings(vendors)

        self.stdout.write(self.style.SUCCESS('✅ Database population complete!'))
        self.stdout.write(self.style.SUCCESS(f'Created {len(vendors)} vendors with menu items and ratings'))

    def _create_vendors(self):
        """Create test vendors"""
        vendors = []
        
        vendor_data = [
            {
                'email': 'pizza_palace@test.com',
                'first_name': 'Pizza',
                'last_name': 'Palace',
                'business_name': 'Pizza Palace',
                'business_category': 'pizza',
                'phone': '+2349012345678',
                'business_description': 'Authentic Italian pizzas and pasta',
            },
            {
                'email': 'nigerian_kitchen@test.com',
                'first_name': 'Nigerian',
                'last_name': 'Kitchen',
                'business_name': 'Nigerian Kitchen',
                'business_category': 'nigerian_food',
                'phone': '+2349012345679',
                'business_description': 'Traditional Nigerian dishes and delicacies',
            },
            {
                'email': 'snack_hub@test.com',
                'first_name': 'Snack',
                'last_name': 'Hub',
                'business_name': 'Snack Hub',
                'business_category': 'snacks',
                'phone': '+2349012345680',
                'business_description': 'Fresh snacks and light bites',
            },
            {
                'email': 'burger_joint@test.com',
                'first_name': 'Burger',
                'last_name': 'Joint',
                'business_name': 'Burger Joint',
                'business_category': 'burgers',
                'phone': '+2349012345681',
                'business_description': 'Juicy burgers and fries',
            },
        ]
        
        for data in vendor_data:
            # Create or get user
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                }
            )
            
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(f'  ✓ Created user: {data["email"]}')
            
            # Create or get vendor profile
            vendor, created = VendorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone': data['phone'],
                    'business_name': data['business_name'],
                    'business_category': data['business_category'],
                    'business_description': data['business_description'],
                    'verification_status': 'approved',
                    'is_suspended': False,
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Created vendor: {data["business_name"]}')
            
            vendors.append(vendor)
        
        return vendors

    def _create_menu_items(self, vendor):
        """Create menu items for a vendor"""
        menu_items_data = {
            'pizza': [
                {'name': 'Pepperoni Pizza', 'price': 5500, 'category': 'pizza', 'description': 'Classic pepperoni with mozzarella', 'color': (220, 20, 60)},
                {'name': 'Margherita Pizza', 'price': 4500, 'category': 'pizza', 'description': 'Fresh tomato, mozzarella, and basil', 'color': (34, 139, 34)},
                {'name': 'Vegetarian Pizza', 'price': 4000, 'category': 'pizza', 'description': 'Mixed vegetables on thin crust', 'color': (255, 165, 0)},
            ],
            'nigerian_food': [
                {'name': 'Eba with Egusi Soup', 'price': 2500, 'category': 'nigerian', 'description': 'Smooth eba with rich egusi soup', 'color': (139, 69, 19)},
                {'name': 'Jollof Rice', 'price': 2000, 'category': 'nigerian', 'description': 'Aromatic jollof rice with chicken', 'color': (255, 140, 0)},
                {'name': 'Pounded Yam with Efo Riro', 'price': 3000, 'category': 'nigerian', 'description': 'Creamy pounded yam with spinach soup', 'color': (184, 134, 11)},
                {'name': 'Moi Moi', 'price': 1500, 'category': 'nigerian', 'description': 'Steamed bean pudding', 'color': (210, 105, 30)},
                {'name': 'Akara', 'price': 1000, 'category': 'nigerian', 'description': 'Fried bean cakes', 'color': (184, 134, 11)},
                {'name': 'Suya', 'price': 2000, 'category': 'nigerian', 'description': 'Spiced grilled meat skewers', 'color': (139, 69, 19)},
                {'name': 'Okoro Soup with Fufu', 'price': 2800, 'category': 'nigerian', 'description': 'Okra soup with smooth fufu', 'color': (34, 139, 34)},
                {'name': 'Pepper Soup', 'price': 2200, 'category': 'nigerian', 'description': 'Spicy pepper soup with meat', 'color': (220, 20, 60)},
                {'name': 'Afang Soup with Semovita', 'price': 3200, 'category': 'nigerian', 'description': 'Afang soup with semovita', 'color': (34, 139, 34)},
                {'name': 'Amala with Ewedu', 'price': 2600, 'category': 'nigerian', 'description': 'Amala with ewedu soup', 'color': (101, 67, 33)},
                {'name': 'Fried Rice', 'price': 1800, 'category': 'nigerian', 'description': 'Delicious fried rice with vegetables', 'color': (255, 215, 0)},
                {'name': 'Plantain Chips', 'price': 1200, 'category': 'nigerian', 'description': 'Crispy fried plantain chips', 'color': (255, 215, 0)},
            ],
            'snacks': [
                {'name': 'Chicken Samosa', 'price': 500, 'category': 'snacks', 'description': 'Crispy fried samosa with chicken filling', 'color': (210, 105, 30)},
                {'name': 'Spring Rolls', 'price': 600, 'category': 'snacks', 'description': 'Golden spring rolls with vegetables', 'color': (184, 134, 11)},
                {'name': 'Meat Pie', 'price': 800, 'category': 'snacks', 'description': 'Flaky pastry with seasoned meat', 'color': (210, 105, 30)},
                {'name': 'Chin Chin', 'price': 1000, 'category': 'snacks', 'description': 'Crispy fried snack', 'color': (184, 134, 11)},
                {'name': 'Popcorn', 'price': 500, 'category': 'snacks', 'description': 'Fresh buttered popcorn', 'color': (255, 215, 0)},
            ],
            'burgers': [
                {'name': 'Classic Burger', 'price': 2500, 'category': 'burgers', 'description': 'Beef patty with lettuce, tomato, and cheese', 'color': (210, 105, 30)},
                {'name': 'Chicken Burger', 'price': 2000, 'category': 'burgers', 'description': 'Crispy chicken breast burger', 'color': (184, 134, 11)},
                {'name': 'Double Cheeseburger', 'price': 3500, 'category': 'burgers', 'description': 'Two beef patties with double cheese', 'color': (139, 69, 19)},
                {'name': 'Veggie Burger', 'price': 1800, 'category': 'burgers', 'description': 'Plant-based patty with fresh vegetables', 'color': (34, 139, 34)},
            ],
        }
        
        # Get menu items for this vendor's category
        category = vendor.business_category
        items = menu_items_data.get(category, [])
        
        for item_data in items:
            # Create or get menu item
            menu_item, created = MenuItem.objects.get_or_create(
                vendor=vendor,
                dish_name=item_data['name'],
                defaults={
                    'price': Decimal(str(item_data['price'])),
                    'category': item_data['category'],
                    'item_description': item_data['description'],
                    'available_now': True,
                    'quantity': 100,
                }
            )

            if created:
                # Try to add a placeholder image with color
                try:
                    color = item_data.get('color', (73, 109, 137))
                    image = self._create_placeholder_image(item_data['name'], color)
                    menu_item.image.save(
                        f"{item_data['name'].replace(' ', '_')}.png",
                        image,
                        save=True
                    )
                    self.stdout.write(f'    ✓ Created menu item: {item_data["name"]} (with image)')
                except Exception as e:
                    self.stdout.write(f'    ✓ Created menu item: {item_data["name"]} (image failed: {str(e)})')

    def _create_placeholder_image(self, text, color=(73, 109, 137)):
        """Create a placeholder image for menu items with text"""
        try:
            # Create a colored image
            img = Image.new('RGB', (400, 300), color=color)
            draw = ImageDraw.Draw(img)

            # Add text to image
            text_color = (255, 255, 255)  # White text
            # Draw text in center
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (400 - text_width) // 2
            y = (300 - text_height) // 2
            draw.text((x, y), text, fill=text_color)

            # Save to BytesIO
            img_io = BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)

            return ContentFile(img_io.getvalue(), name='placeholder.png')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create image: {str(e)}'))
            return None

    def _add_vendor_ratings(self, vendors):
        """Add ratings to vendors"""
        try:
            # Create a test user for ratings
            test_user, _ = User.objects.get_or_create(
                email='test_rater@test.com',
                defaults={
                    'first_name': 'Test',
                    'last_name': 'Rater',
                }
            )

            # Add ratings to each vendor
            ratings = [4.8, 4.6, 4.7, 4.9]
            for vendor, rating in zip(vendors, ratings):
                # Check if rating already exists
                if not VendorRating.objects.filter(vendor=vendor, user=test_user).exists():
                    VendorRating.objects.create(
                        vendor=vendor,
                        user=test_user,
                        rating=rating,
                        review=f"Great service from {vendor.business_name}!"
                    )
                    self.stdout.write(f'  ✓ Added rating {rating}/5 to {vendor.business_name}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not add ratings: {str(e)}'))

