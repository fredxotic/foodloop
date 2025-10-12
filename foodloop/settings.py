"""
Django settings for FoodLoop project.
"""

import os
import sys
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

# Detect environment (development vs production)
DEBUG = config('DEBUG', default=True, cast=bool)
DEVELOPMENT = config('DEVELOPMENT', default=True, cast=bool)

# Get secret key from environment or use development default
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production-2024')

# =============================================================================
# SECURITY SETTINGS - DIFFERENT FOR DEVELOPMENT vs PRODUCTION
# =============================================================================

if DEBUG:
    # DEVELOPMENT SETTINGS (Less secure)
    print("🚀 DEVELOPMENT MODE ACTIVATED")
    ALLOWED_HOSTS = ['*']  # Allow all hosts for development
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
else:
    # PRODUCTION SETTINGS (Secure)
    print("🔒 PRODUCTION MODE ACTIVATED")
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

BASE_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    # 'compressor',  # Optional for production
]

PROJECT_APPS = [
    'core',
]

INSTALLED_APPS = BASE_APPS + THIRD_PARTY_APPS + PROJECT_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_profile',
            ],
        },
    },
]

# =============================================================================
# DATABASE - DIFFERENT FOR DEVELOPMENT vs PRODUCTION
# =============================================================================

if DEBUG:
    # SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # MySQL/PostgreSQL for production (PythonAnywhere uses MySQL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='foodloop_db'),
            'USER': config('DB_USER', default='foodloop_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }

# =============================================================================
# EMAIL CONFIGURATION - DIFFERENT FOR DEVELOPMENT vs PRODUCTION
# =============================================================================

if DEBUG:
    # Development: Print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_VERIFICATION_URL = 'http://127.0.0.1:8000'
    print("📧 Emails will be printed to console")
else:
    # Production: Real email sending
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='FoodLoop <noreply@foodloop.com>')
    EMAIL_VERIFICATION_URL = config('SITE_URL', default='https://yourusername.pythonanywhere.com')
    print("📧 Real email sending enabled")

# =============================================================================
# STATIC AND MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise for static files (works in both environments)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

if not DEBUG:
    # PythonAnywhere specific static files setup
    STATIC_ROOT = '/home/fredxotic/FoodLoop/staticfiles'
    MEDIA_ROOT = '/home/fredxotic/FoodLoop/media'

# =============================================================================
# OTHER SETTINGS (Common to both environments)
# =============================================================================

ROOT_URLCONF = 'foodloop.urls'
WSGI_APPLICATION = 'foodloop.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'max_similarity': 0.7},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://yourusername.pythonanywhere.com',  # Add your PythonAnywhere domain
]

# =============================================================================
# FOODLOOP SPECIFIC SETTINGS
# =============================================================================

FOODLOOP_SETTINGS = {
    'MAX_DONATION_QUANTITY': 1000,
    'DONATION_EXPIRY_DAYS': 7,
    'MAX_IMAGE_SIZE': 5 * 1024 * 1024,
    'ALLOWED_IMAGE_TYPES': ['image/jpeg', 'image/png', 'image/gif'],
    'SITE_URL': EMAIL_VERIFICATION_URL,  # Use the email verification URL
    'NUTRITION_ESTIMATES': True,
    'DIETARY_MATCHING': True,
    'AI_RECOMMENDATIONS': True,
    'MAX_ALLERGIES_LENGTH': 500,
}

# =============================================================================
# ENVIRONMENT-SPECIFIC MESSAGES
# =============================================================================

if DEBUG:
    print("✅ Debug: True")
    print("✅ Allowed Hosts: * (all hosts)")
    print("✅ Security: Relaxed for development")
    print("✅ Database: SQLite")
    print("✅ Static Files: Local serving")
    print("")
    print("⚠️  WARNING: This configuration is INSECURE for production!")
    print("⚠️  Change DEBUG to False and update security settings before deployment!")
    print("")
    print(f"🌐 Development server: http://127.0.0.1:8000")
    print("🐛 Debug information enabled")
else:
    print("✅ Debug: False")
    print("✅ Security: Production hardened")
    print("✅ Database: MySQL")
    print("✅ Static Files: WhiteNoise serving")
    print("✅ Email: Real SMTP server")
    print("")
    print(f"🌐 Production site: {EMAIL_VERIFICATION_URL}")

print("✅ Settings loaded successfully!")
print("🎯 FoodLoop ready!")