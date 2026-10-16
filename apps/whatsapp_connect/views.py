"""Connect a workspace's WhatsApp number by pairing code."""

from __future__ import annotations

import logging
import secrets

import httpx
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.members.decorators import require_permission
from apps.workspaces.models import Workspace

from . import evolution
from .models import WhatsAppConnection

logger = logging.getLogger(__name__)

_STATE_TO_STATUS = {
    "open": WhatsAppConnection.Status.CONNECTED,
    "close": WhatsAppConnection.Status.DISCONNECTED,
    "connecting": WhatsAppConnection.Status.PENDING,
}


def _get_workspace(request, workspace_id):
    return get_object_or_404(Workspace, id=workspace_id, organization=request.org)


@login_required
@require_permission("manage_social_accounts")
def connect(request, workspace_id):
    """GET: show phone form + any existing connections. POST: start pairing."""
    workspace = _get_workspace(request, workspace_id)
    connections = workspace.whatsapp_connections.all()

    if request.method == "POST":
        raw_phone = request.POST.get("phone", "")
        try:
            phone = evolution.normalize_phone(raw_phone)
        except evolution.EvolutionError as exc:
            messages.error(request, str(exc))
            return redirect("whatsapp_connect:connect", workspace_id=workspace_id)

        instance_name = f"ws-{secrets.token_hex(8)}"
        connection = WhatsAppConnection.objects.create(
            workspace=workspace, instance_name=instance_name, phone_number=phone
        )
        try:
            with evolution.new_client() as client:
                evolution.create_instance(client, instance_name=instance_name, phone=phone)
                code = evolution.fetch_pairing_code(client, instance_name=instance_name, phone=phone)
            connection.pairing_code = code
            connection.pairing_code_fetched_at = timezone.now()
            connection.save(update_fields=["pairing_code", "pairing_code_fetched_at", "updated_at"])
        except (evolution.EvolutionError, httpx.HTTPError) as exc:
            connection.status = WhatsAppConnection.Status.FAILED
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            messages.error(request, f"Could not start pairing: {exc}")
            return redirect("whatsapp_connect:connect", workspace_id=workspace_id)
        return redirect("whatsapp_connect:pairing", workspace_id=workspace_id, pk=connection.pk)

    return render(
        request,
        "whatsapp_connect/connect.html",
        {"workspace_id": workspace_id, "connections": connections},
    )


@login_required
@require_permission("manage_social_accounts")
def pairing(request, workspace_id, pk):
    """Show the pairing code; the page polls status until connected."""
    workspace = _get_workspace(request, workspace_id)
    connection = get_object_or_404(
        WhatsAppConnection, pk=pk, workspace=workspace
    )
    return render(
        request,
        "whatsapp_connect/pairing.html",
        {"workspace_id": workspace_id, "connection": connection},
    )


@login_required
@require_permission("manage_social_accounts")
@require_GET
def status_json(request, workspace_id, pk):
    """Poll endpoint: refresh state from Evolution and report our status."""
    workspace = _get_workspace(request, workspace_id)
    connection = get_object_or_404(WhatsAppConnection, pk=pk, workspace=workspace)
    try:
        with evolution.new_client() as client:
            state = evolution.connection_state(client, instance_name=connection.instance_name)
        new_status = _STATE_TO_STATUS.get(state, connection.status)
        if new_status != connection.status:
            connection.status = new_status
            update = ["status", "updated_at"]
            if new_status == WhatsAppConnection.Status.CONNECTED and not connection.connected_at:
                connection.connected_at = timezone.now()
                update.append("connected_at")
            connection.save(update_fields=update)
    except (evolution.EvolutionError, httpx.HTTPError) as exc:
        logger.warning("whatsapp status refresh failed: %s", exc)
    return JsonResponse(
        {"status": connection.status, "phone": connection.phone_number}
    )


@login_required
@require_permission("manage_social_accounts")
@require_POST
def disconnect(request, workspace_id, pk):
    workspace = _get_workspace(request, workspace_id)
    connection = get_object_or_404(WhatsAppConnection, pk=pk, workspace=workspace)
    try:
        with evolution.new_client() as client:
            evolution.delete_instance(client, instance_name=connection.instance_name)
    except (evolution.EvolutionError, httpx.HTTPError) as exc:
        logger.warning("evolution delete failed (marking disconnected anyway): %s", exc)
    connection.status = WhatsAppConnection.Status.DISCONNECTED
    connection.save(update_fields=["status", "updated_at"])
    messages.success(request, f"WhatsApp number {connection.phone_number} disconnected.")
    return redirect("whatsapp_connect:connect", workspace_id=workspace_id)
