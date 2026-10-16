#!/bin/sh
# Free-tier single-container start: Render free plans have no separate worker
# service, so the studio worker runs as a background process next to gunicorn.
# If the worker dies the web keeps serving; the worker restarts on next deploy.
set -e
python manage.py run_studio_worker --sleep 2 &
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4
