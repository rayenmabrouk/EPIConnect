#!/bin/bash
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Starting Gunicorn..."
gunicorn epiconnect.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile '-' \
    --error-logfile '-'
