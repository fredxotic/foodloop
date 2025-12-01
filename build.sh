#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static assets
python manage.py collectstatic --no-input

# Create database migrations
python manage.py makemigrations

# Apply database migrations
python manage.py migrate