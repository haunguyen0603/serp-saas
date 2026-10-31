# M7L — SEO Content & Internal Linking Optimization

**Project:** SERP SaaS (`serp-saas`)  
**Implementation audience:** Codex engineering agent  
**Status:** APPROVED SPECIFICATION / NOT YET IMPLEMENTED  
**Basis:** `docs/verification-seo-content-internal-link-audit.md` (audit dated 2026-10-29; baseline commit `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`)  
**Scope:** Implement audit recommendations **R1–R5 only**. R6–R8 remain excluded.

## 1. Mission and principles

Improve the clarity of existing SERP SaaS public product messaging and the usefulness of editorial-to-product navigation. Make the smallest defensible changes to already functioning English/Vietnamese pages. **This is an implementation milestone**, not a second audit, and it is **not** a request to publish new content or deploy production.

The October 29 audit found no P0 Technical SEO defect: 27/27 public sitemap URLs returned HTTP 200, titles/descriptions were unique, all pages had one H1 and self-canonical, 12 explicit EN/VI pairs were reciprocal, and 3 unpaired Vietnamese articles correctly had no fabricated English alternates. The two Vietnamese checking-related blog posts **already have** body links to the commercial product. Do not duplicate existing links or claim that a ranking/indexing fault has been proven.

### Product truth constraints

- SERP SaaS checks and records **Google Top 10**, not Top 100. A result absent from the checked Top 10 is not a proven exact rank #11 or worse.
- Desktop and Mobile are separate project/search contexts and subscription entitlements.
- Check frequency (daily/weekly or manual) depends on plan/entitlement; no blanket guaranteed schedule or realtime claims.
- Rank changes, history and competitor insights depend on completed, stored observations; do not fabricate live data, measurements, customer results or guarantees.
- Do not claim SERP SaaS analyzes every SERP feature, ads, maps, AI answers or complete Google results pages.
- Site is **user-scoped**, not team/workspace-based. No invented multi-user organization features.

## 2. Required preflight

1. Read the complete audit `docs/verification-seo-content-internal-link-audit.md`, especially findings **R1–R5**, internal-link matrix, limitations and Proposed Implementation Milestone. Verify it exists and do not silently substitute another version.
2. Inspect the repository's current state, route/content definitions, `AGENTS.md` if present, and affected tests. The audit's line numbers and commit are **references, not authority over changed code**. If source has changed, reconcile against current behavior and record any material discrepancy.
3. Establish a before-change baseline for affected rendered HTML: title, description, H1, canonical, `lang`, hreflang, structured data and key existing links. Confirm whether local runtime and browser QA dependencies are available. Do not alter unrelated dependencies merely to execute tests.
4. Keep changes tightly scoped. If any specific requested edit is already implemented, mark it verified/no-op instead of re-adding it.
5. Do not use GSC rankings or traffic forecasts as acceptance criteria. Historical user-provided data includes very small query samples (for example, 3 impressions for `kiểm tra thứ hạng từ khóa` in Vietnam). This is editorial optimization, not a diagnosed penalty or cannibalization fix.

## 3. Implementation requirements

### R1 — Make the Vietnamese core commercial landing clearly identify the tool

**Target route:** `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa`  
**Likely source:** `frontend/src/features/marketing/vietnamese-content.ts` (core product configuration; verify current location)

**Required:**
- Set the landing page's rendered **H1** to exactly: **`Công cụ kiểm tra thứ hạng từ khóa Google`**.
- Tighten its existing introductory lead so a first-time reader understands that **SERP SaaS is a tool for checking an explicitly selected set of Google keywords and retaining completed checks to review rank history and changes**.
- Preserve the existing H1 rendering convention (do not inject a second H1 in JSX or content).
- Retain the existing SEO title, meta description, canonical, route and locale/hreflang mappings.
- Preserve nearby Top 10 and separate Desktop/Mobile limitations, commercial CTAs, pricing links, competitor/report boundaries and meaningful product sections.
- Edit only the necessary copy. Do not rewrite the entire landing page or introduce keyword repetition.

**Suggested Vietnamese lead (adapt to existing component length/style):**

