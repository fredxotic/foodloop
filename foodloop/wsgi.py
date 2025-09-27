import os
import sys
from dotenv import load_dotenv

# Add your project directory to the Python path
path = '/home/fredxotic/foodloop'
if path not in sys.path:
    sys.path.append(path)

# Load environment variables
load_dotenv(os.path.join(path, '.env'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodloop.settings')

# Import and run Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()