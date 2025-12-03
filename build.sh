#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

echo "=== Starting database setup ==="

# Run all migrations normally
python manage.py migrate --noinput

echo "=== Database setup completed ==="