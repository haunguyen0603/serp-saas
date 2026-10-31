# M7L — SEO Content & Internal Linking Optimization verification

**Security follow-up, 2026-10-29:** the critical local Next.js finding was resolved by aligning dependencies with remote M7D's Next 16.4.3. Runtime audit is now clean and M7L regressions pass. The local checkout is four commits behind current remote main; integration is required before a production release to preserve newer product features. See [security remediation and release limitations](verification-milestone-7l-security-remediation.md). The original implementation evidence and decision below remain historical.

Implementation date: **2026-10-29, Asia/Saigon**. Baseline commit: `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`.

Specification: [milestone 7L](milestone-7l-seo-content-internal-linking-optimization.md). Required preflight source: [complete October 29 audit](verification-seo-content-internal-link-audit.md), preserved without edits. No repository/ancestor `AGENTS.md` was found. The specification and audit were already untracked inputs when work started; no pre-existing tracked changes were present.

## 1. Implementation summary

All R1–R5 edits were needed; none were already implemented.

**R1 — Vietnamese product identity.** In `frontend/src/features/marketing/vietnamese-content.ts`, changed the core product heading from “Theo dõi thứ hạng từ khóa trên Google” to exactly **“Công cụ kiểm tra thứ hạng từ khóa Google”**. Replaced the lead:

> Đưa từ khóa, vị trí trên Google và lịch sử kiểm tra vào cùng một dự án để biết đâu là thay đổi cần chú ý trong công việc SEO.

with:

> SERP SaaS là công cụ kiểm tra thứ hạng từ khóa trên Google: bạn chọn bộ từ khóa và môi trường tìm kiếm, kiểm tra theo quyền lợi gói cước, rồi xem lại kết quả đã lưu từ các lần kiểm tra hoàn tất để theo dõi lịch sử và biến động thứ hạng.

The existing adjacent Top 10/separate-device note remains verbatim. The existing renderer still supplies the only H1. SEO title and description remain unchanged.

**R2 — English shared Blog CTA.** In `frontend/src/features/blog/blog-components.tsx`, retained “Explore rank-tracking Plans” → `/pricing` as the button and added one secondary **“Explore the Google rank tracker”** → `/google-serp-rank-tracker` in the existing responsive `public-cta-row` pattern. The Vietnamese branch is unchanged. Raw HTML contains an ordinary anchor on `/blog` and each of the three English articles. Existing `siteHref` conventions produce the commercial absolute URL in the separate-domain build.

**R3 — Vietnamese guide slots.** Updated path, label and description together in `vietnamese-content.ts`; one guide per page and the shared renderer/model remain intact:

| Landing | Previous guide | New guide and label |
| --- | --- | --- |
| `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa` | `/vi/blog/cach-theo-doi-thu-hang-google` | `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` — “Đọc cách kiểm tra thứ hạng từ khóa” |
| `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` | `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` | `/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay` — “Khi nào nên theo dõi thứ hạng hàng ngày?” |
| `/vi/seo-rank-tracking-cho-agency` | `/vi/blog/cach-theo-doi-thu-hang-google` | `/vi/blog/serp-tracking-cho-agency` — “Đọc quy trình báo cáo thứ hạng cho agency” |

Before: core/agency used “Đọc hướng dẫn theo dõi thứ hạng Google” and the broad baseline/setup description; daily used the checking label and manual/tool comparison description. After: descriptions respectively invite one-check setup/reading an observed Google position, comparison of daily/weekly needs, and practical client-report preparation. All destinations return local HTTP 200. Previous articles remain published; English guide mappings are unchanged.

**R4 — Definition to practical guide.** Added exactly one sentence before the next H2, inside “Rank Tracker hoạt động như thế nào?” in `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`:

> Nếu muốn thực hành từng bước và đọc kết quả của một lần kiểm tra, bạn có thể tham khảo hướng dẫn [cách kiểm tra thứ hạng từ khóa](/vi/blog/cach-kiem-tra-thu-hang-tu-khoa).

Preserved `publishedAt: 2026-10-17`; changed `updatedAt` from `2026-10-17` to actual implementation date `2026-10-29`. Existing commercial link, tables, GSC distinctions and limits remain. No reciprocal link or taxonomy change was added.

**R5 — English homepage disclosures.** In `frontend/src/app/(en)/page.tsx`, added these previously absent visible notes using the current `public-cta-note` styling:

- Near the hero plan note: “Checks cover Google's Top 10. Desktop and Mobile tracking are managed separately; available schedules depend on your plan.”
- Inside the CSS preview after its usage display: “Illustrative interface preview. Sample domains, rankings and usage numbers are not live customer results or current plan limits.”

Existing preview markup/data, metadata, CTAs and section structure are retained.

## 2. Change inventory

Application/editorial targets (four):

- `frontend/src/features/marketing/vietnamese-content.ts`
- `frontend/src/features/blog/blog-components.tsx`
- `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`
- `frontend/src/app/(en)/page.tsx`

Verification changes:

