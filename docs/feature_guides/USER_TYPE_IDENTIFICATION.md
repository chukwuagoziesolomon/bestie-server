# 🔍 User Type Identification System

## 🚀 Overview

The User Type Identification System automatically identifies whether a user is a **customer**, **vendor**, or **courier** using multiple identification methods. This enables the AI to provide appropriate responses and context-aware interactions.

## 🎯 Key Features

### ✅ **Multiple Identification Methods**
- **User Object Check**: Direct database lookup
- **Phone Number Lookup**: Profile-based identification
- **Message Content Analysis**: Keyword-based identification
- **Session Context**: Memory-based identification
- **Memory Patterns**: Historical behavior analysis

### ✅ **Intelligent Fallback System**
- **Confidence Scoring**: Each method provides confidence scores
- **Method Prioritization**: Uses most reliable method first
- **Default Fallback**: Assumes customer if unknown
- **Error Handling**: Graceful degradation

### ✅ **Memory Integration**
- **Identification Storage**: Stores identification results
- **Pattern Learning**: Learns from identification patterns
- **Statistics Tracking**: Monitors identification accuracy
- **Continuous Improvement**: Improves over time

## 🔍 Identification Methods

### **1. User Object Check** 🎯
**Confidence**: 1.0 (Highest)
**Method**: Direct database lookup

```python
# Check if user has vendor profile
vendor_profile = VendorProfile.objects.get(user=user)
# Result: user_type = 'vendor', confidence = 1.0

# Check if user has courier profile  
courier_profile = CourierProfile.objects.get(user=user)
# Result: user_type = 'courier', confidence = 1.0

# If no profile found, assume customer
# Result: user_type = 'customer', confidence = 0.8
```

### **2. Phone Number Lookup** 📱
**Confidence**: 0.95 (Very High)
**Method**: Profile database lookup

```python
# Check vendor profiles
vendor_profile = VendorProfile.objects.get(phone_number=normalized_phone)
# Result: user_type = 'vendor', confidence = 0.95

# Check courier profiles
courier_profile = CourierProfile.objects.get(phone_number=normalized_phone)
# Result: user_type = 'courier', confidence = 0.95

# Check user records
user = User.objects.get(phone_number=normalized_phone)
# Result: user_type = 'customer', confidence = 0.7
```

### **3. Message Content Analysis** 💬
**Confidence**: 0.2-0.8 (Variable)
**Method**: Keyword matching

```python
# Vendor keywords
vendor_keywords = [
    'order ready', 'preparing', 'cooking', 'kitchen', 'restaurant',
    'business', 'menu', 'ingredient', 'equipment', 'staff',
    'vendor', 'restaurant owner', 'chef', 'cook'
]

# Courier keywords
courier_keywords = [
    'picked up', 'delivery', 'on the way', 'arrived', 'delivered',
    'courier', 'driver', 'bike', 'motorcycle', 'vehicle',
    'traffic', 'location', 'address', 'customer location'
]

# Customer keywords
customer_keywords = [
    'where is my order', 'delivery time', 'order status',
    'customer', 'hungry', 'food', 'meal', 'order',
    'delivery address', 'payment', 'refund', 'cancel'
]
```

### **4. Session Context** 🧠
**Confidence**: 0.6-0.7 (Medium)
**Method**: Memory-based analysis

```python
# Analyze recent memories for this session
recent_memories = memory_service.retrieve_episodic_memories(
    query=f"session {session_id}",
    limit=10
)

# Count memory types
memory_types = {
    'vendor_interaction': 3,
    'courier_interaction': 1,
    'support_interaction': 2
}

# Result: user_type = 'vendor' (highest count)
```

### **5. Memory Patterns** 🔄
**Confidence**: 0.2-0.8 (Variable)
**Method**: Historical behavior analysis

```python
# Search for patterns in memory
memories = memory_service.retrieve_episodic_memories(
    query=message,
    limit=5
)

# Analyze memory patterns
user_type_counts = {
    'vendor': 2,
    'courier': 1,
    'customer': 3
}

# Result: user_type = 'customer' (most common)
```

## 🔄 Identification Flow

