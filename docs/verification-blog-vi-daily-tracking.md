# Vietnamese daily tracking decision guide verification

Implemented and verified locally on **2026-10-19** (Asia/Saigon).

## Sources and publication metadata

- Editorial source: `docs/seo-blog-theo-doi-thu-hang-hang-ngay-codex.md`.
- Added exactly one article:
  `frontend/content/blog/vi/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay.md`.
- Route: `/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay`.
- Self-canonical:
  `https://serpsaas.com/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay`.
- SEO title: `Có nên theo dõi thứ hạng từ khóa Google hàng ngày? | SERP SaaS`.
  Frontmatter omits the brand suffix because the existing document title template
  adds it. The shared article template supplies the single H1 without the suffix.
- Exact description: `Khi nào nên kiểm tra thứ hạng từ khóa hàng ngày, khi nào theo dõi hàng tuần là đủ? Tìm hiểu cách đọc biến động ranking và chọn lịch kiểm tra SEO.`
- `locale: vi`, `draft: false`, `featured: false`, author `SERP SaaS`.
- Both `publishedAt` and `updatedAt`: `2026-10-19`; no backdating.
- Existing category `Theo dõi thứ hạng`; existing tags `rank tracker`,
  `thứ hạng Google`, `quy trình SEO` support related-post discovery.
- The body matches the supplied article after removing its H1 and applying
  Prettier Markdown formatting. A formatted source/body comparison passed.
- Preserved the decision-guide focus, illustrative-data disclaimer, Top 10 depth,
  unknown positions beyond Top 10, incomplete-check caveat, separate Desktop/Mobile
  projects and plan-dependent daily/weekly schedules. No real-time claim added.

The existing content pipeline supplies listing cards, related posts, static
routes, metadata and sitemap entries. No production renderer, locale mappings,
styles, pricing, billing, authentication, payment or existing route changed.

Updated validation sources:

- `frontend/src/features/marketing/vietnamese-localization.test.tsx`: five VI
  articles; run unpaired-route assertions for both original and new guides.
- `frontend/src/features/marketing/full-public-localization.test.tsx` and
  `frontend/src/proxy.test.ts`: 26 unique sitemap URLs including the new post.
- `frontend/scripts/verify-daily-tracking-blog-browser.mjs`: repeatable local
  article verification, screenshots and sitemap evidence.
- `frontend/scripts/verify-rank-tracker-blog-browser.mjs` and
  `frontend/scripts/verify-full-public-localization-browser.mjs`: five VI articles.

## Automated checks

| Check                                  | Result                                                           |
| -------------------------------------- | ---------------------------------------------------------------- |
| Content validation / prebuild          | Passed: 8 published, 0 drafts (3 EN, 5 VI)                       |
| `npm test`                             | Passed: 35 files, 322 tests, including sitemap/blog/localization |
| `npm run lint`                         | Passed                                                           |
| `npm run typecheck`                    | Passed                                                           |
| `npm run format:check`                 | Passed                                                           |
| `npm run build`                        | Passed; new route prerendered in production output               |
| Editorial source comparison            | Passed after Markdown formatting                                 |
| New article browser checks             | Passed: 8 viewport/JavaScript cases                              |
| English blog browser regression        | Passed: 16 route/viewport cases                                  |
| Existing Rank Tracker guide regression | Passed: 8 viewport/JavaScript cases                              |
| Full public EN/VI browser regression   | Passed: 96 browser, 96 no-JS, 96 keyboard cases                  |

Full localization regression also passed **24 HTTP cases**, **4 synthetic pricing
parity cases** and **2 error/retry cases**, with 26 unique sitemap URLs and all
12 existing locale pairs. The pricing checks use intercepted synthetic fixtures.
The final matrix completed with zero accessibility violations and page exceptions.

The first unit-test invocation supplied separate production site/app origins,
which caused existing tests expecting relative links to fail. The final successful
unit run used the normal test configuration with those origin overrides unset.
The production build and browser checks use separate commercial/app origins.
Updated the existing proxy sitemap expectation to include the new article.

## Browser and SEO evidence

Ran against a local **production standalone build** at `http://127.0.0.1:3010`
using Node 22.22.0 and Chrome 155.0.8059.84, with the existing optional external
Playwright/axe tools. Browser requests to external services were intercepted;
no live account, backend, payment or SERP-provider operation was performed.

The new article passed at **375, 768, 1024 and 1440 px**, with JavaScript both
enabled and disabled:

- HTTP 200, `lang="vi"`, one H1, exact title/description, self-canonical,
  matching Open Graph URL and `index, follow`.
