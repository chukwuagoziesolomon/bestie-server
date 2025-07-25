from django.core.management.base import BaseCommand
from django.conf import settings
from user.models import MenuItem, VendorProfile, UserProfile, CourierProfile, Accommodation
import cloudinary
import cloudinary.uploader
from django.core.files.storage import default_storage

class Command(BaseCommand):
    help = 'Check Cloudinary configuration and test image storage'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Cloudinary Configuration Check ==='))
        
        # Check Django settings
        self.stdout.write(f"DEBUG: {settings.DEBUG}")
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        
        # Check Cloudinary config
        try:
            config = cloudinary.config()
            self.stdout.write(f"Cloudinary Cloud Name: {config.cloud_name or 'NOT SET'}")
            self.stdout.write(f"Cloudinary API Key: {'SET' if config.api_key else 'NOT SET'}")
            self.stdout.write(f"Cloudinary API Secret: {'SET' if config.api_secret else 'NOT SET'}")
            
            if not all([config.cloud_name, config.api_key, config.api_secret]):
                self.stdout.write(self.style.ERROR('❌ Cloudinary credentials are missing!'))
                return
            else:
                self.stdout.write(self.style.SUCCESS('✅ Cloudinary credentials are configured'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error checking Cloudinary config: {e}'))
            return
        
        # Check storage backend
        self.stdout.write(f"\nStorage backend: {default_storage.__class__.__name__}")
        
        # Check existing menu items
        self.stdout.write('\n=== Existing Menu Items ===')
        menu_items = MenuItem.objects.filter(image__isnull=False)[:5]
        
        for item in menu_items:
            self.stdout.write(f"Item: {item.dish_name}")
            self.stdout.write(f"  Image field: {item.image}")
            self.stdout.write(f"  Image URL: {item.image.url if item.image else 'No image'}")
            
            # Check if URL is Cloudinary or local
            if item.image and item.image.url:
                if 'cloudinary.com' in item.image.url:
                    self.stdout.write(self.style.SUCCESS('  ✅ Using Cloudinary'))
                else:
                    self.stdout.write(self.style.WARNING('  ⚠️  Using local storage'))
            self.stdout.write('')
        
        if not menu_items.exists():
            self.stdout.write('No menu items with images found')
        
        self.stdout.write('\n=== Recommendations ===')
        if not all([config.cloud_name, config.api_key, config.api_secret]):
            self.stdout.write('1. Set Cloudinary environment variables in Render:')
            self.stdout.write('   - CLOUDINARY_CLOUD_NAME')
            self.stdout.write('   - CLOUDINARY_API_KEY')
            self.stdout.write('   - CLOUDINARY_API_SECRET')
        
        if menu_items.exists() and any('cloudinary.com' not in item.image.url for item in menu_items if item.image):
            self.stdout.write('2. Some images are still using local storage')
            self.stdout.write('   - New uploads should use Cloudinary automatically')
            self.stdout.write('   - Existing images may need to be re-uploaded')
