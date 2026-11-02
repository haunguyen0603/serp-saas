# Verification: Vietnamese “SERP là gì?” article

Integrated and tested locally on **2026-11-02 (Asia/Saigon)**. No production
publication, push, merge, deployment or indexing request was performed.

## Implementation and exact frontmatter

Added exactly one article at `frontend/content/blog/vi/serp-la-gi.md`, using the
existing Markdown parser, Vietnamese static article route, shared article
template, Blog listing, related-post selection and sitemap.

```yaml
locale: vi
title: SERP là gì? Các thành phần của trang kết quả tìm kiếm Google và vai trò trong SEO
seoTitle: SERP là gì? Các thành phần SERP Google và vai trò SEO
slug: serp-la-gi
description: SERP là gì? Tìm hiểu kết quả tìm kiếm tự nhiên, quảng cáo, Featured Snippet, Local Pack và cách phân tích SERP để tối ưu SEO.
publishedAt: 2026-11-02
updatedAt: 2026-11-02
author: SERP SaaS
category: Kiến thức SEO
tags: [SERP, Google Search, kiến thức SEO]
featured: false
draft: false
```

The dates are the authorized local integration date, not a claim of live
publication. If release occurs on a later date, reconcile both dates and the new
article's date assertions before deployment.

The parser previously supported only one title for both the H1 and metadata.
Added optional, validated `seoTitle` (a nonempty string of at most 140 characters)
and uniqueness checking against other effective SEO titles. Metadata uses
`seoTitle ?? title`; visible headings and article schema keep `title`. The shared
layout still appends ` | SERP SaaS` once, giving the exact requested final title:
`SERP là gì? Các thành phần SERP Google và vai trò SEO | SERP SaaS`.
Existing articles omit the optional field and retain their metadata.

Changed production sources:

- `frontend/content/blog/vi/serp-la-gi.md`
- `frontend/src/features/blog/content.ts`
- `frontend/src/features/blog/seo.ts`

Changed verification sources:

- `frontend/src/features/blog/serp-article.test.tsx`: article discovery, distinct
  H1/SEO title, schema, Vietnamese-only behavior, tables, links and product scope.
- `frontend/src/features/blog/blog.test.tsx`: duplicate effective SEO-title
  rejection, including collisions with an article that has no override.
- `frontend/src/features/marketing/vietnamese-localization.test.tsx`: seven VI
  articles instead of six.
- `frontend/src/features/marketing/full-public-localization.test.tsx`: 28 sitemap
  entries instead of 27.
- `frontend/src/proxy.test.ts`: add the new article to the explicit sitemap list.
- `frontend/scripts/verify-serp-blog-browser.mjs`: repeatable local browser/SSR QA.
- `frontend/scripts/verify-competitor-blog-browser.mjs`,
  `verify-rank-tracker-blog-browser.mjs`, `verify-daily-tracking-blog-browser.mjs`
  and `verify-full-public-localization-browser.mjs`: update only affected current
  article/listing/sitemap counts.
- This report and `docs/verification-artifacts/blog-vi-serp-la-gi/`.

The user-provided brief `docs/seo-blog-vi-serp-la-gi-codex.md` was already
untracked when work began and was preserved. No existing article, URL, locale
registry, canonical rule, pricing, billing, SePay, auth, Ranking Alerts, Cloud
Tasks, backend or infrastructure source was changed.

## Editorial intent, fidelity and product boundaries

The article explains the search results environment: result types, query/context
variation, interpretation and a short five-step analysis method. The existing
Rank Tracker guide defines/evaluates measurement tools; the keyword-checking
guide explains practical checking; the competitor guide explains cross-domain
analysis. The new article links to those guides without replacing their intent
or adding an alternative SaaS walkthrough. No duplicate definition article or
equivalent slug existed in the current catalog. Search-query cannibalization
cannot be measured from repository content alone.

The supplied body is preserved. Changes to the body are limited to Markdown
table formatting. The H1 is supplied by the shared template. QA compares the
entire formatted Markdown body with the brief, then records actual SSR headings,
table cells and anchors in [source-render.json](verification-artifacts/blog-vi-serp-la-gi/source-render.json).
The article has two tables and six column headers, without invented screenshots
or image assets. See [server-rendered HTML](verification-artifacts/blog-vi-serp-la-gi/article-ssr.html).

Product review confirmed the text describes Google **organic Top 10**, completed
stored observations, separate Desktop/Mobile projects, and daily/weekly schedules
subject to plan entitlements. It does not claim paid-ad, map/Local Pack, AI-answer,
Top 100, instant-live or search-volume monitoring. A domain missing from checked
Top 10 has no inferred exact position outside that depth. It distinguishes
observed ranking from aggregated Search Console average position. The supplied
example is explicitly illustrative; there are no fabricated measurements,
testimonials, traffic figures, guarantees or backlink claims. The text makes no
organization/workspace-sharing claim; project/data ownership remains per user.
Read-only checks of the current rank-check, SERP parser, project ownership and
schedule-entitlement services agree with these boundaries.

