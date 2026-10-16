#!/bin/sh
# Free-tier single-container start: Render free plans have no separate worker
# service, so the studio worker runs as a background process next to gunicorn.
# WORKER_ENABLED=false (legacy redirect-only deployments) skips the worker so a
# retired service never double-processes background tasks.
set -e
if [ "$WORKER_ENABLED" != "false" ]; then
  python manage.py run_studio_worker --sleep 2 &
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4
