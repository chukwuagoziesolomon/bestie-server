# Deployment Guide for Bestyy Backend

This guide will help you deploy the Bestyy backend to Render with Supabase as the database.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
3. **Cloudinary Account**: Sign up at [cloudinary.com](https://cloudinary.com) (for file storage)

## Step 1: Set up Supabase Database

1. Create a new project in Supabase
2. Go to Settings > Database
3. Copy the connection string (it will look like):
   ```
   postgresql://postgres:[password]@[host]:5432/postgres
   ```

## Step 2: Deploy to Render

### Option A: Using render.yaml (Recommended)

1. Push your code to GitHub
2. In Render dashboard, click "New +" > "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect the `render.yaml` file
5. Click "Apply" to deploy

### Option B: Manual Setup

1. In Render dashboard, click "New +" > "Web Service"
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `bestyy-backend`
   - **Environment**: `Python 3.11` (specify version to avoid Python 3.13 compatibility issues)
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `daphne -b 0.0.0.0 -p $PORT bestyy.asgi:application`
   - **Plan**: Free (or paid for production)

## Step 3: Environment Variables

Set these environment variables in Render:

### Required Variables
```
DJANGO_SETTINGS_MODULE=bestyy.settings.production
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-render-app.onrender.com
DATABASE_URL=postgresql://username:password@host:port/database_name
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### Optional Variables
```
WEBSOCKET_BASE_URL=wss://your-render-app.onrender.com
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
```

## Step 4: Database Setup

1. After deployment, run migrations:
   ```bash
   python manage.py migrate
   ```

2. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

## Step 5: Static Files

Static files are automatically collected during deployment. If you need to update them:

```bash
python manage.py collectstatic --noinput
```

## Step 6: WebSocket Configuration

**Important**: We're using **Daphne** as the ASGI server instead of Gunicorn because:
- Daphne supports WebSockets and Django Channels
- Gunicorn only supports WSGI (HTTP only)
- Your app uses real-time WebSocket connections for admin activities and notifications

For WebSocket support, you have two options:

### Option 1: Redis (Recommended for Production)
1. Add a Redis service in Render
2. Set the `REDIS_URL` environment variable
3. Update `CHANNEL_LAYERS` in production settings

### Option 2: In-Memory (Default)
- Works for development and small deployments
- Not suitable for multiple server instances

## Step 7: Frontend Configuration

Update your frontend environment variables:

```bash
# .env file for React frontend
REACT_APP_API_URL=https://your-render-app.onrender.com
REACT_APP_WS_URL=wss://your-render-app.onrender.com
REACT_APP_BASE_URL=https://your-render-app.onrender.com
```

## Step 8: Testing Deployment

1. Check if the API is accessible:
   ```bash
   curl https://your-render-app.onrender.com/api/admin/login/
   ```

2. Test WebSocket connection:
   ```javascript
   const ws = new WebSocket('wss://your-render-app.onrender.com/ws/admin/activity/?token=your-token');
   ```

## Troubleshooting

### Common Issues

1. **Build Error: "Getting requirements to build wheel did not run successfully"**
   - This is usually caused by Python 3.13 compatibility issues
   - **Solution**: Use Python 3.11 instead (specified in `runtime.txt` and `render.yaml`)
   - Make sure to set the Python version in Render dashboard to 3.11

2. **Database Connection Error**
   - Check if `DATABASE_URL` is correctly set
   - Verify Supabase database is accessible

3. **Static Files Not Loading**
   - Ensure `STATIC_ROOT` is set correctly
   - Check if `collectstatic` ran during build

4. **WebSocket Connection Failed**
   - Verify `WEBSOCKET_BASE_URL` is set correctly
   - Check if Redis is configured (if using Redis)

5. **CORS Errors**
   - Update `CORS_ALLOWED_ORIGINS` with your frontend domain
   - Ensure `CORS_ALLOW_CREDENTIALS` is set to `True`

### Logs

Check Render logs for debugging:
1. Go to your service in Render dashboard
2. Click on "Logs" tab
3. Look for error messages

## Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set up SSL/HTTPS
- [ ] Configure proper CORS origins
- [ ] Set up monitoring (Sentry)
- [ ] Configure email backend
- [ ] Set up Redis for WebSocket
- [ ] Configure proper logging
- [ ] Set up backup strategy

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to version control
2. **HTTPS**: Always use HTTPS in production
3. **CORS**: Restrict CORS origins to your actual domains
4. **Database**: Use strong passwords and restrict access
5. **Secrets**: Rotate secrets regularly

## Monitoring

Consider setting up:
- **Sentry**: For error tracking
- **Uptime monitoring**: To track service availability
- **Performance monitoring**: To track response times
- **Log aggregation**: For centralized logging

## Scaling

For high-traffic applications:
1. Upgrade to paid Render plan
2. Use Redis for WebSocket scaling
3. Set up load balancing
4. Use CDN for static files
5. Implement caching strategies
