"""WhatsApp pairing tests: Evolution API is always mocked."""

from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from apps.accounts.models import User
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

from . import evolution
from .models import WhatsAppConnection


class FakeResp:
    def __init__(self, payload=None, status=200):
        self._payload = payload or {}
        self.status_code = status

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, *a, **kw):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None, params=None):
        self.calls.append(("POST", url))
        return FakeResp({"instance": {"instanceName": json.get("instanceName")}})

    def get(self, url, headers=None, params=None):
        self.calls.append(("GET", url))
        if "/connect/" in url:
            return FakeResp({"pairingCode": "ABCD-1234"})
        return FakeResp({"instance": {"state": "open"}})

    def delete(self, url, headers=None):
        self.calls.append(("DELETE", url))
        return FakeResp({})


class PhoneNormalizeTests(TestCase):
    def test_sa_number(self):
        self.assertEqual(evolution.normalize_phone("+27 82 555 1234"), "27825551234")

    def test_junk_rejected(self):
        with self.assertRaises(evolution.EvolutionError):
            evolution.normalize_phone("082")


@override_settings(EVOLUTION_API_URL="http://evo.test", EVOLUTION_API_KEY="k")
class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="x", name="Owner", tos_accepted_at=timezone.now())
        self.org = Organization.objects.create(name="Bistro org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Bistro")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER)
        self.client.force_login(self.user)

    def _patch_org(self):
        # request.org comes from middleware; patch the workspace lookup path
        return mock.patch(
            "apps.whatsapp_connect.views._get_workspace",
            side_effect=lambda request, workspace_id: self.workspace,
        )

    def test_start_pairing_creates_connection_with_code(self):
        with mock.patch.object(evolution, "new_client", FakeClient), self._patch_org():
            url = reverse("whatsapp_connect:connect", args=[self.workspace.id])
            resp = self.client.post(url, {"phone": "+27 82 555 1234"})
            self.assertEqual(resp.status_code, 302)
            conn = WhatsAppConnection.objects.get(workspace=self.workspace)
            self.assertEqual(conn.phone_number, "27825551234")
            self.assertEqual(conn.pairing_code, "ABCD-1234")
            self.assertEqual(conn.status, WhatsAppConnection.Status.PENDING)

    def test_bad_phone_shows_error_no_connection(self):
        with self._patch_org():
            url = reverse("whatsapp_connect:connect", args=[self.workspace.id])
            self.client.post(url, {"phone": "082"})
            self.assertEqual(WhatsAppConnection.objects.count(), 0)

    def test_status_json_marks_connected(self):
        conn = WhatsAppConnection.objects.create(
            workspace=self.workspace, instance_name="ws-x", phone_number="27825551234",
            pairing_code="ABCD-1234",
        )
        with mock.patch.object(evolution, "new_client", FakeClient), self._patch_org():
            url = reverse("whatsapp_connect:status_json", args=[self.workspace.id, conn.pk])
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            conn.refresh_from_db()
            self.assertEqual(conn.status, WhatsAppConnection.Status.CONNECTED)
            self.assertIsNotNone(conn.connected_at)

    def test_disconnect_marks_disconnected(self):
        conn = WhatsAppConnection.objects.create(
            workspace=self.workspace, instance_name="ws-x", phone_number="27825551234",
            status=WhatsAppConnection.Status.CONNECTED,
        )
        with mock.patch.object(evolution, "new_client", FakeClient), self._patch_org():
            url = reverse("whatsapp_connect:disconnect", args=[self.workspace.id, conn.pk])
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 302)
            conn.refresh_from_db()
            self.assertEqual(conn.status, WhatsAppConnection.Status.DISCONNECTED)
