# Password management — Production release

Released on **2026-10-10**, following the user's explicit production deployment request.

## Release

- Backend source: [`572d078`](https://github.com/haunguyen0603/serp-saas/commit/572d078d7b5ec1ab99490d63affe29cda10d7f86). [Cloud Build](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/fbb54769-e43a-47ec-9915-07fc078c6652?project=833917440392): **success**, completed `2026-10-10T05:35:42Z`.
- Frontend source: [`e956ecd`](https://github.com/haunguyen0603/serp-saas/commit/e956ecdb61b9d1eed922a88e216315fe1cb4f467). [Cloud Build](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/b48461d6-98c1-49ff-9cb6-5935bc037ad1?project=833917440392): **success**, completed `2026-10-10T05:45:38Z`.
- Existing targets: `serp-api`, `serp-worker` and `serp-web`, project `serp-saas`, region `asia-southeast1`; repository triggers run in `europe-west1`.

Backend was released and checked before pushing the frontend commit. The configured backend pipeline successfully executed the migration job with `0014_password_management`, then updated worker/API and checked database health. The migration adds the reset-token table and password version column; existing tokens with no version remain valid for accounts that have not changed their password. The frontend pipeline subsequently built and released the new pages.

This release adds Forgot Password at `/login` and `/forgot-password`, single-use emailed reset links at `/reset-password`, and Change Password at `/app/settings`. Reset links expire after 30 minutes by default. Reset revokes previous sessions; authenticated change renews the current session and revokes other sessions and pending reset links. Existing SMTP, secret bindings, origins and IAM were preserved by image-only releases. No force push or manual parallel Cloud Run deployment was used.

## Verification

Before release, **205 frontend tests**, frontend lint/typecheck, and all backend lint/format checks passed. The previous local work also passed backend unit/auth integration tests, migration/model checks, mypy, the frontend build, and real browser password changes/reset with SMTP Mailpit.

After backend release, 10 production HTTP checks passed. After frontend release, **19 HTTP checks** and **6 Chrome browser cases** passed on the actual domains:

- API/database health and the three OpenAPI password endpoints.
- Invalid reset tokens, unauthenticated password changes and untrusted-origin requests are rejected; authentication responses use `Cache-Control: no-store`.
- Login links to Forgot Password; new auth pages return 200, are excluded from indexing and set no-referrer metadata. Commercial-domain auth routes redirect to the app domain.
- Desktop/mobile Forgot Password and Reset Password at 375/1440 px have no horizontal overflow or page exceptions. The reset secret is removed from the URL; an invalid token displays the recovery link. Anonymous Settings visitors redirect to Login.
- Existing Home, Pricing and Blog return 200.

Evidence: [backend build](verification-artifacts/password-management/backend-build.json), [frontend build](verification-artifacts/password-management/frontend-build.json), [backend HTTP](verification-artifacts/password-management/production-backend-http.json), [full HTTP](verification-artifacts/password-management/production-http.json), [browser](verification-artifacts/password-management/production-browser.json).

## Limits

Production verification used public pages and invalid unauthenticated requests. It did not create accounts, change real passwords or send reset emails to real recipients. End-to-end email/reset/change behavior was tested locally; production inbox delivery and a real authenticated password change remain unverified. Cloud SDK is unavailable on this workstation; migration/release completion is evidenced by the successful existing pipelines and public API checks, without separate control-plane revision/digest queries. No rollback was required.
