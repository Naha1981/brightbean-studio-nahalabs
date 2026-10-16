from django.conf import settings
from django.core.management.base import BaseCommand

from apps.content_agent.models import AgentConfig
from apps.content_agent.services import run_for_config


class Command(BaseCommand):
    help = (
        "Run the content agent for every workspace with an enabled AgentConfig. "
        "Drafts land in the review queue; nothing is approved or scheduled. "
        "No-ops unless settings.CONTENT_AGENT_ENABLED is true."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", help="Limit to one workspace UUID.")

    def handle(self, *args, **options):
        if not getattr(settings, "CONTENT_AGENT_ENABLED", False):
            self.stdout.write("content-agent disabled (CONTENT_AGENT_ENABLED=false); nothing to do")
            return
        configs = AgentConfig.objects.filter(enabled=True).select_related("workspace")
        if options.get("workspace"):
            configs = configs.filter(workspace_id=options["workspace"])
        ran = 0
        for config in configs:
            run = run_for_config(config)
            if run is not None:
                ran += 1
                self.stdout.write(f"{config.workspace.name}: {run.status} ({len(run.post_ids)} posts)")
        self.stdout.write(f"content-agent: {ran} run(s)")
