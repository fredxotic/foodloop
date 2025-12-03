#!/usr/bin/env bash
set -o errexit

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Starting database setup ==="

# Create migrations if needed
python manage.py makemigrations

# Run ALL migrations (Django built-ins + your apps)
python manage.py migrate

echo "=== Database setup completed ==="