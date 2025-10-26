#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.models import AIResponseTemplate, WhatsAppMessage, WhatsAppConversation
from bestyy.communication.whatsapp.ai_service import WhatsAppAIService

def test_ai_service():
    print("Testing AI Service...")

    # Check if templates exist
    templates = AIResponseTemplate.objects.all()
    print(f"Total templates: {templates.count()}")

    if templates.count() == 0:
        print("No templates found. Creating basic templates...")

        # Create basic templates
        template_data = [
            ('greeting', 'Hello! Welcome to Bestyy! How can I help you today?', []),
            ('new_user_greeting', 'Hi there! I see this is your first time with us. Welcome to Bestyy!', []),
            ('returning_user_greeting', 'Welcome back, {user_first_name}! Great to see you again.', ['user_first_name']),
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
            print(f"{'Created' if created else 'Found'} template: {category}")

    print(f"Total templates now: {AIResponseTemplate.objects.count()}")

    # Create a test conversation for response generation testing
    conversation = WhatsAppConversation.objects.create(
        phone_number="+1234567890",
        is_active=True
    )

    # Test AI service
    try:
        ai_service = WhatsAppAIService()
        print("AI Service initialized successfully")

        # Test message categorization
        test_message = "i want to order pizza"
        category = ai_service._categorize_message(test_message)
        print(f"Message '{test_message}' categorized as: {category}")

        # Test with a greeting
        greeting_message = "hello"
        greeting_category = ai_service._categorize_message(greeting_message)
        print(f"Message '{greeting_message}' categorized as: {greeting_category}")

        # Test actual response generation
        print("\n=== Testing Response Generation ===")
        try:
            # Create a test message object
            whatsapp_message = WhatsAppMessage.objects.create(
                conversation=conversation,
                message_type='text',
                content='hello',
                direction='inbound'
            )

            # Test response generation
            response = ai_service.process_message(whatsapp_message, context={'user_exists': True})
            print(f"Response generation success: {response.get('success', False)}")
            if response.get('success'):
                print(f"Generated response: {response.get('response', '')[:100]}...")
            else:
                print(f"Response generation failed: {response.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"Response generation test failed: {e}")
            import traceback
            traceback.print_exc()

        print("AI Service test completed successfully!")

    except Exception as e:
        print(f"Error testing AI service: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            conversation.delete()
        except:
            pass

if __name__ == '__main__':
    test_ai_service()
