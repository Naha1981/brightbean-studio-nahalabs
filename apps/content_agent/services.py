"""Content-agent pipeline: trend research -> LLM draft -> review queue.

Every external dependency degrades to a safe fallback: no SearXNG -> use the
configured topics; no Gemini key -> no drafts (run recorded as failed, never
silently empty). The agent NEVER auto-approves or schedules: drafts land as
``pending_review`` and a human moves them forward.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_TIMEOUT = 20
DEFAULT_GEMINI_TIMEOUT = 60
MAX_TREND_TOPICS = 8
CAPTION_PROMPT_LIMIT = 2200  # chars, fits every supported platform

_DRAFT_RULES = (
    "Rules: write for a real local business. NEVER invent statistics, "
    "customer testimonials, review counts, awards, or claims the business "
    "could not verify. No fake urgency. No 'AI' buzzwords. Plain, warm, "
    "specific language. South African English. Keep the caption under "
    f"{CAPTION_PROMPT_LIMIT} characters including hashtags."
)


@dataclass
class Draft:
    topic: str
    caption: str
    first_comment: str = ""
    hashtags: list[str] = field(default_factory=list)


def research_trends(config, *, client=None) -> tuple[list[str], str]:
    """Return (topics, source). Live SearXNG results when reachable, else the
    configured seed topics. Never raises - an unreachable search backend is a
    fallback, not a failure."""

    seeds = [t for t in (config.topics or []) if isinstance(t, str) and t.strip()]
    base_url = getattr(settings, "CONTENT_AGENT_SEARXNG_URL", "") or ""
    if not base_url:
        return seeds[:MAX_TREND_TOPICS], "seeds"
    query = f"{config.niche} trends" if config.niche else " ".join(seeds[:3])
    if not query.strip():
        return [], "none"
    try:
        http = client or httpx.Client(timeout=DEFAULT_SEARXNG_TIMEOUT)
        resp = http.get(
            base_url.rstrip("/") + "/search",
            params={"q": query, "format": "json", "categories": "general"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network, non-JSON, 4xx/5xx - all the same fallback
        logger.warning("content-agent: SearXNG unavailable (%s); using seed topics", exc)
        return seeds[:MAX_TREND_TOPICS], "seeds"
    topics = []
    for result in data.get("results", []):
        title = (result.get("title") or "").strip()
        if title and title.lower() not in {t.lower() for t in topics}:
            topics.append(title)
        if len(topics) >= MAX_TREND_TOPICS:
            break
    if not topics:
        return seeds[:MAX_TREND_TOPICS], "seeds"
    return topics, "searxng"


def _extract_json_object(text: str) -> dict:
    """Pull the first JSON object out of an LLM reply, fence-tolerant."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object in model reply")
    return json.loads(match.group(0))


def draft_posts(config, topics: list[str], *, client=None) -> list[Draft]:
    """Draft one caption per topic via Gemini free tier. Topics that fail to
    draft are skipped (the run records them as partial), never guessed."""

    api_key = getattr(settings, "CONTENT_AGENT_GEMINI_API_KEY", "") or ""
    if not api_key:
        raise RuntimeError("CONTENT_AGENT_GEMINI_API_KEY is not set")
    model = getattr(settings, "CONTENT_AGENT_GEMINI_MODEL", "gemini-2.5-flash")
    niche = config.niche or "local restaurant"
    drafts: list[Draft] = []
    http = client or httpx.Client(timeout=DEFAULT_GEMINI_TIMEOUT)
    for topic in topics[: config.posts_per_run]:
        prompt = (
            f"Business: {niche}.\n"
            f"Write one social media post for this business about: {topic}.\n"
            f"{_DRAFT_RULES}\n"
            'Reply with JSON only: {"caption": "...", "hashtags": ["#tag", ...]}'
        )
        try:
            resp = http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            parsed = _extract_json_object(text)
            caption = (parsed.get("caption") or "").strip()
            if not caption:
                raise ValueError("empty caption")
            hashtags = [h for h in parsed.get("hashtags", []) if isinstance(h, str)][:10]
            drafts.append(Draft(topic=topic, caption=caption, hashtags=hashtags))
        except Exception as exc:
            logger.warning("content-agent: draft failed for topic %r: %s", topic, exc)
    return drafts


def queue_drafts_for_review(config, drafts: list[Draft], *, now=None) -> list[str]:
    """Create composer Posts with one pending_review PlatformPost per
    connected social account in the workspace. Returns created post ids."""

    from apps.composer.models import PlatformPost, Post
    from apps.social_accounts.models import SocialAccount

    now = now or timezone.now()
    accounts = list(
        SocialAccount.objects.filter(
            workspace=config.workspace,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
    )
    created: list[str] = []
    for draft in drafts:
        hashtags = " ".join(draft.hashtags)
        caption = f"{draft.caption}\n\n{hashtags}".strip() if hashtags else draft.caption
        post = Post.objects.create(
            workspace=config.workspace,
            caption=caption,
            tags=["content-agent"],
            internal_notes=(
                f"Drafted by content-agent from topic: {draft.topic}\n"
                "Verify facts before approving - agent drafts are unverified."
            ),
        )
        if accounts:
            for account in accounts:
                PlatformPost.objects.create(
                    post=post,
                    social_account=account,
                    status=PlatformPost.Status.PENDING_REVIEW,
                )
        created.append(str(post.id))
    return created


def run_for_config(config, *, client=None) -> "object":
    """Run the pipeline for one workspace config and record the outcome."""

    from .models import GenerationRun

    if not config.enabled:
        return None
    last_ok = (
        config.workspace.content_agent_runs.filter(
            status__in=[GenerationRun.Status.SUCCESS, GenerationRun.Status.PARTIAL]
        )
        .order_by("-started_at")
        .first()
    )
    if last_ok and (timezone.now() - last_ok.started_at).total_seconds() < config.min_interval_hours * 3600:
        return GenerationRun.objects.create(
            workspace=config.workspace,
            status=GenerationRun.Status.SKIPPED,
            error=f"ran less than {config.min_interval_hours}h ago",
            finished_at=timezone.now(),
        )
    topics, source = research_trends(config, client=client)
    try:
        drafts = draft_posts(config, topics, client=client)
    except Exception as exc:
        return GenerationRun.objects.create(
            workspace=config.workspace,
            status=GenerationRun.Status.FAILED,
            topics_found=topics,
            trend_source=source,
            error=str(exc),
            finished_at=timezone.now(),
        )
    post_ids = queue_drafts_for_review(config, drafts)
    status = GenerationRun.Status.SUCCESS
    if len(drafts) < min(len(topics), config.posts_per_run):
        status = GenerationRun.Status.PARTIAL
    if not drafts:
        status = GenerationRun.Status.FAILED
    return GenerationRun.objects.create(
        workspace=config.workspace,
        status=status,
        topics_found=topics,
        trend_source=source,
        post_ids=post_ids,
        error="" if drafts else "no drafts produced",
        finished_at=timezone.now(),
    )
