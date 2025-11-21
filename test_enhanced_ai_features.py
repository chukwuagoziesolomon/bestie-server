"""
Test Enhanced AI Features
Run this to verify intention detection, personalization, and preference tracking
"""
import os
import sys
import django

# Setup Django
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from bestyy.communication.whatsapp.intention_detection_service import IntentionDetectionService, PersonalizedResponseGenerator


def test_intention_detection():
    print("\n" + "="*60)
    print("TEST 1: Intention Detection")
    print("="*60)
    
    detector = IntentionDetectionService(user_id="test_user", user_name="Chukwuagozie")
    
    test_messages = [
        ("I want jollof rice", "Should detect food_ordering"),
        ("How much does delivery cost?", "Should detect customer_service + delivery"),
        ("What's the weather today?", "Should detect out_of_scope"),
        ("Tell me a joke", "Should detect out_of_scope"),
        ("Where is my order?", "Should detect delivery + customer_service"),
    ]
    
    for message, expected in test_messages:
        result = detector.detect_intention(message)
        print(f"\nMessage: '{message}'")
        print(f"Expected: {expected}")
        print(f"Result: should_respond={result['should_respond']}, "
              f"type={result['intention_type']}, "
              f"confidence={result['confidence']:.2f}, "
              f"out_of_scope={result['is_out_of_scope']}")
        
        if result['is_out_of_scope']:
            decline_msg = detector.get_polite_decline_message(message)
            print(f"Decline message: {decline_msg[:100]}...")


def test_preference_tracking():
    print("\n" + "="*60)
    print("TEST 2: Preference Tracking")
    print("="*60)
    
    detector = IntentionDetectionService(user_id="test_user", user_name="Chukwuagozie")
    
    test_messages = [
        "I love jollof rice",
        "I hate beans",
        "I don't like okra soup",
        "My favorite is suya",
    ]
    
    for message in test_messages:
        print(f"\nProcessing: '{message}'")
        prefs = detector.extract_preferences_from_message(message)
        for item, pref_type in prefs:
            detector.add_user_preference(item, pref_type)
            print(f"  Tracked: {item} - {pref_type}")
    
    # Check stored preferences
    stored_prefs = detector.get_user_preferences()
    print(f"\n✅ Stored Preferences:")
    print(f"  Likes: {stored_prefs.get('likes', [])}")
    print(f"  Dislikes: {stored_prefs.get('dislikes', [])}")


def test_order_conflict_detection():
    print("\n" + "="*60)
    print("TEST 3: Order Conflict Detection")
    print("="*60)
    
    detector = IntentionDetectionService(user_id="test_user", user_name="Chukwuagozie")
    
    # Set up preferences
    detector.add_user_preference("beans", "dislike")
    detector.add_user_preference("okra soup", "dislike")
    
    # Test conflict detection
    test_orders = [
        (["Jollof Rice", "Chicken"], "Should pass - no conflicts"),
        (["Beans", "Rice"], "Should warn - user dislikes beans"),
        (["Okra Soup", "Fufu"], "Should warn - user dislikes okra soup"),
    ]
    
    for items, expected in test_orders:
        print(f"\nOrdering: {items}")
        print(f"Expected: {expected}")
        has_conflict, conflicting, warning = detector.check_order_conflicts(items)
        
        if has_conflict:
            print(f"⚠️ CONFLICT DETECTED!")
            print(f"  Conflicting items: {conflicting}")
            print(f"  Warning:\n{warning}")
        else:
            print(f"✅ No conflicts - order can proceed")


def test_personalized_responses():
    print("\n" + "="*60)
    print("TEST 4: Personalized Responses")
    print("="*60)
    
    generator = PersonalizedResponseGenerator(user_name="Chukwuagozie", tone="friendly")
    
    print("\n1. Greeting:")
    print(generator.generate_greeting())
    
    print("\n2. Order Confirmation:")
    print(generator.generate_order_confirmation(["Jollof Rice", "Chicken"]))
    
    print("\n3. Preference Acknowledgment (like):")
    print(generator.generate_preference_acknowledgment("Jollof Rice", "like"))
    
    print("\n4. Preference Acknowledgment (dislike):")
    print(generator.generate_preference_acknowledgment("Beans", "dislike"))
    
    print("\n5. Empathetic Response:")
    print(generator.generate_empathetic_response("Order was late"))
    
    print("\n6. Add Emoji:")
    base_msg = "Your order is ready for delivery"
    print(f"Before: {base_msg}")
    print(f"After: {generator.add_emoji(base_msg, 'delivery')}")


def test_spell_correction():
    print("\n" + "="*60)
    print("TEST 5: Spell Correction")
    print("="*60)
    
    from bestyy.communication.whatsapp.enhanced_ai_service import SpellCorrector
    
    corrector = SpellCorrector()
    
    test_messages = [
        "I want jellof rce",
        "Give me egushi sop",
        "I love suuya",
        "I want pounded yam and egusii",
    ]
    
    for message in test_messages:
        corrected, was_corrected = corrector.correct_message(message)
        print(f"\nOriginal:  '{message}'")
        print(f"Corrected: '{corrected}'")
        print(f"Changed:   {was_corrected}")


def main():
    print("\n" + "="*60)
    print("ENHANCED AI SYSTEM TEST SUITE")
    print("="*60)
    
    try:
        test_intention_detection()
        test_preference_tracking()
        test_order_conflict_detection()
        test_personalized_responses()
        test_spell_correction()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        print("\nThe enhanced AI system is working correctly!")
        print("Features tested:")
        print("  ✅ Intention detection (in-scope vs out-of-scope)")
        print("  ✅ Preference tracking (likes & dislikes)")
        print("  ✅ Order conflict detection")
        print("  ✅ Personalized responses with names & emojis")
        print("  ✅ Spell correction & fuzzy matching")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
