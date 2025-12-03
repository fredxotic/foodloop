#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static assets
python manage.py collectstatic --no-input

echo "=== Starting database migrations ==="

# Apply migrations for Django's built-in apps first
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate authtoken --noinput

# Fake problematic migrations that conflict with existing DB
echo "Faking migration 0002 (has duplicate index)..."
python manage.py migrate core 0002_remove_gps_fields --fake --noinput || echo "Migration 0002 fake failed, continuing..."

# Apply remaining migrations normally
echo "Applying remaining core migrations..."
python manage.py migrate core --noinput || echo "Warning: Some core migrations skipped"

# Apply any remaining migrations
python manage.py migrate --noinput || echo "Some migrations may have been skipped"

echo "=== Migrations completed ==="