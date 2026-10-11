# Milestone 7I — Vietnamese SEO localization verification

Implementation and local verification: **2026-10-11**. Production deployment and Search Console actions have **not** been performed.

## Routes and explicit locale mapping

`frontend/src/lib/public-locales.ts` is the single explicit mapping used by the language switcher, metadata alternates and localization tests. No translated slug is inferred algorithmically.

| English                                | Vietnamese                                |
| -------------------------------------- | ----------------------------------------- |
| `/`                                    | `/vi`                                     |
| `/google-serp-rank-tracker`            | `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa`   |
| `/daily-serp-tracker`                  | `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` |
| `/serp-tracking-for-agencies`          | `/vi/seo-rank-tracking-cho-agency`        |
| `/blog`                                | `/vi/blog`                                |
| `/blog/how-to-track-google-rankings`   | `/vi/blog/cach-theo-doi-thu-hang-google`  |
| `/blog/how-to-monitor-keyword-ranking` | `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` |

All seven Vietnamese routes are prerendered and return HTTP 200 in the production standalone build. Every route has one H1. The first Vietnamese article explains building a consistent monitoring baseline and review process; the second explains checking a particular keyword, interpreting its status and URL, and comparing manual searches with tool observations.

## Layout, content and language switching

Existing English page routes now live under `frontend/src/app/(en)/`, with unchanged URLs. Vietnamese routes use `frontend/src/app/vi/`. Two root layouts reuse `RootDocument` and render the HTML language directly on the server: `en` for existing pages and `vi` for Vietnamese pages. Switching across roots performs a document navigation, which gives the destination its correct HTML language without a client mutation or request-header-dependent rendering. **31 moved English files remain byte-for-byte unchanged.** Sitemap and robots metadata files remain at the app root; Next requires root placement for robots discovery.

Commercial landing pages share `LandingPage`, with Vietnamese content in `vietnamese-content.ts`. Blog indexes, article layouts, Markdown rendering, cards, dates and CTAs are shared. Existing English Markdown remains in `content/blog/*.md`; Vietnamese Markdown lives in `content/blog/vi/*.md`, with validated `locale: vi` frontmatter. Validation checks each locale independently, rejects mismatched locales, retains duplicate-field/draft/date/image validation, and validates both locales before build. English listing, related posts and RSS retain their three English guides. Vietnamese listing and related posts contain only the two Vietnamese guides. Standalone content tracing includes Vietnamese Markdown.

PublicShell localizes Home, Pricing, account actions, navigation, footer labels and skip links. Pricing and legal/about pages remain English and use their existing URLs. Vietnamese Home, footer and Blog content link to Vietnamese commercial pages where equivalents exist.

The visible header **EN / VI** control uses crawlable links, language names, `lang`, `hreflang`, current-language indication and visible keyboard focus. It remains visible outside the drawer on mobile and works without JavaScript. Both targets are at least 44 × 44px in browser QA. Home switches `/` ↔ `/vi`; mapped pages switch to their paired route. Unmapped pages such as `/about`, `/pricing` and the English agency Blog guide fall back to the destination locale Home. No locale cookie, persistence, GeoIP, browser-language redirect or authentication dependency was added.

## Rendered titles and descriptions

Each Vietnamese route has unique title, description, OG title/description/URL and Twitter title/description/card metadata. The following values were collected from rendered standalone HTML:

