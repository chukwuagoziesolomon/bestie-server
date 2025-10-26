import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from bestyy.communication.whatsapp.models import AIResponseTemplate

def create_templates():
    # Create basic AI response templates
    templates_data = [
        {
            'category': 'greeting',
            'template_text': 'Hello! Welcome to Bestyy! How can I help you today?',
            'variables': []
        },
        {
            'category': 'new_user_greeting',
            'template_text': 'Hi there! I see this is your first time with us. Welcome to Bestyy! I\'d be happy to help you get started. What would you like to know about our food delivery service?',
            'variables': []
        },
        {
            'category': 'returning_user_greeting',
            'template_text': 'Welcome back, {user_first_name}! Great to see you again. How can I assist you today?',
            'variables': ['user_first_name']
        },
        {
            'category': 'food_recommendation',
            'template_text': 'I\'d be happy to recommend some delicious options! Based on our popular items, you might enjoy: {top_item_1_name} - {top_item_1_description} for ${top_item_1_price}. Would you like to know more about this or see other recommendations?',
            'variables': ['top_item_1_name', 'top_item_1_description', 'top_item_1_price']
        },
        {
            'category': 'specific_food_request',
            'template_text': 'I understand you\'re interested in {user_message}. We have some great options in that category! Let me check our current menu and get back to you with the best matches.',
            'variables': ['user_message']
        },
        {
            'category': 'order_inquiry',
            'template_text': 'I\'d be happy to help you place an order! To get started, could you tell me what you\'d like to order? You can browse our menu or let me know if you have something specific in mind.',
            'variables': []
        },
        {
            'category': 'menu_request',
            'template_text': 'Here are some of our most popular menu items:\n\n{top_item_1_name} - {top_item_1_description} - ${top_item_1_price}\n{top_item_2_name} - {top_item_2_description} - ${top_item_2_price}\n\nWould you like to order any of these or see more options?',
            'variables': ['top_item_1_name', 'top_item_1_description', 'top_item_1_price', 'top_item_2_name', 'top_item_2_description', 'top_item_2_price']
        },
        {
            'category': 'fallback',
            'template_text': 'I understand you need help with: {user_message}. I\'m here to assist you with your food delivery needs. Could you please provide more details about what you\'re looking for?',
            'variables': ['user_message']
        }
    ]

    for template_data in templates_data:
        template, created = AIResponseTemplate.objects.get_or_create(
            category=template_data['category'],
            language='en',
            defaults={
                'template_text': template_data['template_text'],
                'variables': template_data['variables'],
                'is_active': True
            }
        )
        status = 'Created' if created else 'Found'
        print(f'{status} template: {template.category}')

    total_count = AIResponseTemplate.objects.count()
    print(f'Total templates created/found: {total_count}')

if __name__ == '__main__':
    create_templates()
