#!/bin/bash
# Local / container quick-start. On the Azure VM Gunicorn is managed by
# systemd instead (deploy/systemd/gunicorn.service).
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Starting Gunicorn on ${BIND:-127.0.0.1:8000}..."
exec gunicorn epiconnect.wsgi:application \
    --bind "${BIND:-127.0.0.1:8000}" \
    --workers "${WORKERS:-3}" \
    --timeout 120 \
    --access-logfile '-' \
    --error-logfile '-'
