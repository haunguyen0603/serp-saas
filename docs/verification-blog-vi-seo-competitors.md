# Vietnamese competitor-analysis article verification

Implemented and verified locally on **2026-10-21** (Asia/Saigon); production release
details are recorded below.

## Article and integration

- Editorial source: `docs/seo-blog-vi-theo-doi-doi-thu-codex.md` (preserved).
- Added exactly one article: `frontend/content/blog/vi/cach-theo-doi-thu-hang-doi-thu-seo.md`.
- Route: `/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo`.
- Canonical: `https://serpsaas.com/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo`.
- H1: `Cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP`.
- SEO title: `Cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP | SERP SaaS`.
- Description: `Hướng dẫn xác định đối thủ SEO từ kết quả Google, so sánh thứ hạng theo nhóm từ khóa và tìm cơ hội nội dung bằng dữ liệu SERP.`
- Both `publishedAt` and `updatedAt`: `2026-10-21`, the date of editing and production publication.
- `locale: vi`, `draft: false`, `featured: false`, author `SERP SaaS`.
- Category: `Phân tích đối thủ`; tags: `đối thủ SEO`, `phân tích SERP`, `thứ hạng Google`. The parser supports free-text categories; the shared Google-ranking tag allows contextual related-post discovery.

Inspected the content parser/frontmatter validation, Vietnamese and English static
routes, listing, related-post scoring, shared Markdown renderer/styles, metadata,
JSON-LD, explicit locale pairs, sitemap, robots and English RSS. Existing shared
behavior discovers the article without production code, styling or locale-map
changes. No existing article or unrelated metadata was overwritten.

The browser QA script compares the formatted article body with the editorial
source. The supplied text is preserved, with one added paragraph explicitly
clarifying user-owned projects and separate Desktop/Mobile projects. The source
H1 is not copied into Markdown; the shared template renders the only H1 and the
layout adds the title suffix exactly once.

The article retains illustrative-data labels, the distinction between business
and SERP competitors, search-intent grouping, repeated observations, content-gap
analysis, incomplete-check caveats and the different measurement semantics of
Google Search Console average position. It preserves stored-SERP analysis, Top 10
checked depth, unknown exact positions beyond that depth, one primary tracked site
and at most five competitors. These boundaries also match the current competitor
selection schema and analytics service's ownership/environment/snapshot filtering.
No keyword volumes, actual performance, testimonials or ranking guarantees added.

Editorial scope was compared with all five existing Vietnamese articles:

| Existing article                             | Existing focus                          | New article's distinct focus                      |
| -------------------------------------------- | --------------------------------------- | ------------------------------------------------- |
| `cong-cu-rank-tracker-la-gi`                 | Definition and tool evaluation          | Identifying and comparing SERP competitors        |
| `co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay` | Daily versus weekly cadence             | Competitor trends and content opportunities       |
| `cach-theo-doi-thu-hang-google`              | A project's ranking workflow            | Cross-domain comparison within query groups       |
| `cach-kiem-tra-thu-hang-tu-khoa`             | Checking a keyword's observed position  | Interpreting repeated competitor presence/absence |
| `serp-tracking-cho-agency`                   | Client project organization and reports | Practical competitor-analysis method              |

Titles and descriptions remain unique. Introductory context overlaps naturally;
the new article has a distinct primary educational intent. Actual search-query
cannibalization cannot be measured from source content alone and is unverified.

## Discovery, SEO and language behavior

Actual repository/runtime counts: **9 published articles, 0 drafts: 3 EN and 6 VI**
(previously 3 EN / 5 VI). The VI listing has six cards, with this article appearing
once. Each card retains its existing title/read-guide links. The sitemap contains
**27 unique public URLs** (previously 26), with exactly one entry for this article.
The article has three VI related posts and is discoverable in related posts on
the existing Rank Tracker definition guide.

Verified in server-rendered HTML and browser contexts:

- HTTP 200, `html lang="vi"`, one H1, exact description/title, self-canonical,
  matching Open Graph URL and `index, follow`.
- `BlogPosting` and `BreadcrumbList` with VI language, canonical URL and both
  dates `2026-10-21`; no unsupported FAQ/rating schema added.
- Both required in-body links retain their destinations and return HTTP 200:
  `/vi/blog/cong-cu-rank-tracker-la-gi` and `/vi/seo-rank-tracking-cho-agency`.
  All 13 distinct rendered Vietnamese link destinations return HTTP 200 locally.
- No English translation, hreflang alternate or VI RSS discovery invented.
  `/blog/cach-theo-doi-thu-hang-doi-thu-seo` returns HTTP 404. English RSS retains
  exactly three EN entries and excludes the new article.
- The existing unpaired language switch falls back to `/` for English and `/vi`
  for Vietnamese; the Home language round trip works with JS enabled/disabled.
- English language preferences do not redirect the VI article; app-host requests
  preserve the path/query in the existing 307 commercial-origin redirect.
- Robots remains unchanged and permits VI crawling. Production English routes,
  authentication, billing, pricing and locale mappings remain unchanged.

## Automated gates

