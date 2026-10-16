import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentConfig",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("enabled", models.BooleanField(default=False)),
                ("niche", models.CharField(blank=True, default="", max_length=255)),
                ("topics", models.JSONField(blank=True, default=list)),
                ("posts_per_run", models.PositiveSmallIntegerField(default=3)),
                ("min_interval_hours", models.PositiveSmallIntegerField(default=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_agent_config",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={"db_table": "content_agent_config"},
        ),
        migrations.CreateModel(
            name="GenerationRun",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("status", models.CharField(choices=[("success", "Success"), ("partial", "Partial"), ("failed", "Failed"), ("skipped", "Skipped")], db_index=True, max_length=16)),
                ("topics_found", models.JSONField(blank=True, default=list)),
                ("post_ids", models.JSONField(blank=True, default=list)),
                ("error", models.TextField(blank=True, default="")),
                ("trend_source", models.CharField(blank=True, default="", max_length=32)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_agent_runs",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={"db_table": "content_agent_generation_run", "ordering": ["-started_at"]},
        ),
    ]
