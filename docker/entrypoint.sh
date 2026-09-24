#!/bin/sh
# Container entrypoint. One image, several roles:
#   web      Gunicorn (default; what the ECS service runs)
#   migrate  apply migrations + create the rate-limit cache table
#            (run as a one-off ECS task by the pipeline BEFORE the new
#            version receives traffic, never by every web container)
#   *        any other argument is passed to manage.py, e.g. "seed_perks"
set -eu

case "${1:-web}" in
  web)
    exec gunicorn epiconnect.wsgi:application --config /app/docker/gunicorn.conf.py
    ;;
  migrate)
    python manage.py migrate --noinput
    python manage.py createcachetable
    ;;
  *)
    exec python manage.py "$@"
    ;;
esac