Verified primary references on the integration date:

- [Google Visual Elements Gallery](https://developers.google.com/search/docs/appearance/visual-elements-gallery):
  visual result types and context-dependent appearance.
- [How Google Search Works](https://developers.google.com/search/docs/fundamentals/how-search-works):
  relevance signals and query-dependent search features.
- [Featured Snippets](https://developers.google.com/search/docs/appearance/featured-snippets):
  Google decides eligibility; markup does not force a featured snippet.
- [Search Console impressions, position and clicks](https://support.google.com/webmasters/answer/7042828):
  aggregate position differs from a single manual observation.

The first three references remain crawlable article links. The fourth was used
to verify the supplied Search Console distinction; no extra prose was inserted.

## Discovery, SEO and regression results

Actual counts: **10 published articles, zero drafts: 3 EN and 7 VI**. Before this
change there were 9 articles (3 EN / 6 VI) and 27 sitemap URLs. The final sitemap
has **28 unique URLs**, including this article exactly once. The VI Blog has seven
cards, with the new article once. Three Vietnamese related articles render; the
existing keyword-checking guide also discovers this article through the existing
shared `SERP` tag. Navigation remains the normal Vietnamese Blog navigation.

Verified HTTP and server-rendered/browser metadata:

- HTTP 200 at `/vi/blog/serp-la-gi`; `html lang="vi"`; one exact H1; exact unique
  SEO title/description; `index, follow`; no `X-Robots-Tag` blocking indexing.
- Canonical and Open Graph URL:
  `https://serpsaas.com/vi/blog/serp-la-gi`.
- `BlogPosting` and `BreadcrumbList` retain the correct canonical, language,
  headline, author and integration dates. No FAQ/rating schema was invented.
- No article hreflang alternates or VI RSS discovery were added. The untranslated
  `/blog/serp-la-gi` returns 404. English RSS still contains three EN entries and
  excludes this article. Robots permits the VI route.
- Unpaired language switching falls back to `/` and `/vi`; the language round
  trip works with JS on/off. English language preferences do not redirect the
  VI URL. App-host requests preserve path/query in the existing 307 redirect.
- All distinct rendered VI link destinations return HTTP 200 locally. Each of
  the four required destinations occurs once in the article body; the existing
  template CTA remains unchanged.

[SSR inventory](verification-artifacts/blog-vi-serp-la-gi/ssr-inventory.json)
checks every final sitemap URL, with 28 unique titles and descriptions. Compared
with the previously verified **2026-11-01 local baseline**, all **27 existing
pages** retain their exact title, description, H1, language, canonical, hreflang,
structured data, robots and article prose. Related-post cards/listings may include
the newly discoverable article as designed. This is local regression evidence,
not a production crawl.

## Test matrix and browser evidence

The production build and automated frontend gates ran in repository-standard
Linux Docker with Node **22.22.0**, npm **10.9.4**, Next **16.4.3** and the unchanged
lockfile. The image runs only on `127.0.0.1:3014`; there is no live backend.
Browser QA uses Windows Chrome **156.0.8078.74**, Playwright **1.58.2** and
`@axe-core/playwright` **4.11.1**, from the already available external QA tools.
Anonymous-session calls and public-pricing fixtures are intercepted locally.

| Check                                        | Result                                                    |
| -------------------------------------------- | --------------------------------------------------------- |
| `npm run prebuild`                           | PASS: 10 published, zero drafts                           |
| `npm test`                                   | PASS: 38 files, 349 tests                                 |
| `npm run lint`                               | PASS                                                      |
| `npm run typecheck`                          | PASS                                                      |
| `npm run format:check`                       | PASS                                                      |
| `npm run build` via production Docker target | PASS; new VI route prerendered                            |
| `npm audit --omit=dev --json`                | PASS: zero vulnerabilities                                |
| Source/body fidelity and SSR inventory       | PASS: supplied body preserved; all 28 public URLs checked |
| New article: 375/768/1024/1440 px, JS on/off | PASS: eight cases                                         |
| Existing competitor article: same matrix     | PASS: eight cases                                         |
| Existing Rank Tracker article: same matrix   | PASS: eight cases                                         |
| Existing daily-tracking article: same matrix | PASS: eight cases                                         |
| Full EN/VI paired public-page regression     | PASS: 96 JS-on, 96 no-JS and 96 keyboard cases            |
| `git diff --check`                           | PASS                                                      |

In all eight new-article cases: no whole-page horizontal overflow, uncaught page
errors, hydration errors or unexpected HTTP errors. Both named table scroll
regions are reachable using Tab; ArrowRight scrolls each table at 375 px with JS
enabled and disabled. The text, tables and navigation are server-rendered and
remain usable without JS. Axe reports **zero WCAG 2 A/AA and WCAG 2.1 A/AA
violations** at all four JS-enabled widths; axe is not run with JS disabled.

The full paired regression also passed 24 HTTP cases across all 12 EN/VI pairs,
four synthetic pricing-parity cases and two pricing-error/retry cases. It found
zero axe violations in its 96 JS-enabled cases. Together with the four separate
article matrices, browser coverage includes all 28 public sitemap pages. The
three existing unpaired VI guides each passed eight JS-on/off cases.

Visually inspected the 375 px and 1440 px article screenshots and the focused
375 px no-JS table screenshot: Vietnamese accents, headline wrapping, reading
width and visible keyboard focus are legible. This covers automated, keyboard
and documented visual checks; it is not a complete assistive-technology audit.

Evidence:

- [Linux frontend gates](verification-artifacts/blog-vi-serp-la-gi/linux-checks.txt),
  [production build](verification-artifacts/blog-vi-serp-la-gi/build.txt),
  [runtime audit](verification-artifacts/blog-vi-serp-la-gi/runtime-audit.json).
- [Final QA-script lint/format](verification-artifacts/blog-vi-serp-la-gi/final-qa-script-checks.txt),
  [runtime identity](verification-artifacts/blog-vi-serp-la-gi/runtime.json),
  [production-source hashes](verification-artifacts/blog-vi-serp-la-gi/source-manifest.json).
- [New article browser report](verification-artifacts/blog-vi-serp-la-gi/browser-qa.json),
  [sitemap](verification-artifacts/blog-vi-serp-la-gi/sitemap.xml),
  [SSR regression log](verification-artifacts/blog-vi-serp-la-gi/ssr.txt).
- [375 px article](verification-artifacts/blog-vi-serp-la-gi/article-375.png),
  [768 px article](verification-artifacts/blog-vi-serp-la-gi/article-768.png),
  [1024 px article](verification-artifacts/blog-vi-serp-la-gi/article-1024.png),
  [1440 px article](verification-artifacts/blog-vi-serp-la-gi/article-1440.png),
  [375 px no-JS table](verification-artifacts/blog-vi-serp-la-gi/article-tables-375-no-js.png).
- [Competitor regression](verification-artifacts/blog-vi-serp-la-gi/competitor-regression/browser-qa.json),
  [Rank Tracker regression](verification-artifacts/blog-vi-serp-la-gi/definition-regression/browser-qa.json),
  [daily guide regression](verification-artifacts/blog-vi-serp-la-gi/daily-regression/browser-qa.json).
- [Public EN/VI browser regression](verification-artifacts/blog-vi-serp-la-gi/localization-regression/browser-qa.json),
  [public regression log](verification-artifacts/blog-vi-serp-la-gi/localization-browser.txt).

The first host test run caught the old explicit sitemap list in `proxy.test.ts`;
its sole failure is retained in `tests.txt`. Adding this article to the list fixed
that failure; the final complete Linux suite above passed. Docker Desktop was
started for local Linux verification; no dependencies or system components were
installed. Historical evidence from earlier tasks was not overwritten.

## Reproduction and readiness

From the repository root, build the existing
`infrastructure/docker/frontend.Dockerfile` production target with the current
frontend contents, excluding host `node_modules` and `.next`. Use build args:
`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`,
`NEXT_PUBLIC_APP_ENV=production`,
`NEXT_PUBLIC_SITE_URL=https://serpsaas.com`, and
`NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`.
Run the resulting standalone image with `-p 127.0.0.1:3014:3000`.

For frontend checks, use Node 22.22+ and `npm ci` in the Linux development target,
then run the gates in the matrix. Tests use `NEXT_PUBLIC_APP_ENV=test`, local API
URL and no site/app URL overrides.

From `frontend/`, set `QA_BASE_URL=http://127.0.0.1:3014`,
`QA_TOOLS_DIRECTORY` to the optional external tools' `node_modules` and
`QA_CHROME_PATH` to Chrome. Use separate `QA_ARTIFACT_DIRECTORY` values for
regression runs:

```text
node scripts/verify-serp-blog-browser.mjs
node scripts/verify-competitor-blog-browser.mjs
node scripts/verify-rank-tracker-blog-browser.mjs
node scripts/verify-daily-tracking-blog-browser.mjs
node --experimental-strip-types scripts/verify-full-public-localization-browser.mjs
```

The new article script requires the original brief for fidelity comparison.
The separate saved `verify-ssr.mjs` evidence script checks all public SSR URLs
against the existing local 2026-11-01 baseline.

**Readiness: ready for review and an explicitly authorized release.** All
required local gates passed. The two task-labeled local QA containers were
removed after evidence capture; the built image remains available. Production
availability, indexing, Search Console metrics, traffic and live rankings are
unverified. A release on a different date requires reconciling publication dates
and the corresponding assertions before deployment.