> SERP SaaS là công cụ kiểm tra thứ hạng từ khóa trên Google: bạn chọn bộ từ khóa và môi trường tìm kiếm, thực hiện các lượt kiểm tra theo quyền lợi gói cước, rồi xem lại kết quả đã lưu để theo dõi biến động thứ hạng. Desktop và Mobile được quản lý riêng; phạm vi kiểm tra là Top 10.

This is sample editorial copy, **not an instruction to replace other established text blindly**. If the existing surrounding Top 10 note already states limitations clearly, keep the lead concise and avoid repeating identical disclaimers.

**Acceptance:** one H1 with exact required text; rendered first-screen copy makes product identity clear; metadata/canonical and limits unchanged; no claims of Top 100, exact out-of-depth rank or instant lookup.

### R2 — Add a useful product CTA to the English Blog shared CTA

**Target routes:** `/blog` and **all three** currently published EN articles  
**Likely source:** `frontend/src/features/blog/blog-components.tsx`, `BlogCta`

**Required:**
- Add **one** English-only accessible anchor with label **`Explore the Google rank tracker`** pointing to **`/google-serp-rank-tracker`**.
- Put it beside/in the existing Blog CTA product/pricing action area, as a secondary option; **retain** the existing Pricing link/button and its semantics.
- Ensure the link appears as a normal crawlable `<a href>` in server-rendered HTML, including when JavaScript is disabled.
- Keep the current Vietnamese Blog CTA unchanged: the Vietnamese CTA already provides product and pricing links.
- Use the current design system, focus states, responsive wrapping and button/link styles; no extra sitewide footer links, generic copy-pasted body links or cross-locale URLs.

**Acceptance:** `/blog` + all three EN article pages each contain the new SSR link exactly once in their shared CTA (excluding existing footer links); destination returns HTTP 200; Pricing remains; Vietnamese pages have no new unintended English CTA.

### R3 — Align the three Vietnamese landing-page guide slots with the reader's task

**Likely source:** `frontend/src/features/marketing/vietnamese-content.ts`; preserve the existing single-guide configuration model and shared rendering component.

Update **guide URL, visible label and short description together**. Preserve product CTA, pricing CTA and sibling-product links.

| Source landing | New guide destination | Required visible guide label | Desired guide description |
|---|---|---|---|
| `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa` | `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` | `Đọc cách kiểm tra thứ hạng từ khóa` | Invite users to learn one-check setup and reading the observed Google position. |
| `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` | `/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay` | `Khi nào nên theo dõi thứ hạng hàng ngày?` | Invite readers to compare daily and weekly monitoring needs. |
| `/vi/seo-rank-tracking-cho-agency` | `/vi/blog/serp-tracking-cho-agency` | `Đọc quy trình báo cáo thứ hạng cho agency` | Invite readers to review a practical client-reporting workflow. |

All three destinations were reported live/HTTP 200 at audit time, but verify again in the current environment. Use grammatically natural final Vietnamese copy without making unsupported product promises. Updating the guide **does not** mean deleting other existing routes, blog links or old guide articles.

**Acceptance:** each of the three existing single-guide slots has the intended label and href in SSR HTML, no second duplicated guide slot, and a functioning 200 destination; EN guide mappings and all locale routes are unchanged.

### R4 — Add one contextual definition-to-practical-guide link

**Source article:** `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`  
**Target:** `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa`  
**Suggested anchor:** `cách kiểm tra thứ hạng từ khóa`

In the section **“Rank Tracker hoạt động như thế nào?”**, add **one brief natural handoff sentence** leading readers who want a practical single-check workflow to the existing checking tutorial.

Example sentence (fit it to the surrounding prose, avoiding redundancy):

> Nếu muốn thực hành từng bước và đọc kết quả của một lần kiểm tra, bạn có thể tham khảo hướng dẫn [cách kiểm tra thứ hạng từ khóa](/vi/blog/cach-kiem-tra-thu-hang-tu-khoa).

Do not add another H1. Preserve original article purpose (tool definition/evaluation), original contextual link to the commercial landing, existing Google Search Console distinctions, tables and Top 10 caveats. Do not force a reciprocal link in the other article or modify related-post ranking/taxonomy.

**Dates:** preserve the original `publishedAt`. Set `updatedAt` only if the substantive article edit is made, to the **actual implementation date**, following the content parser's date convention; update relevant test fixtures accordingly. Do not backdate or use the audit date by default.

