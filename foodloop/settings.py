"""
Django settings for FoodLoop project.
Clean, production-ready configuration with proper environment separation.
"""

import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# ENVIRONMENT & SECURITY
# =============================================================================

DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='CHANGE-ME-IN-PRODUCTION')

# Hosts configuration
# 1. Get base hosts from env or default
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='localhost,127.0.0.1')

# 2. Automatically add Render.com hostname if present
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# 3. Development override
if DEBUG:
    ALLOWED_HOSTS = ['*']

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'channels',  # For real-time features
    'rest_framework',  # Django REST Framework
    'rest_framework.authtoken',  # Token authentication
    'corsheaders',  # CORS headers for mobile/web apps
    'django_filters',  # Advanced filtering
    'drf_spectacular',  # API 
    'cloudinary_storage',
    'cloudinary',
]

LOCAL_APPS = [
    'core',
    'api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS support
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'foodloop.urls'

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'  # Kenya timezone
USE_I18N = True
USE_TZ = True

# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/min',
        'donation_create': '10/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'FoodLoop API',
    'DESCRIPTION': 'RESTful API for the FoodLoop food sharing platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'FoodLoop Support',
        'email': 'support@foodloop.com',
    },
    'LICENSE': {
        'name': 'MIT',
    },
}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# CORS settings for mobile apps and frontend frameworks
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # React development
    'http://127.0.0.1:3000',
    'http://localhost:8080',  # Vue development
    'http://127.0.0.1:8080',
] + [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['*', 'localhost', '127.0.0.1']]

CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True  # Only in development

CORS_ALLOWED_HEADERS = [
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

# =============================================================================
# TEMPLATES
# =============================================================================

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
                'core.context_processors.user_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'foodloop.wsgi.application'
ASGI_APPLICATION = 'foodloop.asgi.application'

# =============================================================================
# DATABASE
# =============================================================================

if DEBUG:
    # SQLite for development (local)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # PostgreSQL for production (Render)
    DATABASES = {
        'default': dj_database_url.config(
            # This looks for the DATABASE_URL environment variable automatically
            default=config('DATABASE_URL', default=''),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# =============================================================================
# CACHING & REDIS (for real-time features)
# =============================================================================

if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    
    # Channel layers for WebSocket
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [config('REDIS_URL', default='redis://127.0.0.1:6379/1')],
            },
        },
    }

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='FoodLoop <noreply@foodloop.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Static files storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'  # Kenya timezone
USE_I18N = True
USE_TZ = True

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =============================================================================
# AUTHENTICATION
# =============================================================================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# =============================================================================
# CSRF PROTECTION
# =============================================================================

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
] + [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['*', 'localhost', '127.0.0.1']]

# =============================================================================
# FILE UPLOADS
# =============================================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# FOODLOOP SPECIFIC SETTINGS
# =============================================================================

FOODLOOP_CONFIG = {
    # Application settings
    'SITE_NAME': 'FoodLoop',
    'SITE_URL': config('SITE_URL', default='http://127.0.0.1:8000'),
    
    # File limits
    'MAX_IMAGE_SIZE': 5 * 1024 * 1024,  # 5MB
    'ALLOWED_IMAGE_FORMATS': ['JPEG', 'PNG', 'GIF'],
    
    # Donation settings
    'MAX_DONATIONS_PER_USER_PER_DAY': 10,
    'MAX_ACTIVE_CLAIMS_PER_USER': 5,
    'DONATION_EXPIRY_REMINDER_HOURS': [24, 6, 1],
    
    # AI & Recommendations
    'MAX_RECOMMENDATIONS': 12,
    'RECOMMENDATION_REFRESH_MINUTES': 30,
    'MIN_MATCH_SCORE_FOR_NOTIFICATION': 60,
    
    # Notifications
    'MAX_NOTIFICATIONS_PER_USER': 50,
    'NOTIFICATION_CLEANUP_DAYS': 30,
    
    # Analytics
    'ANALYTICS_RETENTION_DAYS': 365,
    'NUTRITION_SCORE_WEIGHTS': {
        'food_category': 0.4,
        'dietary_tags': 0.3,
        'calories': 0.2,
        'freshness': 0.1
    },
    
    # API Settings
    'API_VERSION': 'v1',
    'MAX_API_REQUESTS_PER_HOUR': 1000,
    'MOBILE_APP_VERSIONS': ['1.0.0', '1.1.0'],
}

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'foodloop.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if DEBUG else 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
(BASE_DIR / 'logs').mkdir(exist_ok=True)

# =============================================================================
# MEDIA CONFIGURATION (Cloudinary)
# =============================================================================

# Configuration for Cloudinary Storage
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# Tell Django to use Cloudinary for all media (uploaded) files
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# ENVIRONMENT FEEDBACK
# =============================================================================

if DEBUG:
    print("🔧 DEVELOPMENT MODE")
    print(f"   Database: SQLite")
    print(f"   Email: Console backend")
    print(f"   Static: Local serving")
    print(f"   Security: Relaxed")
    print(f"   API: Full access + documentation")
else:
    print("🚀 PRODUCTION MODE")
    print(f"   Database: {config('DB_ENGINE', 'Not configured')}")
    print(f"   Email: SMTP")
    print(f"   Static: WhiteNoise + CDN")
    print(f"   Security: Hardened")
    print(f"   API: Throttled + secure")

print(f"✅ FoodLoop settings loaded successfully!")