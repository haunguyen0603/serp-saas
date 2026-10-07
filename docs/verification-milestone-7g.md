# Milestone 7G — Blog & SEO Content verification

**Production follow-up, 2026-10-07:** M7G and M7G.1 were subsequently [deployed and checked on the public domains](deployment-milestone-7g1.md) after explicit authorization. Search Console inspection remains pending. The following local report preserves the original pre-deployment evidence.

Verified locally on 2026-10-07 against base commit `abb3beb`. Implementation, static production build and local browser QA pass. **Production deployment, public-domain checks and Search Console inspection remain pending**; this task did not authorize deployment or GitHub publishing.

## Implementation and scope

- `/blog` uses the existing PublicShell, the heading “SERP Tracking & SEO Insights”, category/date/reading-time cards and a featured first guide.
- `/blog/[slug]` statically generates published Markdown guides with one H1, lead, byline/dates, visible breadcrumbs, GFM prose, two related guides and a contextual Pricing CTA. Desktop reading width is 760 px. Tables and code blocks scroll inside keyboard-focusable containers.
- Content lives in `frontend/content/blog/`. `content.ts` validates YAML frontmatter and computes reading time. The automatic `prebuild` script fails on invalid content, including drafts. Tests execute the real gate against valid and invalid temporary fixtures.
- `draft: true` is excluded from listing, lookups, static params, sitemap and RSS. `dynamicParams = false` and explicit `notFound()` protect unknown/draft slugs. There is no runtime publishing, database, CMS, taxonomy page or executable MDX.
- Each guide has distinct title/description/OG/Twitter metadata, an absolute HTTPS canonical, safely serialized BlogPosting and BreadcrumbList JSON-LD. No ratings, reviews or FAQ markup were invented.
- The canonical helper preserves the configured production origin but falls back to `https://serpsaas.com` for localhost, run.app, app or API origins. Navigation and authentication origins keep their existing configuration semantics.
- Public header, footer and mobile drawer contain Blog. App sidebar routes are unchanged. App-domain Blog children and RSS redirect to the commercial domain; existing app noindex/robots rules are retained.
- `/feed.xml` provides escaped RSS 2.0 with three published items. The sitemap retains the five existing public pages and adds the Blog index and three guides.
- Next standalone file tracing includes the Markdown files. All three are present in `.next/standalone/content/blog/`, and QA ran the standalone server, not `next dev`.

Only frontend/content/documentation files changed. Backend, database, migrations, provider settings, authentication behavior, Cloud Run/CI configuration and `.env` were not changed. The existing shared shell/auth providers remain; the blog adds no charts or authenticated feature clients. New runtime dependencies are pinned `react-markdown` 10.1.0, `remark-gfm` 4.0.1 and `yaml` 2.9.1.

## Published content and metadata

All three guides have author `SERP SaaS`, `draft: false`, and `publishedAt` / `updatedAt` of `2026-10-07`. Publication here means inclusion in the local production build, not an already-deployed production URL.

| Route | Title | Category | Read time | Featured |
| --- | --- | --- | --- | --- |
| `/blog/how-to-track-google-rankings` | How to Track Google Rankings: A Practical Starting Guide | Rank Tracking | 5 min | Yes |
| `/blog/serp-tracking-for-agencies` | SERP Tracking for Agencies: A Repeatable Client Reporting Workflow | Agency SEO | 6 min | No |
| `/blog/how-to-monitor-keyword-ranking` | How to Monitor Keyword Ranking and Investigate Meaningful Changes | SERP Analytics | 5 min | No |

Descriptions are respectively:

1. “Build a reliable Google rank-tracking baseline: choose keywords, fix the search environment, understand Top 10 results and compare changes fairly.”
2. “Organize client rank tracking with clear project boundaries, keyword groups, same-check competitor comparisons and reports that explain the evidence.”
3. “Create a repeatable keyword monitoring routine: keep cohorts stable, compare ranking history, investigate drops and turn observations into next actions.”