### **Step-by-Step Process**
```
1. User Object Check
   ↓ (if user provided)
   User has profile? → Return profile type
   ↓ (if no profile)
   Assume customer

2. Phone Number Lookup
   ↓ (if phone provided)
   Check vendor profiles → Found? → Return vendor
   ↓ (if not found)
   Check courier profiles → Found? → Return courier
   ↓ (if not found)
   Check user records → Found? → Return customer

3. Message Content Analysis
   ↓ (if message provided)
   Count vendor keywords → High score? → Return vendor
   ↓ (if not high)
   Count courier keywords → High score? → Return courier
   ↓ (if not high)
   Count customer keywords → High score? → Return customer

4. Session Context
   ↓ (if session provided)
   Analyze recent memories → Pattern found? → Return type

5. Memory Patterns
   ↓ (if available)
   Search historical patterns → Pattern found? → Return type

6. Default Fallback
   ↓ (if all methods fail)
   Return customer (confidence: 0.3)
```

## 📱 Phone Number Normalization

### **Supported Formats**
```python
# Nigerian formats
"+2348123456789"  # International format
"08123456789"     # Local format with 0
"8123456789"      # Local format without 0
"2348123456789"   # International without +

# Normalization result
"+2348123456789"  # Standardized format
```

### **Normalization Process**
```python
def _normalize_phone_number(self, phone_number: str) -> str:
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different formats
    if digits_only.startswith('234'):
        return f"+{digits_only}"
    elif digits_only.startswith('081'):
        return f"+234{digits_only[1:]}"
    elif digits_only.startswith('812'):
        return f"+234{digits_only}"
    elif len(digits_only) == 10:
        return f"+234{digits_only}"
    else:
        return f"+{digits_only}"
```

## 🎯 Usage Examples

### **Basic Identification**
```python
# Initialize service
user_type_identifier = UserTypeIdentificationService()

# Identify user type
result = user_type_identifier.identify_user_type(
    user=customer_user,
    phone_number="+2348123456789",
    message="Where is my order?",
    session_id="session_123"
)

# Result:
# {
#     'user_type': 'customer',
#     'confidence': 0.8,
#     'identification_method': 'user_object',
#     'user_id': 123,
#     'profile_id': None,
#     'phone_number': '+2348123456789'
# }
```

### **Phone Number Only**
```python
result = user_type_identifier.identify_user_type(
    phone_number="+2348123456789"
)

# Result:
# {
#     'user_type': 'vendor',
#     'confidence': 0.95,
#     'identification_method': 'phone_lookup',
#     'user_id': 456,
#     'profile_id': 789,
#     'phone_number': '+2348123456789',
#     'business_name': 'Burger Palace'
# }
```

### **Message Content Only**
```python
result = user_type_identifier.identify_user_type(
    message="Order is ready for pickup"
)

# Result:
# {
#     'user_type': 'vendor',
#     'confidence': 0.6,
#     'identification_method': 'message_analysis',
#     'message_analysis': {
#         'vendor_score': 2,
#         'courier_score': 0,
#         'customer_score': 0
#     }
# }
```

## 🔗 Integration with Intent Analysis

### **Auto-Identification Intent Analysis**
```python
# Initialize intent analyzer
intent_analyzer = IntentAnalysisService()

# Analyze with auto-identification
result = intent_analyzer.analyze_intent_with_auto_identification(
    message="Where is my order?",
    user=customer_user,
    phone_number="+2348123456789",
    session_id="session_123",
    conversation_id="conv_456"
)

# Result includes:
# {
#     'intent_analysis': {
#         'primary_intent': 'order_status',
#         'confidence': 0.8,
#         'urgency_level': 'medium',
#         'relevant_memories': [...],
#         'conversation_history': [...]
#     },
#     'user_identification': {
#         'user_type': 'customer',
#         'confidence': 0.8,
#         'identification_method': 'user_object',
#         'user_id': 123
#     },
#     'analysis_timestamp': '2025-01-15T10:30:00Z'
# }
```

## 📊 Statistics and Analytics

