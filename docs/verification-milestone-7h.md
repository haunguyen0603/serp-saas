# Milestone 7H — SEO landing pages verification

Local implementation dated **2026-10-10**. Production deployment and Search Console checks have **not** been performed. Local verification uses the final Next 16.3.8 production build.

## Routes, search intent and SEO outputs

All three routes use normal App Router server pages and share the existing PublicShell, public design tokens, links and buttons. The build prerenders their content. No ranking API, dashboard feature or chart library is imported by the landing pages. The inherited root providers and public navigation remain in place.

| Route                         | Search intent / H1                               | Absolute title                                                        | Description                                                                                                                                        |
| ----------------------------- | ------------------------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/google-serp-rank-tracker`   | Broad product / Google SERP Rank Tracker         | Google SERP Rank Tracker for Keyword Position Monitoring \| SERP SaaS | Track Google keyword positions, compare ranking changes, monitor competitors, and review ranking history with SERP SaaS.                           |
| `/daily-serp-tracker`         | Recurring monitoring / Daily SERP Tracker        | Daily SERP Tracker for Google Keyword Rankings \| SERP SaaS           | Monitor Google keyword ranking changes on a recurring schedule, review movement over time, and investigate meaningful SERP changes with SERP SaaS. |
| `/serp-tracking-for-agencies` | Client workflow / SERP Tracking for SEO Agencies | SERP Tracking for SEO Agencies \| Client Rank Tracking \| SERP SaaS   | Organize client keyword tracking, compare competitors, monitor ranking movement, and create reports with SERP SaaS.                                |

Canonical and Open Graph URLs are absolute and identical for each route:

- `https://serpsaas.com/google-serp-rank-tracker`
- `https://serpsaas.com/daily-serp-tracker`
- `https://serpsaas.com/serp-tracking-for-agencies`

Every page has its own title/description, OG website metadata, Twitter summary/title/description and explicit `index, follow` metadata. Local, HTTP, www, app, API and preview origins cannot change its canonical/OG origin. No screenshot or invented customer evidence is used.

Each page emits an escaped JSON-LD graph with `WebPage`, the existing `SoftwareApplication` description and `BreadcrumbList`. The software entity uses `https://serpsaas.com/#software`; WebPage and breadcrumb IDs use the canonical page URL. Visible Home/page breadcrumbs correspond to the structured breadcrumbs. No rating, review, offer or FAQ schema is added.

The marketing route classification now includes the three pages. AppShell uses that shared classification to select PublicShell. The existing proxy redirects these commercial routes from the app host to the commercial host, preserving query strings; commercial-host responses do not add `X-Robots-Tag: noindex`. No load-balancer, www/apex redirect or Cloud Run configuration was edited.

## Product claim review

Copy was checked against existing product implementation: `ranking_explorer.py`, `competitor_analytics.py`, report scheduling/delivery, billing entitlements, frontend report/keyword flows and the existing Blog guides.

- Current checks cover **Top 10**. Outside a complete checked depth has an unknown exact position; failed or incomplete observations do not establish absence. No Top 100 or continuous-ranking promise is made.
- Daily or weekly ranking schedules depend on Plan entitlement. Desktop and Mobile have separate Projects, Plans and usage limits. Prices and numeric Plan limits are not copied into landing content; Pricing remains the live catalog.
- User-based ownership supports managing multiple client Projects from one account. No organization, team access or client portal capability is implied.
- CSV/PDF reporting and report previews are described. Scheduled report email delivery is conditional on configuration and uses the account's own verified email, rather than arbitrary client recipients.
- Competitor comparisons use the same stored checks; coverage is checked-dataset presence, not market share or traffic. Current active aliases affect matching of stored results.

The three pages have distinct sections and paragraph copy. The Blog guides remain educational. Tests verify that commercial section paragraphs are not copied into the related Blog guide.

## Sitemap, robots and internal links

The existing `/sitemap.xml` retains Home, Pricing, About, Privacy, Terms, Blog and all three published guides, and adds the three landing URLs: **12 public URLs total**. Private/authenticated routes are excluded. Landing URL priority is 0.8; no artificial modification date is supplied.

`/robots.txt` explicitly allows all three pages and keeps `Sitemap: https://serpsaas.com/sitemap.xml`. Existing private-route disallow rules remain. The app-host robots response remains disallow-all/noindex.

