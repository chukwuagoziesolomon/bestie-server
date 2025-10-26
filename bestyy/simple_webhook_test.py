#!/usr/bin/env python3
"""
Simple webhook test to debug the 403 issue
"""

import os
import sys
import django

# Add the project root directory to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.conf import settings

def check_environment():
    """Check what environment variables are actually set"""
    print("Environment Variables Check:")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    print(f".env file exists: {os.path.exists(env_file)}")
    
    if os.path.exists(env_file):
        print(f".env file path: {env_file}")
        with open(env_file, 'r') as f:
            lines = f.readlines()
            whatsapp_lines = [line for line in lines if 'WHATSAPP' in line]
            if whatsapp_lines:
                print("WhatsApp related lines in .env:")
                for line in whatsapp_lines:
                    print(f"  {line.strip()}")
            else:
                print("No WhatsApp lines found in .env file")
    
    print()
    
    # Check Django settings
    print("Django Settings:")
    print(f"WHATSAPP_VERIFY_TOKEN: {getattr(settings, 'WHATSAPP_VERIFY_TOKEN', 'NOT SET')}")
    print(f"WHATSAPP_ACCESS_TOKEN: {getattr(settings, 'WHATSAPP_ACCESS_TOKEN', 'NOT SET')}")
    print(f"WHATSAPP_PHONE_NUMBER_ID: {getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', 'NOT SET')}")
    print(f"META_APP_SECRET: {getattr(settings, 'META_APP_SECRET', 'NOT SET')}")
    
    print()
    print("Environment Variables from os.environ:")
    whatsapp_env_vars = {k: v for k, v in os.environ.items() if 'WHATSAPP' in k or 'META' in k}
    for k, v in whatsapp_env_vars.items():
        if 'SECRET' in k or 'TOKEN' in k:
            print(f"  {k}: {v[:10]}..." if len(v) > 10 else f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

if __name__ == "__main__":
    check_environment()


