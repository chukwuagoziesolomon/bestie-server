"""
Django settings for bestyy project.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config

# Load environment variables from .env file
from dotenv import load_dotenv
import os
# Load .env from project root (bestyy_server)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
print(f"Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path)
print(f"WHATSAPP_ACCESS_TOKEN loaded: {'YES' if os.getenv('WHATSAPP_ACCESS_TOKEN') else 'NO'}")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-th5kfgtyu#mxlxtezbd)v9asvrrcc2n791313@ox4$d09mrsfm')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG_STR = config('DEBUG', default='False').lower()
DEBUG = DEBUG_STR in ('true', '1', 'yes', 'on')

# Production mode will be enabled when DEBUG=False in environment
if DEBUG:
    print("=== DEVELOPMENT MODE ENABLED ===")
    print(f"DEBUG setting: {DEBUG}")
    print(f"========================")

# Allow ngrok domains
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app', 'f570d64ef94e.ngrok-free.app', 'bestyy-server.onrender.com', '.onrender.com', 'bestyy-web.vercel.app']
print(f"ALLOWED_HOSTS set to: {ALLOWED_HOSTS}")

# ===================================
# CORS CONFIGURATION (MUST BE EARLY)
# ===================================
# Django CORS headers - Configuration MUST come before middleware initialization

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-cart-token',  # Custom header for JWT-based cart authentication
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# Base URL for the application
BASE_URL = config('BASE_URL', default='https://127.0.0.1:8000')
# near the top of the file (import


SELF_BASE_URL = os.getenv('SELF_BASE_URL', 'http://127.0.0.1:8000')

# Google OAuth settings
GOOGLE_OAUTH_REDIRECT_URI = f"{BASE_URL}/auth/google/callback/"

# OpenRouteService API settings (free alternative to Google Maps)
OPENROUTESERVICE_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImUwNzc0NWU1YjIwMDQ3MDk4YTI0YjQ3OGYzNWQyYzNjIiwiaCI6Im11cm11cjY0In0'

# OpenRouter AI settings
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY', default='')
OPENROUTER_APP_URL = config('OPENROUTER_APP_URL', default='https://your-app.com')
OPENROUTER_APP_NAME = config('OPENROUTER_APP_NAME', default='WhatsApp AI Bot')

# Google Maps API settings
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# WhatsApp Business API settings (unified)
WHATSAPP_VERIFY_TOKEN = config('WHATSAPP_VERIFY_TOKEN', default='your_verify_token')
WHATSAPP_ACCESS_TOKEN = config('WHATSAPP_ACCESS_TOKEN', default='')
WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')
META_APP_SECRET = config('META_APP_SECRET', default='')

# Paystack settings
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='bestie-server.onrender.com,bestyy-web.vercel.app,bestie-admin.vercel.app,localhost,127.0.0.1,*.onrender.com,*.vercel.app').split(',')
# Ensure ngrok hosts are allowed during development
ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ['.ngrok-free.app', 'f570d64ef94e.ngrok-free.app']))
print(f"ALLOWED_HOSTS set to: {ALLOWED_HOSTS}")

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'cloudinary',
    'cloudinary_storage',
    'django_filters',
    'django.contrib.sites',
    'sslserver',  # For HTTPS support in development
    # Temporarily disabled allauth for deployment
    # 'allauth',
    # 'allauth.account',
    # 'allauth.socialaccount',
    # 'allauth.socialaccount.providers.google',
    # 'dj_rest_auth',
    # 'dj_rest_auth.registration',
]

LOCAL_APPS = [
    'bestyy.core_features.user',
    'bestyy.payment_analytics.analytics',
    'bestyy.payment_analytics.payment',
    'bestyy.restaurant_features.vendor',
    'bestyy.restaurant_features.product',
    'bestyy.restaurant_features.order',
    'bestyy.delivery_features.delivery',
    'bestyy.delivery_features.courier',
    'bestyy.communication.notification',
    'bestyy.communication.whatsapp',
    'utils',
    'bestyy.adminpanel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'allauth.account.middleware.AccountMiddleware',  # Temporarily disabled
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bestyy.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bestyy.config.wsgi.application'
ASGI_APPLICATION = 'bestyy.config.asgi.application'

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation - relaxed for user convenience
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files - Using Cloudinary for all file uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary Storage Configuration
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'

# Celery Beat Schedule for automated tasks
# Note: Import crontab in celery.py or use string format for schedule
CELERY_BEAT_SCHEDULE = {
    # Send menu update reminders daily at 9 AM
    'send-menu-update-reminders': {
        'task': 'bestyy.core_features.user.tasks.send_menu_update_reminders',
        'schedule': 60 * 60 * 24,  # Daily (24 hours in seconds)
    },
    
    # Update vendor popularity metrics every 6 hours
    'update-vendor-popularity-metrics': {
        'task': 'bestyy.core_features.user.tasks.update_vendor_popularity_metrics',
        'schedule': 60 * 60 * 6,  # Every 6 hours
    },
}

# Custom User Model
AUTH_USER_MODEL = 'user.User'

# Django Sites Framework (required for allauth)
SITE_ID = 1

# Django Allauth Configuration (temporarily disabled)
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_USERNAME_REQUIRED = False
# ACCOUNT_AUTHENTICATION_METHOD = 'email'
# ACCOUNT_EMAIL_VERIFICATION = 'none'  # Set to 'mandatory' for production
# ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False

# CORS allowed origins - Prioritize environment variable
env_cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
if env_cors_origins:
    # If environment variable is set, use it (comma-separated list)
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in env_cors_origins.split(',') if origin.strip()]
    print(f"Using CORS_ALLOWED_ORIGINS from environment: {CORS_ALLOWED_ORIGINS}")
else:
    # Fallback to default (for local development)
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',  # Admin frontend
        'http://127.0.0.1:3001',  # Admin frontend
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'https://bestie-admin.vercel.app',  # Production admin frontend
        'https://bestyy-web.vercel.app',  # Production customer frontend
    ]
    print(f"Using default CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")

# CORS expose headers (so frontend can read them from responses)
CORS_EXPOSE_HEADERS = [
    'x-cart-token',
]

# Note: CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS, and CORS_ALLOW_CREDENTIALS 
# are now configured at the TOP of settings.py (lines 42-64) to ensure
# django-cors-headers loads them before middleware initialization

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Cloudinary settings
CLOUDINARY = {
    'cloud_name': config('CLOUDINARY_CLOUD_NAME', default=''),
    'api_key': config('CLOUDINARY_API_KEY', default=''),
    'api_secret': config('CLOUDINARY_API_SECRET', default=''),
    'upload_preset': config('CLOUDINARY_UPLOAD_PRESET', default='bestie AI'),
}

# Channels/WebSocket settings
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# WebSocket base URL
WEBSOCKET_BASE_URL = config('WEBSOCKET_BASE_URL', default='ws://127.0.0.1:8000')

# Email settings for vendor notifications
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)  # Changed to 465 (SSL)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)  # Disabled TLS
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)  # Enabled SSL
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@bestyy.com')

# Debug email settings
print("=== EMAIL SETTINGS DEBUG ===")
print(f"EMAIL_BACKEND: {EMAIL_BACKEND}")
print(f"EMAIL_HOST: {EMAIL_HOST}")
print(f"EMAIL_PORT: {EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {DEFAULT_FROM_EMAIL}")
print("============================")

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Production settings (when DEBUG=False)
if not DEBUG:
    # Security settings for production
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Use database cache for production
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }
    
    print(f"=== PRODUCTION MODE ACTIVATED ===")
    print(f"=================================")
    
    # CORS origins are already set from environment variable at the top of settings.py
    # No need to override here
    print(f"Production CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")
    
    # Update WebSocket URL for production
    WEBSOCKET_BASE_URL = config('WEBSOCKET_BASE_URL', default='wss://bestie-server.onrender.com')
