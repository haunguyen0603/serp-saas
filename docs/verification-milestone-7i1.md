# Milestone 7I.1 — Full public localization verification

Implemented and verified locally on **2026-10-11**, extending M7I. Production
deployment, production redirect checks and Search Console actions have **not**
been performed.

## Public routes and locale map

`frontend/src/lib/public-locales.ts` defines all 12 pairs explicitly. Language
selection, reciprocal metadata and tests consume that map. Translated slugs are
not inferred. M7I routes remain available; M7I.1 adds five Vietnamese routes.

| English                                | Vietnamese                                |
| -------------------------------------- | ----------------------------------------- |
| `/`                                    | `/vi`                                     |
| `/pricing`                             | `/vi/bang-gia`                            |
| `/about`                               | `/vi/gioi-thieu`                          |
| `/privacy`                             | `/vi/chinh-sach-bao-mat`                  |
| `/terms`                               | `/vi/dieu-khoan-dich-vu`                  |
| `/google-serp-rank-tracker`            | `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa`   |
| `/daily-serp-tracker`                  | `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` |
| `/serp-tracking-for-agencies`          | `/vi/seo-rank-tracking-cho-agency`        |
| `/blog`                                | `/vi/blog`                                |
| `/blog/how-to-track-google-rankings`   | `/vi/blog/cach-theo-doi-thu-hang-google`  |
| `/blog/how-to-monitor-keyword-ranking` | `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` |
| `/blog/serp-tracking-for-agencies`     | `/vi/blog/serp-tracking-cho-agency`       |

The five additions are prerendered. Vietnamese Blog now has three published
articles. Its agency guide explains client project boundaries, keyword cohorts,
capacity planning, shared competitor evidence and reporting, separately from the
commercial `/vi/seo-rank-tracking-cho-agency` landing page. It preserves the
product's user-owned account scope, Top 10 measurement limits and delivery to the
account's own verified email.

## Language selector, navigation and flags

The segmented EN/VI control is replaced by shared `LanguageSelect`, using the
existing native `details` dropdown primitive. A local US/Vietnam SVG appears before
the visible English/Tiếng Việt label; flags have empty alternative text and are
decorative. Assets are `/flags/us.svg` and `/flags/vi.svg`, with no external image
service or new dependency.

The header selector stays visible on desktop and mobile, has
`aria-label="Change language"`, visible focus and a minimum 44px trigger/menu
target height. Enter and Space open it; Escape closes it and restores trigger
focus; an outside click or leaving its focus closes it. The active option has a
checkmark and `aria-current="page"`. Both real locale links are server-rendered;
native expansion and navigation remain usable with JavaScript disabled.

All mapped switches preserve page intent. Only genuinely unmapped routes fall
back to the target locale Home. URL paths determine the language; no preference
storage, automatic browser-language/GeoIP redirects or selector API call is added.

Shared desktop/mobile navigation and footer translate all public labels and select
Vietnamese destinations. Home, landing CTAs, Blog content and legal cross-links
also use Vietnamese equivalents. Login/Register and account actions retain the
configured `https://app.serpsaas.com` destination. The dashboard remains English.

## Pricing consistency

Both pricing pages render `PricingCatalog` and use the same TanStack query key,
request to `GET /api/v1/billing/plans`, `groupPlans` ordering and price formatter.
Only copy, units, scheduling labels, FAQ and loading/error/retry messages vary by
locale. Plan IDs, names, prices, currency, project/keyword/check limits, scheduling
entitlements and availability remain backend data. No fallback prices or limits
are introduced. Free/paid and authenticated CTA destinations retain their existing
behavior.

Unit coverage uses a reversed catalog with an omitted plan, fractional prices and
disabled/weekly/daily schedules. Browser coverage compares six synthetic plans at
every width and checks catalog failure/retry in both languages. These checks prove
presentation consistency with controlled API fixtures; they do not inspect or
change the live backend catalog.

## Legal and About translation

About follows the source product purpose and implemented features without adding
customer counts, company size, history, funding, awards or office claims.

Privacy and Terms preserve all eight source sections and their paragraph coverage.
Privacy retains **2026-10-05** and Terms **2026-09-20** as their revision dates.
`supports@serpsaas.com` remains the Privacy/About contact; Terms continues directing
questions to the account administrator, as the English source does.

