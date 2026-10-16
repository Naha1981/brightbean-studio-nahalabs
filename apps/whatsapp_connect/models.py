"""WhatsApp Business pairing via the self-hosted Evolution API.

A restaurant pairs its own WhatsApp number with a pairing code - no QR scan,
no Meta App Review. The connection record tracks the Evolution instance
backing the number so the workspace's enquiry features can trust the source.
"""

from __future__ import annotations

import uuid

from django.db import models


class WhatsAppConnection(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending_pairing", "Pending pairing"
        CONNECTED = "connected", "Connected"
        DISCONNECTED = "disconnected", "Disconnected"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="whatsapp_connections",
    )
    instance_name = models.CharField(max_length=64, unique=True)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    pairing_code = models.CharField(max_length=32, blank=True, default="")
    pairing_code_fetched_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "whatsapp_connect_connection"
        ordering = ["-created_at"]

    def __str__(self):
        return f"WhatsAppConnection({self.phone_number}, {self.status})"