- `BlogPosting` and `BreadcrumbList` with correct language, dates and canonical.
- No fabricated English route, hreflang alternate or English RSS discovery.
  The nonexistent `/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay` returns 404.
- Both GFM tables, five column headers, named keyboard-focusable scroll regions
  and keyboard table scrolling on mobile; no page-level horizontal overflow.
- Zero axe WCAG 2 A/AA and WCAG 2.1 A/AA violations at all four widths;
  no page exceptions or hydration errors in all eight cases.
- Five Vietnamese listing cards, including this article; three related guides
  on the article; discovery of the new article from the existing Rank Tracker guide.
- All 13 distinct Vietnamese URLs linked from the rendered page return HTTP 200,
  including `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` and
  `/vi/blog/cong-cu-rank-tracker-la-gi`.
- Language selection preserves the unpaired-page fallback: English goes to `/`,
  Vietnamese to `/vi`; the Home round trip works with and without JavaScript.
- English language preferences do not redirect the VI article. App-host requests
  keep the path/query in the existing 307 redirect to the commercial origin.
- Exactly one sitemap entry for this article; English RSS retains three entries
  and excludes the article; robots allows Vietnamese pages.

Visually inspected mobile article/table and desktop article screenshots:
Vietnamese accents, title wrapping, body width and visible table focus are legible.
The inherited table containers scroll horizontally on narrow screens.

Evidence:

- [Article QA JSON](verification-artifacts/blog-vi-daily-tracking/browser-qa.json)
- [Sitemap XML](verification-artifacts/blog-vi-daily-tracking/sitemap.xml)
- [375 px article](verification-artifacts/blog-vi-daily-tracking/article-375.png)
- [375 px table](verification-artifacts/blog-vi-daily-tracking/article-tables-375.png)
- [768 px article](verification-artifacts/blog-vi-daily-tracking/article-768.png)
- [1024 px article](verification-artifacts/blog-vi-daily-tracking/article-1024.png)
- [1440 px article](verification-artifacts/blog-vi-daily-tracking/article-1440.png)
- [English blog regression](verification-artifacts/blog-vi-daily-tracking/english-regression/browser-qa.json)
- [Existing guide regression](verification-artifacts/blog-vi-daily-tracking/definition-regression/browser-qa.json)
- [Full localization regression](verification-artifacts/blog-vi-daily-tracking/localization-regression/browser-qa.json)

## Reproduction

Use Node 22.22+ from `frontend/`. Run unit tests with
`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`, `NEXT_PUBLIC_APP_ENV=test`, and
`NEXT_PUBLIC_SITE_URL` / `NEXT_PUBLIC_APP_URL` unset. Run `npm test`,
`npm run lint`, `npm run typecheck` and `npm run format:check`.

For `npm run build`, additionally set `NEXT_PUBLIC_SITE_URL=https://serpsaas.com`
and `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`. Copy `public` and `.next/static`
into the corresponding standalone directories. Start `.next/standalone/server.js`
with `PORT=3010`, `HOSTNAME=127.0.0.1` and the same public environment.

Set `QA_BASE_URL=http://127.0.0.1:3010`, `QA_TOOLS_DIRECTORY` to the optional QA
tools' `node_modules`, and `QA_CHROME_PATH` to Chrome. Run:

```text
node scripts/verify-daily-tracking-blog-browser.mjs
node scripts/verify-blog-browser.mjs
node scripts/verify-rank-tracker-blog-browser.mjs
node --experimental-strip-types scripts/verify-full-public-localization-browser.mjs
```

Use a distinct `QA_ARTIFACT_DIRECTORY` for each regression script to preserve
earlier evidence.

## Deployment status and limitations

**Not deployed.** The article is published in repository content (`draft: false`)
and verified in the local production build only. No remote publication, merge,
hosting or production configuration change was performed.

Live URL availability, Google indexing, Search Console and traffic have not been
verified. Accessibility results cover automated axe checks and the documented
keyboard/visual checks; they do not claim a complete assistive-technology audit.

The standalone server logged four Next.js `NoFallbackError` messages during the
four intentional missing-article probes (unknown slug, draft slug and the two
untranslated English slugs). All four responses were verified as HTTP 404;
published article and internal-link checks returned HTTP 200.

## Subsequent release authorization

On **2026-10-19**, the user authorized a direct push to GitHub `main`. The
repository's existing frontend pipeline automatically builds and deploys after
a main-branch push. Production deployment and live validation for this article
have not yet been confirmed; the results above describe the local production build.