Privacy retains account/password-hash records, tracking/subscription/operational
data, essential HttpOnly refresh cookies, in-memory access tokens, no advertising
or analytics trackers, Serper/SerpApi and hosting/email providers, possible overseas
processing, account ownership restrictions, report expiry (30 days by default),
metadata retention and no automatic deletion period for other records. Security
limitations and administrator-assisted requests/identity verification are retained.

Terms retains service/account obligations, acceptable use and access restriction,
ranking snapshots/provider availability/no guaranteed outcomes, separate device
plans, logical checks, saved subscription terms, manual bank-transfer activation,
cancellation/refund questions, Free limits after expiry, authorized input and
maintenance/updates. No jurisdiction, additional warranty/liability structure or
prevailing-language clause absent from the English source is invented. This work
translates existing product documents rather than revising their legal obligations.

## SEO and crawler behavior

Every pair self-canonicalizes at `https://serpsaas.com` and emits reciprocal `en`,
`vi` and English `x-default` alternates. English About/Pricing/Privacy/Terms retain
their existing titles, descriptions and content, with reciprocal alternates added.
All 12 Vietnamese pages have distinct titles/descriptions, OG/Twitter metadata and
index/follow directives. Metadata collected from rendered pages is included in the
browser evidence.

Rendered titles for the five additions:

| Vietnamese route                    | Title                                                                         |
| ----------------------------------- | ----------------------------------------------------------------------------- |
| `/vi/bang-gia`                      | Bảng giá SERP SaaS \| Gói theo dõi thứ hạng từ khóa                           |
| `/vi/gioi-thieu`                    | Giới thiệu SERP SaaS \| Công cụ theo dõi thứ hạng Google                      |
| `/vi/chinh-sach-bao-mat`            | Chính sách bảo mật \| SERP SaaS                                               |
| `/vi/dieu-khoan-dich-vu`            | Điều khoản dịch vụ \| SERP SaaS                                               |
| `/vi/blog/serp-tracking-cho-agency` | Theo dõi SERP cho agency: Quy trình báo cáo khách hàng nhất quán \| SERP SaaS |

The M7I root layouts still render `lang="en"` or `lang="vi"` in raw server HTML.
Accept-Language does not override a directly requested URL. Supported Vietnamese
JSON-LD uses WebPage, SoftwareApplication, BreadcrumbList and BlogPosting with
localized text; no invented ratings, reviews or offers appear.

The sitemap contains **24 unique public URLs**, including all five additions.
Blog dates come from content; private/auth routes are excluded. Robots continues
allowing `/vi` and preserves all private/app/auth/API restrictions and the canonical
sitemap URL. Local HTTP checks also verify existing app-host 307 ownership redirects
and query preservation, including the app root redirect to `/app`.

## Build and automated checks

| Check                  | Result                                                       | Evidence                                                             |
| ---------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------- |
| `npm test`             | 273 passed, 31 files                                         | [Tests](verification-artifacts/milestone-7i1/tests.txt)              |
| `npm run lint`         | Pass                                                         | [Lint](verification-artifacts/milestone-7i1/lint.txt)                |
| `npm run typecheck`    | Pass                                                         | [TypeScript](verification-artifacts/milestone-7i1/typecheck.txt)     |
| `npm run format:check` | Pass                                                         | [Formatting](verification-artifacts/milestone-7i1/format-check.txt)  |
| `npm run build`        | Pass; 49 static pages, 6 published Blog articles validated   | [Build](verification-artifacts/milestone-7i1/build.txt)              |
| `npm audit --omit=dev` | Exit 0; 0 runtime vulnerabilities, including 0 high/critical | [Audit](verification-artifacts/milestone-7i1/runtime-audit.json)     |
| `git diff --check`     | Pass                                                         | [Git check](verification-artifacts/milestone-7i1/git-diff-check.txt) |

Node 22.22.0 and Next 16.3.8; no dependency/lockfile change. The temporary Node
distribution uses the installed npm entrypoint at
`/usr/local/lib/node_modules/npm/bin/npm-cli.js`. No remote CI or Docker build was run.
Backend, email templates, database and infrastructure remain outside this change.

New coverage verifies current flags/ordering, native dropdown behavior, Escape and
outside closing, all mappings, fallback, complete nav/footer, pricing equality and
error recovery, legal section/date preservation, agency content and metadata.
Existing M7I, English SEO, auth and app suites pass.

## Local production browser QA

