"""Guarantee the recurring content-agent Task row exists.

post_migrate registration is belt; this migration is braces - it runs in the
deploy preDeploy step and inserts the background-task row idempotently.
"""

from django.db import migrations


def ensure_task(apps, schema_editor):
    Task = apps.get_model("background_task", "Task")
    if Task.objects.filter(task_name="apps.content_agent.tasks.run_content_agent_cycle").exists():
        return
    from django.utils import timezone
    import hashlib
    Task.objects.create(
        task_name="apps.content_agent.tasks.run_content_agent_cycle",
        task_params="[[], {}]",
        task_hash=hashlib.md5(b"apps.content_agent.tasks.run_content_agent_cycle[{}, []]").hexdigest(),
        verbose_name="run_content_agent_cycle",
        run_at=timezone.now(),
        repeat=6 * 60 * 60,
        queue="",
        priority=0,
    )


class Migration(migrations.Migration):
    dependencies = [("content_agent", "0001_initial")]
    operations = [migrations.RunPython(ensure_task, migrations.RunPython.noop)]
