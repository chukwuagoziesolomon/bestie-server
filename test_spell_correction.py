#!/usr/bin/env python3
"""
Test spell correction for jollof rice message
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.enhanced_ai_service import SpellCorrector

print("=== TESTING SPELL CORRECTION ===")

# Test the message from user's screenshot
test_message = "i want to order jollof rice"

corrector = SpellCorrector()
print(f"Food dictionary contains 'jollof': {'jollof' in corrector.food_dictionary}")
print(f"Food dictionary contains 'rice': {'rice' in corrector.food_dictionary}")

corrected_text, was_corrected = corrector.correct_message(test_message)

print(f"\nOriginal: '{test_message}'")
print(f"Corrected: '{corrected_text}'")
print(f"Was corrected: {was_corrected}")

if was_corrected:
    print("❌ PROBLEM: Message was incorrectly flagged as needing correction")
else:
    print("✅ OK: Message was not flagged for correction")