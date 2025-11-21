# Enhanced AI System with Memory, Context, and RLHF

## Overview

The enhanced AI system provides intelligent message processing with:

1. **Conversation Memory** - Short-term and long-term memory storage
2. **Context Management** - Maintains conversation state and user preferences
3. **RLHF (Reinforcement Learning from Human Feedback)** - Continuous improvement through user feedback
4. **Spell Correction** - Handles typos and misspellings gracefully
5. **AI-First Processing** - Routes all messages through AI before rule-based handlers

## Architecture

### Components

#### 1. ConversationMemory (`enhanced_ai_service.py`)
- **Short-term memory**: Stores last 10 messages in Redis cache
- **Long-term memory**: Tracks user preferences, order history, common requests
- **Context storage**: Maintains current conversation state (2-hour TTL)

**Usage:**
```python
memory = ConversationMemory(conversation_id)
memory.add_message('user', 'I want jollof rice', metadata={'category': 'food_order'})
short_term = memory.get_short_term()  # Last 10 messages
long_term = memory.get_long_term()    # User preferences, history
```

#### 2. SpellCorrector (`enhanced_ai_service.py`)
- Fuzzy matching for food items (75% similarity threshold)
- Nigerian dishes database integration
- Common misspelling corrections

**Example corrections:**
- "jellof rice" → "jollof rice"
- "egushi soup" → "egusi soup"
- "suuya" → "suya"

#### 3. RLHFFeedbackCollector (`enhanced_ai_service.py`)
- Records AI interactions for feedback
- Collects user feedback (positive/negative/corrections)
- Tracks category performance metrics
- Stores feedback in Redis (7-day retention)

**Feedback triggers:**
- User types: "👍", "good", "helpful" → Positive feedback
- User types: "👎", "wrong", "not helpful" → Negative feedback

#### 4. EnhancedAIService (`enhanced_ai_service.py`)
- Combines memory, spell correction, and RLHF
- Preprocesses messages before AI processing
- Builds contextual prompts with conversation history

#### 5. AIFirstMessageProcessor (`ai_first_processor.py`)
- Routes all messages through AI first
- Bypasses AI only for direct commands (PAID, ACCEPT, REJECT, etc.)
- Integrates seamlessly with existing flow

## Integration

### Message Flow

```
User Message
    ↓
[1] AI-First Processor
    ↓
[2] Spell Correction (if needed)
    ↓
[3] Check for Feedback Commands (👍/👎)
    ↓
[4] Build Contextual Prompt (with memory)
    ↓
[5] Process with Base AI Service
    ↓
[6] Add to Conversation Memory
    ↓
[7] Record for RLHF
    ↓
[8] Send Response (with correction note if applicable)
```

### Bypass Conditions

AI-first processing is **bypassed** for:
- Direct commands: `PAID`, `ACCEPT`, `REJECT`, `READY`, `STATUS`, `CANCEL`, `HELP`, `MENU`
- Numeric selections: `1`, `2`, `3` (restaurant/menu selection)

All other messages go through AI first, including:
- Addresses (AI validates if it looks like an address)
- Food orders with typos
- General conversation
- Ambiguous inputs

## Features

### 1. Conversation Memory

**Short-term (Last 10 messages):**
```json
{
  "role": "user",
  "content": "I want jollof rice",
  "timestamp": "2025-11-20T10:30:00",
  "metadata": {"category": "food_order"}
}
```

**Long-term Summary:**
```json
{
  "user_preferences": {
    "jollof rice": 5,
    "egusi soup": 3,
    "suya": 2
  },
  "order_history": [
    {"timestamp": "...", "order_id": "ORD-123"}
  ],
  "interaction_count": 25
}
```

### 2. Spell Correction

**Before:**
```
User: "i want jellof riec"
```

**After AI Processing:**
```
AI: "i want jollof rice"
Response: "Great choice! Here are restaurants serving jollof rice..."
Note: 📝 I understood you meant 'jollof rice'
```

### 3. RLHF (Continuous Improvement)

**Feedback Collection:**
```python
# User provides feedback
User: "👍"  # or "that was helpful"
System: "Thank you for the positive feedback! 😊"

# Metrics updated in Redis
{
  "category": "food_order",
  "total_interactions": 100,
  "positive_feedback": 85,
  "negative_feedback": 5,
  "avg_score": 4.5
}
```

**Performance Tracking:**
- Track success rate per category
- Identify categories needing improvement
- Adjust AI prompts based on feedback

### 4. Context Management

**Example Context Flow:**
```python
# Order flow with context
Context: {
  "last_food_type": "jollof rice",
  "vendor_offset": 0,
  "current_order_id": "ORD-123",
  "awaiting_address": True
}

# Context persists across messages
User: "Show more restaurants"
→ AI knows: last_food_type = "jollof rice", offset = 3
```

## Configuration

### Redis Requirements
- Cache backend required for memory storage
- Default TTL: 24 hours (short-term), 30 days (long-term)

### Settings (Django)
```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# OpenRouter API (already configured)
OPENROUTER_API_KEY = 'your-key'
```

## Testing

