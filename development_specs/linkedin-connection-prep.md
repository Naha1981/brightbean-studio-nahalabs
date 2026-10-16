# LinkedIn (Company Page) connection prep - NahaLabs QA, 2026-10-16

Goal: publish from BrightBean QA to the NahaLabs LinkedIn Company Page -
the first real BrightBean publish (the Facebook test was dropped 16 Oct;
LinkedIn needs NO Meta App Review). Same shape later for client workspaces.

## What needs the browser (00:05, after daily budget reset)

1. developer.linkedin.com with the user's LinkedIn login (vault: LinkedIn - Thabiso Naha).
2. Create app: name "NahaLabs BrightBean", LinkedIn Page = NahaLabs
   (company page required to create the app; he is a page admin - he posted
   to it 16 Oct 05:24).
3. Products tab: request **Share on LinkedIn** (w_member_social) and
   **Sign In with LinkedIn using OpenID Connect**. For company-page posting
   also request **Community Management API** if listed (self-serve for page
   admins; grants w_organization_social, r_organization_social,
   rw_organization_admin). The provider asks for exactly these scopes
   (providers/linkedin_company.py): r_basicprofile, w_member_social,
   w_organization_social, r_organization_social, rw_organization_admin.
   If Community Management is not grantable in the portal, fall back to
   linkedin_personal (OIDC + w_member_social posts to his profile) and flag.
4. Auth tab -> Authorized redirect URLs:
   `https://nahalabs-brightbean-qa.onrender.com/social-accounts/callback/linkedin_company/`
   (and `.../callback/linkedin_personal/` if the personal path is used).
5. Copy Client ID + Client Secret.

## Render env vars to set on nahalabs-brightbean-qa (srv-db893uuq1p3s73a2283g)

- PLATFORM_LINKEDIN_COMPANY_CLIENT_ID
- PLATFORM_LINKEDIN_COMPANY_CLIENT_SECRET
(Legacy fallback names PLATFORM_LINKEDIN_CLIENT_ID/SECRET also work;
PLATFORM_LINKEDIN_PERSONAL_* only if a dedicated personal app is created.)

Non-browser: setting these + service restart is Render API only.

## Then in the app (browser OAuth, user logged into LinkedIn)

1. Log into QA as the QA owner.
2. Workspace "NahaLabs" -> Social accounts -> Connect -> LinkedIn (Company Page).
3. OAuth consent -> provider lists organizations the member administers
   -> pick the NahaLabs page (providers/linkedin_company.get_user_pages).
4. Compose test post -> approval gate -> publish -> verify on the page
   and via GET of the page's posts (API-checkable, no browser needed).

## Why LinkedIn first (16 Oct decision)

Restaurant bundle v1 must not depend on Meta App Review. LinkedIn app +
scopes are self-serve and free; posting works for pages the app owner
administers without review. FB/IG added later, post-review.

## QA limits to remember

EMAIL_BACKEND_TYPE=dummy, EMAIL_DAILY_SEND_LIMIT=0: approval magic-link
emails don't send in QA; use in-app approval for the test.
