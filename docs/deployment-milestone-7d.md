# M7D production rollout

User-authorized production deployment on 2026-10-26 (Asia/Ho_Chi_Minh).
Target: GCP project `serp-saas`, Cloud Run region `asia-southeast1`; existing
Developer Connect/Cloud Build triggers execute in `europe-west1`.

## Release sequence

1. Backend commit `052bec3`: durable evaluations/inbox/preferences/email outbox,
   migration `0017_ranking_alerts`, and existing worker/queue integration.
2. Wait for backend CI tests, production image build/push, existing release migration
   job, worker/API image updates, traffic promotion and `/health/db` smoke to succeed.
3. Verify public deployed API contracts and authentication boundaries.
4. Release the frontend inbox/preferences/badge and Next.js security update separately.
5. Verify production app assets/routes and existing billing/SePay contracts, then
   record final build IDs and outcomes below.

The backend release uses the existing `cloud-run-release.sh`: the release lock
serializes backend migrations/deployments; the migration job must finish before
worker/API updates. It updates images/traffic while retaining runtime identities,
Cloud SQL, secret bindings, SMTP and SePay configuration. The frontend uses the
existing production origin substitutions.

## Email policy

No outbound ranking email enablement is authorized or performed by this rollout.
M7D code defaults `RANKING_ALERT_EMAIL_ENABLED=false`; per-project email preferences
also default false. Existing account verification/password SMTP configuration is
retained. No test accounts, real rank-provider requests, payments or real alert
emails are created by production smoke checks. SMTP deliverability and a live
opted-in send remain unverified.

## Verification and evidence

Local pre-release verification: [M7D verification report](verification-milestone-7d.md).
Production smoke scripts: `scripts/verify-ranking-alerts-production.mjs` and
`scripts/verify-ranking-alerts-production-browser.mjs`.
The script's PATCH/POST/PUT probes have no bearer token and must return 401 before
any application mutation. It also verifies the private worker remains IAM protected,
existing billing paths/catalog and, after frontend deployment, the inbox/badge
bundles and app/public pages. It does not exercise authenticated tenant data flows.

Backend Cloud Build:
[f5eb6bfc-45e8-43b4-a71a-98a8412bef07](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/f5eb6bfc-45e8-43b4-a71a-98a8412bef07?project=833917440392).

## Completed rollout

Both release builds completed successfully:

| Component | Source commit | Cloud Build | Result |
|---|---|---|---|
| Migration + worker/API | `052bec3ca1e0189b0ad6947bce989f3a79582d05` | `f5eb6bfc-45e8-43b4-a71a-98a8412bef07` | SUCCESS, completed 2026-10-26 16:49:01 UTC |
| Frontend | `a037da0d9e415dfee82463fe9c1db513d8563476` | `1c730fbd-d6a9-4c71-b7f8-901324a125cd` | SUCCESS, completed 2026-10-26 16:58:35 UTC |

[Frontend build](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/1c730fbd-d6a9-4c71-b7f8-901324a125cd?project=833917440392).
The backend pipeline's success includes the existing `serp-db-migrate` execution,
worker/API deployments and traffic promotion; no direct production SQL connection
or extra migration invocation was used. Images use the corresponding unique build
IDs under `asia-southeast1-docker.pkg.dev/serp-saas/serp-saas/{backend,frontend}`.

After backend rollout, **14 backend-only HTTP checks passed**. After frontend
rollout, **23 complete HTTP smoke checks passed**. Verified API/database health,
all M7D routes and auth gates, email opt-in schema default false, private-worker
IAM denial, VND catalog, existing SePay/invoice contracts, deployed inbox/badge
bundles, app/billing pages, public site and existing Vietnamese competitor guide.

A fresh anonymous Chrome context also passed **3 production browser checks**:
Ranking Alerts redirects to login at 375px and 1440px; session refresh targets
`https://api.serpsaas.com` and correctly returns 401 without a cookie. No page or
hydration errors occurred. No authenticated customer data, real ranking provider,
SMTP delivery, payment creation or gateway transaction was tested.

Production URL: [Ranking Alerts](https://app.serpsaas.com/app/ranking-alerts).
Preferences: open an existing Project and select **Alert Preferences**.
Existing pre-release rank checks intentionally do not backfill; the first eligible
completed post-release check establishes a baseline. A second eligible check is
needed before a meaningful transition can create an alert.

Evidence:

- [Backend build status](verification-artifacts/milestone-7d/production/backend-build.json)
- [Frontend build status](verification-artifacts/milestone-7d/production/frontend-build.json)
- [Backend smoke](verification-artifacts/milestone-7d/production/backend-http-smoke.json)
- [Complete HTTP smoke](verification-artifacts/milestone-7d/production/http-smoke.json)
- [Anonymous browser smoke](verification-artifacts/milestone-7d/production/browser-smoke.json)

No outbound ranking email switch was enabled. Real email deliverability and
production authenticated alert/preference flows remain unverified. The runtime
SMTP/SePay bindings were retained by the image-only release commands; public
checks do not establish private secret-version or operational-flag values.

For code rollback, use the Cloud Run revision/traffic controls to select a known
previous ready revision for each affected service, checking schema compatibility.
Keep additive alert tables/history rather than downgrading production evidence.
Operational alert/email disable switches are documented in the verification report.
