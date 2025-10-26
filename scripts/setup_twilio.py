#!/usr/bin/env python3
"""
Setup script for Twilio WhatsApp integration
"""
import os
import sys
import subprocess

def install_twilio():
    """Install Twilio Python SDK"""
    try:
        print("Installing Twilio Python SDK...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "twilio"])
        print("✅ Twilio SDK installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Twilio SDK: {e}")
        return False

def check_twilio_installation():
    """Check if Twilio is properly installed"""
    try:
        import twilio
        from twilio.rest import Client
        print("✅ Twilio is properly installed and importable")
        return True
    except ImportError as e:
        print(f"❌ Twilio import failed: {e}")
        return False

def create_env_example():
    """Create .env.example with Twilio configuration"""
    env_example_content = """# Twilio WhatsApp Configuration (Development)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# WhatsApp Business API Configuration (Production)
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here

# Environment Settings
DEBUG=True
"""
    
    try:
        with open('.env.example', 'w') as f:
            f.write(env_example_content)
        print("✅ Created .env.example with Twilio configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env.example: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Twilio WhatsApp integration...")
    print("=" * 50)
    
    # Install Twilio
    if not install_twilio():
        sys.exit(1)
    
    # Check installation
    if not check_twilio_installation():
        sys.exit(1)
    
    # Create .env.example
    create_env_example()
    
    print("\n" + "=" * 50)
    print("✅ Twilio WhatsApp setup completed!")
    print("\n📋 Next steps:")
    print("1. Get your Twilio credentials from https://console.twilio.com/")
    print("2. Add credentials to your .env file:")
    print("   TWILIO_ACCOUNT_SID=your_account_sid")
    print("   TWILIO_AUTH_TOKEN=your_auth_token")
    print("   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886")
    print("3. Test the integration:")
    print("   curl -X GET http://localhost:8000/api/user/whatsapp/config/")
    print("4. Send test message:")
    print("   curl -X POST http://localhost:8000/api/user/whatsapp/test/ \\")
    print("     -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"phone_number\": \"+234-123-456-7890\"}'")
    print("\n🔗 Twilio WhatsApp Sandbox: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn")

if __name__ == "__main__":
    main()