### **Identification Statistics**
```python
# Get identification statistics
stats = user_type_identifier.get_user_type_statistics()

# Result:
# {
#     'total_identifications': 150,
#     'user_type_distribution': {
#         'customer': 120,
#         'vendor': 20,
#         'courier': 10
#     },
#     'method_distribution': {
#         'user_object': 80,
#         'phone_lookup': 45,
#         'message_analysis': 20,
#         'session_context': 5
#     },
#     'average_confidence': 0.85,
#     'high_confidence_rate': 0.92
# }
```

## 🔧 API Endpoints

### **Message Analysis Webhook**
```bash
# Analyze message with auto-identification
POST /api/user/webhook/
{
    "event_type": "message.analyze",
    "data": {
        "message": "Where is my order?",
        "user_id": 123,
        "phone_number": "+2348123456789",
        "session_id": "session_123",
        "conversation_id": "conv_456"
    }
}
```

### **Response Format**
```json
{
    "success": true,
    "message": "Message analyzed successfully",
    "result": {
        "intent_analysis": {
            "primary_intent": "order_status",
            "confidence": 0.8,
            "urgency_level": "medium",
            "relevant_memories": [...],
            "conversation_history": [...]
        },
        "user_identification": {
            "user_type": "customer",
            "confidence": 0.8,
            "identification_method": "user_object",
            "user_id": 123,
            "profile_id": null,
            "phone_number": "+2348123456789"
        },
        "analysis_timestamp": "2025-01-15T10:30:00Z"
    },
    "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🧪 Testing

### **Unit Tests**
```python
def test_user_object_identification():
    # Test vendor identification
    vendor_user = User.objects.get(id=vendor_id)
    result = user_type_identifier.identify_user_type(user=vendor_user)
    assert result['user_type'] == 'vendor'
    assert result['confidence'] == 1.0

def test_phone_number_identification():
    # Test phone number lookup
    result = user_type_identifier.identify_user_type(
        phone_number="+2348123456789"
    )
    assert result['user_type'] in ['customer', 'vendor', 'courier']
    assert result['confidence'] > 0.0

def test_message_content_identification():
    # Test message analysis
    result = user_type_identifier.identify_user_type(
        message="Order is ready for pickup"
    )
    assert result['user_type'] == 'vendor'
    assert result['confidence'] > 0.0
```

### **Integration Tests**
```python
def test_auto_identification_intent_analysis():
    # Test complete flow
    result = intent_analyzer.analyze_intent_with_auto_identification(
        message="Where is my order?",
        phone_number="+2348123456789"
    )
    
    assert 'intent_analysis' in result
    assert 'user_identification' in result
    assert result['user_identification']['user_type'] != 'unknown'
```

## 🚀 Key Benefits

### ✅ **For AI System**
- **Automatic User Type Detection**: No manual configuration needed
- **Context-Aware Responses**: Appropriate responses for each user type
- **Improved Accuracy**: Better intent understanding with user context
- **Seamless Integration**: Works with existing memory and intent systems

### ✅ **For Users**
- **Personalized Experience**: Responses tailored to user type
- **No Manual Setup**: Automatic identification without user input
- **Consistent Interactions**: Same experience across all touchpoints
- **Intelligent Responses**: AI understands user role and context

### ✅ **For Business**
- **Operational Efficiency**: Automated user type detection
- **Better Analytics**: Track user type distribution and behavior
- **Improved Support**: Appropriate responses for each user type
- **Scalable Solution**: Handles large volumes of interactions

## 🔄 Continuous Improvement

### **Learning and Adaptation**
- **Pattern Recognition**: Learns from identification patterns
- **Confidence Scoring**: Tracks and improves accuracy
- **Method Optimization**: Optimizes identification methods
- **Memory Integration**: Uses historical data for better identification

### **Performance Monitoring**
- **Success Rate Tracking**: Monitors identification accuracy
- **Method Performance**: Tracks which methods work best
- **Confidence Analysis**: Analyzes confidence score distribution
- **Error Rate Monitoring**: Tracks and reduces identification errors

The User Type Identification System provides intelligent, automatic user type detection that enables context-aware AI interactions! 🔍✨
