# WhatsApp AI Integration Guide

This document provides a comprehensive guide for the WhatsApp AI integration using OpenRouter.

## Overview

The WhatsApp AI feature allows your Django application to:
- Receive WhatsApp messages via webhooks
- Process messages with AI using OpenRouter
- Generate intelligent responses
- Track conversations and AI performance
- Manage AI response templates

## Setup

### 1. Environment Variables

Add these environment variables to your `.env` file:

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_APP_URL=https://your-app.com
OPENROUTER_APP_NAME=WhatsApp AI Bot

# WhatsApp Configuration
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
```

### 2. Database Migration

Run the migration to create the WhatsApp AI tables:

```bash
python manage.py migrate whatsapp_ai
```

## API Endpoints

### Webhook Endpoint
- **URL**: `/api/whatsapp/webhook/`
- **Methods**: GET (verification), POST (receive messages)
- **Authentication**: None (WhatsApp webhook)

### Conversation Management
- **List Conversations**: `GET /api/whatsapp/conversations/`
- **Get Conversation**: `GET /api/whatsapp/conversations/{id}/`
- **Update Conversation**: `PUT /api/whatsapp/conversations/{id}/`

### Message Management
- **List Messages**: `GET /api/whatsapp/conversations/{id}/messages/`
- **Create Message**: `POST /api/whatsapp/conversations/{id}/messages/`

### AI Templates (Admin Only)
- **List Templates**: `GET /api/whatsapp/templates/`
- **Create Template**: `POST /api/whatsapp/templates/`
- **Update Template**: `PUT /api/whatsapp/templates/{id}/`
- **Delete Template**: `DELETE /api/whatsapp/templates/{id}/`

### AI Operations
- **Generate Response**: `POST /api/whatsapp/generate-response/`
- **Send Message**: `POST /api/whatsapp/send-message/`
- **Test AI**: `POST /api/whatsapp/test/`

### Analytics (Admin Only)
- **Conversation Stats**: `GET /api/whatsapp/stats/`
- **Available Models**: `GET /api/whatsapp/models/`
- **AI Logs**: `GET /api/whatsapp/logs/`

## Models

### WhatsAppConversation
Stores conversation metadata:
- `phone_number`: WhatsApp phone number
- `user`: Associated Django user (optional)
- `language`: Preferred language
- `timezone`: User timezone
- `is_active`: Conversation status

### WhatsAppMessage
Stores individual messages:
- `conversation`: Related conversation
- `message_id`: WhatsApp message ID
- `message_type`: Type (text, image, audio, etc.)
- `content`: Message content
- `direction`: inbound/outbound
- `is_ai_processed`: AI processing status
- `ai_response`: Generated AI response
- `ai_confidence`: AI confidence score

### AIResponseTemplate
Stores AI response templates:
- `category`: Template category (greeting, order_inquiry, etc.)
- `language`: Template language
- `template_text`: Template with placeholders
- `ai_model`: OpenRouter model to use
- `temperature`: AI temperature setting
- `max_tokens`: Maximum tokens for response

### AIProcessingLog
Tracks AI processing:
- `message`: Related message
- `template`: Template used
- `status`: Processing status
- `processing_time`: Time taken
- `tokens_used`: Tokens consumed
- `cost`: Processing cost

## OpenRouter Integration

### Supported Models

The system supports all OpenRouter models, with these recommended:

1. **Free Models**:
   - `meta-llama/llama-3.3-8b-instruct:free`

2. **Premium Models**:
   - `openai/gpt-3.5-turbo`
   - `openai/gpt-4`
   - `anthropic/claude-3-haiku`
   - `google/gemini-pro`

### API Usage

The system uses direct HTTP requests to OpenRouter:

```python
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_APP_URL,
        "X-Title": OPENROUTER_APP_NAME,
    },
    data=json.dumps({
        "model": "meta-llama/llama-3.3-8b-instruct:free",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant for a food delivery service."
            },
            {
                "role": "user",
                "content": "User message here"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 150
    })
)
```

## Message Categories

The AI automatically categorizes messages:

1. **greeting**: Hello, hi, good morning
2. **order_inquiry**: Order, buy, purchase, delivery
3. **menu_request**: Menu, food, dish, available
4. **delivery_status**: Delivery, status, where, track
5. **payment_help**: Payment, pay, money, cost
6. **complaint**: Problem, issue, wrong, bad
7. **general_info**: Default category

## Template Variables

Templates support these variables:
- `{user_message}`: The user's message
- `{phone_number}`: User's phone number
- `{language}`: Conversation language
- `{timestamp}`: Message timestamp

Example template:
```
User message: {user_message}

Please respond to this message in a helpful and friendly manner for our food delivery service.
```

## Testing

### Test AI Response

Use the test endpoint to verify OpenRouter integration:

```bash
curl -X POST http://localhost:8000/api/whatsapp/test/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, I want to order food",
    "model": "meta-llama/llama-3.3-8b-instruct:free"
  }'
```

### Get Available Models

```bash
curl -X GET http://localhost:8000/api/whatsapp/models/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Admin Interface

Access the Django admin to:
- View conversations and messages
- Manage AI response templates
- Monitor AI processing logs
- View webhook logs
- Track performance statistics

## Webhook Configuration

### WhatsApp Business API Setup

1. Create a WhatsApp Business account
2. Set up a Meta Developer account
3. Configure webhook URL: `https://your-domain.com/api/whatsapp/webhook/`
4. Set verify token to match `WHATSAPP_VERIFY_TOKEN`

### Webhook Verification

WhatsApp will send a GET request to verify your webhook:

```
GET /api/whatsapp/webhook/?hub.verify_token=YOUR_TOKEN&hub.challenge=CHALLENGE
```

### Message Processing

Incoming messages are automatically:
1. Logged in `WhatsAppWebhookLog`
2. Stored in `WhatsAppMessage`
3. Categorized by AI
4. Processed with appropriate template
5. Response sent back to user

## Error Handling

The system includes comprehensive error handling:
- API failures are logged
- Fallback responses for errors
- Retry mechanisms for failed requests
- Detailed error logging in `AIProcessingLog`

## Performance Monitoring

Track AI performance through:
- Processing time metrics
- Success/failure rates
- Token usage and costs
- Response quality scores

## Security

- Webhook verification with tokens
- User authentication for admin endpoints
- Rate limiting on AI requests
- Input validation and sanitization

## Deployment

For production deployment:
1. Set all environment variables
2. Run migrations
3. Configure WhatsApp webhook
4. Test with sample messages
5. Monitor logs and performance

## Troubleshooting

### Common Issues

1. **OpenRouter API Key Not Working**
   - Verify API key is correct
   - Check account balance
   - Ensure proper headers

2. **Webhook Not Receiving Messages**
   - Verify webhook URL is accessible
   - Check verify token matches
   - Ensure HTTPS is enabled

3. **AI Responses Not Generated**
   - Check template configuration
   - Verify model availability
   - Review error logs

### Debug Mode

Enable debug logging:

```python
LOGGING = {
    'loggers': {
        'whatsapp_ai': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## Support

For issues or questions:
1. Check the logs in Django admin
2. Review OpenRouter documentation
3. Test with the `/api/whatsapp/test/` endpoint
4. Verify environment variables
