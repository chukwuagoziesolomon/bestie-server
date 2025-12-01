#!/usr/bin/env python3
"""
Quick script to search for the note message in AI templates
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.models import AIResponseTemplate, WhatsAppMessage

print("=== SEARCHING FOR NOTE MESSAGE ===")

# Search in AI templates
templates = AIResponseTemplate.objects.filter(template_text__icontains="Note")
print(f"\nTemplates containing 'Note': {templates.count()}")
for template in templates:
    print(f"Category: {template.category}")
    print(f"Template: {template.template_text[:150]}...")
    print()

# Search in messages
messages = WhatsAppMessage.objects.filter(content__icontains="📝").order_by('-created_at')
print(f"\nRecent messages with 📝: {messages.count()}")
for msg in messages[:5]:
    print(f"Direction: {msg.direction}")
    print(f"Content: {msg.content}")
    print(f"Created: {msg.created_at}")
    print("---")

# Search in messages for the exact pattern
exact_messages = WhatsAppMessage.objects.filter(content__icontains="understood you meant").order_by('-created_at')
print(f"\nMessages with 'understood you meant': {exact_messages.count()}")
for msg in exact_messages[:3]:
    print(f"Direction: {msg.direction}")
    print(f"Content: {msg.content}")
    print(f"Created: {msg.created_at}")
    print("---")