- `frontend/src/features/blog/blog.test.tsx` — shared product/Pricing CTA on the index and all three EN posts.
- `frontend/src/features/marketing/public-site.test.tsx` — homepage scope and preview disclosure.
- `frontend/src/features/marketing/vietnamese-localization.test.tsx` — exact heading/guide mappings, contextual link and dates.
- `frontend/scripts/verify-rank-tracker-blog-browser.mjs` — existing expected article `dateModified` fixture updated.
- `frontend/scripts/verify-milestone-7l.mjs` — reproducible before/after raw HTML, navigation, browser and axe checks.
- `docs/verification-milestone-7l.md` — this report.
- `docs/verification-artifacts/milestone-7l/` — before/after inventories, check output, browser results and screenshots.

R6–R8, dependency manifests/lockfiles, routes, canonical/metadata generators, locale map, sitemap/robots/RSS generators, related-post logic, backend, auth, billing/SePay, workers, infrastructure and databases were untouched. No new article or product screenshot was created. QA screenshots document the existing rendered interface.

## 3. Product truth and editorial review

The revised lead identifies explicitly selected keywords, configured search context, entitlement-dependent checks and stored completed observations. The existing landing note continues to state Top 10 and separate Desktop/Mobile projects. Existing sections preserve out-of-depth uncertainty, failed/incomplete-check caveats, stored competitor comparisons, account ownership, reporting/export boundaries and plan-based scheduling. The homepage now makes the same scope visible and labels domains/ranks/usage as illustrative.

No Top 100 capability, exact rank outside checked depth, realtime guarantee, complete SERP-feature analysis, shared organization/workspace feature, actual customer result or ranking/traffic outcome was introduced. Existing article commercial links were verified and preserved; duplicate sales links were unnecessary.

## 4. SEO/SSR regression

The existing pre-edit standalone build was available. Captured and checked its rendered HTML before source edits. Built current source after edits and repeated the same crawl against the local production standalone server at `http://127.0.0.1:3010`; public links/canonicals use `https://serpsaas.com`, with same-host routing during browser navigation.

Evidence: [before inventory](verification-artifacts/milestone-7l/baseline.json), [after inventory](verification-artifacts/milestone-7l/after.json). Each contains all 27 routes' title, description, H1, lang, canonical, alternates, robots, parsed JSON-LD, anchors, shared CTA, guide/prose and main copy. This is local evidence, not a fresh production crawl.

| Invariant / acceptance | Result |
| --- | --- |
| Sitemap | 27 distinct unchanged URLs, all local HTTP 200 |
| Titles/descriptions | 27 distinct titles and descriptions; identical before/after per route |
| H1 | Exactly one per route; only the required VI commercial H1 changed |
| Canonical/lang/robots | Unchanged per route; self-canonical paths and expected EN/VI language |
| Locale alternates | 24 pages form 12 reciprocal en/vi/x-default mappings; unchanged |
| Unpaired VI posts | Definition, daily-decision and competitor guides retain zero invented alternates |
| Blog counts | 3 EN + 6 VI = 9; no new route/article |
| Feed/robots | HTTP 200 and identical before/after; feed has 3 EN items, no VI posts |
| JSON-LD | All existing blocks parse; automatic heading-derived WebPage/breadcrumb names changed for R1 and article dateModified for R4; all other data unchanged |
| Internal anchors | Every discovered same-origin anchor destination returns 200; prior destinations/labels retained except the three intentionally reassigned guides |
| EN CTA | Exactly one new secondary link in each of 4 shared CTAs; Pricing retained |
| VI CTA | Identical rendered shared CTA before/after on index and all six posts |
| Definition body | Exactly one new checking-guide link; original product link retained; published date unchanged |
| Homepage | Both disclosures present in raw HTML and visible in browser, including 375 px |
| 404s | Candidate SERP article, synthetic absent VI article and three untranslated EN slugs still return 404 |
| App/pricing links | Existing anchor destinations retained; no authenticated flow/payment was exercised |

The R1 change naturally propagates through existing `landingStructuredData` into `WebPage.name` and the current-page breadcrumb label. This is existing heading-derived behavior, not an R8 schema/breadcrumb redesign. No material discrepancy with the audit's routes or original content was found.

## 5. Tests and browser QA

Environment: Windows/PowerShell; Node **22.22.0**, npm **10.9.4**, Next **16.3.8**, React **19.3.0**, Vitest **4.1.11**. Node was absent from PATH and old temporary executables had been removed. Downloaded the official Node archive to a task-specific temporary directory and added it only to command-local PATH; no project dependency change. Installed Playwright **1.58.2** and `@axe-core/playwright` **4.11.1** in another temporary directory. Browser: installed Chrome **156.0.8078.49**.

Commands executed from `frontend/` on October 29:

