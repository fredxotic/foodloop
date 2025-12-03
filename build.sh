#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

echo "=== Starting database migrations ==="

# Apply Django's built-in apps first
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate authtoken --noinput

# ✅ NUCLEAR OPTION: Drop and recreate core tables
echo "Dropping old core tables..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodloop.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('DROP TABLE IF EXISTS user_profiles CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS donations CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS ratings CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS notifications CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS email_verifications CASCADE;')
    print('✅ Dropped all core tables')
"

echo "Creating tables with fresh schema..."
python manage.py migrate core --noinput

echo "Applying remaining migrations..."
python manage.py migrate --noinput

echo "=== Migrations completed ==="