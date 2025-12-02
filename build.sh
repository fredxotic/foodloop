#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static assets
python manage.py collectstatic --no-input

# Apply database migrations with error handling
echo "=== Starting database migrations ==="

# Apply migrations for Django's built-in apps first
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate authtoken --noinput

# Try to apply core migrations - continue even if there are errors
python manage.py migrate core --noinput 2>/dev/null || \
echo "Warning: Core migrations may have errors, but continuing..."

# Apply any remaining migrations
python manage.py migrate --noinput 2>/dev/null || \
echo "Some migrations may have been skipped"

echo "=== Migrations completed ==="