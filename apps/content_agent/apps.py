from django.apps import AppConfig


class ContentAgentAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content_agent"
    verbose_name = "Content Agent"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._register_tasks, sender=self)

    @staticmethod
    def _register_tasks(sender, **kwargs):
        from apps.common.background import register_recurring_task
        from apps.content_agent.tasks import CONTENT_AGENT_INTERVAL_SECONDS, run_content_agent_cycle

        register_recurring_task(
            run_content_agent_cycle,
            repeat=CONTENT_AGENT_INTERVAL_SECONDS,
            verbose_name="run_content_agent_cycle",
        )
