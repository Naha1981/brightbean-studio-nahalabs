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
            name="WhatsAppConnection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("instance_name", models.CharField(max_length=64, unique=True)),
                ("phone_number", models.CharField(max_length=20)),
                ("status", models.CharField(choices=[("pending_pairing", "Pending pairing"), ("connected", "Connected"), ("disconnected", "Disconnected"), ("failed", "Failed")], db_index=True, default="pending_pairing", max_length=20)),
                ("pairing_code", models.CharField(blank=True, default="", max_length=32)),
                ("pairing_code_fetched_at", models.DateTimeField(blank=True, null=True)),
                ("connected_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="whatsapp_connections",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={"db_table": "whatsapp_connect_connection", "ordering": ["-created_at"]},
        ),
    ]