| Check                                       | Final result                                                        |
| ------------------------------------------- | ------------------------------------------------------------------- |
| `npm run prebuild`                          | Passed: 9 published, 0 drafts                                       |
| `npm test`                                  | Passed: 36 files, 326 tests                                         |
| `npm run lint`                              | Passed                                                              |
| `npm run typecheck`                         | Passed                                                              |
| `npm run format:check`                      | Passed                                                              |
| `npm run build`                             | Passed; new route prerendered in standalone production output       |
| `npm audit --omit=dev`                      | Passed: 0 vulnerabilities                                           |
| `git diff --check`                          | Passed                                                              |
| Source/body fidelity                        | Passed after Markdown formatting and the documented added paragraph |
| New article browser matrix                  | Passed: 8 viewport/JavaScript cases                                 |
| English blog regression                     | Passed: 16 route/viewport cases                                     |
| Existing Rank Tracker definition regression | Passed: 8 viewport/JavaScript cases                                 |
| Existing daily-tracking guide regression    | Passed: 8 viewport/JavaScript cases                                 |
| Full public EN/VI regression                | Passed: 96 JS-on, 96 no-JS and 96 keyboard cases                    |

The full localization regression also passed 24 HTTP cases across all 12 existing
locale pairs, four synthetic pricing parity cases and two pricing error/retry
cases. It verified 27 unique sitemap URLs, with no browser exceptions or axe
violations in its 96 JavaScript-enabled cases. Pricing fixtures were intercepted
locally; these checks did not modify pricing or call a live backend.

Updated the expected VI listing/sitemap counts in existing unit/browser checks,
extended unpaired-page checks to this article, and added two article integration
tests for discovery, metadata, product boundaries, accessible tables and links.
The repeatable new browser script additionally validates editorial source fidelity.
That comparison belongs to repository QA rather than the unit suite so the frontend
unit tests still work in the existing Docker context containing only `frontend/`.

An initial build caught an unsupported Testing Library `exact` option in the new
test; it was removed, and the final build/typecheck/tests passed. The initial
new-article browser run timed out using animation-frame polling in a no-JS
context. The harness now polls keyboard scroll state from Node. The final run
passed all eight cases, including actual Tab/ArrowRight behavior with JS disabled.

## Browser and accessibility evidence

Tested against the local production standalone server at `http://127.0.0.1:3010`
with Node **22.22.0**, Chrome **155.0.8059.85**, Playwright **1.64.1** and
`@axe-core/playwright` **4.14.0**, using the existing optional external QA tools.
Backend/session requests were intercepted as anonymous local fixtures; no real
account, payment or SERP-provider operation was performed.

At **375, 768, 1024 and 1440 px**, with JavaScript enabled and disabled:

- All four tables render with 12 column headers and named focusable scroll regions.
  Every table is reachable using Tab in all eight cases; ArrowRight scrolls each
  table on mobile. Page-level horizontal overflow is absent.
- No page exceptions or hydration errors; server-rendered content and navigation
  remain usable with JS disabled.
- Zero axe WCAG 2 A/AA and WCAG 2.1 A/AA violations at all four JS-enabled widths.
  Axe is not run in no-JS contexts.
- Saved article and table viewport screenshots for all eight cases and full-page
  screenshots at all four JS-enabled widths. Visually inspected mobile/desktop
  headings, Vietnamese accents, body text and mobile no-JS table focus/scrolling.

Evidence:

- [New article QA JSON](verification-artifacts/blog-vi-seo-competitors/browser-qa.json)
- [Sitemap XML](verification-artifacts/blog-vi-seo-competitors/sitemap.xml)
- [Runtime dependency audit](verification-artifacts/blog-vi-seo-competitors/runtime-audit.json)
- Gate logs: [tests](verification-artifacts/blog-vi-seo-competitors/tests.txt),
  [build](verification-artifacts/blog-vi-seo-competitors/build.txt),
  [lint](verification-artifacts/blog-vi-seo-competitors/lint.txt),
  [format](verification-artifacts/blog-vi-seo-competitors/format.txt).
- [375 px article](verification-artifacts/blog-vi-seo-competitors/article-375.png)
- [375 px no-JS table](verification-artifacts/blog-vi-seo-competitors/article-tables-375-no-js.png)
- [768 px article](verification-artifacts/blog-vi-seo-competitors/article-768.png)
- [1024 px article](verification-artifacts/blog-vi-seo-competitors/article-1024.png)
- [1440 px article](verification-artifacts/blog-vi-seo-competitors/article-1440.png)
- [Full mobile article](verification-artifacts/blog-vi-seo-competitors/article-full-375.png)
- [English blog regression](verification-artifacts/blog-vi-seo-competitors/english-regression/browser-qa.json)
- [Definition guide regression](verification-artifacts/blog-vi-seo-competitors/definition-regression/browser-qa.json)
- [Daily guide regression](verification-artifacts/blog-vi-seo-competitors/daily-regression/browser-qa.json)
- [Public EN/VI regression](verification-artifacts/blog-vi-seo-competitors/localization-regression/browser-qa.json)

## Reproduction