**Acceptance:** exactly one new useful article-body link to the tutorial; target 200; original commercial link retained; one rendered H1; valid frontmatter; original `publishedAt` preserved; content scope unaltered.

### R5 — Make the English homepage scope and example UI transparent

**Target:** `/`  
**Likely source:** `frontend/src/app/(en)/page.tsx`

**Required:**
- Add a short, visible, accessible disclosure near the existing hero/plan note explicitly stating: **ranking checks cover Google's Top 10**, and **Desktop and Mobile are managed separately**.
- Add an always-visible caption adjacent to the existing styled CSS product preview clarifying that **displayed domains, ranks and usage numbers are illustrative interface data, not verified customer performance or live account/plan limits**.
- Preserve the existing CSS preview; do not fabricate a real screenshot or customer outcome. Do not convert the preview to a misleading image.
- Maintain existing CTAs, marketing structure and EN home metadata. Keep copy brief enough for small screens and check color contrast/readability.

Suggested concise text, adaptable to current UI:

- Scope note: `Checks cover Google's Top 10. Desktop and Mobile tracking are managed separately; available schedules depend on your plan.`
- Preview caption: `Illustrative interface preview. Sample domains, rankings and usage numbers are not live customer results or current plan limits.`

**Acceptance:** visible in SSR HTML and at 375px; no suggestion that the examples are actual rankings or account billing data; no SEO/meta/structural regressions.

## 4. Explicit out-of-scope items

Do **not** implement audit R6, R7 or R8 in M7L:

- **R6:** genuine product screenshots (requires separately supplied authorized, redacted source asset).
- **R7:** new `/vi/blog/serp-la-gi` article or any other new article. It remains a separate content milestone.
- **R8:** SoftwareApplication schema changes, breadcrumb rework, editorial translation parity review or hreflang restructuring.

Also excluded: URL/slug changes, redirects, canonical/meta title/description rewrites, sitemap/robots generation changes, global SEO taxonomy, related-post ranking algorithm, account/auth, billing/SePay, ranking workers, alerts, infrastructure, database migrations and production deployment.

**Preserve** the functioning sitemap/hreflang system. Do not add an English alternate to the three existing unpaired Vietnamese articles.

## 5. Verification requirements and acceptance matrix

Run all checks from a suitable local environment; do not label tests as passed unless run and evidenced. If tools/dependencies are missing, record the blocker and unverified areas accurately.

### A. Static/repository checks

- Confirm the diff is limited to the four expected editorial/application targets, relevant tests/scripts and the requested verification report (additional narrowly necessary files only with rationale).
- Run `git diff --check`.
- Confirm marketing config and article frontmatter parse correctly; no duplicated CTA, H1 or guide slot.
- Confirm changed source does not invent product features, guarantees, sample-customer results or unsanctioned SEO metadata changes.

### B. Frontend quality gates

From `frontend/` use the repository's existing commands:

```bash
npm run prebuild
npm test
npm run lint
npm run typecheck
npm run format:check
npm run build
npm audit --omit=dev
```

If the current repo differs, adapt only after checking `package.json` scripts; document exact commands/results. Do not automatically upgrade dependencies as part of this editorial milestone.

### C. Live-like SSR/rendering checks

Prefer the **local production standalone build** with same-host routing to inspect server-rendered HTML. Exercise both JS-on and JS-off contexts where possible. The acceptance table:

| Route/family | Required verification |
|---|---|
| `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa` | Exact R1 H1, revised lead, R3 guide href/label, original SEO metadata and Top 10/device limitations |
| `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay` | R3 daily-vs-weekly guide href/label, original core/product links |
| `/vi/seo-rank-tracking-cho-agency` | R3 agency reporting guide href/label, original product limits |
| `/vi/blog/cong-cu-rank-tracker-la-gi` | R4 one contextual link, existing commercial link, dates, single H1 |
| `/blog` and all 3 EN published posts | R2 shared CTA with new product link + retained Pricing, no accidental VI changes |
| `/` | R5 visible scope note and preview caption, original CTAs and metadata |
| `/vi/blog` and representative VI articles | VI shared CTA unchanged and published listing intact |

Check each **new/reassigned URL** using local app routing or verified production 200 where appropriate. The link must be crawlable in HTML, not only a JS onClick handler.

