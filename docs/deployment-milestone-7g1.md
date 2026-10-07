# M7G + M7G.1 — Production release

Production frontend deployment and public smoke verification completed on **2026-10-07**, following the user's explicit request to deploy after disclosure of the remaining development-only audit findings.

## Release identity

- Source commit: [`7edae61b29291bce20b7f812cf8b794012c1a995`](https://github.com/haunguyen0603/serp-saas/commit/7edae61b29291bce20b7f812cf8b794012c1a995), pushed normally to `main`.
- Scope: static M7G Blog/SEO, shared index/detail CTA alignment and M7G.1 dependency patches. Next / eslint-config-next 16.3.6, sharp 0.35.5 and source-map-js 1.2.2.
- Cloud Build trigger: `serp-web-main (serp-saas)` through the existing Developer Connect connection in `europe-west1`.
- [Build `57751efe-e4df-459a-b242-7ec61647c42f`](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/57751efe-e4df-459a-b242-7ec61647c42f?project=833917440392): **success**, started `11:21:11 UTC`, completed `11:29:45 UTC` (18:21–18:29 Vietnam time).
- Existing deployment target: Cloud Run `serp-web`, project `serp-saas`, region `asia-southeast1`. The configured release helper updates the image and routes traffic to the latest revision while preserving service configuration/IAM.
- Image tag specified by the successful pipeline: `asia-southeast1-docker.pkg.dev/serp-saas/serp-saas/frontend:57751efe-e4df-459a-b242-7ec61647c42f`.
- Backend trigger concluded **neutral**: changed files did not match its filter. No backend/worker/database/migration/secret changes were released.

The pre-release GitHub main was `abb3beb`. `/blog` returned 404 before release and 200 after successful deployment. `.env` remained ignored and was not committed or uploaded. No force push, new trigger, service, IAM permission or direct/manual concurrent Cloud Run deployment was used.

Cloud SDK is not installed on this workstation. Deployment was performed by the already functioning repository pipeline, and its result was verified via the GitHub check for the exact source SHA plus requests to the actual production domains. Cloud Run revision names, image digest and control-plane traffic state were not independently queried with gcloud; those are not claimed as separate checks.

## Gates and public verification

Immediately before push: **186 tests / 27 files passed**, lint, typecheck, format and diff checks passed; runtime audit reported **0 vulnerabilities**. The prior [M7G.1 local report](verification-milestone-7g1.md) contains the host/AMD64/ARM64 builds, sharp native/image optimization and local browser/standalone evidence. The successful Cloud Build run additionally executed its configured check/build/push/release pipeline against the committed source.

Post-release public HTTP checks: **23 passed** on the real domains.

- `https://serpsaas.com/`, Pricing, About, Privacy, Terms, Blog index and all three guides return 200.
- Blog output has one H1, commercial HTTPS canonical/OG URL, server-rendered article content, BlogPosting/BreadcrumbList markup, public navigation and CTA. Public Blog has no noindex response header/meta directive.
- Unknown and private-draft Blog slugs return 404, not 500.
- RSS returns 200 with `application/rss+xml` and exactly three items. Sitemap contains four canonical Blog URLs, without draft, app-domain or `run.app` URLs. Commercial robots allows Blog and points to the commercial sitemap.
- App-domain Login, Register, Verify Email, App and Projects return 200 with `X-Robots-Tag: noindex, nofollow`; app robots disallows all crawling.
- App-domain Blog index/article redirect 307 to the commercial domain; commercial Login redirects 307 to `app.serpsaas.com/login`.

Post-release Chrome/axe checks: **16 passed**, four Blog routes at **375 / 768 / 1024 / 1440**. Zero page/hydration exceptions, zero horizontal overflow and zero WCAG A/AA axe violations. Canonicals and Blog-active desktop/mobile navigation passed; mobile menu opens and closes with Escape. CTA left edge/width matches the featured card or related-guide block on every index/detail case. All four routes also remain readable with JavaScript disabled.

This browser smoke only loaded public pages/assets. Auth refresh was intercepted with a synthetic anonymous response, so no live account/session/provider/API mutation was used. Public app HTTP responses are not a claim of a real authenticated end-to-end login, ranking, billing, report generation or competitor workflow. Those feature regressions remain covered by the passing existing suites.

Evidence: [exact-commit Cloud Build checks](verification-artifacts/milestone-7g1/production-build.json), [production HTTP results](verification-artifacts/milestone-7g1/production-http.json), [production browser results](verification-artifacts/milestone-7g1/production-browser.json).

## Remaining limitations

Runtime audit is 0; full audit still has **5 high dev-only findings** propagated from the unpatched braces advisory. That disclosed upstream exception is carried forward for this authorized release; it is not silently suppressed or misrepresented as a clean full audit. The development package was absent from the locally verified production standalone image. The risk/mitigation and compatible-update follow-up remain in the [security verification report](verification-milestone-7g1.md).

`NoFallbackError` was observed locally with correct unknown-slug 404 responses. Production unknown slugs were verified as 404; production container logs were not independently inspected. Google Search Console URL Inspection, indexing status and real-account business workflows are still not verified. No rollback was required or performed.
