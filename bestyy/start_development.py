#!/usr/bin/env python3
"""
Simple script to start development server
"""
import os
import sys
import subprocess

def start_development():
    """Start development server with SQLite"""
    print("🚀 Starting Bestyy Development Server...")
    print("=" * 50)
    
    # Set environment variables for development
    os.environ['DEBUG'] = 'True'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'bestyy.settings'
    
    print("✅ Development mode enabled")
    print("✅ Using SQLite database")
    print("✅ WhatsApp: Twilio (development)")
    print("✅ WebSocket: Enabled")
    
    print(f"\n🌐 Server will start at: http://127.0.0.1:8000")
    print(f"📱 WhatsApp config: http://127.0.0.1:8000/api/user/whatsapp/config/")
    print(f"🔍 Search vendors: http://127.0.0.1:8000/api/user/search/vendors/")
    print(f"📋 Order endpoints: http://127.0.0.1:8000/api/user/orders/")
    
    print(f"\n🔌 WebSocket endpoints:")
    print(f"   ws://127.0.0.1:8000/ws/vendor/notifications/")
    print(f"   ws://127.0.0.1:8000/ws/admin/activity/")
    
    print(f"\n📖 API Documentation:")
    print(f"   - Complete endpoints: docs/COMPLETE_API_ENDPOINTS_SUMMARY.md")
    print(f"   - WhatsApp setup: docs/WHATSAPP_VENDOR_NOTIFICATIONS_SETUP.md")
    print(f"   - Search API: docs/VENDOR_SEARCH_API.md")
    
    print(f"\n🎯 To start the server, run:")
    print(f"   python manage.py runsslserver 0.0.0.0:8000")  # HTTPS for development
    print(f"   OR")
    print(f"   python manage.py runserver 0.0.0.0:8000")  # HTTP fallback
    print(f"   OR")
    print(f"   daphne -b 0.0.0.0 -p 8000 bestyy.asgi:application")
    
    return True

if __name__ == "__main__":
    start_development()






