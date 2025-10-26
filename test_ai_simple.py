#!/usr/bin/env python
import os
import sys

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')

import django
django.setup()

from bestyy.communication.whatsapp.models import AIResponseTemplate
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService

print("Testing AI Service...")

# Check templates
templates = AIResponseTemplate.objects.all()
print(f"Current templates: {templates.count()}")

# Create templates if none exist
if templates.count() == 0:
    print("Creating basic templates...")
    template_data = [
        ('greeting', 'Hello! Welcome to Bestyy! How can I help you today?', []),
        ('new_user_greeting', 'Hi there! Welcome to Bestyy!', []),
        ('returning_user_greeting', 'Welcome back! Great to see you again.', ['user_first_name']),
        ('food_recommendation', 'I would be happy to recommend some delicious options!', []),
        ('specific_food_request', 'I understand you are interested in {user_message}.', ['user_message']),
        ('order_inquiry', 'I would be happy to help you place an order!', []),
        ('menu_request', 'Here are some of our most popular menu items!', []),
        ('fallback', 'I understand you need help with: {user_message}.', ['user_message'])
    ]

    for category, template_text, variables in template_data:
        template, created = AIResponseTemplate.objects.get_or_create(
            category=category,
            language='en',
            defaults={
                'template_text': template_text,
                'variables': variables,
                'is_active': True
            }
        )
        print(f"{'Created' if created else 'Found'}: {category}")

print(f"Total templates: {AIResponseTemplate.objects.count()}")

# Test AI service
try:
    ai_service = WhatsAppAIService()
    print("AI Service initialized")

    # Test categorization
    test_cases = [
        "i want to order pizza",
        "hello",
        "what food do you have",
        "how much does delivery cost"
    ]

    for test_msg in test_cases:
        category = ai_service._categorize_message(test_msg)
        print(f"'{test_msg}' -> {category}")

    print("AI Service test completed!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