| Source                                          | Destination                                                                 |
| ----------------------------------------------- | --------------------------------------------------------------------------- |
| Home workflow section; shared Product footer    | All three landing pages                                                     |
| `/blog/how-to-track-google-rankings`            | `/google-serp-rank-tracker`                                                 |
| `/blog/how-to-monitor-keyword-ranking`          | `/daily-serp-tracker`                                                       |
| `/blog/serp-tracking-for-agencies`              | `/serp-tracking-for-agencies`                                               |
| Each landing page's guide section               | Its corresponding Blog guide                                                |
| Each landing page's related workflow navigation | The other two landing pages                                                 |
| Hero, middle and final CTA on each page         | Registration on the configured app origin; Pricing on the commercial origin |
| Visible landing breadcrumb                      | Home                                                                        |

Blog `updatedAt` dates are advanced to 2026-10-10 for the contextual-link additions. Existing publication dates, informational copy, index, RSS and draft behavior are preserved. Primary navigation is unchanged.

## Runtime security gate

The initial live `npm audit --omit=dev` identified **1 high / 0 critical affected runtime packages**: Next 16.3.6, with six underlying advisories. That baseline no longer satisfied M7H's runtime gate. The upstream [16.3.8 security release](https://github.com/vercel/next.js/releases/tag/v16.3.8) and [image-optimization advisory](https://github.com/advisories/GHSA-cjq9-62q9-8jv4) confirm a patched release.

Next and eslint-config-next are pinned to **16.3.8**, with matching env, ESLint plugin and all eight platform SWC entries. [The version comparison](verification-artifacts/milestone-7h/dependency-version-changes.json) contains 12 changed entries, no package additions/removals and no unrelated version changes. Existing lockfile license metadata is preserved. React, sharp 0.35.5, source-map-js 1.2.2 and the prior brace-expansion fixes remain unchanged. No major/minor framework upgrade, overrides or forced audit fix was used.

Final live `npm audit --omit=dev` exits **0**, with **0 vulnerabilities, including 0 high / 0 critical**. See [raw runtime audit](verification-artifacts/milestone-7h/runtime-audit.json). This report does not claim that the full development dependency tree has zero vulnerabilities; the full audit was not repeated for M7H.

## Automated verification

| Final check                         | Result                                                                                          |
| ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| Clean final-lock `npm ci --offline` | Pass; 557 packages installed from the combined temporary cache                                  |
| `npm test`                          | **233 passed / 29 files**; [output](verification-artifacts/milestone-7h/tests.txt)              |
| `npm run lint`                      | Pass                                                                                            |
| `npm run typecheck`                 | Pass                                                                                            |
| `npm run format:check`              | Pass                                                                                            |
| `npm run build`                     | Pass, Next 16.3.8 Webpack / standalone; [output](verification-artifacts/milestone-7h/build.txt) |
| Blog prebuild validation            | Pass; 3 published, 0 drafts                                                                     |
| `npm audit --omit=dev`              | Pass; zero findings                                                                             |
| `git diff --check`                  | Pass                                                                                            |

The final build generates 37 static pages, including all three landing routes. Tests cover their public shell, H1/sections, distinct metadata, alternate configured origins, supported structured data, sitemap/robots, CTAs, homepage/footer/Blog links, distinct copy and product limitations. Proxy tests cover app-host redirects and absence of commercial-host noindex. Existing authenticated feature suites pass unchanged. No Docker or remote CI build was executed for M7H.

Tools use Node 22.22.0, matching the repository contract. The pre-existing temporary Node distribution's npm entrypoint is incomplete, so npm commands use `/usr/local/lib/node_modules/npm/bin/npm-cli.js` under Node 22.22.0 (npm 10.2.4). The online clean installation timed out downloading zwitch. A separate temporary cache was seeded with the existing M7G.1 cache and the newly downloaded patched packages; the clean offline installation then passed without regenerating the lockfile. The user's existing cache was not changed. Sandbox network and localhost restrictions required tool escalation for the npm registry, standalone listener and Chrome; no production permission was requested or used.

Production build configuration: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, `NEXT_PUBLIC_APP_ENV=production`, `NEXT_PUBLIC_SITE_URL=https://serpsaas.com`, `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`. Unit tests use the same local API origin and `NEXT_PUBLIC_APP_ENV=test`.

## Browser QA and accessibility

QA ran at `http://localhost:3011` against the final Next 16.3.8 standalone server.

| Landing route                 | 375  | 768  | 1024 | 1440 |
| ----------------------------- | ---- | ---- | ---- | ---- |
| `/google-serp-rank-tracker`   | Pass | Pass | Pass | Pass |
| `/daily-serp-tracker`         | Pass | Pass | Pass | Pass |
| `/serp-tracking-for-agencies` | Pass | Pass | Pass | Pass |