The fundamentals guide explains measurement/setup; the agency guide explains client organization/reporting; the monitoring guide explains ongoing review and investigation. They link to each other and `/pricing`. Product caveats cover Top 10 depth, incomplete/failed observations, separate devices, current active aliases, same-check competitor comparisons, coverage denominators, Plan-dependent scheduling, user-only accounts and own-verified-email report delivery. Google references link to primary Search Console documentation. There are no initial images, customer screenshots or invented live data.

See [authoring instructions](blog-authoring.md) for frontmatter, images, drafts and validation.

## Executed automated checks

Node 22.22.0 was used for checks (the host's default Node 20 is below the project's engine requirement). Run from `frontend/` with the required non-secret test configuration:

```bash
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
export NEXT_PUBLIC_APP_ENV=development
npm test
npm run lint
npm run typecheck
npm run format:check
NEXT_PUBLIC_SITE_URL=https://serpsaas.com \
NEXT_PUBLIC_APP_URL=https://app.serpsaas.com npm run build
```

| Check | Result |
| --- | --- |
| Full frontend Vitest suite | **186 passed**, 27 files |
| ESLint | Pass |
| TypeScript | Pass |
| Prettier check | Pass |
| Prebuild content validation | Pass: 3 published, 0 drafts |
| Real prebuild fixture gate | Valid fixture exits 0; invalid boolean exits 1 with field error |
| Next.js production build | Pass: Blog index/RSS/sitemap static; all three articles SSG |
| `git diff --check` | Pass |
| Optional standalone browser script | Pass: 16 route/viewport cases |

The Blog tests cover listing and route rendering, actual Markdown tables/lists/headings/callouts/code, drafts in every discovery surface, unknown/draft 404s, malformed/missing metadata, invalid dates/chronology/booleans, duplicate YAML keys/tags/article metadata, slug/filename agreement, image metadata, canonical-host safety, unique metadata, safe JSON-LD, deterministic related guides and escaped RSS. PublicShell and proxy regression tests cover Blog links and commercial/app domain routing; the unchanged feature/authentication suites also pass.

The full suite requires the two environment variables above. An initial run without them refused to import three existing suites due to missing API configuration; the configured rerun passed. No backend or live provider was needed.

### Dependency audit warning

**Follow-up on 2026-10-07:** [M7G.1 remediation](verification-milestone-7g1.md) subsequently fixed all three runtime findings (runtime audit now 0) and reran tests, Docker/standalone and browser QA. Full audit still has 5 dev-only high findings from the unpatched braces chain; review that exception before deployment. The following paragraph records the historical M7G baseline, not the current patched tree.

`npm install` reported 9 findings (8 high, 1 critical) across the existing dependency tree. `npm audit --omit=dev --json` reported 3 runtime findings: Next.js (critical), sharp (high), source-map-js (high). Their locked versions are unchanged from `HEAD`: 16.3.4, 0.35.4 and 1.2.1 respectively. The audit reported no finding for the new Markdown/YAML dependencies. No existing package version was upgraded by this milestone.

These findings are **not resolved**. Treat dependency remediation as a separate reviewed patch and rerun the full checks before deployment. No broad `npm audit fix --force` or framework upgrade was performed.

## Local HTTP and SEO output

QA used `http://localhost:3010`, served by `.next/standalone/server.js`, with the production commercial/app origin configuration. All four Blog routes return HTTP 200 and remain readable with JavaScript disabled. Both `/blog/unknown-slug` and `/blog/private-draft` return 404; the actual draft fixture is additionally tested at the loader/route/build-gate boundary.

During the two deliberately unknown-slug requests, this Next.js version logged `Internal: NoFallbackError` on the standalone server. Both HTTP responses were correctly 404, not 500, and published-page browser checks passed. Retest this framework diagnostic when applying the pending dependency patch.

The sitemap response contains these nine URLs:

