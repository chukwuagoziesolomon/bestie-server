import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.conf import settings

print("\n=== CLOUDINARY CONFIGURATION ===")
print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
print(f"\nCloudinary Settings:")
for key, value in settings.CLOUDINARY.items():
    if 'secret' in key.lower():
        print(f"  {key}: {'*' * 10 if value else 'NOT SET'}")
    else:
        print(f"  {key}: {value if value else 'NOT SET'}")

print(f"\n=== TESTING UPLOAD ===")
# Check if cloudinary is configured
if settings.CLOUDINARY.get('cloud_name'):
    print("Cloudinary cloud_name is configured")
    
    # Try to import cloudinary
    try:
        import cloudinary
        import cloudinary.config
        
        cloudinary.config(
            cloud_name=settings.CLOUDINARY['cloud_name'],
            api_key=settings.CLOUDINARY['api_key'],
            api_secret=settings.CLOUDINARY['api_secret']
        )
        print("Cloudinary module imported and configured successfully")
        
        # Test config
        config = cloudinary.config()
        print(f"Cloudinary configured with cloud: {config.cloud_name}")
        
    except Exception as e:
        print(f"Error with cloudinary: {e}")
else:
    print("ERROR: Cloudinary cloud_name is NOT configured!")
    print("Files will be saved locally to /media/ folder")
