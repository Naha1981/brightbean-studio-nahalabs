"""Content-agent configuration and run log.

The agent drafts social posts for a workspace from live trend research
(SearXNG) plus an LLM (Gemini free tier) and drops them into the normal
composer review queue (PlatformPost status ``pending_review``). Nothing the
agent creates can publish without a human approval - it never writes
``approved``/``scheduled`` states.
"""

from __future__ import annotations

import uuid

from django.db import models


class AgentConfig(models.Model):
    """Per-workspace content-agent settings. Disabled by default."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="content_agent_config",
    )
    enabled = models.BooleanField(default=False)
    # What the business is about, in the owner's words. Drives both the
    # trend queries and the drafting prompt.
    niche = models.CharField(max_length=255, blank=True, default="")
    # Fallback/seed topics used when live research is unavailable.
    topics = models.JSONField(default=list, blank=True)
    posts_per_run = models.PositiveSmallIntegerField(default=3)
    min_interval_hours = models.PositiveSmallIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_agent_config"

    def __str__(self):
        return f"AgentConfig({self.workspace_id}, enabled={self.enabled})"


class GenerationRun(models.Model):
    """One agent run for one workspace - the evidence trail."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="content_agent_runs",
    )
    status = models.CharField(max_length=16, choices=Status.choices, db_index=True)
    topics_found = models.JSONField(default=list, blank=True)
    post_ids = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True, default="")
    trend_source = models.CharField(max_length=32, blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "content_agent_generation_run"
        ordering = ["-started_at"]

    def __str__(self):
        return f"GenerationRun({self.workspace_id}, {self.status})"