| Command | Final result |
| --- | --- |
| `npm run prebuild` | PASS — 9 published, 0 drafts |
| `npm test` | PASS — 36 files, 331 tests |
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run format:check` | PASS |
| `npm run build` | PASS — production Webpack build/standalone output |
| `npm audit --omit=dev` | FAIL — 1 critical finding in existing Next dependency; no fix offered by this audit run |
| `git diff --check` (repo root) | PASS — only Git LF/CRLF informational warnings |
| `node scripts/verify-milestone-7l.mjs --baseline` | PASS — pre-edit crawl saved |
| `node scripts/verify-milestone-7l.mjs` | PASS — SSR regression, 88 browser cases and 44 axe analyses |

The first test attempt lacked `NEXT_PUBLIC_API_BASE_URL` and failed to load three unrelated test suites; reran with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` and `NEXT_PUBLIC_APP_ENV=test`, with all 331 tests passing. The initial typecheck caught unsupported Testing Library `exact` options in the new assertions; removed them and reran successfully. No application change was needed for either issue.

Build variables: `NEXT_PUBLIC_APP_ENV=production`, `NEXT_PUBLIC_SITE_URL=https://serpsaas.com`, `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. Runtime: `PORT=3010`, `HOSTNAME=127.0.0.1`, `node frontend/.next/standalone/server.js` from repository root. Copied `.next/static` and `public` into the generated standalone directory, as required for local asset serving. These generated files are ignored.

Reproduce browser QA by setting `QA_TOOLS_DIRECTORY` to the temporary tool `node_modules`, `QA_CHROME_PATH` to installed Chrome and optionally `QA_BASE_URL` (defaults to local port 3010), then running the script above. `--ssr-only` runs only the raw HTML regression. Preserve `baseline.json` when repeating after-checks; baseline mode intentionally overwrites it.

Browser scope: homepage, three VI landings, EN Blog index/all three posts, VI index, definition and checking articles — **11 routes × 4 widths (375/768/1024/1440) × 2 JS modes**. Checks include one H1, no horizontal overflow, visible disclosures, keyboard Shift+Tab/Tab focus with visible outline, Enter navigation for new CTA/guide/body links, and React page/hydration errors. Full-page axe WCAG 2/2.1 A/AA runs in JS-enabled cases, with no rule/element exclusions; JS-disabled cases verify native SSR navigation and copy. External commercial URLs route back to the local server; anonymous auth refresh alone is mocked with 401/CORS responses, avoiding real backend/account operations.

Result: **88/88 browser cases passed**, **44/44 axe analyses returned zero violations**, no tested horizontal overflow or page/hydration errors, and all exercised keyboard links navigated successfully in both JS modes. Browser results are saved in [browser-qa.json](verification-artifacts/milestone-7l/browser-qa.json).

Saved evidence lives in `docs/verification-artifacts/milestone-7l/`: `checks.txt`, `baseline.json`, `after.json`, `browser-qa.json` and screenshots named by route/width. Screenshots focus on the preview caption, landing guide slots and EN shared CTA; browser assertions also cover the hero disclosure and article handoff. Manual visual inspection includes the 375 px homepage caption and EN CTA; automated axe complements this and does not establish full screen-reader usability.

## 6. Known limitations

`npm audit --omit=dev` exits 1 for the unchanged locked Next.js dependency, reporting these advisories: `GHSA-2464-fhr4-w9xw`, `GHSA-p3m5-59mp-jv5r`, `GHSA-673q-mjm6-r5xr`. The command reports “No fix available”. This milestone does not upgrade dependencies or determine exploitability; security remediation/release review remains a blocker to declaring every release gate passed. Preserve the audit output rather than infer safety from successful page tests.

No production deployment/recheck, GSC export/inspection, real SERP measurement, indexing request, billing/auth operation, screen-reader session or customer outcome measurement was performed. Local checks cannot establish Google ranking, CTR, conversions, indexing state or selected canonical. Test effects on production only after a separately authorized release.

Both the original standalone server and rebuilt server logged Next `Internal: NoFallbackError` while probing absent static article slugs; all five probes returned the expected HTTP 404. This existing server-side diagnostic did not appear as a React/browser error in the tested published pages. The temporary local server was stopped after QA.

## 7. Rollout and rollback

Confirmed frontend-only source/content change; no migration, backend release, billing change or deploy-order dependency. Once release/security gates and owner review are satisfied, use the existing approved frontend release path. Post-deploy, fetch raw production HTML for all changed routes and destinations, verify exact heading/guide/CTA/disclosure copy, HTTP 200, single H1, canonical/alternates and counts (27 sitemap URLs, 3 EN feed items, 6 VI posts); check a 375 px production render. No deployment was executed here.

Rollback by redeploying the previous frontend artifact, or reverting only this milestone's four application/content files and matching verification fixtures, then rebuilding. Preserve the user's existing audit/specification inputs and any later unrelated work. A future SERP definition article, genuine authorized product screenshot and schema review remain separate milestones. Record any eventual release date for comparable GSC follow-up with identical filters and explicit sample sizes; local PASS results are not impact claims.

## 8. Final decision

**PARTIAL — R1–R5 implemented; 331 tests, frontend quality/build checks, 27-route SSR regression and all 88 browser cases pass, with zero axe violations. The dependency audit fails on one existing critical Next finding, so production readiness cannot be declared until security/release review resolves that gate.**

**NOT DEPLOYED.** No commit, push, indexing action or production modification was performed.
