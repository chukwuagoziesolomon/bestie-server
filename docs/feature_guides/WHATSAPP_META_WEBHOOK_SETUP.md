# WhatsApp Meta Webhook Setup Guide

This guide walks you through setting up WhatsApp Business API webhooks using Meta's official API for both local development (with ngrok) and production deployment on Render.

## Prerequisites

- Meta Developer Account
- WhatsApp Business App created in Meta Developer Console
- Django project with WhatsApp AI integration

## Step 1: Get Meta WhatsApp Credentials

### 1.1 Access Token
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Select your WhatsApp Business App
3. Go to **WhatsApp > API Setup**
4. Copy the **Temporary Access Token** (for testing)
5. For production, you'll need to generate a **System User Access Token**

### 1.2 Phone Number ID
1. In the same **API Setup** page
2. Find the **Phone number ID** field
3. Copy this ID (it's a long numeric string)

### 1.3 App Secret
1. Go to **App Settings > Basic**
2. Copy the **App Secret** (click "Show" to reveal it)

### 1.4 Generate Verify Token
Create a secure random string for webhook verification:
```bash
# Generate a secure token (Linux/Mac)
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root with:

```bash
# WhatsApp Meta Business API
WHATSAPP_VERIFY_TOKEN=your_generated_verify_token_here
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
META_APP_SECRET=your_meta_app_secret

# OpenRouter AI (for WhatsApp responses)
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_APP_URL=https://your-app.com
OPENROUTER_APP_NAME=WhatsApp AI Bot
```

## Step 3: Local Development Setup with ngrok

### 3.1 Install ngrok
```bash
# Download from https://ngrok.com/download
# Or install via package manager
brew install ngrok  # macOS
choco install ngrok  # Windows
```

### 3.2 Start Django Server
```bash
cd bestyy_server
python manage.py runserver
```

### 3.3 Start ngrok Tunnel
```bash
# In a new terminal
ngrok http 8000
```

You'll see output like:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 3.4 Configure Meta Webhook
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Select your WhatsApp Business App
3. Go to **WhatsApp > Configuration**
4. In the **Webhook** section:
   - **Callback URL**: `https://abc123.ngrok.io/api/whatsapp/webhook/`
   - **Verify Token**: Your generated verify token from Step 1.4
5. Click **Verify and Save**

### 3.5 Test Webhook Verification
Meta will send a GET request to verify your webhook. Check your Django logs for:
```
WhatsApp webhook verified successfully
```

## Step 4: Test Message Processing

### 4.1 Send Test Message
1. Send a WhatsApp message to your business number
2. Check Django logs for incoming webhook processing
3. Verify the message appears in Django admin at `/django-admin/whatsapp_ai/whatsappmessage/`

### 4.2 Check AI Response
If OpenRouter is configured, the AI should automatically respond to text messages.

## Step 5: Production Deployment on Render

### 5.1 Update Environment Variables on Render
1. Go to your Render dashboard
2. Select your web service
3. Go to **Environment** tab
4. Add all the environment variables from your `.env` file

### 5.2 Update Webhook URL
1. In Meta Developer Console
2. Go to **WhatsApp > Configuration**
3. Update **Callback URL** to: `https://your-app-name.onrender.com/api/whatsapp/webhook/`
4. Click **Verify and Save**

### 5.3 Deploy
Push your changes to trigger a new deployment on Render.

## Step 6: Production Considerations

### 6.1 Generate Permanent Access Token
1. Create a **System User** in your Meta App
2. Generate a **System User Access Token** with WhatsApp permissions
3. Update `WHATSAPP_ACCESS_TOKEN` with the permanent token

### 6.2 Webhook Security
- The webhook endpoint validates Meta's signature using `META_APP_SECRET`
- In development, signature validation is skipped if `META_APP_SECRET` is not set
- Always set `META_APP_SECRET` in production

### 6.3 Rate Limits
- Meta has rate limits for WhatsApp API calls
- Monitor your usage in the Meta Developer Console
- Implement proper error handling for rate limit responses

## Troubleshooting

### Common Issues

#### 1. Webhook Verification Fails
- **Check verify token**: Ensure it matches exactly in both `.env` and Meta console
- **Check URL**: Ensure the webhook URL is accessible via HTTPS
- **Check Django logs**: Look for verification attempt logs

#### 2. Messages Not Received
- **Check webhook URL**: Ensure it's correctly configured in Meta console
- **Check Django logs**: Look for incoming webhook processing
- **Check signature validation**: Ensure `META_APP_SECRET` is set correctly

#### 3. AI Responses Not Sent
- **Check OpenRouter API key**: Ensure it's valid and has credits
- **Check Django logs**: Look for AI processing errors
- **Check Meta access token**: Ensure it has send message permissions

#### 4. ngrok Issues
- **Free tier limits**: Free ngrok has session limits
- **Tunnel stability**: Restart ngrok if tunnel becomes unstable
- **HTTPS required**: Meta requires HTTPS for webhooks

### Debug Commands

```bash
# Check if Django server is running
curl http://localhost:8000/api/whatsapp/webhook/

# Test webhook verification manually
curl "https://your-ngrok-url.ngrok.io/api/whatsapp/webhook/?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=your_token"

# Check Django logs
tail -f logs/django.log
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong verify tokens** (32+ characters, random)
3. **Always use HTTPS** for webhook URLs
4. **Validate webhook signatures** in production
5. **Rotate access tokens** regularly
6. **Monitor webhook logs** for suspicious activity

## API Endpoints

Your WhatsApp webhook is available at:
- **Development**: `https://<ngrok-subdomain>.ngrok.io/api/whatsapp/webhook/`
- **Production**: `https://<your-app>.onrender.com/api/whatsapp/webhook/`

### Webhook Methods
- **GET**: Webhook verification (returns challenge)
- **POST**: Receives incoming messages

### Admin Interface
Access WhatsApp data at: `/django-admin/whatsapp_ai/`

## Support

For issues:
1. Check Django logs for errors
2. Verify Meta webhook configuration
3. Test with Meta's webhook testing tools
4. Review Meta's WhatsApp Business API documentation

## Next Steps

After successful setup:
1. Customize AI response templates
2. Implement message categorization
3. Add user authentication flows
4. Set up analytics and monitoring
5. Configure message templates for business verification
