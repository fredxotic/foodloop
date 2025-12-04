#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "=== Build started at $(date) ==="

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input --clear

echo "=== Running database migrations ==="
# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
import sys
from django.db import connection
from django.core.management import execute_from_command_line

max_attempts = 30
for attempt in range(max_attempts):
    try:
        connection.ensure_connection()
        print(f'Database ready after {attempt + 1} attempts')
        break
    except Exception as e:
        if attempt == max_attempts - 1:
            print(f'Database not ready after {max_attempts} attempts: {e}')
            sys.exit(1)
        print(f'Attempt {attempt + 1}/{max_attempts}: Waiting for database...')
        time.sleep(2)
"

# Now run migrations
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "=== Build completed successfully at $(date) ==="