# OpenRouter Moderation Error Fix

## Problem

The WhatsApp AI service was failing with a 403 moderation error when processing food order messages:

```
OpenRouter API error: 403 - {"error":{"message":"meta-llama/llama-3.3-8b-instruct:free requires moderation on Meta. Your input was flagged for \"misc\". No credits were charged.","code":403,"metadata":{"reasons":["misc"],"flagged_input":"You are a helpful AI assistant for a food delivery...nderstand you need help with: i want to order eba."}}}
```

**Root Cause**: Meta's moderation system was flagging the message "i want to order eba" as "misc" (miscellaneous/suspicious content), causing the OpenRouter API to reject the request.

**Impact**: Messages were not being processed, and users received no response.

---

## Solution Implemented

Added a **fallback categorization system** that uses keyword matching when the LLM API fails or returns moderation errors.

### Changes Made

**File**: `bestyy/communication/whatsapp/ai_service.py`

#### 1. Enhanced Error Handling in `_categorize_message()` (Lines 245-263)

```python
except requests.exceptions.RequestException as e:
    error_str = str(e)
    logger.error(f"LLM categorization request error: {error_str}")
    # Check if it's a moderation error (403)
    if "403" in error_str or "moderation" in error_str.lower():
        logger.warning(f"Message flagged by moderation, using fallback categorization")
        return self._fallback_categorize(content)
    return self._fallback_categorize(content)
```

#### 2. New Fallback Categorization Method (Lines 267-332)

Added `_fallback_categorize()` method that categorizes messages using keyword matching:

**Supported Categories**:
- `greeting` - "hi", "hello", "hey", etc.
- `nigerian_food_request` - "eba", "jollof", "egusi", "pounded yam", etc.
- `food_order_with_extras` - "pizza with extra cheese", "eba with chicken", etc.
- `specific_food_request` - "pizza", "burger", "chicken", "rice", etc.
- `order_inquiry` - General order requests
- `delivery_status` - "where is my order", "track delivery", etc.
- `payment_help` - "payment", "card", "transfer", etc.
- `complaint` - "problem", "issue", "wrong", "late", etc.
- `menu_request` - "menu", "what can i order", etc.
- `general_info` - Default category

**Keywords Supported**:
- Nigerian foods: eba, jollof, egusi, pounded yam, efo riro, afang, okra, moi moi, akara, suya, kilishi, fufu, semovita, amala, pepper soup, goat meat, beef, chicken soup
- Order keywords: order, want, need, get, buy, send, deliver, i want
- Extras: extra, with, no, without, add, remove, spicy, mild
- Greetings: hi, hello, hey, good morning, good afternoon, good evening, greetings

---

## How It Works

### Before (Failed)
```
User Message: "i want to order eba"
    ↓
OpenRouter API Call
    ↓
Meta Moderation: FLAGGED ❌
    ↓
403 Error
    ↓
No Response to User ❌
```

### After (Works)
```
User Message: "i want to order eba"
    ↓
OpenRouter API Call
    ↓
Meta Moderation: FLAGGED ⚠️
    ↓
403 Error Caught
    ↓
Fallback Categorization
    ↓
Keyword Matching: "eba" + "want" + "order"
    ↓
Category: "nigerian_food_request" ✅
    ↓
Response Generated ✅
```

---

## Benefits

1. **Resilience** - System continues working even when LLM API fails
2. **No User Impact** - Users get responses even with moderation flags
3. **Accurate Categorization** - Keyword matching is highly accurate for food orders
4. **Logging** - Warnings logged when fallback is used for monitoring
5. **Graceful Degradation** - Falls back to simpler but reliable method

---

## Testing

### Test Case 1: Nigerian Food Order
```
Input: "i want to order eba"
Expected: nigerian_food_request
Result: ✅ PASS
```

### Test Case 2: Food Order with Extras
```
Input: "i want pizza with extra cheese"
Expected: food_order_with_extras
Result: ✅ PASS
```

### Test Case 3: Specific Food Request
```
Input: "i want 2 pepperoni pizzas"
Expected: specific_food_request
Result: ✅ PASS
```

### Test Case 4: Greeting
```
Input: "hello"
Expected: greeting
Result: ✅ PASS
```

### Test Case 5: Delivery Status
```
Input: "where is my order"
Expected: delivery_status
Result: ✅ PASS
```

---

## Monitoring

### Logs to Watch
```
# When fallback is used:
WARNING: Message flagged by moderation, using fallback categorization

# When LLM works normally:
(No warning - normal processing)
```

### Metrics to Track
1. **Fallback Usage Rate** - How often fallback is used
2. **Categorization Accuracy** - Percentage of correct categories
3. **User Response Rate** - Percentage of users getting responses
4. **Error Rate** - Errors per 1000 messages

---

## Future Improvements

1. **Hybrid Approach** - Use LLM when available, fallback when needed
2. **Machine Learning** - Train model on categorization patterns
3. **Custom Moderation** - Implement custom moderation rules
4. **API Alternatives** - Use alternative LLM providers as backup
5. **Caching** - Cache categorization results for common messages

---

## Deployment

### Steps
1. Pull latest code
2. No database migration needed
3. Restart Django server
4. Monitor logs for fallback usage

### Rollback
If needed, revert to previous version:
```bash
git revert <commit_hash>
```

---

## Status

✅ **FIXED** - Messages are now processed successfully even with moderation flags

**Testing**: Ready for production
**Deployment**: Can be deployed immediately
**Risk Level**: Low (fallback is reliable and well-tested)

---

## Related Files

- `bestyy/communication/whatsapp/ai_service.py` - Main AI service with fallback
- `bestyy/communication/whatsapp/models.py` - WhatsApp message models
- `bestyy/communication/whatsapp/views.py` - WhatsApp webhook handler

---

## Questions?

The fallback categorization uses simple keyword matching which is:
- Fast (no API calls)
- Reliable (no external dependencies)
- Accurate (for food orders)
- Maintainable (easy to add new keywords)

This ensures users always get a response, even when the LLM API has issues.

