# Vietnamese Rank Tracker article verification

Implemented and verified locally on **2026-10-17** (Asia/Saigon).

## Implementation

- Added exactly one published Vietnamese Markdown post:
  `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`.
- Route: `/vi/blog/cong-cu-rank-tracker-la-gi`.
- Canonical: `https://serpsaas.com/vi/blog/cong-cu-rank-tracker-la-gi`.
- Used the existing frontmatter schema: `locale`, `title`, `slug`, `description`,
  `publishedAt`, `updatedAt`, `author`, `category`, `tags`, `featured`, `draft`.
  Both dates are `2026-10-17`; `draft: false`, `featured: false`.
- Preserved the editorial article, apart from removing its source H1 (the shared
  template supplies it) and formatting Markdown table spacing. The article
  explains the definition and comparison with Google Search Console separately
  from the existing operational guides and commercial landing page.
- Retained the Top 10 checked-depth caveat, unknown position beyond checked depth,
  illustrative data disclosure, Desktop/Mobile distinction and plan-dependent
  daily/weekly schedules. No real-time or Top 100 coverage promise was added.
- Reused shared rendering, styles, metadata, structured data, sitemap, related
  posts and language routing. No new locale pair or English translation was added.
  The root title template appends `| SERP SaaS` once.
- Updated existing content-count and sitemap expectations. Added a unit regression
  for an unpaired Vietnamese route and a repeatable local browser QA script at
  `frontend/scripts/verify-rank-tracker-blog-browser.mjs`.

Browser accessibility checks found existing shared accessible names that omitted
their visible labels. The language trigger now includes the current language in
its accessible name; blog card links include the full visible “Đọc hướng dẫn” /
“Read guide” text before the article title. Only these labels and their validation
changed; styling and language destinations retain the existing behavior.

## Automated validation

| Check                              | Final result                                           |
| ---------------------------------- | ------------------------------------------------------ |
| `npm ci --no-audit --no-fund`      | Passed; repository dependency versions retained        |
| `npm run prebuild`                 | Passed: 7 published articles, 0 drafts (3 EN, 4 VI)    |
| `npm test`                         | Passed: 35 test files, 320 tests                       |
| `npm run lint`                     | Passed                                                 |
| `npm run typecheck`                | Passed                                                 |
| `npm run format:check`             | Passed                                                 |
| `npm run build`                    | Passed, including the new prerendered Vietnamese route |
| Editorial prose comparison         | Matches the supplied source                            |
| New article browser QA             | Passed: 8 viewport/JavaScript combinations             |
| Existing `verify-blog-browser.mjs` | Passed: 16 route/viewport cases                        |

The existing `verify-full-public-localization-browser.mjs` also passed: **96 browser
cases, 96 no-JavaScript cases, 96 keyboard switches, 24 HTTP cases, 4 pricing-parity
cases and 2 retry cases**. This includes its four-width accessibility matrix,
paired-route hreflang checks and synthetic pricing checks. Its sitemap assertions
include the additional unpaired article: 25 unique URLs and all 12 locale pairs.
See the [full EN/VI regression evidence](verification-artifacts/blog-vi-rank-tracker/localization-regression/browser-qa.json).

The first test/build attempts lacked the project's required public API/environment
configuration. The final successful runs supplied local test configuration. The
initial browser run caught the shared accessible-name issues described above;
the final article and English blog runs passed after those corrections.

## Browser evidence

Ran against a local **production standalone build** at `http://127.0.0.1:3010`,
using Node **22.22.0**, Chrome **155.0.8059.84**, Playwright **1.64.1** and axe
**4.14.0**. Optional QA packages were installed outside the repository. API calls
were intercepted; no real backend, account, payment or SERP provider was used.

The new article script verified:

- 375, 768, 1024 and 1440 px, with JavaScript both enabled and disabled.
- HTTP 200, `lang="vi"`, a single H1, the exact requested SEO title and description,
  self-canonical, matching Open Graph URL and `index, follow`.
- `BlogPosting` and `BreadcrumbList`, correct language, canonical and dates.
- No fabricated hreflang alternate or RSS discovery link for the unpaired route.
- Both GFM tables, five column headers, named keyboard-focusable table regions,
  keyboard scrolling on mobile, and no page-level horizontal overflow.
- Zero axe WCAG 2 A/AA and WCAG 2.1 A/AA violations on the article at all four widths;
  zero page exceptions or hydration errors in all eight cases.
- Four cards in the Vietnamese listing, including the new article; three existing
  Vietnamese related guides on the new article.
- All 13 distinct Vietnamese URLs linked from the rendered page return HTTP 200,
  including both editorial body links.
- Existing unpaired-route language fallback: English goes to `/`; Vietnamese goes
  to `/vi`. The English Home → Vietnamese Home round trip works with and without JS.
- An English `Accept-Language` and locale cookie do not redirect the Vietnamese
  route. App-host requests retain the path/query in the existing 307 redirect to
  the commercial host.
- Exactly one sitemap entry for the article; English RSS still has three items and
  excludes it; its nonexistent English article route returns 404; robots allows VI.

Manually inspected the 375 px article and table screenshots and the 1440 px article
screenshot. Vietnamese accents, heading wrapping, reading width, table scrolling
and visible focus remain readable within the existing design.

Artifacts:

- [Article QA JSON](verification-artifacts/blog-vi-rank-tracker/browser-qa.json)
- [Mobile article](verification-artifacts/blog-vi-rank-tracker/article-375.png)
- [Mobile table](verification-artifacts/blog-vi-rank-tracker/article-tables-375.png)
- [Desktop article](verification-artifacts/blog-vi-rank-tracker/article-1440.png)
- [English blog regression](verification-artifacts/blog-vi-rank-tracker/english-regression/browser-qa.json)

## Reproduction

From `frontend/`, with Node 22.22+ on PATH:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8000'
$env:NEXT_PUBLIC_APP_ENV = 'test'
$env:NEXT_PUBLIC_SITE_URL = 'https://serpsaas.com'
$env:NEXT_PUBLIC_APP_URL = 'https://app.serpsaas.com'
npm test
npm run lint
npm run typecheck
npm run format:check
npm run build
```

Copy `public/*` and `.next/static/*` to the corresponding standalone directories,
then run `.next/standalone/server.js` with `PORT=3010`, `HOSTNAME=127.0.0.1` and the
same public environment. In another terminal set `QA_BASE_URL` to that local URL,
`QA_TOOLS_DIRECTORY` to the optional tools' `node_modules` directory and
`QA_CHROME_PATH` to Chrome. Run:

```powershell
node scripts/verify-rank-tracker-blog-browser.mjs
node scripts/verify-blog-browser.mjs
node --experimental-strip-types scripts/verify-full-public-localization-browser.mjs
```

Use `QA_ARTIFACT_DIRECTORY` to keep regression evidence in a separate directory.
The expanded localization script uses synthetic plan fixtures only.

## Publication status

The repository content is ready for the normal frontend deployment process.
Production deployment, production URL checks, Google indexing, Search Console and
traffic have **not** been verified or claimed.
