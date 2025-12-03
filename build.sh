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

# using --fake-initial to skip existing database objects
echo "Applying core migrations with --fake-initial..."
python manage.py migrate core --fake-initial --noinput || echo "Warning: Some core migrations skipped"

# Apply any remaining migrations
python manage.py migrate --noinput || echo "Some migrations may have been skipped"

echo "=== Migrations completed ==="