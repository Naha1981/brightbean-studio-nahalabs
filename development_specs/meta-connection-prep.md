# Meta (Facebook Page) connection prep - NahaLabs QA, 2026-10-15

Goal: publish from BrightBean QA to the NahaLabs Facebook Page, then reuse the
same shape for every client workspace.

## What needs the browser (after 00:00 budget reset)

1. developers.facebook.com with the user's Facebook login (vault: Facebook).
2. Create app, type **Business** (README section "Meta"). Name: NahaLabs BrightBean.
3. Add product **Facebook Login** -> Valid OAuth redirect URI:
   `https://nahalabs-brightbean-qa.onrender.com/social-accounts/callback/facebook/`
4. Leave the app in **development mode**. Dev mode + the user being an app
   admin and Page admin is enough to publish to OUR page. No App Review is
   needed for pages where app admins have a role. Client pages later need the
   app reviewed (pages_manage_posts etc.) OR each client added with a role -
   flag before client onboarding #1.
5. Copy App ID + App Secret.

## Render env vars to set on nahalabs-brightbean-qa (srv-db893uuq1p3s73a2283g)

- PLATFORM_FACEBOOK_APP_ID
- PLATFORM_FACEBOOK_APP_SECRET
(Instagram shares the same pair; PLATFORM_FACEBOOK_CONFIG_ID stays empty -
classic Login, scopes are requested in code.)

## Scopes the provider already requests (providers/facebook.py)

business_management, pages_show_list, pages_manage_engagement,
pages_manage_posts, pages_read_engagement, pages_read_user_content

## Then in the app (browser OAuth, needs the user logged into Facebook)

1. Log into QA as qa-owner@example.invalid.
2. Workspace "NahaLabs" -> Social accounts -> Connect Facebook.
3. OAuth consent -> pick the NahaLabs Page -> grants land as a SocialAccount
   scoped to that workspace only (isolation tests prove scoping).
4. Compose a test post -> approval gate (workspace mode) -> schedule/publish
   -> worker publishes -> confirm on the Page and in analytics.

## Webhooks (later, not needed for the first publish test)

FACEBOOK_WEBHOOK_VERIFY_TOKEN + callback {APP_URL}/webhooks/facebook/ for
comments/mentions ingestion. Without it, inbox works on the 5-min polling
fallback. `python manage.py diagnose_facebook --account-id <uuid>` checks.

## QA limits to remember

EMAIL_BACKEND_TYPE=dummy and EMAIL_DAILY_SEND_LIMIT=0: client approval
magic-link EMAILS will not send in QA. For our own-page test use workspace
approval mode required_internal (in-app approval, no email). Client magic-link
approval is covered by tests (locmem) and needs real SMTP before client #1.
