"""Recurring content-agent runner (django-background-tasks)."""

import logging

from background_task import background
from django.conf import settings

logger = logging.getLogger(__name__)

CONTENT_AGENT_INTERVAL_SECONDS = 6 * 60 * 60  # every 6 hours; per-workspace min_interval still applies


@background(schedule=0)
def run_content_agent_cycle():
    if not getattr(settings, "CONTENT_AGENT_ENABLED", False):
        return
    from .models import AgentConfig
    from .services import run_for_config

    for config in AgentConfig.objects.filter(enabled=True).select_related("workspace"):
        try:
            run_for_config(config)
        except Exception:
            logger.exception("content-agent run failed for workspace %s", config.workspace_id)
