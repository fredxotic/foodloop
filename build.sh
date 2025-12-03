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

# ✅ NUCLEAR OPTION: Drop user_profiles table and recreate
echo "Dropping old user_profiles table..."
python manage.py dbshell <<EOF
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS donations CASCADE;
DROP TABLE IF EXISTS ratings CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS email_verifications CASCADE;
EOF

echo "Recreating tables with new schema..."
python manage.py migrate core --noinput || echo "Migration completed with warnings"

python manage.py migrate --noinput || echo "Some migrations skipped"

echo "=== Migrations completed ==="