"""
ASGI config for FoodLoop project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Add project directory to Python path
sys.path.append(str(BASE_DIR))

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodloop.settings')

# Import Django ASGI application
from django.core.asgi import get_asgi_application

# Create ASGI application
application = get_asgi_application()