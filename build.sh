#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

echo "=== Starting database setup ==="

# First, apply all Django built-in migrations
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate authtoken --noinput

# Now handle core app migrations
echo "Applying core app migrations..."

# Check if there are any migration files
if python manage.py showmigrations core | grep -q "\[ \]"; then
    echo "Core has unapplied migrations, running them..."
    python manage.py migrate core --noinput
else
    echo "No unapplied migrations for core, running makemigrations..."
    python manage.py makemigrations core --noinput
    python manage.py migrate core --noinput
fi

# Apply any remaining migrations
python manage.py migrate --noinput

echo "=== Database setup completed ==="