### D. Full SEO regression invariants

For the current public site baseline (unless unrelated new content is explicitly authorized in another task):

- **27 public sitemap URLs**, all expected HTTP 200 and distinct; no new blog article/route in M7L.
- **12 reciprocal EN/VI/x-default locale mappings** unchanged; **3 unpaired VI blog articles** remain unpaired.
- One H1 per public route, `html lang` correct, unique titles/descriptions, correct self-canonical, robots/indexability and existing relevant JSON-LD.
- English RSS remains **3 EN articles**; Vietnamese blog count remains **6**; total blog count remains **9**.
- Existing public 404 behavior unchanged; no broken internal content hrefs.
- Confirm key external app/pricing CTA destinations did not change; no need to test payments or auth state.

### E. Responsive, accessibility, navigation

Test the changed areas at **375, 768, 1024 and 1440 px**. Include:

- No horizontal overflow or clipped new labels/captions.
- Keyboard Tab/focus order and visible focus indicators for the new link.
- JS-disabled navigation/SSR copy available and readable.
- No React console/hydration errors in tested flows.
- Automated axe WCAG 2/2.1 A/AA on relevant changed pages if tools are available; describe scope and any exclusions.

### F. No impact claims

Do **not** claim improvements to Google rankings, CTR, clicks, conversions or indexing from these local tests. A follow-up measurement plan is useful, but is not a shipping gate.

## 6. Deliverable and report structure

Write the implementation verification report to:

`docs/verification-milestone-7l.md`

Include the following sections:

1. **Implementation summary** — exactly what was changed for R1–R5, source paths, before/after wording and href mappings; identify any verified no-ops.
2. **Change inventory** — full diff paths, confirmation that R6–R8 and unrelated systems were untouched.
3. **Product truth and editorial review** — evidence Top 10/device/schedule bounds remain accurate.
4. **SEO/SSR regression** — all pages, titles/H1/canonicals/hreflang/sitemap/robots/RSS counts; changes verified by local HTML, and any production checks distinctly labeled.
5. **Tests and browser QA** — exact commands, results, dates, versions, viewport/JS modes, axe scope and saved artifact paths if generated.
6. **Known limitations** — untested production/GSC effects, missing tools, observed regressions or remaining nonblocking questions.
7. **Rollout and rollback** — minimum compatible deploy order (frontend-only if confirmed), post-deploy production checks, easy rollback of editorial/config changes, and separation from future new-content milestone.
8. **Final decision** — PASS/FAIL/PARTIAL, with blockers, and clear `NOT DEPLOYED` statement unless separately authorized and actually executed.

Use repo-relative evidence paths; do not fabricate logs, screenshots, source checks or successful live measurements. Preserve and reference `docs/verification-seo-content-internal-link-audit.md` rather than overwriting it.

## 7. Rollout and measurement notes (do not execute deployment)

After owner review, deploy through the existing approved frontend release path. Verify the affected production URLs return HTTP 200, render the new H1/guide links/CTA/disclosures in raw HTML, preserve canonical/hreflang, and that sitemap/RSS counts did not unexpectedly change. Check a small-screen production render.

For SEO follow-up, record the implementation/release date and compare **the same** GSC country, search type, device, query and date scopes; preserve sample sizes and reporting limitations. Prior historical examples (`serp là gì`: six impressions; `serp google checker`: two; Vietnamese checking query: three) are **too small** to justify a causal ranking claim. Do not issue repeated indexing requests or use `Validate Fix` for a non-error.

## 8. Definition of Done

- R1–R5 implemented precisely, with any deviations explained and approved by the actual repo state.
- No unrelated behavior, route, metadata, canonical, locale or product scope changes.
- Required guide and CTA hrefs exist and are crawlable; relevant destinations return 200.
- Edited article keeps original `publishedAt` and correct implementation-date `updatedAt`.
- All feasible existing tests/build/SSR/browser/accessibility gates run and pass; unmet gates reported honestly.
- `docs/verification-milestone-7l.md` exists with reproducible evidence and final status.
- No production deploy, GSC indexing action, commit or push unless separately requested.

**Codex final response:** summarize the five changes, list checks run and failures/limitations, and state whether M7L is ready for production deployment. Do not describe it as already deployed.