| Vietnamese route                          | Rendered title                                                        | Meta description                                                                                                                                      |
| ----------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/vi`                                     | Theo dõi thứ hạng từ khóa Google dễ dàng \| SERP SaaS                 | Theo dõi vị trí từ khóa Google, phân tích biến động, so sánh đối thủ và tạo báo cáo SEO. Quản lý dự án Desktop và Mobile riêng biệt với SERP SaaS.    |
| `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa`   | Công cụ kiểm tra thứ hạng từ khóa Google \| SERP SaaS                 | Kiểm tra thứ hạng từ khóa Google, xem lịch sử, phân tích biến động và so sánh đối thủ với SERP SaaS. Theo dõi Desktop và Mobile riêng biệt.           |
| `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` | Theo dõi thứ hạng từ khóa hàng ngày \| SERP SaaS                      | Theo dõi biến động thứ hạng từ khóa Google theo lịch, xem lịch sử và kiểm tra các thay đổi đáng chú ý. Lịch hàng ngày hoặc hàng tuần tùy gói dịch vụ. |
| `/vi/seo-rank-tracking-cho-agency`        | Theo dõi thứ hạng từ khóa cho SEO Agency \| SERP SaaS                 | Quản lý nhiều dự án khách hàng, nhóm từ khóa, so sánh đối thủ và xuất báo cáo SEO trong cùng một tài khoản SERP SaaS dành cho người làm agency.       |
| `/vi/blog`                                | Kiến thức SEO & Theo dõi thứ hạng \| SERP SaaS                        | Hướng dẫn theo dõi thứ hạng Google, kiểm tra vị trí từ khóa và đọc biến động SEO tại Việt Nam với môi trường tìm kiếm nhất quán.                      |
| `/vi/blog/cach-theo-doi-thu-hang-google`  | Cách theo dõi thứ hạng Google cho một dự án SEO \| SERP SaaS          | Xây dựng bộ từ khóa, chọn môi trường Google tại Việt Nam và duy trì lịch sử thứ hạng để so sánh kết quả SEO qua các lần kiểm tra.                     |
| `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` | Cách kiểm tra thứ hạng từ khóa và đọc vị trí trên Google \| SERP SaaS | Kiểm tra thứ hạng từ khóa bằng tìm kiếm thủ công hoặc công cụ, đối chiếu URL và hiểu giới hạn Top 10 trước khi kết luận về vị trí trên Google.        |

Vietnamese canonical and OG URLs are `https://serpsaas.com` plus the exact Vietnamese path in the table. They self-canonicalize and never point at the English equivalent. Alternate origins (localhost, www, app and run.app) cannot change the public SEO origin. English Home retains its existing production root canonical behavior; Next serializes the root URL without a trailing slash, which resolves to `/`.

Each locale pair emits reciprocal `en`, `vi` and `x-default` alternates on both pages. `x-default` points to that pair's English URL. All seven Vietnamese pages emit `index, follow`; commercial-host HTTP responses have no `X-Robots-Tag: noindex`. Real local HTTP checks with commercial/app Host headers verify the existing app-host 307 redirects preserve Vietnamese paths and query strings. The existing app-host root still redirects to `/app`.

## Structured data, sitemap, robots and internal links

Vietnamese Home and commercial pages emit supported `WebPage`, `SoftwareApplication` and `BreadcrumbList` data with Vietnamese text and language. The Vietnamese Blog index emits `WebPage`; articles emit `BlogPosting` and localized `BreadcrumbList`. JSON-LD is escaped with the existing serializer. No ratings, reviews, customer counts, offers or FAQ rich results are invented.

The existing sitemap has **19 public URLs**: the previous 12 plus seven Vietnamese URLs. Articles use their actual update dates; no artificial modification dates are added to landing pages. Draft Vietnamese articles remain absent from static params, lookups and sitemap. Unknown or wrong-locale Blog slugs use the existing 404 behavior.

`robots.txt` explicitly allows `/vi`, preserves all app/admin/auth/API disallow rules, and retains `Sitemap: https://serpsaas.com/sitemap.xml`. Actual standalone responses are saved as [sitemap](verification-artifacts/milestone-7i/sitemap.xml) and [robots](verification-artifacts/milestone-7i/robots.txt).

Internal links verified:

- Vietnamese Home and shared Product footer → three Vietnamese commercial pages and `/vi/blog`.
- Vietnamese Blog index → only Vietnamese articles, plus the Vietnamese rank-tracker CTA.
- Both Vietnamese articles → contextual Vietnamese rank-tracker/daily-tracker links and each other's guide.
- Baseline article → Vietnamese agency page; landing pages → Vietnamese guides and related commercial pages.
- Vietnamese page breadcrumbs → `/vi`; article breadcrumbs → `/vi/blog`.
- Registration/login/account actions → existing configured app-domain routes; Pricing → existing commercial `/pricing`.

## Product claims and scope

Copy uses natural Vietnamese and explains Vietnam/tiếng Việt, Google search context, and separate Desktop/Mobile Projects. Current measurements cover **Top 10**. A complete check without a match does not supply an exact position beyond that depth; incomplete observations and failed runs do not prove absence. No Top 100 or real-time promise appears.

Daily or weekly scheduling depends on the Plan. Desktop and Mobile retain separate Plans and limits; prices and numeric entitlements are not copied into Vietnamese landing content. Agency copy describes multiple client Projects in one user-owned account and existing CSV/PDF reports. It does not claim organizations, team permissions or client portals. Scheduled report delivery, where configured, sends to the account's own verified email.

Backend, auth emails, database, billing, provider routing, ranking execution, Cloud Run architecture and load-balancer configuration are unchanged. The English authenticated application is not localized.

## Automated verification

