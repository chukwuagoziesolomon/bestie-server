"""
Django settings for bestyy project.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-th5kfgtyu#mxlxtezbd)v9asvrrcc2n791313@ox4$d09mrsfm')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG_STR = config('DEBUG', default='True').lower()
DEBUG = DEBUG_STR in ('true', '1', 'yes', 'on')

# Force production mode if we're on Render
if 'RENDER' in os.environ or 'onrender.com' in config('BASE_URL', default=''):
    DEBUG = False
    print("=== FORCED PRODUCTION MODE (Render detected) ===")

# Temporary debugging for deployment
print(f"=== DEPLOYMENT DEBUG ===")
print(f"DEBUG setting: {DEBUG}")
print(f"DEBUG env var: {config('DEBUG', default='True')}")
print(f"DEBUG_STR: {DEBUG_STR}")
print(f"RENDER env: {'RENDER' in os.environ}")
print(f"========================")

# Base URL for the application
BASE_URL = config('BASE_URL', default='http://127.0.0.1:8000')

# Google OAuth settings
GOOGLE_OAUTH_REDIRECT_URI = f"{BASE_URL}/auth/google/callback/"

# OpenRouter AI settings
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY', default='')
OPENROUTER_APP_URL = config('OPENROUTER_APP_URL', default='https://your-app.com')
OPENROUTER_APP_NAME = config('OPENROUTER_APP_NAME', default='WhatsApp AI Bot')

# WhatsApp settings
WHATSAPP_VERIFY_TOKEN = config('WHATSAPP_VERIFY_TOKEN', default='your_verify_token')
WHATSAPP_ACCESS_TOKEN = config('WHATSAPP_ACCESS_TOKEN', default='')
WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='bestie-server.onrender.com,localhost,127.0.0.1,*.onrender.com').split(',')
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
    'django_filters',
    'django.contrib.sites',
    # Temporarily disabled allauth for deployment
    # 'allauth',
    # 'allauth.account',
    # 'allauth.socialaccount',
    # 'allauth.socialaccount.providers.google',
    # 'dj_rest_auth',
    # 'dj_rest_auth.registration',
]

LOCAL_APPS = [
    'user',
    'analytics',
    'order',
    'payment',
    'vendor',
    'product',
    'delivery',
    'courier',
    'notification',
    'utils',
    'whatsapp_ai',
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

ROOT_URLCONF = 'bestyy.urls'

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

WSGI_APPLICATION = 'bestyy.wsgi.application'
ASGI_APPLICATION = 'bestyy.asgi.application'

# Database
import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Temporary fallback to SQLite if PostgreSQL connection fails
if not DEBUG and 'postgresql' in config('DATABASE_URL', default=''):
    try:
        # Test the connection
        import psycopg2
        conn = psycopg2.connect(config('DATABASE_URL'))
        conn.close()
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        print("Falling back to SQLite for deployment")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
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

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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
CORS_ALLOW_CREDENTIALS = True

# Default CORS allowed origins (for development)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',  # Admin frontend
    'http://127.0.0.1:3001',  # Admin frontend
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

print(f"Default CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")

# CORS allowed headers
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
]

# CORS allowed methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
# Remove duplicate - CORS_ALLOWED_ORIGINS is already defined above

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

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
    
    # Update CORS origins for production
    CORS_ALLOWED_ORIGINS = [
        'https://bestyy-web.vercel.app',
        'https://bestie-admin.vercel.app',
        'https://bestie-server.onrender.com',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]
    
    # Also allow the environment variable if set
    env_cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
    if env_cors_origins:
        CORS_ALLOWED_ORIGINS.extend(env_cors_origins.split(','))
    
    print(f"CORS_ALLOWED_ORIGINS set to: {CORS_ALLOWED_ORIGINS}")
    
    # Update WebSocket URL for production
    WEBSOCKET_BASE_URL = config('WEBSOCKET_BASE_URL', default='wss://bestie-server.onrender.com')