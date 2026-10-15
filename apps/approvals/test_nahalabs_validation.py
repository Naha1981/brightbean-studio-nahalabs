"""NahaLabs negative-path validation on unmodified upstream handlers."""
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from apps.approvals.test_workflow import ApprovalWorkflowBase, _make_user
from apps.approvals import services
from apps.members.models import WorkspaceMembership
from apps.client_portal.models import MagicLinkToken
from apps.client_portal.services import consume_magic_link, create_portal_session
from django.test import Client

class NahaLabsValidation(ApprovalWorkflowBase):
    def setUp(self):
        super().setUp()
        self.ws.approval_workflow_mode = 'required_internal_and_client'
        self.ws.save()
    def _save(self, user, action):
        self.client.force_login(user)
        tomorrow = timezone.now() + timedelta(days=1)
        response = self.client.post(reverse('composer:save_post',kwargs={'workspace_id': self.ws.id}), {
            'action':action, 'caption':'SYNTHETIC QA ONLY', 'selected_accounts':str(self.account.id),
            'scheduled_date':tomorrow.date().isoformat(), 'scheduled_time':'12:00',
        })
        from apps.composer.models import PlatformPost
        states = list(PlatformPost.objects.values_list('status',flat=True))
        print('QA_NEGATIVE',user.email,action,response.status_code,states)
        return response,states
    def test_contributor_cannot_schedule_without_client_approval(self):
        response,states=self._save(self.author,'schedule')
        self.assertNotIn('scheduled',states)
    def test_manager_cannot_publish_now_without_client_approval(self):
        response,states=self._save(self.reviewer,'publish_now')
        self.assertNotIn('scheduled',states)
    def test_real_magic_link_client_approval_transition_and_isolation(self):
        client_user=_make_user('synthetic-client@example.invalid')
        WorkspaceMembership.objects.create(user=client_user,workspace=self.ws,workspace_role='client')
        post=self._post('draft')
        services.submit_for_review(post,self.author,self.ws)
        self.assertEqual(post.platform_posts.get().status,'pending_review')
        services.approve_post(post,self.reviewer,self.ws)
        self.assertEqual(post.platform_posts.get().status,'pending_client')
        token=MagicLinkToken.objects.create(user=client_user,workspace=self.ws)
        portal=Client()
        link=reverse('client_portal:magic_link_entry',kwargs={'token':token.token})
        get=portal.get(link)
        token.refresh_from_db(); self.assertFalse(token.is_consumed)
        response=portal.post(link)
        token.refresh_from_db(); self.assertTrue(token.is_consumed)
        self.assertEqual(post.platform_posts.get().status,'pending_client')
        response=portal.post(reverse('client_portal:approve',kwargs={'post_id':post.id}))
        self.assertEqual(post.platform_posts.get().status,'approved')
        self.assertFalse(consume_magic_link(token.token)[2])
    def test_client_cannot_read_or_approve_another_workspace(self):
        from apps.workspaces.models import Workspace
        from apps.composer.models import Post,PlatformPost
        client_user=_make_user('isolation-client@example.invalid')
        WorkspaceMembership.objects.create(user=client_user,workspace=self.ws,workspace_role='client')
        other_ws=Workspace.objects.create(organization=self.org,name='PRIVATE OTHER CLIENT')
        other_post=Post.objects.create(workspace=other_ws,author=self.reviewer,caption='SECRET OTHER CLIENT')
        PlatformPost.objects.create(post=other_post,social_account=self.account,status='pending_client')
        token=MagicLinkToken.objects.create(user=client_user,workspace=self.ws)
        portal=Client(); portal.post(reverse('client_portal:magic_link_entry',kwargs={'token':token.token}))
        response=portal.get(reverse('client_portal:approval_queue'))
        self.assertNotContains(response,'SECRET OTHER CLIENT')
        response=portal.post(reverse('client_portal:approve',kwargs={'post_id':other_post.id}))
        self.assertEqual(response.status_code,404)
        response=portal.get(reverse('composer:drafts_list',kwargs={'workspace_id':other_ws.id}))
        self.assertEqual(response.status_code,403)
        self.assertEqual(other_post.platform_posts.get().status,'pending_client')
    def test_membership_revocation_stops_existing_portal_session(self):
        client_user=_make_user('revoked-client@example.invalid')
        membership=WorkspaceMembership.objects.create(user=client_user,workspace=self.ws,workspace_role='client')
        token=MagicLinkToken.objects.create(user=client_user,workspace=self.ws)
        portal=Client(); portal.post(reverse('client_portal:magic_link_entry',kwargs={'token':token.token}))
        membership.delete()
        response=portal.get(reverse('client_portal:approval_queue'))
        self.assertRedirects(response,reverse('client_portal:magic_link_expired'))
