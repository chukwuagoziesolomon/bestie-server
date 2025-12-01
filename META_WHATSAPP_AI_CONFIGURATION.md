# Meta Dashboard & WhatsApp AI Configuration Guide

## 📱 Overview

Your Bestyy platform integrates with **Meta's WhatsApp Business API** and **OpenRouter AI** to enable intelligent WhatsApp messaging for customer order placement and support.

---

## 🎯 What Needs to Be Configured

### 1. **Meta Developer Dashboard Setup**

#### Step 1: Create Meta Developer Account
1. Go to [developers.meta.com](https://developers.meta.com)
2. Sign up and create a new App

#### Step 2: Create WhatsApp Business App
1. In Meta Dashboard → Click "My Apps"
2. Create a new app:
   - **App Name**: `Bestyy WhatsApp`
   - **App Type**: `Business`
3. Add **WhatsApp** product to your app
4. Click "WhatsApp" → "Getting Started"

#### Step 3: Get Your Credentials
You need to collect:
- **Phone Number ID** (for your business number)
- **Access Token** (API token for sending messages)
- **Meta App Secret** (for webhook verification)

**Location to find these:**
- Go to: Meta Dashboard → WhatsApp → API Setup
- **Phone Number ID**: Under "Phone Numbers"
- **Access Token**: Click "Generate Token" (valid for 24 hours, get a permanent one)
- **Verify Token**: Create a random secure token (32+ characters)

---

### 2. **Production Webhook Configuration (Critical for Paystack)**

You mentioned **Paystack callback URL** - this is similar but different:

#### Paystack Webhook URL
```
https://bestie-server.onrender.com/api/order/payment/verify/
```

#### WhatsApp Webhook URL (in Meta Dashboard)
```
https://bestie-server.onrender.com/api/whatsapp/webhook/
```

**Where to Configure:**
1. Meta Dashboard → WhatsApp → Configuration
2. Click "Edit" → Callback URL section
3. Paste: `https://bestie-server.onrender.com/api/whatsapp/webhook/`
4. Verify Token: Use the value you set in environment variables

---

## 🔐 Environment Variables (Render Dashboard)

Set these in your Render.com dashboard under **Environment Variables**:

```
WHATSAPP_ACCESS_TOKEN=EAA...your_meta_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id_here
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token_here

OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_APP_URL=https://bestie-server.onrender.com
OPENROUTER_APP_NAME=Bestyy WhatsApp AI
```

---

## ✅ Step-by-Step Setup Checklist

### Phase 1: Meta Developer Setup (One-time)
- [ ] Create Meta Developer Account at [developers.meta.com](https://developers.meta.com)
- [ ] Create WhatsApp Business App
- [ ] Generate **Phone Number ID**
- [ ] Generate **Access Token** (make it permanent)
- [ ] Create **Verify Token** (32+ random characters)
- [ ] Get **Meta App Secret**

### Phase 2: Environment Variables (Render)
- [ ] Go to Render Dashboard: [dashboard.render.com](https://dashboard.render.com)
- [ ] Click your `bestyy-backend` service
- [ ] Go to "Environment" tab
- [ ] Add the following variables:
  - `WHATSAPP_ACCESS_TOKEN` = Your Meta token
  - `WHATSAPP_PHONE_NUMBER_ID` = Your phone number ID
  - `WHATSAPP_VERIFY_TOKEN` = Your custom verify token
  - `OPENROUTER_API_KEY` = Your OpenRouter key

### Phase 3: Meta Webhook Configuration (Meta Dashboard)
- [ ] Go to Meta Dashboard → WhatsApp
- [ ] Find "Configuration" or "Webhook Settings"
- [ ] Set Callback URL: `https://bestie-server.onrender.com/api/whatsapp/webhook/`
- [ ] Set Verify Token: Same as `WHATSAPP_VERIFY_TOKEN` above
- [ ] Subscribe to events:
  - `messages` (incoming messages)
  - `message_status` (delivery status)

### Phase 4: Test WhatsApp Integration
- [ ] Send a WhatsApp message to your Bestyy business number
- [ ] Check Render logs to verify message received
- [ ] Verify AI response is sent back

---

## 📊 System Architecture

```
User sends WhatsApp message
        ↓
Meta WhatsApp Server
        ↓
Render Webhook (POST /api/whatsapp/webhook/)
        ↓
Django WhatsApp Views (views.py → _process_meta_message)
        ↓
AI Processing (OpenRouter)
        ↓
Response sent back via Meta WhatsApp API
```

---

## 🤖 WhatsApp AI Capabilities

Your WhatsApp bot currently handles:

### 1. **User Registration/Verification**
- Users send 6-digit verification codes
- System links WhatsApp number to user account
- Stores conversation history

### 2. **Food Ordering**
- Users describe what they want to eat
- AI understands intentions (e.g., "cheap pizza under 3000")
- Bot recommends restaurants and dishes
- Creates order in system

### 3. **Budget-Based Recommendations**
- Users can mention budget
- AI filters restaurants matching price range
- Example: "Show me restaurants under ₦5000"

### 4. **General Queries**
- Non-food queries handled by OpenRouter AI
- Smart fallbacks for unclear messages

---

## 📡 API Endpoints (Reference)

### Public Endpoints (No Auth)
```
GET  /api/whatsapp/webhook/ → Webhook verification
POST /api/whatsapp/webhook/ → Receive messages from Meta
GET  /api/user/banners/     → Get banners (for frontend)
```

### Admin Endpoints (Requires JWT Token)
```
GET    /api/whatsapp/conversations/       → View all conversations
GET    /api/whatsapp/conversations/<id>/ → View single conversation
GET    /api/whatsapp/templates/           → View AI response templates
POST   /api/whatsapp/templates/           → Create template
PUT    /api/whatsapp/templates/<id>/      → Update template
GET    /api/whatsapp/stats/               → Analytics
```

---

## 🔧 Troubleshooting

### "Webhook verification failed"
- Check `WHATSAPP_VERIFY_TOKEN` matches in Meta Dashboard and Render
- Verify webhook URL is correct: `https://bestie-server.onrender.com/api/whatsapp/webhook/`

### "Messages not received"
- Check Meta Dashboard has your webhook URL subscribed
- Verify `WHATSAPP_ACCESS_TOKEN` is set and valid
- Check Render logs: `tail -f render-logs`

### "AI responses not working"
- Verify `OPENROUTER_API_KEY` is set
- Check OpenRouter account has credits
- View logs for AI errors

### "Meta App Secret error"
- Go to Meta Dashboard → App Settings → Basic
- Copy the App Secret
- Add to Render as `META_APP_SECRET`

---

## 📝 Django Admin Access

Monitor WhatsApp activity in Django Admin:

```
https://bestie-server.onrender.com/admin/whatsapp_ai/
```

Available sections:
- **Conversations**: View all WhatsApp conversations with users
- **Messages**: View individual messages (incoming/outgoing)
- **AI Templates**: Configure response templates
- **AI Logs**: Monitor AI processing performance
- **Webhook Logs**: Debug webhook issues

---

## 🚀 Current Production Status

✅ **Deployed**: `https://bestie-server.onrender.com`

### What's Already Integrated:
- ✅ Meta WhatsApp webhook receiver (`/api/whatsapp/webhook/`)
- ✅ AI-first message processing with OpenRouter
- ✅ User verification flow (6-digit codes)
- ✅ Food ordering from WhatsApp
- ✅ Conversation history tracking
- ✅ Smart intent detection
- ✅ Budget-based recommendations

### What Needs Configuration:
- ⚠️ Meta app credentials in Render environment variables
- ⚠️ Meta webhook URL verification
- ⚠️ OpenRouter API key (if using premium models)

---

## 📋 Paystack vs WhatsApp Configuration

| Aspect | Paystack | WhatsApp |
|--------|----------|----------|
| **Purpose** | Payment verification | Customer messaging |
| **Webhook URL** | `/api/order/payment/verify/` | `/api/whatsapp/webhook/` |
| **Production URL** | `https://bestie-server.onrender.com/api/order/payment/verify/` | `https://bestie-server.onrender.com/api/whatsapp/webhook/` |
| **Dashboard** | Paystack.com | Meta.developers.com |
| **Configured In** | Paystack Dashboard Settings | Meta WhatsApp Configuration |
| **Trigger** | Payment status changes | Incoming WhatsApp messages |

---

## 📞 Support Resources

- **Meta WhatsApp Docs**: https://developers.facebook.com/docs/whatsapp
- **OpenRouter Docs**: https://openrouter.ai/docs
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Render.com Docs**: https://render.com/docs

---

## 🎯 Next Actions

1. **Get Meta Credentials** (5 mins)
   - Create Meta Developer App
   - Get Phone Number ID, Access Token, Verify Token

2. **Set Environment Variables** (2 mins)
   - Go to Render Dashboard
   - Paste credentials in Environment section

3. **Configure Webhook** (2 mins)
   - Go to Meta Dashboard
   - Set webhook URL: `https://bestie-server.onrender.com/api/whatsapp/webhook/`
   - Set Verify Token (same as Render)

4. **Test Integration** (5 mins)
   - Send WhatsApp message to Bestyy number
   - Verify response received
   - Check Render logs for confirmation

**Total Time**: ~15 minutes

---

**Status**: Ready for configuration 🚀
