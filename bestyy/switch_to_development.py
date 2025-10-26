#!/usr/bin/env python3
"""
Script to switch to development mode with SQLite database
"""
import os
import sys
import subprocess
from pathlib import Path

def switch_to_development():
    """Switch to development mode"""
    print("🔧 Switching to Development Mode...")
    print("=" * 50)
    
    # Set environment variable for development settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'bestyy.settings_development'
    
    # Check if db.sqlite3 exists
    db_path = Path('db.sqlite3')
    if db_path.exists():
        print("✅ SQLite database found")
    else:
        print("📝 Creating new SQLite database...")
    
    # Run migrations
    try:
        print("\n🔄 Running database migrations...")
        subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
        print("✅ Migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    # Create superuser if needed
    try:
        print("\n👤 Checking for superuser...")
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c',
            'from django.contrib.auth import get_user_model; User = get_user_model(); print("Superuser exists" if User.objects.filter(is_superuser=True).exists() else "No superuser")'
        ], capture_output=True, text=True)
        
        if "No superuser" in result.stdout:
            print("👤 No superuser found. You can create one with:")
            print("   python manage.py createsuperuser")
        
    except Exception as e:
        print(f"⚠️  Could not check superuser: {e}")
    
    print(f"\n✅ Development mode setup complete!")
    print(f"\n📋 Next steps:")
    print(f"1. Start the Daphne server:")
    print(f"   daphne -b 0.0.0.0 -p 8000 bestyy.asgi:application")
    print(f"\n2. Or start with Django development server:")
    print(f"   python manage.py runserver")
    print(f"\n3. Test WhatsApp configuration:")
    print(f"   python test_whatsapp_setup.py")
    
    return True

if __name__ == "__main__":
    success = switch_to_development()
    if success:
        print(f"\n🎉 Ready for development!")
    else:
        print(f"\n❌ Setup failed!")
        sys.exit(1)