From `frontend/`, use Node 22.22+ with
`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`, `NEXT_PUBLIC_APP_ENV=test`, and
site/app URL overrides unset for unit tests. Run `npm run prebuild`, `npm test`,
`npm run lint`, `npm run typecheck`, `npm run format:check` and
`npm audit --omit=dev`. Run `git diff --check` from the repository root.

For `npm run build`, set `NEXT_PUBLIC_SITE_URL=https://serpsaas.com` and
`NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`. Copy `public/*` and `.next/static/*`
into the matching standalone directories, then run `.next/standalone/server.js`
with `PORT=3010` and `HOSTNAME=127.0.0.1`.

Set `QA_BASE_URL=http://127.0.0.1:3010`, `QA_TOOLS_DIRECTORY` to the external
tools' `node_modules`, and `QA_CHROME_PATH` to Chrome. Use a separate
`QA_ARTIFACT_DIRECTORY` for each regression script:

```text
node scripts/verify-competitor-blog-browser.mjs
node scripts/verify-blog-browser.mjs
node scripts/verify-rank-tracker-blog-browser.mjs
node scripts/verify-daily-tracking-blog-browser.mjs
node --experimental-strip-types scripts/verify-full-public-localization-browser.mjs
```

The new browser script's default artifact directory is
`docs/verification-artifacts/blog-vi-seo-competitors`. It requires the original
editorial brief in the repository's `docs/` directory for its fidelity comparison.

## Production status and limits

**Deployed successfully at 15:18:52 on 2026-10-21 (Asia/Saigon).** After the user
explicitly authorized production deployment, commit
[`0d04f64`](https://github.com/haunguyen0603/serp-saas/commit/0d04f64286f9e2f1acc1354294faea7f98027de5)
was pushed to `main` with the existing remote history preserved. The
`serp-web-main` pipeline ran
[Cloud Build 24a59711](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/24a59711-56fc-470a-9355-8f64287372cf?project=833917440392),
which completed successfully at `2026-10-21T08:18:52Z`. The backend pipeline was
skipped by its file filter; no backend or infrastructure change was deployed.
The [live article](https://serpsaas.com/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo)
returned HTTP 200 after the release.

Production QA completed at `2026-10-21T08:19:48Z` (15:19:48 Asia/Saigon):

- Passed all eight viewport/JavaScript combinations at 375, 768, 1024 and 1440 px.
  No page exceptions, hydration errors or page-level horizontal overflow.
- Exact title/description, one H1, Vietnamese document language, self-canonical,
  `index, follow`, `BlogPosting` and `BreadcrumbList` with both dates `2026-10-21`.
- Six VI listing cards, the new article present once, three VI related guides,
  and discovery from the existing Rank Tracker guide.
- All 13 distinct linked VI URLs returned HTTP 200, including both editorial
  destinations. Sitemap contains 27 URLs and this article exactly once; English
  RSS retains three items and excludes the article.
- No invented English hreflang or article route; the untranslated EN URL returns 404. Unpaired language fallback and the Home round trip work with and without
  JavaScript. The app-host path/query redirect remains HTTP 307.
- All four tables are reachable with Tab in every case; mobile ArrowRight
  scrolling works with JavaScript enabled and disabled. Zero axe violations at
  all four JS-enabled widths. Inspected production mobile/desktop article and
  mobile no-JS table screenshots; accents, wrapping and focus are legible.

Production browser checks intercepted anonymous session-refresh requests. No real
account, payment or SERP-provider operation was performed.

Production evidence:

- [Cloud Build checks](verification-artifacts/blog-vi-seo-competitors/production/cloud-build-checks.json)
- [HTTP/browser QA](verification-artifacts/blog-vi-seo-competitors/production/browser-qa.json)
- [Sitemap](verification-artifacts/blog-vi-seo-competitors/production/sitemap.xml)
- [Mobile screenshot](verification-artifacts/blog-vi-seo-competitors/production/article-375.png)
- [Desktop screenshot](verification-artifacts/blog-vi-seo-competitors/production/article-1440.png)
- [Mobile no-JS table](verification-artifacts/blog-vi-seo-competitors/production/article-tables-375-no-js.png)
- [Repeatable production QA script](verification-artifacts/blog-vi-seo-competitors/production/verify-production.mjs)

To repeat production QA, run the saved script from `frontend/` with the same
`QA_TOOLS_DIRECTORY` and `QA_CHROME_PATH` used locally, and set
`QA_BASE_URL=https://serpsaas.com`. Its default artifact directory is the
production evidence directory above.

No indexing request was submitted. Google indexing, Search Console measurements,
traffic and ranking outcomes remain unverified.

Accessibility evidence covers automated axe, keyboard and the documented visual
checks; a complete assistive-technology audit was not performed. No live Google
Search Console measurements or competitor ranking data were used.

The standalone server logged five Next.js `NoFallbackError` messages during the
intentional missing-article probes (unknown/draft English slugs and the three
untranslated VI slugs). Those responses were verified as HTTP 404; published
article and internal-link checks returned HTTP 200. The local QA server was
stopped after verification.