### Test Spell Correction
```python
from bestyy.communication.whatsapp.enhanced_ai_service import SpellCorrector

corrector = SpellCorrector()
corrected, changed = corrector.correct_message("i want jellof riec")
# Result: "i want jollof rice", True
```

### Test Memory
```python
from bestyy.communication.whatsapp.enhanced_ai_service import ConversationMemory

memory = ConversationMemory("test-conversation-id")
memory.add_message('user', 'I want jollof rice')
memory.add_message('assistant', 'Great choice!')

history = memory.get_short_term()
# Returns: [{'role': 'user', 'content': '...'}, ...]
```

### Test RLHF
```python
from bestyy.communication.whatsapp.enhanced_ai_service import RLHFFeedbackCollector

rlhf = RLHFFeedbackCollector()
rlhf.record_interaction(
    conversation_id="test",
    message_id="msg-123",
    user_message="i want jollof rice",
    ai_response="Great choice! Here are restaurants...",
    category="food_order",
    confidence=0.95
)

# Collect feedback
rlhf.collect_feedback("msg-123", "positive", feedback_score=5.0)

# Get performance
metrics = rlhf.get_category_performance("food_order")
```

## API Usage

### Process Message with AI-First
```python
from bestyy.communication.whatsapp.ai_first_processor import AIFirstMessageProcessor

processor = AIFirstMessageProcessor(conversation_id)
result = processor.process_with_ai_first(
    content="i want jellof riec",
    whatsapp_message=message,
    context={'user_exists': True}
)

# Result:
{
    'response': 'Great choice! Here are restaurants...',
    'handled_by': 'ai',
    'confidence': 0.95,
    'metadata': {
        'was_spell_corrected': True,
        'corrections': [{'from': 'jellof', 'to': 'jollof'}],
        'category': 'food_order'
    }
}
```

### Get Conversation Summary
```python
processor = AIFirstMessageProcessor(conversation_id)
summary = processor.get_conversation_summary()

# Result:
{
    'conversation_id': 'conv-123',
    'message_count': 8,
    'total_interactions': 25,
    'user_preferences': {'jollof rice': 5, 'egusi soup': 3},
    'order_history_count': 3,
    'recent_messages': [...]
}
```

## Monitoring

### Check RLHF Metrics
```python
from django.core.cache import cache

# Get metrics for a category
metrics = cache.get('rlhf_metrics_food_order')
print(f"Success rate: {metrics['positive_feedback'] / metrics['total_interactions'] * 100}%")
print(f"Average score: {metrics['avg_score']}/5.0")
```

### Check Memory Usage
```python
memory = ConversationMemory(conversation_id)
short_term = memory.get_short_term()
long_term = memory.get_long_term()

print(f"Recent messages: {len(short_term)}")
print(f"Total interactions: {long_term['interaction_count']}")
print(f"Favorite foods: {long_term['user_preferences']}")
```

## Benefits

1. **Better User Experience**
   - Handles typos gracefully
   - Remembers conversation context
   - Learns from feedback

2. **Improved Accuracy**
   - Spell correction reduces errors
   - Context prevents repeated questions
   - Memory improves personalization

3. **Continuous Improvement**
   - RLHF tracks performance
   - Identifies problem areas
   - Enables data-driven optimization

4. **Robust Error Handling**
   - Fuzzy matching for food names
   - Graceful degradation
   - Comprehensive logging

## Next Steps

1. **Add Analytics Dashboard**
   - View RLHF metrics
   - Track conversation quality
   - Monitor spell correction rates

2. **Expand Spell Dictionary**
   - Add more food items
   - Include regional variations
   - Support multiple languages

3. **Advanced Context**
   - Track dietary preferences
   - Remember delivery addresses
   - Suggest based on time of day

4. **RLHF Integration**
   - Train custom models
   - Fine-tune on successful interactions
   - A/B test different prompts

## Troubleshooting

### Issue: Spell correction too aggressive
**Solution:** Adjust threshold in SpellCorrector (default: 0.75)
```python
corrector = SpellCorrector()
# Lower threshold = less aggressive (0.6 - 0.8 recommended)
```

### Issue: Memory not persisting
**Solution:** Check Redis connection
```python
from django.core.cache import cache
cache.set('test_key', 'test_value', 60)
print(cache.get('test_key'))  # Should print 'test_value'
```

### Issue: RLHF feedback not recording
**Solution:** Check cache TTL and message_id
```python
# Verify interaction was recorded
cache_key = f"rlhf_feedback_{message_id}"
data = cache.get(cache_key)
print(data)  # Should show interaction data
```

## Files Modified

1. `bestyy/communication/whatsapp/enhanced_ai_service.py` - New enhanced AI components
2. `bestyy/communication/whatsapp/ai_first_processor.py` - AI-first message processor
3. `bestyy/communication/whatsapp/views.py` - Integration into message flow
4. `bestyy/communication/whatsapp/ai_service.py` - Existing base AI service (unchanged)

## Deployment Notes

- ✅ No database migrations required (uses Redis cache)
- ✅ Backward compatible with existing flow
- ✅ Can be disabled by removing AI-first call in views.py
- ✅ Redis required for memory and RLHF features
