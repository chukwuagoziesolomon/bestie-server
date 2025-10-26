#!/usr/bin/env python
"""
Test script to verify Cloudinary configuration for Render deployment
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from django.conf import settings
import cloudinary
import cloudinary.uploader

def test_cloudinary_config():
    """Test Cloudinary configuration"""
    print("=== Cloudinary Configuration Test ===")
    
    # Check if Cloudinary is configured
    try:
        config = cloudinary.config()
        print(f"✓ Cloudinary Cloud Name: {config.cloud_name}")
        print(f"✓ Cloudinary API Key: {config.api_key[:10]}..." if config.api_key else "✗ API Key missing")
        print(f"✓ Cloudinary API Secret: {'*' * 10}" if config.api_secret else "✗ API Secret missing")
        
        if not all([config.cloud_name, config.api_key, config.api_secret]):
            print("✗ Cloudinary configuration incomplete!")
            return False
            
        print("✓ Cloudinary configuration looks good!")
        return True
        
    except Exception as e:
        print(f"✗ Error checking Cloudinary config: {e}")
        return False

def test_django_settings():
    """Test Django media settings"""
    print("\n=== Django Settings Test ===")
    
    try:
        print(f"DEBUG: {settings.DEBUG}")
        print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        print(f"MEDIA_URL: {settings.MEDIA_URL}")
        
        if hasattr(settings, 'CLOUDINARY_STORAGE'):
            storage_config = settings.CLOUDINARY_STORAGE
            print(f"✓ CLOUDINARY_STORAGE configured")
            print(f"  - Cloud Name: {storage_config.get('CLOUD_NAME', 'Not set')}")
            print(f"  - API Key: {'Set' if storage_config.get('API_KEY') else 'Not set'}")
            print(f"  - API Secret: {'Set' if storage_config.get('API_SECRET') else 'Not set'}")
        else:
            print("✗ CLOUDINARY_STORAGE not configured")
            
        return True
        
    except Exception as e:
        print(f"✗ Error checking Django settings: {e}")
        return False

def test_environment_variables():
    """Test environment variables"""
    print("\n=== Environment Variables Test ===")
    
    env_vars = [
        'CLOUDINARY_CLOUD_NAME',
        'CLOUDINARY_API_KEY', 
        'CLOUDINARY_API_SECRET'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Not set")
            
    # Check for secret files (Render specific)
    secret_files = [
        '/etc/secrets/CLOUDINARY_CLOUD_NAME',
        '/etc/secrets/CLOUDINARY_API_KEY',
        '/etc/secrets/CLOUDINARY_API_SECRET'
    ]
    
    print("\n--- Render Secret Files ---")
    for file_path in secret_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}: Exists")
        else:
            print(f"✗ {file_path}: Not found")

if __name__ == "__main__":
    print("Testing Cloudinary setup for Render deployment...\n")
    
    config_ok = test_cloudinary_config()
    settings_ok = test_django_settings()
    test_environment_variables()
    
    print("\n=== Summary ===")
    if config_ok and settings_ok:
        print("✓ Configuration looks good! Your media files should work on Render.")
    else:
        print("✗ There are configuration issues that need to be fixed.")
        print("\nNext steps:")
        print("1. Make sure your Cloudinary credentials are set in Render environment variables")
        print("2. Or add them as secret files in Render's /etc/secrets/ directory")
        print("3. Redeploy your application after fixing the configuration")
