# 🚀 Bestyy Backend Deployment to Render

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to GitHub
3. **Environment Variables**: Set up all required API keys and secrets

## 🏗️ Project Structure for Deployment

```
bestyy_server/
├── bestyy/                    # Django project
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── core_features/
│   ├── restaurant_features/
│   ├── payment_analytics/
│   ├── delivery_features/
│   └── manage.py
├── requirements.txt           # Dependencies
├── runtime.txt               # Python version
├── render.yaml               # Render deployment config
├── Procfile                  # Process definitions
├── .env.example              # Environment variables template
└── README.md
```

## ⚙️ Environment Variables Setup

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Required Environment Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-secret-key-here` |
| `DATABASE_URL` | PostgreSQL connection string | Auto-set by Render |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `your-secret` |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Business API token | `your-token` |
| `PAYSTACK_SECRET_KEY` | Paystack secret key | `sk_test_...` |

## 🚀 Deployment Steps

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Create Render Service

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

#### Service Settings:
- **Name**: `bestyy-backend`
- **Environment**: `Python`
- **Runtime**: `Python 3.11.9`
- **Build Command**:
  ```bash
  ./bestyy/build.sh
  ```
- **Start Command**:
  ```bash
  daphne -b 0.0.0.0 -p $PORT bestyy.config.asgi:application
  ```

**Note**: The `manage.py` file is in the root directory and points to `bestyy.config.settings`, so no directory changes are needed in the commands.

### 3. Environment Variables

Set these in Render dashboard:

```
SECRET_KEY=your-secret-key-here
DEBUG=False
DJANGO_SETTINGS_MODULE=bestyy.settings
ALLOWED_HOSTS=your-app.onrender.com
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
PAYSTACK_SECRET_KEY=your-paystack-key
GOOGLE_MAPS_API_KEY=your-google-maps-key
```

### 4. Database Setup

Render automatically creates a PostgreSQL database. The `DATABASE_URL` is set automatically.

### 5. Deploy

Click "Create Web Service" and wait for deployment to complete.

## 🔧 Build & Start Commands

### Build Command (in render.yaml):
```bash
./bestyy/build.sh
```

### Start Command (in render.yaml):
```bash
daphne -b 0.0.0.0 -p $PORT bestyy.config.asgi:application
```

## 🐛 Troubleshooting

### Common Issues:

1. **Migration Errors**:
   ```bash
   cd bestyy
   python manage.py showmigrations
   python manage.py migrate --verbosity=2
   ```

2. **Static Files Issues**:
   ```bash
   cd bestyy
   python manage.py collectstatic --noinput --clear
   ```

3. **Port Issues**:
   - Render automatically sets `$PORT`
   - Daphne binds to `0.0.0.0:$PORT`

4. **Database Connection**:
   - Check `DATABASE_URL` is set correctly
   - Ensure PostgreSQL database is created

## 📊 Monitoring

- **Logs**: View in Render dashboard under "Logs" tab
- **Metrics**: Monitor CPU, memory, and response times
- **Health Checks**: Set up `/api/health/` endpoint if needed

## 🔄 Updates

To deploy updates:
```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render will automatically redeploy.

## 🌐 Production URLs

After deployment, your API will be available at:
- **API Base**: `https://your-app.onrender.com/api/`
- **Admin**: `https://your-app.onrender.com/admin/`
- **WebSocket**: `wss://your-app.onrender.com/ws/`

## 📞 Support

If you encounter issues:
1. Check Render logs
2. Verify environment variables
3. Test locally with production settings
4. Check database connectivity

---

**🎉 Happy Deploying! Your Bestyy backend is now live on Render!**