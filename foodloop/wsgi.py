import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add project directory to the Python path
sys.path.append(str(BASE_DIR))

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodloop.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()