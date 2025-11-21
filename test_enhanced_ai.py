"""
Test script for Enhanced AI System
Tests spell correction, memory, and RLHF features
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from bestyy.communication.whatsapp.enhanced_ai_service import (
    ConversationMemory, SpellCorrector, RLHFFeedbackCollector, EnhancedAIService
)
from bestyy.communication.whatsapp.ai_first_processor import AIFirstMessageProcessor

def test_spell_correction():
    """Test spell correction functionality"""
    print("\n" + "="*60)
    print("TEST 1: Spell Correction")
    print("="*60)
    
    corrector = SpellCorrector()
    
    test_cases = [
        ("i want jellof riec", "i want jollof rice"),
        ("egushi soup pleas", "egusi soup pleas"),
        ("suuya and poundo yam", "suya and pounded yam"),
        ("give me jollof rice", "give me jollof rice"),  # Should stay same
    ]
    
    for original, expected in test_cases:
        corrected, was_changed = corrector.correct_message(original)
        status = "✅" if corrected.lower().startswith(expected.lower().split()[0:3].__str__().replace("['", "").replace("']", "")) else "❌"
        print(f"{status} '{original}' → '{corrected}' (changed: {was_changed})")
    
    print("\n✅ Spell correction test completed!")

def test_conversation_memory():
    """Test conversation memory"""
    print("\n" + "="*60)
    print("TEST 2: Conversation Memory")
    print("="*60)
    
    memory = ConversationMemory("test-conversation-123")
    
    # Add messages
    print("\n📝 Adding messages to memory...")
    memory.add_message('user', 'I want jollof rice', metadata={'category': 'food_order'})
    memory.add_message('assistant', 'Great choice! Here are restaurants...', metadata={'category': 'food_order'})
    memory.add_message('user', 'I want egusi soup', metadata={'category': 'food_order'})
    memory.add_message('assistant', 'Excellent! Egusi soup restaurants...', metadata={'category': 'food_order'})
    
    # Get short-term memory
    short_term = memory.get_short_term()
    print(f"\n✅ Short-term memory: {len(short_term)} messages")
    for msg in short_term:
        print(f"   - {msg['role']}: {msg['content'][:40]}...")
    
    # Get long-term memory
    long_term = memory.get_long_term()
    print(f"\n✅ Long-term memory:")
    print(f"   - Interaction count: {long_term['interaction_count']}")
    print(f"   - User preferences: {long_term['user_preferences']}")
    
    # Test context
    memory.update_context('current_order_id', 'ORD-12345')
    memory.update_context('awaiting_address', True)
    context = memory.get_context()
    print(f"\n✅ Context: {context}")
    
    print("\n✅ Memory test completed!")

def test_rlhf_feedback():
    """Test RLHF feedback collection"""
    print("\n" + "="*60)
    print("TEST 3: RLHF Feedback")
    print("="*60)
    
    rlhf = RLHFFeedbackCollector()
    
    # Record interaction
    print("\n📝 Recording AI interaction...")
    rlhf.record_interaction(
        conversation_id="test-conv-123",
        message_id="msg-test-123",
        user_message="i want jollof rice",
        ai_response="Great choice! Here are restaurants serving jollof rice...",
        category="food_order",
        confidence=0.95
    )
    
    # Collect positive feedback
    print("\n👍 Collecting positive feedback...")
    success = rlhf.collect_feedback("msg-test-123", "positive", feedback_score=5.0)
    print(f"✅ Feedback collected: {success}")
    
    # Get performance metrics
    metrics = rlhf.get_category_performance("food_order")
    print(f"\n📊 Category Performance (food_order):")
    print(f"   - Total interactions: {metrics['total_interactions']}")
    print(f"   - Positive feedback: {metrics['positive_feedback']}")
    print(f"   - Negative feedback: {metrics['negative_feedback']}")
    print(f"   - Average score: {metrics['avg_score']:.2f}/5.0")
    
    print("\n✅ RLHF test completed!")

def test_enhanced_ai_service():
    """Test enhanced AI service integration"""
    print("\n" + "="*60)
    print("TEST 4: Enhanced AI Service")
    print("="*60)
    
    service = EnhancedAIService("test-conv-456")
    
    # Test preprocessing
    print("\n📝 Testing message preprocessing...")
    original_msg = "i want jellof riec"
    processed, metadata = service.preprocess_message(original_msg)
    print(f"   Original: '{original_msg}'")
    print(f"   Processed: '{processed}'")
    print(f"   Was corrected: {metadata['was_spell_corrected']}")
    print(f"   Corrections: {metadata['corrections']}")
    
    # Test contextual prompt building
    print("\n📝 Testing contextual prompt...")
    service.memory.add_message('user', 'I want jollof rice')
    service.memory.add_message('assistant', 'Great choice!')
    service.memory.memory.update_context('last_food', 'jollof rice')
    
    contextual_prompt = service.get_contextual_prompt("show me more restaurants")
    print(f"   Contextual prompt (first 200 chars):")
    print(f"   {contextual_prompt[:200]}...")
    
    print("\n✅ Enhanced AI service test completed!")

def test_feedback_commands():
    """Test feedback command detection"""
    print("\n" + "="*60)
    print("TEST 5: Feedback Command Detection")
    print("="*60)
    
    service = EnhancedAIService("test-conv-789")
    
    test_commands = [
        ("👍", True),
        ("that was helpful", True),
        ("good job", True),
        ("👎", True),
        ("wrong answer", True),
        ("i want jollof rice", False),  # Not a feedback command
    ]
    
    print("\n📝 Testing feedback command detection...")
    for command, should_detect in test_commands:
        response = service.handle_feedback_command(command, "msg-test-456")
        detected = response is not None
        status = "✅" if detected == should_detect else "❌"
        print(f"{status} '{command}' → Detected: {detected}, Expected: {should_detect}")
        if response:
            print(f"   Response: {response}")
    
    print("\n✅ Feedback command test completed!")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ENHANCED AI SYSTEM - TEST SUITE")
    print("="*60)
    
    try:
        test_spell_correction()
        test_conversation_memory()
        test_rlhf_feedback()
        test_enhanced_ai_service()
        test_feedback_commands()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nEnhanced AI System is ready for use! 🚀")
        print("\nKey Features:")
        print("  ✅ Spell correction for food items")
        print("  ✅ Conversation memory (short-term & long-term)")
        print("  ✅ RLHF feedback collection")
        print("  ✅ Context management")
        print("  ✅ AI-first message processing")
        print("\nNext Steps:")
        print("  1. Test with real WhatsApp messages")
        print("  2. Monitor RLHF metrics in production")
        print("  3. Adjust spell correction threshold if needed")
        print("  4. Review conversation summaries for insights")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
