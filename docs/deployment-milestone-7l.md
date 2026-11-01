# M7L production rollout

**Deployment completed successfully on 2026-11-01**, following the user's explicit `deploy production` instruction after the combined M7D/M7L release gates passed and the remaining development-only audit findings were disclosed.

## Release identity

| Item | Value |
| --- | --- |
| Deployed source | [`18d3a19862a504c052f38533237bc01162b62d57`](https://github.com/haunguyen0603/serp-saas/commit/18d3a19862a504c052f38533237bc01162b62d57) |
| Previous main | `25dd7806a1385818541196785dc44c80261d5c29` |
| Cloud Build | [`d605560d-75e7-4c4b-a846-0bc93ab37a14`](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/d605560d-75e7-4c4b-a846-0bc93ab37a14?project=833917440392), **SUCCESS** |
| Build started | `2026-11-01T07:30:41Z` / **14:30:41 Asia/Saigon** |
| Build completed | `2026-11-01T07:40:34Z` / **14:40:34 Asia/Saigon** |
| Cloud Run target | Existing **serp-web**, project **serp-saas**, region **asia-southeast1** |
| Trigger | **serp-web-main (serp-saas)**, Developer Connect / Cloud Build in **europe-west1** |
| Pipeline image tag | `asia-southeast1-docker.pkg.dev/serp-saas/serp-saas/frontend:d605560d-75e7-4c4b-a846-0bc93ab37a14` |
| Production Next Build ID | **767IBhnzxf_whvx7ob7ZT**, observed on both website and app |
| Previous observed Build ID | `BZfnOHRkuTRxE8VdouaaU` |

The release commit was pushed normally as a fast-forward to `main`; no force-push was used. The existing Cloud Build pipeline performed checks, production build, registry push, image update, traffic promotion and HTTP smoke checks. Its release helper uses the existing release lock and an image-only update of `serp-web`; it does not rewrite runtime settings or IAM.

The backend trigger explicitly concluded **neutral — Changed files did not match file filter**. **No backend/worker release or production migration was run.** SePay, billing, subscription, SMTP and production provider settings were not modified. No new service, trigger, IAM permission, secret version or infrastructure resource was created for deployment. [Exact-source build status](verification-artifacts/milestone-7l-deployment/checks-success.json), [push confirmation](verification-artifacts/milestone-7l-deployment/push-confirmation.json).

M7L R1–R5 were already present on remote main and production before this rollout. This release promotes the fully verified candidate and the targeted Vitest/Vite/Zod security patches while retaining all M7D Ranking Alerts and newer Project behavior. It does not reapply the product changes or replace main with the older M7L baseline.

## Pre-release verification and source preservation

The [final release-gate report](verification-milestone-7l-final-release.md) retains the complete Linux/Docker evidence: **402 backend tests in one clean run with real PostgreSQL/Redis**, **342 frontend tests**, **56 infrastructure tests**, lint/typecheck/format, production image builds, migration roundtrip, real disposable-API M7D flows and M7L SEO/browser regression. Source/context hashes were rechecked before the release commit; no application implementation changed after those gates.

The six substantive tracked changes are the two frontend dependency files, two browser harnesses and two infrastructure test portability fixtures described in that report. Backend implementation/migrations, frontend product source/content, Dockerfiles and Compose remain unchanged. Next/eslint-config-next stay **16.4.3**, React/React DOM **19.3.0**, sharp **0.35.5**. Development patches: Vitest **4.1.12**, Vite **8.2.4**, Zod **4.6.6**, with all runtime lock entries preserved.

Before Git mutations, the candidate and evidence were backed up to `.tools/m7l-deployment-backup-20261101/` with a SHA-256 manifest and patch. The main IDE workspace was then safely fast-forwarded to the release commit after its 189 untracked evidence/report files were moved into the verified `.tools/m7l-production-main-sync-backup-20261101/`. Those original copies remain available; no reset or clean was used. [Main workspace synchronization](verification-artifacts/milestone-7l-deployment/main-workspace-sync.json).

Staging exposed trailing whitespace in original CLI/JUnit captures. Those raw captures were preserved, and the whitespace check passed for all source and authored documentation, excluding only `docs/verification-artifacts/**`. No test assertion or application format rule was disabled. [Review](verification-artifacts/milestone-7l-deployment/evidence-whitespace-review.json).

## Verification on the deployed domains

The deployment finished at 14:40 local time. After the user resumed the task, production smoke checks ran at approximately **21:08–21:13 Asia/Saigon**; these checks were performed against the deployed domains, not the local Docker containers.

| Check | Result |
| --- | --- |
| Fresh website/app HTTP and Build ID checks | **6 passed**; one new Build ID across EN, VI and Ranking Alerts routes; API/database health 200 |
| M7L sitemap/SSR regression | **27 URLs passed**; inventory identical to the verified Linux artifact |
| M7L responsive/browser regression | **88/88 passed** at 375/768/1024/1440 px, JavaScript on/off |
| M7L accessibility | **44 axe analyses, zero violations**, no exclusions |
| M7D/existing-product HTTP smoke | **23 passed** |
| M7D live anonymous browser smoke | **3 passed**, no page/hydration errors |
| Canonical redirects, app robots and native image processing | **6 passed** |

M7L checks include unique title/description and one H1 per page, language, self-canonical, reciprocal hreflang/x-default mappings, robots/indexability, structured data, sitemap/RSS counts, retained/new internal links, expected 404s and all R1–R5 copy/link assertions. Keyboard focus/Enter navigation, overflow and hydration checks pass. The 375px English Blog CTA screenshot was visually inspected and remains readable and correctly arranged.

The production M7D smoke verifies API/PostgreSQL health, deployed OpenAPI alert/preferences contracts and opt-in defaults, unauthenticated access restrictions, private-worker IAM denial, inbox/badge assets, current VND catalog, existing SePay/invoice contracts and application routes. A fresh browser verifies anonymous Ranking Alerts redirects to login at 375/1440 px and confirms real session refresh uses **https://api.serpsaas.com**, returning 401 without a cookie.

HTTP → HTTPS and www → apex return 301; app-domain Blog and commercial Login redirect to their correct domains with 307. App robots disallows crawling. Native image processing returns **200 image/png, 282 bytes** for the benign local apple-icon probe.

An extra redirect probe initially expected a literal `https://serpsaas.com/`, while the existing HTTP redirect returned `https://serpsaas.com:443/`. Investigation confirmed that standard URL parsing normalizes the HTTPS default port to the identical URL. The probe now compares normalized URLs while retaining strict status, scheme, host and path checks; all six extra checks pass. No production redirect configuration was changed. [Original probe output](verification-artifacts/milestone-7l-deployment/production-extra-initial-failure.txt), [raw and normalized targets](verification-artifacts/milestone-7l-deployment/production-extra-smoke.json).

Production harnesses are copies of the existing verified assertions. M7L changes only the target guard to the exact production origin and resolves the existing host JSDOM dependency. M7D changes only its artifact output directory, preserving earlier milestone evidence. Exact executed commands from the release worktree were:

```text
node ../m7l-final-setup/verify-m7l-production.mjs
node ../m7l-final-setup/verify-m7d-production-http.mjs
node ../m7l-final-setup/verify-m7d-production-browser.mjs
```

M7L uses `QA_BASE_URL=https://serpsaas.com`, the immutable original M7L baseline through `QA_BASELINE_FILE`, the existing task-local Playwright/axe modules and host Chrome **156.0.8078.74**. Separate artifact directories prevent overwriting local or earlier production evidence. The exact harness copies are archived under [harnesses/](verification-artifacts/milestone-7l-deployment/harnesses/).

Evidence:

- [Consolidated production results](verification-artifacts/milestone-7l-deployment/production-summary.json)
- [Before rollout](verification-artifacts/milestone-7l-deployment/before-http.json) and [after rollout](verification-artifacts/milestone-7l-deployment/after-http.json)
- [M7L SSR inventory](verification-artifacts/milestone-7l-deployment/seo/after.json), [browser/axe results](verification-artifacts/milestone-7l-deployment/seo/browser-qa.json), [execution log](verification-artifacts/milestone-7l-deployment/m7l-production.txt)
- [M7D HTTP smoke](verification-artifacts/milestone-7l-deployment/m7d/http-smoke.json), [anonymous browser smoke](verification-artifacts/milestone-7l-deployment/m7d/browser-smoke.json)
- [Redirects/robots/image smoke](verification-artifacts/milestone-7l-deployment/production-extra-smoke.json)

## Security and verification limits

Fresh post-deployment `npm audit --omit=dev --json` against the deployed source lockfile exits **0 — zero vulnerabilities**. Full audit exits **1 — 16 moderate development-only affected packages, zero high/critical**, as disclosed before authorization. Findings remain the minimatch lint-toolchain advisory family; their risk, lack of a compatible patch across current callers and absence from the inspected production standalone dependencies are documented in the final release report. No forced override/downgrade or full-audit-zero claim is made. [Runtime audit](verification-artifacts/milestone-7l-deployment/post-deploy-runtime-audit.json), [full audit](verification-artifacts/milestone-7l-deployment/post-deploy-full-audit.json), [exit codes](verification-artifacts/milestone-7l-deployment/post-deploy-audit-results.json).

Production checks created **zero accounts, rank checks, payments or emails**. Mutation-shaped auth probes carry no credentials and must fail before application mutation. No customer session or authenticated tenant data was used. M7L public-page browser checks intercept anonymous refresh for isolation; the separate M7D browser checks verify the actual API origin/401 response. Authenticated Ranking Alerts flows were validated against the disposable real backend/DB before release, not against production customer data. Real SMTP deliverability, paid SERP calls and payment execution remain untested by this rollout.

Cloud SDK is unavailable on this workstation. Deployment completion is evidenced by the Google Developer Connect check for the exact release SHA, successful configured release pipeline, changed live Build ID and passing domain checks. Cloud Run revision names, registry digest and control-plane traffic/configuration were not independently queried; they are not claimed as separate evidence. No rollback was needed or performed. If rollback becomes necessary, use the existing Cloud Run revision/image controls and confirm readiness/traffic; the previous successful frontend pipeline tag was `8fe97166-13e1-457d-ae52-2f43d3ecd9d2`. No database downgrade is appropriate for this frontend-only release.

**Production release status: SUCCESS.** A documentation-only follow-up records this evidence; it does not change application source or require another frontend/backend deployment.
