# Client onboarding runbook - the repeatable template (QA-verified 2026-10-15)

Nothing below is hardcoded to NahaLabs. Every step is per-organization and
per-workspace config. The guarantees cited are enforced by
apps/approvals/test_nahalabs_validation.py (6 tests, green on main).

## Per client (target: minutes, repeatable 100x)

1. **Create the organization** (admin): Organizations -> Add. One org per
   client business. All data (workspaces, social accounts, posts, media,
   credentials) is org-scoped; the client-isolation test proves a client in
   org A cannot read or approve org B's posts.
2. **Create the workspace** inside that org. Set
   `approval_workflow_mode = required_internal_and_client` for full service
   (internal review, then client approval) or `required_internal` while the
   client trusts us to post. Modes: none / optional / required_internal /
   required_internal_and_client.
3. **Invite our staff** to the workspace with roles (contributor drafts,
   manager schedules/publishes within the gate).
4. **Connect the client's socials without giving them a login**: workspace ->
   Onboarding -> create connection link (apps/onboarding: signed, rate-limited,
   revocable token link). Send it to the client; they click, OAuth with their
   own Facebook/Instagram/LinkedIn login, and the account lands scoped to
   THEIR workspace only. Revoke the link after connect.
   - Facebook/Instagram need the platform app env vars (see
     meta-connection-prep.md). Clients who want their own Meta app: per-org
     PlatformCredential row overrides the env fallback (admin-entered).
5. **Approval gate**: contributor drafts -> internal approver -> client gets a
   magic approval link -> client approves -> only then can a post be
   scheduled/published. Negative tests prove contributor-schedule and
   manager-publish-now without client approval stay drafts on EVERY path
   (composer save, chip transition, calendar drag, bulk publish, REST/MCP).
6. **Publish + confirm**: the studio worker (run_studio_worker) publishes at
   the scheduled time; confirm delivery in analytics and the platform itself.
7. **Ongoing**: inbox (comments/mentions), analytics backfills, audit trail in
   approvals (ApprovalAction rows per decision).

## First-client checklist before real onboarding

- [ ] Meta app out of dev mode OR client given a role on the app (App Review
      for pages_manage_posts/pages_read_engagement otherwise).
- [ ] Real SMTP (EMAIL_BACKEND_TYPE + limits) so client magic links send.
- [ ] Durable Postgres (QA uses disposable sqlite in /tmp).
- [ ] Storage backend s3 (QA uses local).
- [ ] FACEBOOK_WEBHOOK_VERIFY_TOKEN + webhook callback for live inbox.
- [ ] Per-client timezone on the workspace (affects scheduling).

## Standing rules

- Our own NahaLabs page first, never a client, until the whole loop above is
  proven end to end on us.
- No cross-client data paths: never share one org/workspace across clients.
- QA deployment stays disposable; no real client data in QA, ever.