| Check                  | Result                                                               | Evidence                                                        |
| ---------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------- |
| `npm test`             | 253 passed, 30 files                                                 | [tests](verification-artifacts/milestone-7i/tests.txt)          |
| `npm run lint`         | Pass                                                                 | [lint](verification-artifacts/milestone-7i/lint.txt)            |
| `npm run typecheck`    | Pass                                                                 | [typecheck](verification-artifacts/milestone-7i/typecheck.txt)  |
| `npm run format:check` | Pass                                                                 | [format](verification-artifacts/milestone-7i/format-check.txt)  |
| `npm run build`        | Pass; 44 static pages generated, 5 published Blog articles validated | [build](verification-artifacts/milestone-7i/build.txt)          |
| `npm audit --omit=dev` | Exit 0; 0 runtime vulnerabilities, including 0 high/critical         | [audit](verification-artifacts/milestone-7i/runtime-audit.json) |
| `git diff --check`     | Pass                                                                 | Local Git check                                                 |

New tests cover locale mapping/fallbacks, both Home controls, localized mobile navigation, Vietnamese page content, metadata/canonical/reciprocal alternates, HTML-language declarations, Blog isolation/drafts/validation/404s, supported structured data, internal links, sitemap/robots, indexability and host redirects. Existing English metadata, Blog and authenticated feature suites pass.

Node **22.22.0**, npm **10.2.4**, Next **16.3.8**. No dependency or lockfile changes. The temporary Node distribution uses the system npm entrypoint at `/usr/local/lib/node_modules/npm/bin/npm-cli.js`. The first typecheck encountered stale generated `.next` types after route moves; those generated type directories were removed and regenerated by the production build, then standalone typecheck passed. No remote CI or Docker build was run.

## Browser QA and accessibility

QA ran at `http://127.0.0.1:3012` against the production standalone build, at **375, 768, 1024 and 1440px**. This is local validation, not a production test.

- **32 browser cases**: English Home plus all seven Vietnamese pages at four widths. HTTP 200, one visible H1, correct HTML language/canonical/hreflang/OG/Twitter metadata, supported JSON-LD, no horizontal overflow, zero browser exceptions/hydration errors and zero axe WCAG A/AA violations.
- **32 JavaScript-disabled cases**: readable server-rendered content, correct language, usable Home language switching and no horizontal overflow at each width.
- **34 keyboard language-switch cases**: 32 mapped-page cases and two `/about` fallback cases (375/1440). Destination language and URL are checked. Mobile Home menus also pass Enter/Escape and focus restoration.
- **14 raw HTTP page checks**: seven reciprocal pairs checked for language, alternates, indexability, no forced Accept-Language redirects and the existing app-host redirect behavior. Sitemap and robots return 200.
- **26 existing app browser regression cases**: anonymous, verified and unverified fixtures pass, with no page/hydration errors or normal-user admin API requests. [App regression evidence](verification-artifacts/milestone-7i/app/app-browser-qa.json).

[Browser evidence](verification-artifacts/milestone-7i/browser-qa.json), [runner output](verification-artifacts/milestone-7i/browser-qa.txt) and all 32 screenshots are saved beside the results. Vietnamese Home mobile/desktop and the mobile keyword-checking article screenshots were visually inspected. QA caught an existing English Home dark-card eyebrow contrast issue; its text color is corrected to `#b5c6ff`, and the full Home axe check passes.

The QA script uses optional external Playwright and axe installations, without adding frontend dependencies. External public navigation is redirected to the corresponding localhost path by test interception; session restoration receives an anonymous local fixture. No real account/backend mutation, provider call or production request occurs. Raw HTTP uses `node:http` to preserve Host headers; Node fetch did not preserve the intended app Host during the initial runner check. Raw HTML alternate checks accept React's `hrefLang` capitalization, while browser DOM checks verify the actual hreflang values. These runner corrections do not change application behavior.

Reproduce from `frontend/` with Node 22.22.0:

```bash
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
PORT=3012 HOSTNAME=127.0.0.1 node .next/standalone/server.js
# In another terminal; point QA_TOOLS_DIRECTORY / QA_CHROME_PATH at your local tools:
QA_BASE_URL=http://127.0.0.1:3012 node --experimental-strip-types scripts/verify-localization-browser.mjs
```

## Production and Search Console status

**Not deployed.** No push, release, Cloud Run revision, DNS/load-balancer change, production HTTP/www 301 verification or Search Console action was performed. Existing apex/www HTTPS routing is preserved in source and infrastructure; its current production behavior has not been reverified.

After an authorized release, verify each real Vietnamese URL and the production sitemap/robots, then verify HTTP/www variants preserve `/vi` paths in their 301 destination. In Search Console, inspect the initial Vietnamese pages, run Live Test and request indexing once. Monitor Performance with Country = Vietnam for queries, pages, impressions, clicks, CTR and average position. Indexing and traffic require later observation; no outcome is claimed here.