```text
https://serpsaas.com/
https://serpsaas.com/pricing
https://serpsaas.com/terms
https://serpsaas.com/privacy
https://serpsaas.com/about
https://serpsaas.com/blog
https://serpsaas.com/blog/how-to-monitor-keyword-ranking
https://serpsaas.com/blog/how-to-track-google-rankings
https://serpsaas.com/blog/serp-tracking-for-agencies
```

Each article has `<lastmod>2026-10-07</lastmod>`. No app/auth/admin URL, preview origin or draft appears. The robots response includes `Allow: /blog` and `Sitemap: https://serpsaas.com/sitemap.xml`, while retaining app/admin/settings/API/auth exclusions.

RSS returns HTTP 200 with `application/rss+xml; charset=utf-8`, three items, canonical links and published dates. A request to an article with `Host: app.serpsaas.com` returns 307 to the corresponding `https://serpsaas.com/blog/...` URL. Unit tests additionally verify the index and feed redirects. Existing `/`, `/pricing`, `/login`, `/register`, `/app` and `/app/projects` return HTTP 200 locally; authenticated behaviors are covered by the existing test suite rather than a new real-account browser journey.

## Responsive, accessibility and browser QA

Playwright 1.63.0, axe Playwright 4.13.0 and installed Google Chrome ran [the reproducible script](../frontend/scripts/verify-blog-browser.mjs). Browser tools were installed outside the repository. The inherited local unauthenticated refresh was stubbed; no live API, provider, email or production write occurred.

All four routes were checked at every width:

| Viewport | Horizontal scroll width | Article reading width | Browser exceptions | Axe WCAG A/AA violations |
| --- | --- | --- | --- | --- |
| 375 px | 375 px | 343 px | 0 | 0 |
| 768 px | 768 px | 720 px | 0 | 0 |
| 1024 px | 1024 px | 760 px | 0 | 0 |
| 1440 px | 1440 px | 760 px | 0 | 0 |

Checks include one H1, rendered metadata/JSON-LD, real table headers, related guides, Pricing CTA, header/footer links, active Blog navigation, first-tab skip-link focus/outline, mobile menu opening/Escape closure and readable JavaScript-disabled content. The first axe run identified a non-focusable horizontally scrolling code block; adding a labeled `tabIndex=0` fixed it, and the complete rerun passed. Table scrolling is also focusable. Automated WCAG scans do not replace a full human screen-reader audit.

A PerformanceObserver recorded local initial layout shift of 0 in all 16 cases. Local response-start timing ranged about 2.5–88 ms; this is a development-machine observation, not a production performance guarantee. No images or client chart code were introduced.

Detailed results: [browser-qa.json](verification-artifacts/milestone-7g/browser-qa.json).

| Page | 375 px | 768 px | 1024 px | 1440 px |
| --- | --- | --- | --- | --- |
| Blog index | [Image](verification-artifacts/milestone-7g/blog-375.png) | [Image](verification-artifacts/milestone-7g/blog-768.png) | [Image](verification-artifacts/milestone-7g/blog-1024.png) | [Image](verification-artifacts/milestone-7g/blog-1440.png) |
| Google ranking fundamentals | [Image](verification-artifacts/milestone-7g/how-to-track-google-rankings-375.png) | [Image](verification-artifacts/milestone-7g/how-to-track-google-rankings-768.png) | [Image](verification-artifacts/milestone-7g/how-to-track-google-rankings-1024.png) | [Image](verification-artifacts/milestone-7g/how-to-track-google-rankings-1440.png) |
| Agency workflow | [Image](verification-artifacts/milestone-7g/serp-tracking-for-agencies-375.png) | [Image](verification-artifacts/milestone-7g/serp-tracking-for-agencies-768.png) | [Image](verification-artifacts/milestone-7g/serp-tracking-for-agencies-1024.png) | [Image](verification-artifacts/milestone-7g/serp-tracking-for-agencies-1440.png) |
| Ongoing monitoring | [Image](verification-artifacts/milestone-7g/how-to-monitor-keyword-ranking-375.png) | [Image](verification-artifacts/milestone-7g/how-to-monitor-keyword-ranking-768.png) | [Image](verification-artifacts/milestone-7g/how-to-monitor-keyword-ranking-1024.png) | [Image](verification-artifacts/milestone-7g/how-to-monitor-keyword-ranking-1440.png) |

