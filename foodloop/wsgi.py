# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.
#
# The below has been auto-generated for your Django project

import os
import sys

# Add your project directory to the Python path
path = '/home/fredxotic/foodloop'  # UPDATE WITH YOUR USERNAME AND PATH
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'foodloop.settings'

# Import and run Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()