- **12 browser cases**: HTTP 200, zero page/hydration errors, zero horizontal overflow and zero axe WCAG A/AA violations. Observed CLS was **0** in every case; this is a local measurement, not a production performance claim.
- **12 JavaScript-disabled cases** at the same four widths: readable static content, usable CTA links and no overflow.
- Real HTTP requests using `Host: serpsaas.com`: 200 without noindex for each route. `Host: app.serpsaas.com`: 307 to each commercial URL, preserving the query string. Sitemap and robots return 200 and the expected contents.
- Homepage, all Product footer links, contextual links in the three Blog guides, landing-to-guide links and related product links pass. Hero CTAs meet the tested 44px minimum height; all three registration/Pricing placements per page have the intended destinations.
- **16 Blog browser cases** pass after the link changes and dependency patch, including axe, metadata, reading/CTA layout, mobile navigation, sitemap, RSS and unknown/draft 404 checks. Four Blog routes remain readable without JavaScript.
- **26 existing app browser regression cases** pass, with zero page/hydration errors and zero normal-user admin API requests. Anonymous, verified-user and unverified-user fixtures retain the existing authentication/verification gates.

Evidence: [landing results](verification-artifacts/milestone-7h/browser-qa.json), [Blog results](verification-artifacts/milestone-7h/blog/browser-qa.json), [app regression results](verification-artifacts/milestone-7h/app-browser-qa.json), [actual sitemap](verification-artifacts/milestone-7h/sitemap.xml) and [actual robots](verification-artifacts/milestone-7h/robots.txt). All 12 landing screenshots and 16 Blog screenshots are retained beside their results. Desktop and mobile landing screenshots were visually inspected; the temporary QA server was stopped afterward.

**Existing framework diagnostic:** standalone still logs `Internal: NoFallbackError`; the deliberately unknown and draft Blog slug checks return the correct 404. Published Blog and landing routes pass. This diagnostic was already documented in M7G.1 and is not presented as a new landing-page failure.

The new `frontend/scripts/verify-landing-browser.mjs` runs against **production standalone**, not next dev. Playwright and axe remain optional external QA tools, not new project dependencies. It checks HTTP status, one visible H1, exact title/description, canonical/OG/Twitter metadata, JSON-LD, indexability, CTA locations/destinations, footer/contextual internal links, keyboard skip focus, visible focus outline, mobile-menu Enter/Escape/focus restoration, readable widths, horizontal overflow and layout shift. axe uses WCAG 2 A/AA and 2.1 A/AA tags.

JavaScript-disabled cases verify H1, all explanatory sections, CTA links and overflow at every required viewport. They establish static-content readability; the inherited mobile drawer remains a JavaScript interaction.

All external browser requests are intercepted. Session restoration receives an anonymous local fixture; app-regression fixtures are synthetic and do not make live backend mutations. These checks do not claim real-account authentication, provider calls or report delivery.

Reproduction from `frontend/`, using a Node 22.22.0 environment:

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test
npm run lint
npm run typecheck
npm run format:check
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=production \
  NEXT_PUBLIC_SITE_URL=https://serpsaas.com NEXT_PUBLIC_APP_URL=https://app.serpsaas.com npm run build
npm audit --omit=dev
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/
cp -R public .next/standalone/public
PORT=3011 HOSTNAME=127.0.0.1 node .next/standalone/server.js
# In another terminal; QA_TOOLS_DIRECTORY and QA_CHROME_PATH point to local tools:
QA_BASE_URL=http://localhost:3011 node scripts/verify-landing-browser.mjs
QA_BASE_URL=http://localhost:3011 \
  QA_ARTIFACT_DIRECTORY=../docs/verification-artifacts/milestone-7h/blog \
  node scripts/verify-blog-browser.mjs
QA_BASE_URL=http://localhost:3011 \
  QA_ARTIFACT_DIRECTORY=../docs/verification-artifacts/milestone-7h \
  node scripts/verify-security-regression.mjs
```

## Production and Search Console status

**Not deployed.** No remote CI, Cloud Run revision, DNS/load-balancer change, production URL/301 verification, push or Search Console action was performed. Backend, database, ranking execution, provider routing, billing and authenticated feature implementations are unchanged. Existing apex/www HTTPS canonical redirect infrastructure is preserved in source; its current production behavior was not reverified here.

After an authorized release, verify all three real URLs, sitemap/robots and HTTP/www redirect variants, then inspect each URL in Search Console, run Live Test and request indexing once. Indexing, impressions, queries, clicks, CTR and position trends require later observation; no traffic or indexing guarantee is asserted.
