"""Optional canonical-host redirect, env-gated per deployment.

Set CANONICAL_HOST_REDIRECT=https://nahalabs-growth.onrender.com on a legacy
deployment and every request 301s to the canonical host (path and query
preserved). Unset = no-op, so the canonical service itself runs unchanged.
"""

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin


class CanonicalHostRedirectMiddleware(MiddlewareMixin):
    def process_request(self, request):
        target = getattr(settings, "CANONICAL_HOST_REDIRECT", "")
        if not target:
            return None
        host = request.get_host().split(":")[0]
        target_host = target.split("://", 1)[-1].split("/")[0].split(":")[0]
        if host == target_host:
            return None
        return HttpResponsePermanentRedirect(target.rstrip("/") + request.get_full_path())
