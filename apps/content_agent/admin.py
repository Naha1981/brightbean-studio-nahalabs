from django.contrib import admin

from .models import AgentConfig, GenerationRun


@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ("workspace", "enabled", "niche", "posts_per_run", "min_interval_hours")
    list_filter = ("enabled",)


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = ("workspace", "status", "trend_source", "started_at", "finished_at")
    list_filter = ("status",)
    readonly_fields = ("workspace", "status", "topics_found", "post_ids", "error", "trend_source", "started_at", "finished_at")
