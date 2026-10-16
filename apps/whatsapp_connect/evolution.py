"""Thin Evolution API v2 client. Every call raises EvolutionError on failure;
views decide what the user sees. The apikey never reaches templates or logs.
"""

from __future__ import annotations

import re

import httpx
from django.conf import settings

DEFAULT_TIMEOUT = 30


class EvolutionError(RuntimeError):
    pass


def _config():
    base = getattr(settings, "EVOLUTION_API_URL", "") or ""
    key = getattr(settings, "EVOLUTION_API_KEY", "") or ""
    if not base or not key:
        raise EvolutionError("Evolution API is not configured on this server")
    return base.rstrip("/"), {"apikey": key}


def normalize_phone(raw: str) -> str:
    """Digits only, leading zeros stripped into international form when the
    number clearly carries a country code already. Raises on junk."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) < 10 or len(digits) > 15:
        raise EvolutionError("Enter the full number with country code, e.g. 27...")
    return digits


def create_instance(client: httpx.Client, *, instance_name: str, phone: str) -> dict:
    base, headers = _config()
    resp = client.post(
        f"{base}/instance/create",
        headers=headers,
        json={
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": False,
            "number": phone,
        },
    )
    if resp.status_code >= 400:
        raise EvolutionError(f"could not create WhatsApp instance (HTTP {resp.status_code})")
    return resp.json()


def fetch_pairing_code(client: httpx.Client, *, instance_name: str, phone: str) -> str:
    """Ask Evolution to generate a pairing code for the number."""
    base, headers = _config()
    resp = client.get(
        f"{base}/instance/connect/{instance_name}",
        headers=headers,
        params={"number": phone},
    )
    if resp.status_code >= 400:
        raise EvolutionError(f"could not get a pairing code (HTTP {resp.status_code})")
    data = resp.json()
    code = (data.get("pairingCode") or data.get("code") or "").strip()
    if not code:
        raise EvolutionError("no pairing code returned - WhatsApp may already be linked")
    return code


def connection_state(client: httpx.Client, *, instance_name: str) -> str:
    """Return 'open' | 'connecting' | 'close' (or 'unknown' on odd replies)."""
    base, headers = _config()
    resp = client.get(f"{base}/instance/connectionState/{instance_name}", headers=headers)
    if resp.status_code >= 400:
        raise EvolutionError(f"could not read connection state (HTTP {resp.status_code})")
    data = resp.json()
    state = data.get("instance", {}).get("state") or data.get("state") or "unknown"
    return str(state)


def delete_instance(client: httpx.Client, *, instance_name: str) -> None:
    base, headers = _config()
    resp = client.delete(f"{base}/instance/{instance_name}", headers=headers)
    if resp.status_code >= 400:
        raise EvolutionError(f"could not remove the instance (HTTP {resp.status_code})")


def new_client() -> httpx.Client:
    return httpx.Client(timeout=DEFAULT_TIMEOUT)