Screenshots capture the initial viewport; automated checks inspect the full page, including CTA/footer/tables. The mobile menu focus outline is intentionally visible after Escape.

### Follow-up: Shared Blog CTA alignment

The earlier index-only override was replaced with a common `.blog-cta` rule: `width: 100%`, no 960 px cap, and no horizontal margins. This applies to the index and all three article pages; the CTA aligns with the featured card on the index and the full “Keep reading” section on detail pages. Article prose retains its 760 px desktop reading width.

Frontend Docker was rebuilt and updated on localhost:3000, with no backend restart. The 26 Blog tests, ESLint and Docker production build passed. A targeted JavaScript-enabled Chrome check covered all 16 route/viewport cases and confirmed equal left edges/widths at 375 (343 px), 768 (720 px), 1024 (976 px) and 1440 (1180 px), no page overflow and zero browser exceptions. API calls were intercepted for the unauthenticated QA session; no live backend/provider was contacted. The reusable browser script now asserts CTA alignment on both the index and detail pages.

Updated index evidence: [375 px](verification-artifacts/milestone-7g/blog-cta-alignment-375.png), [768 px](verification-artifacts/milestone-7g/blog-cta-alignment-768.png), [1024 px](verification-artifacts/milestone-7g/blog-cta-alignment-1024.png), [1440 px](verification-artifacts/milestone-7g/blog-cta-alignment-1440.png). Detail evidence: [Google ranking guide](verification-artifacts/milestone-7g/how-to-track-google-rankings-cta-alignment-1440.png), [Agency guide](verification-artifacts/milestone-7g/serp-tracking-for-agencies-cta-alignment-1440.png), [Monitoring guide](verification-artifacts/milestone-7g/how-to-monitor-keyword-ranking-cta-alignment-1440.png). All detail screenshots are also available at 375/768/1024 px with the corresponding filename suffix.

## Production verification follow-up

At the initial local verification, no deployment, Git commit or push had been performed. The subsequent authorized release and successful production HTTP/browser checks are recorded in [the deployment report](deployment-milestone-7g1.md). Google indexing status is still not claimed. Public checks can be repeated with:

```bash
curl -I https://serpsaas.com/blog
curl -I https://serpsaas.com/blog/how-to-track-google-rankings
curl -I https://serpsaas.com/blog/serp-tracking-for-agencies
curl -I https://serpsaas.com/blog/how-to-monitor-keyword-ranking
curl https://serpsaas.com/sitemap.xml
curl https://serpsaas.com/robots.txt
curl https://serpsaas.com/feed.xml
```

Confirm HTTP 200, commercial HTTPS canonicals, four Blog URLs in sitemap, allowed Blog crawling, three RSS items and no accidental noindex on the commercial host. Then use Google Search Console URL Inspection for the index and all three guides. This requires the site's authorized Search Console access and is not covered by local tests.

- [x] Routes, three useful guides, static publication/draft handling and maintainable source.
- [x] Distinct metadata, canonical/OG/Twitter, Article/Breadcrumb JSON-LD.
- [x] Public navigation, sitemap/robots/RSS, related guides and contextual CTAs.
- [x] Responsive/browser/accessibility QA, production build and frontend regression suite.
- [x] Runtime findings remediated by [M7G.1](verification-milestone-7g1.md); the disclosed dev-only braces exception is carried forward for the authorized release.
- [x] Authorized production deployment and post-deployment URL/browser checks; see [release evidence](deployment-milestone-7g1.md).
- [ ] Google Search Console URL Inspection.
