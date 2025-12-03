#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

echo "=== Starting database setup ==="

# Apply any pending migrations
python manage.py makemigrations core

# Run all migrations normally
python manage.py migrate core

echo "=== Database setup completed ==="