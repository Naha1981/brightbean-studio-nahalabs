"""NahaLabs PRODUCTION deployment, 2026-10-16. Durable Postgres (DATABASE_URL), real client workspaces.
AGPL-3.0, source: https://github.com/Naha1981/brightbean-studio-nahalabs
The publishing worker runs in-process beside gunicorn (single Render web
service, no paid worker dyno). Data is durable Postgres. Outbound email stays off until Resend is wired (EMAIL_BACKEND_TYPE=dummy).
"""
import os
import subprocess
import sys
import threading
import time

subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], check=True)
# Idempotent across a restart that retains /tmp. No credential is logged.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.utils import timezone
from allauth.account.models import EmailAddress
User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL']
user, created = User.objects.get_or_create(email=email, defaults={'is_staff': True, 'is_superuser': True, 'tos_accepted_at':timezone.now()})
if created:
    user.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
    user.save()
EmailAddress.objects.update_or_create(user=user,email=email,defaults={'verified':True,'primary':True})


def _worker_loop():
    """Keep one studio worker alive for the life of the QA container.

    run_studio_worker recycles itself hourly (--duration 3600, same as the
    Procfile); the loop simply starts the next instance. A crash is retried
    after a short backoff instead of silently leaving QA with no publisher.
    The thread is a daemon and os.execvp replaces this process with
    gunicorn, so Render's container stop kills the worker with the web.
    """
    while True:
        try:
            subprocess.run(
                [sys.executable, 'manage.py', 'run_studio_worker', '--duration', '3600'],
                check=False,
            )
        except Exception:
            pass
        time.sleep(5)


threading.Thread(target=_worker_loop, daemon=True, name='studio-worker-supervisor').start()

os.execvp('gunicorn', ['gunicorn','config.wsgi:application','--bind','0.0.0.0:'+os.environ.get('PORT','8000'),'--workers','1','--threads','4'])