The production standalone build runs at `http://127.0.0.1:3013`, using Chrome,
optional external Playwright and axe tools. No frontend QA dependencies are added.
API responses use synthetic plans and anonymous sessions; external public
navigation is intercepted back to localhost. No real account, backend mutation,
search provider or production request occurs.

All 24 public URLs pass at **375, 768, 1024 and 1440px**:

- **96 browser cases:** correct flag/text order, language, one visible H1,
  self-canonical/reciprocal alternates, localized links, no overflow, no browser
  exceptions/hydration errors and **zero axe WCAG 2/2.1 A/AA violations** with the
  dropdown open. Enter/Space, Escape/focus restoration, outside closing and mobile
  drawer interactions pass.
- **96 keyboard language switches:** mapped destinations and destination language
  are correct in both directions at every width.
- **96 JavaScript-disabled cases:** readable server content, correct language,
  no overflow, native dropdown expansion and working alternate-page links.
- **24 raw HTTP page cases:** commercial-host HTTP 200, server language, canonical,
  reciprocal alternates, crawlable links, no forced Accept-Language redirect or
  noindex response header; paired app-host redirects preserve paths/queries.
- **4 pricing parity cases:** identical plan IDs, prices, limits, order,
  availability and CTA destinations at every width, with correct translated
  disabled/weekly/daily scheduling labels.
- **2 pricing outage/retry cases:** no fallback cards during failure and all six
  catalog cards return after retry, for English and Vietnamese.

All 12 Vietnamese titles and descriptions are distinct. The sitemap/robots and
both local SVG responses also pass. Full-page screenshots and four additional
viewport captures are saved. Vietnamese Pricing mobile, Privacy mobile and Home
desktop dropdown screenshots were visually inspected.

The existing app browser regression passes **26 cases** for anonymous, verified
and unverified fixtures, with no page/hydration errors or normal-user admin
requests: [App evidence](verification-artifacts/milestone-7i1/app/app-browser-qa.json).

[Browser results](verification-artifacts/milestone-7i1/browser-qa.json),
[runner output](verification-artifacts/milestone-7i1/browser-qa.txt), screenshots,
[sitemap](verification-artifacts/milestone-7i1/sitemap.xml) and
[robots](verification-artifacts/milestone-7i1/robots.txt) are saved alongside the
gate logs. The first browser run's outside-click test targeted a legal-page H1
covered by the open dropdown. The runner now clicks a clear page margin; application
behavior was unaffected. An unused-variable lint warning in the runner was removed.
The final pricing-error stage initially matched both the catalog alert and Next's
route announcer. Its locator is now scoped to the pricing alert. Both error/retry
cases and raw HTTP checks were rerun successfully against the same unchanged build:
[Final pricing/HTTP recheck](verification-artifacts/milestone-7i1/pricing-recheck.txt).
The explicit `QA_RECHECK_PRICING=1` mode requires saved complete 96-case responsive,
no-JavaScript and keyboard matrices, 24 metadata records and four parity checks.
Default execution always runs the full matrix from scratch.

Reproduce from `frontend/` with Node 22.22.0 and the same build environment:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test
npm run lint
npm run typecheck
npm run format:check
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=production \
  NEXT_PUBLIC_SITE_URL=https://serpsaas.com \
  NEXT_PUBLIC_APP_URL=https://app.serpsaas.com npm run build
npm audit --omit=dev
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/
cp -R public .next/standalone/public
PORT=3013 HOSTNAME=127.0.0.1 node .next/standalone/server.js
# In another terminal, with local optional Playwright/axe and Chrome configured:
QA_BASE_URL=http://127.0.0.1:3013 \
  node --experimental-strip-types scripts/verify-full-public-localization-browser.mjs
```

`verify-localization-browser.mjs` delegates to the expanded runner; M7I historical
evidence remains unchanged.

## Production and Search Console status

**Not deployed.** No push, Cloud Run revision, production HTTP/www 301 check or
Search Console indexing request was performed. Current canonical redirect source
and infrastructure are preserved; local host checks do not verify production
load-balancer behavior.

After an authorized deployment, verify the five new real URLs return 200,
indexable server HTML, self-canonical, reciprocal alternates and `lang="vi"`.
Verify HTTP/www variants redirect 301 to the apex HTTPS URL preserving the full
Vietnamese path. Inspect the sitemap/robots, then request indexing once for each
new Vietnamese URL in Search Console. Monitor Country = Vietnam for queries,
pages, impressions, clicks, CTR and average position. No indexing or traffic result
is claimed here.
