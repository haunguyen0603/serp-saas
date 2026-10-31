# SERP SaaS — SEO Content & Internal Linking Audit

- **Audit date:** 2026-10-29, Asia/Saigon.
- **Repository baseline:** `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`, branch `main`.
- **Production:** https://serpsaas.com. Live sitemap crawl completed at 23:07:22 Asia/Saigon (16:07:22 UTC); additional HTTP probes followed on the same date.
- **Scope:** Audit only. The sole repository addition is this requested report. No application, content, metadata, route, infrastructure, deployment, indexing request, commit or push was performed.

All URL paths below refer to https://serpsaas.com unless another origin is written explicitly. Recommendations are proposals, not implemented changes.

## A. Executive Summary

The site already has a sound public SEO foundation. All **27 sitemap URLs returned HTTP 200**, each had one H1, a self-referencing canonical after normalizing the root trailing slash, a language matching its route, and a unique title and description. Twelve EN/VI pairs have reciprocal alternates; three Vietnamese-only articles correctly have no invented English alternates. The targeted missing-page probes returned 404. No P0 problem was established.

The main opportunities concern **page purpose and the next useful reader action**, rather than missing indexing directives:

1. **The important Vietnamese commercial links already exist.** Both the Rank Tracker explainer and the single-check tutorial link to the keyword-checking landing page in server-rendered body content, in addition to the shared CTA and footer. Adding duplicate links to these same destinations is not the priority.
2. **The commercial landing page can declare its product role more clearly.** Its title and eyebrow say “Công cụ kiểm tra…”, but its H1 is “Theo dõi thứ hạng từ khóa trên Google” and its introduction describes a workflow rather than identifying the tool. This is an editorial clarity opportunity, not proof that Google has misunderstood or penalized the page.
3. **Some reader journeys are less specific than the available content.** The English blog CTA goes only to Pricing; product links exist in the footer. The Vietnamese daily and agency landing pages send their main guide links to broader tutorials even though dedicated daily/weekly and agency guides are published.
4. **The English homepage lacks an explicit Top 10 disclosure in its main copy.** Its CSS product preview is a mockup, not a real screenshot or verified customer result; visible “illustrative data” labeling would improve transparency. The other priority product pages explain the checked depth more directly.
5. **A dedicated “SERP là gì?” article is an editorial gap.** No such article exists in source, listing or sitemap, and the proposed route currently returns 404. It would answer a different question from “Rank Tracker là gì?”. Six historical impressions provide only a weak demand hint, not keyword-volume or traffic evidence.

### GSC evidence and what it does not establish

The following is **user-supplied historical evidence (U1)**, not a fresh GSC export or a live ranking check:

| Query / page grouping | Impressions | Average position | Interpretation permitted |
| --- | ---: | ---: | --- |
| `serp là gì` → `/vi` | 6 | 80.8 | A small observed informational query sample; a definition article may serve the question better than a homepage. |
| `serp google checker` → `/` | 2 | 72.0 | A small English commercial/conceptual query sample; insufficient to retarget the homepage. |
| `kiểm tra thứ hạng từ khóa`, query grouping | 3 | 97.7 | Too little evidence for trends, stable URL preference or cannibalization. |
| Same query → `/vi/blog/cong-cu-rank-tracker-la-gi` | 2 | 97.5 | The explainer received impressions in that historical filtered view. |
| Same query → `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` | 1 | 98.0 | The practical guide also received an impression. |
| Same query → `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa` | No row | Not available | Absence from this filtered table does not establish absence from Google's index. |

The user confirms that the commercial VI landing page and the Rank Tracker explainer are indexed. The supplied landing-page inspection allowed indexing, fetched successfully, contained the relevant product terms, and showed a last crawl of **October 11, 2026**. These inspection facts were not independently rechecked in GSC during this audit. Current HTTP/indexability checks are a different evidence source.

The query date range, full export, click data, device breakdown, URL preference over time and conversion attribution were not supplied. Google documents that query filtering omits anonymized queries and can change totals; average position is aggregated performance data rather than a single controlled SERP observation. Earlier unusual numeric-prefixed queries also mean broad impression totals should not automatically be treated as verified human demand. No penalty, ranking trend, deindexing, or keyword cannibalization conclusion follows from this sample. See [GSC filtering](https://support.google.com/webmasters/answer/17011165?hl=en), [query-data limitations](https://support.google.com/webmasters/answer/17011259?hl=en) and [metric definitions](https://support.google.com/webmasters/answer/7576553?hl=en).

## B. Current SEO Architecture

### Routes and page roles

The 27 public sitemap entries consist of:

- **12 English URLs:** homepage; three commercial landings; Blog index; three published articles; Pricing, About, Privacy and Terms.
- **15 Vietnamese URLs:** homepage; three commercial landings; Blog index; six published articles; localized pricing, about and legal pages.

The three commercial intent families are:

| Family | English | Vietnamese |
| --- | --- | --- |
| Core rank-tracking product | /google-serp-rank-tracker | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa |
| Recurring monitoring | /daily-serp-tracker | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay |
| Agency workflow | /serp-tracking-for-agencies | /vi/seo-rank-tracking-cho-agency |

English route groups under `frontend/src/app/(en)/` do not add `(en)` to public URLs. Vietnamese pages live under `frontend/src/app/vi/`. The application uses a separate app origin; public register/login CTAs point to https://app.serpsaas.com. Public marketing content is available without authentication.

### Content, rendering and discovery

- **S1:** `frontend/src/lib/public-locales.ts` lists twelve explicit language pairs. It does not infer translations from slugs.
- **S2:** `frontend/src/features/marketing/landing-content.ts` and `vietnamese-content.ts` define the six commercial pages. `landing-page.tsx` supplies H1, sections, registration/pricing CTAs, a primary guide link, and sibling product links.
- **S3:** EN homepage copy lives in `frontend/src/app/(en)/page.tsx`; VI homepage copy in `frontend/src/app/vi/page.tsx`.
- **S4:** `frontend/content/blog/*.md` contains three EN articles; `frontend/content/blog/vi/*.md` contains six VI articles. `content.ts` validates frontmatter, filename/slug agreement, locale, dates, unique metadata and absence of an in-body H1; it filters drafts and sorts dates deterministically.
- **S5:** `blog-index.tsx` renders published cards, including featured ordering. `blog-article.tsx` supplies the single H1, byline, article JSON-LD, breadcrumbs, Markdown, related posts and CTA. `blog-components.tsx` uses React Markdown + GFM, ordinary links, and named focusable table containers.
- **S6:** `frontend/src/design-system/public-shell.tsx` renders the header, footer, language control and drawer. Product footer links are localized; general header links cover Home, Pricing, Blog, About and legal pages.
- **S7:** `frontend/src/features/blog/seo.ts` and `frontend/src/features/marketing/seo.ts` generate metadata/JSON-LD. `frontend/src/components/root-document.tsx` supplies the title suffix template and document language. Landing titles use absolute metadata, so the brand is not appended twice.
- **S8:** `frontend/src/app/sitemap.ts` discovers published EN/VI posts. `robots.ts` allows the public site while excluding app/account paths. English `feed.xml` includes only the three EN articles.
- **S9:** `frontend/src/lib/site.ts` and `frontend/src/proxy.ts` separate commercial and app URLs, normalize public canonical origin, and redirect public paths from the app origin.
- **S10:** Backend read-only cross-checks: `backend/app/schemas/competitor_analytics.py` caps selected competitors at five; `services/competitor_analytics.py` uses owned projects, stored observations and project-specific environments. Provider adapters parse organic results; this does not establish support for every visual SERP feature.

### Locale and related-post behavior

The three unpaired VI articles are:

- /vi/blog/cong-cu-rank-tracker-la-gi
- /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay
- /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo

Their language controls fall back to the locale homepages; this is navigation, not a declaration that the homepages are article translations. Their HTML correctly omits hreflang alternates. English RSS correctly excludes all VI posts.

Related posts are same-locale published articles, scored by **exact matching tags plus category**, then slug as a tie-break, with at most three results (`content.ts:173–190`). There is no minimum relevance score or editorial override. Six VI posts therefore show three related articles each; three EN posts show the other two. Cards have both title links and read-guide links with descriptive aria-labels; those repeated destinations are normal UI, not evidence of link spam.

## C. Page-by-Page Audit

### Priority metadata, verified in production HTML (L1)

| URL | Current SEO title | Current H1 | Current meta description |
| --- | --- | --- | --- |
| / | Google Rank Tracker for Desktop & Mobile \| SERP SaaS | Track your Google rankings with clarity. | Track Google keyword rankings across Desktop and Mobile, schedule rank checks, monitor ranking history, and manage SEO sites in one place. |
| /vi | Theo dõi thứ hạng từ khóa Google dễ dàng \| SERP SaaS | Theo dõi thứ hạng từ khóa Google dễ dàng | Theo dõi vị trí từ khóa Google, phân tích biến động, so sánh đối thủ và tạo báo cáo SEO. Quản lý dự án Desktop và Mobile riêng biệt với SERP SaaS. |
| /google-serp-rank-tracker | Google SERP Rank Tracker for Keyword Position Monitoring \| SERP SaaS | Google SERP Rank Tracker | Track Google keyword positions, compare ranking changes, monitor competitors, and review ranking history with SERP SaaS. |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa Google \| SERP SaaS | Theo dõi thứ hạng từ khóa trên Google | Kiểm tra thứ hạng từ khóa Google, xem lịch sử, phân tích biến động và so sánh đối thủ với SERP SaaS. Theo dõi Desktop và Mobile riêng biệt. |
| /vi/blog/cong-cu-rank-tracker-la-gi | Rank Tracker là gì? Cách theo dõi thứ hạng từ khóa hiệu quả \| SERP SaaS | Rank Tracker là gì? Cách theo dõi thứ hạng từ khóa hiệu quả | Tìm hiểu Rank Tracker là gì, cách công cụ theo dõi thứ hạng từ khóa hoạt động, khác gì Google Search Console và cách lựa chọn Rank Tracker phù hợp. |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | Cách kiểm tra thứ hạng từ khóa và đọc vị trí trên Google \| SERP SaaS | Cách kiểm tra thứ hạng từ khóa và đọc vị trí trên Google | Kiểm tra thứ hạng từ khóa bằng tìm kiếm thủ công hoặc công cụ, đối chiếu URL và hiểu giới hạn Top 10 trước khi kết luận về vị trí trên Google. |
| /vi/blog | Kiến thức SEO & Theo dõi thứ hạng \| SERP SaaS | Kiến thức SEO & Theo dõi thứ hạng | Hướng dẫn theo dõi thứ hạng Google, kiểm tra vị trí từ khóa và đọc biến động SEO tại Việt Nam với môi trường tìm kiếm nhất quán. |

All seven descriptions are distinct. Their wording is coherent with the page subject; this audit does not prescribe character-count targets or exact-match H1 rules.

### Priority content assessment

| URL | Search intent / audience | Primary topic | Current strengths | Identified weaknesses / opportunities | Evidence | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| / | Commercial/navigational; English-speaking SEO practitioners evaluating the product | Google rank tracker; separate Desktop/Mobile monitoring | Clear product H1, four-step workflow, features and plan-based schedules; main-content links to all three EN landings; registration/pricing CTAs | No explicit Top 10 statement in main copy; numerical CSS mockup is not a real screenshot; no visible illustrative-data caption | L1; S3, homepage lines 98–148 and 274–299 | R5: add checked-depth disclosure and demo caption. Keep broad product intent; do not turn it into a “SERP definition” page. |
| /vi | Commercial/navigational; Vietnamese SEO freelancers, in-house teams and agencies | Theo dõi thứ hạng từ khóa Google | Clear local-language introduction, four setup steps, six feature cards, environment/device explanation; Top 10 and plan limits present; direct product and Blog links | Mostly explanatory copy with no real product image or worked UI example; repeated generic “Tìm hiểu công cụ” card labels can be more specific | L1; S3, VI homepage | Keep its commercial orientation and existing product links. Consider R6 product evidence; R7 may add an educational entry point later. |
| /google-serp-rank-tracker | Commercial investigation; English product buyers | Google SERP rank tracker / keyword position monitoring | Explicit tool H1, checked-depth note near hero, stored-check competitor explanation, export/report limits; primary guide + sibling landings | Dense feature explanations without an actual UI screenshot; some jargon needs an example more than more prose | L1; S2; S7 | Preserve messaging and technical SEO. R6: show one genuine, safely anonymized product workflow when available. |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Commercial product evaluation; Vietnamese SEO users | Công cụ kiểm tra thứ hạng từ khóa Google | Commercial title/eyebrow, Top 10 note, local environment setup, comparisons and reporting; hero/mid/final product CTAs | H1/lead can more directly identify the product; “Theo dõi vị trí…” and “Xem lịch sử…” overlap in presentation; primary guide currently points to the broad baseline article, not the dedicated checking tutorial; no real screenshot | L1; S2, `vietnamese-content.ts:23–87` | R1 clarify tool identity; R3 use the checking guide in the existing guide slot. Preserve all measurement caveats. |
| /vi/blog/cong-cu-rank-tracker-la-gi | Informational tool definition/evaluation; beginners and tool researchers | Rank Tracker là gì | Direct definition; why/use/how sections; illustrative ranking table; GSC comparison; feature-selection guidance; contextual product link already present | Title also promises “Cách theo dõi…”, so it naturally shares some procedural context with how-to pages; no direct link to the single-check tutorial in body or current related set; no genuine product example | L1; S4; S5; exact body links in D | Keep definition, selection criteria, GSC distinction and examples. R4 link once to the checking tutorial for execution detail; do not duplicate the commercial link. |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | Informational practical how-to; people checking a keyword/URL now | Cách kiểm tra thứ hạng từ khóa | Intro distinguishes one observation from ongoing tracking; manual and configured checks; status table; URL/domain matching; explicit commercial, pricing, daily-product and baseline links | Could benefit from one real completed-check example; no need to expand generic product sales copy or repeat definitions | L1; S4, this article lines 15–72; S5 | Preserve its operational scope and existing links. Use R6 only if a real, labeled example is available. |
| /vi/blog | Informational discovery hub; Vietnamese readers choosing a guide | Kiến thức SEO và theo dõi thứ hạng | Six crawlable cards; distinct titles/descriptions; featured baseline guide; direct product + Pricing CTA; localized schema and footer | No “SERP là gì?” entry because the article does not exist; cards alone do not explicitly explain the learn/check/monitor/evaluate paths | L1; S5; S8 | Keep discovery and CTA. After approved new content, allow normal index discovery; optional short intent-based hub introduction, not a long SEO essay. |

### Heading hierarchy, introductions and depth

- **EN home:** H1 → workflow H2 with four H3 steps → feature H2/H3 cards → environment/domain/schedule H2s → plans, three product-use-case H3s, future integrations and final CTA. Hierarchy is coherent. The initial copy clearly sells monitoring; it does not answer the acronym query.
- **VI home:** H1 → four-step H2 → feature H2 with six H3 cards → environment/device H2s → product-selection H2 with three H3 cards → knowledge hub and final CTA. Its introductory purpose is clear.
- **EN product landing:** H1 → setup workflow H2 → position tracking, movement, competitors, organization, reporting and measurement H2s, with mid/final CTA headings. It has substantive product information rather than an empty keyword landing.
- **VI product landing:** H1 → “Từ thiết lập đến kết quả đầu tiên” → tracking over time, movement, competitor comparison, grouping, history, reporting and help/CTA H2s. No H3s are needed merely for symmetry. The limitation note is already near the top.
- **Definition guide:** H2s cover the definition, reasons to use a tool, operation, GSC, features, keyword selection, product start and conclusion; four numbered H3s describe operation. These sections support definition/evaluation intent. Delegate detailed execution to the practical guide.
- **Checking guide:** Seven H2s cover preparation, manual checks, configured checks, result status, URL/domain matching, GSC and saving results. It is already meaningfully different from a longitudinal monitoring guide.
- **VI blog index:** H2 card titles plus the shared CTA H2 beneath one H1. “Đọc thêm” and CTA headings on article pages belong to supplementary navigation; they are not duplicate article H1s.

No sampled priority hierarchy skipped directly from H1 to H3. More text or more exact-match headings are not automatic improvements. The useful next addition is a clearer product example and more specific hand-offs.

**Visual evidence:** No priority page has a product screenshot in a main-content `img`. The EN home uses a styled HTML preview; the articles use text/tables, with illustrative disclaimers where ranking figures appear. This is an evidence/presentation opportunity, not an image-indexing failure. A screenshot should be captured from an actual authorized demo with sensitive data removed, and labeled with its environment, time and Top 10 scope; it must not be presented as a customer result.

### Other relevant pages inspected

| URL | Search intent / topic | Current strength | Opportunity / recommendation | Evidence |
| --- | --- | --- | --- | --- |
| /daily-serp-tracker | Commercial recurring monitoring | Daily/weekly entitlement and Top 10 limits; main guide links to ongoing monitoring article; sibling products | Keep existing monitoring-guide hand-off; no need to manufacture another cross-language link | L1; S2 |
| /serp-tracking-for-agencies | Commercial agency workflow | User-scoped project organization, stored competitor data and reporting boundaries; dedicated agency guide | Preserve; a real report example may help later | L1; S2 |
| /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Commercial recurring tracking | Appropriate cadence and Top 10 caveats | Primary guide currently goes to single-check tutorial; R3 can point to the dedicated daily/weekly decision guide | L1; S2 |
| /vi/seo-rank-tracking-cho-agency | Commercial agency tracking | Own-account projects, separate device plans and correct report-delivery explanation | Primary guide is the generic baseline; R3 can use the already-published agency reporting guide | L1; S2 |
| /blog | English educational hub | Three crawlable guides and Pricing CTA; product footer links | Product exploration is footer-only at index level; R2 adds a contextual product CTA beside the existing Pricing action | L1; S5 |
| /blog/how-to-track-google-rankings | Informational baseline setup | Manual/tool distinction, environment, GSC caveats; body link to core product | Keep direct product link and baseline focus | L1; S4 |
| /blog/how-to-monitor-keyword-ranking | Informational recurring review / investigating changes | Explicit recurring-product link, dates/cohort/status caveats, external Google references | Core product is footer-only, but the daily landing is a sensible primary destination; do not force every article to point to every product | L1; S4 |
| /blog/serp-tracking-for-agencies | Informational reporting workflow | Explicit agency product link, own-account permissions and report limitations | Preserve agency focus; general product/footer link is enough unless an additional paragraph genuinely needs it | L1; S4 |
| /vi/blog/cach-theo-doi-thu-hang-google | Informational longitudinal project setup | Explains its distinction from a single check; links to checking, product, daily, pricing and agency pages | Keep as baseline hub; do not merge with the single-check guide | L1; S4 |
| /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | Informational daily-vs-weekly choice | Cadence scenarios, illustrative table, GSC and scope caveats; daily-product body link | Use as the daily landing's primary related guide | L1; S4 |
| /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | Informational competitor analysis | Business-vs-SERP distinction, illustrative comparisons, stored Top 10 and five-competitor boundaries; agency-product body link | Keep; an eventual SERP definition can link here without copying its analysis sections | L1; S4 |
| /vi/blog/serp-tracking-cho-agency | Informational client reporting | Own-account boundaries, keyword labels, competitor and report interpretation; relevant commercial links | Use as the agency landing's primary related guide | L1; S4 |

Pricing, About and legal pages were included in the technical crawl and link validity inventory, but were not subjected to an unrelated billing/legal product audit.

## D. Internal Linking Matrix

### D1. Required relationships and missing opportunities

“SSR” means an ordinary anchor with an href was present in the fetched production HTML **without executing JavaScript**. “Footer-only” is an existing relationship, not a broken or absent link. All existing same-origin destinations in the tables returned 200.

| Source URL | Destination URL | Existing anchor text | Current link status / location | Proposed improvement | Priority |
| --- | --- | --- | --- | --- | --- |
| /vi | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa; Tìm hiểu công cụ → | Existing: main product card + footer; SSR/200 | Keep the descriptive title link. Optionally differentiate the generic secondary card label. | Keep / P2 |
| /vi/blog/cong-cu-rank-tracker-la-gi | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | công cụ kiểm tra thứ hạng từ khóa Google | Existing: body; also shared CTA and footer; SSR/200 | Keep. No additional exact-match link is required. | Keep |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa | Existing: body; also shared CTA and footer; SSR/200 | Keep. Preserve the explanation of configured checks around it. | Keep |
| /vi/blog | All six VI articles | Each article's title + Đọc hướng dẫn → with a specific aria-label | Existing: six listing cards, two links per card; SSR/200 | Preserve discovery; no extra duplicate listing required. | Keep |
| All six VI article pages | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Tìm hiểu công cụ kiểm tra thứ hạng → | Existing: shared bottom CTA + footer; SSR/200 | Preserve; use body links only where the article's subject warrants them. | Keep |
| /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | theo dõi thứ hạng từ khóa hàng ngày | Existing: body; SSR/200 | Keep the informational-to-product hand-off. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | /vi/seo-rank-tracking-cho-agency | SERP SaaS dành cho SEO Agency | Existing: body; SSR/200 | Keep in the multi-project context; not a mandate for all competitor paragraphs to become sales links. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/seo-rank-tracking-cho-agency | SERP SaaS dành cho theo dõi thứ hạng agency | Existing: body; SSR/200 | Keep. Add the complementary product-to-guide journey via R3. | Keep / P1 |
| / | /google-serp-rank-tracker | Google SERP Rank Tracker; Explore Google SERP Rank Tracker → | Existing: main card + footer; SSR/200 | Keep; the commercial product is not orphaned. | Keep |
| /blog | /google-serp-rank-tracker | Google SERP Rank Tracker | Existing in footer; missing from main CTA | R2: add “Explore the Google rank tracker” beside Pricing. | P1 |
| /blog/how-to-track-google-rankings | /google-serp-rank-tracker | SERP SaaS Google rank tracker | Existing: body + footer; SSR/200 | Keep. | Keep |
| /blog/how-to-monitor-keyword-ranking | /google-serp-rank-tracker | Google SERP Rank Tracker | Footer-only; no body/core-product CTA | Its body already links to the daily product. Keep that specific journey; R2 provides optional general product exploration at the shared CTA. | P1 shared CTA; no forced body link |
| /blog/serp-tracking-for-agencies | /google-serp-rank-tracker | Google SERP Rank Tracker | Footer-only; no body/core-product CTA | Preserve the body link to the agency product; do not replace it with a less specific generic destination. | Keep; R2 optional CTA |
| /daily-serp-tracker | /blog/how-to-monitor-keyword-ranking | Read the keyword monitoring guide → | Existing: guide module; SSR/200 | Keep; this is already the intended monitoring journey. | Keep |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | None on this source page | Missing; destination valid/200 | R3: use the existing primary guide slot for the exact checking workflow. | P1 |
| /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | None on this source page | Missing; destination valid/200 | R3: use “Khi nào nên theo dõi thứ hạng hàng ngày?” as a cadence-specific hand-off. | P1 |
| /vi/seo-rank-tracking-cho-agency | /vi/blog/serp-tracking-cho-agency | None on this source page | Missing; destination valid/200 | R3: use “Đọc quy trình báo cáo thứ hạng cho agency”. | P1 |
| /vi/blog/cong-cu-rank-tracker-la-gi | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | None | Missing in body and current related set; destination valid/200 | R4: one contextual link where the definition guide hands execution detail to a tutorial. | P1 |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | /vi/blog/cong-cu-rank-tracker-la-gi | None | Missing; destination valid/200 | Optional tool-definition help if user research justifies a second help link; not required in the first milestone. | P2 |

These proposals serve specific decisions. They do not require repeated keyword anchors, unrelated language links, more footer links, or reciprocal links merely to form a loop. Google's [crawlable-link and anchor guidance](https://developers.google.com/search/docs/crawling-indexing/links-crawlable) supports ordinary href anchors and useful contextual descriptions; no ranking improvement is guaranteed by link count.

### D2. Repeated navigation and CTA inventory

| Source family / location | Existing destinations and anchors | SSR / validity | Audit decision |
| --- | --- | --- | --- |
| EN public header and drawer | / “Home”; /pricing “Pricing”; /blog “Blog”; /about “About us”; /privacy “Privacy Policy”; /terms “Terms of Service”; brand to / | Source S6; HTML home sample; same-origin targets 200 | Coherent navigation. Drawer/header repetition is expected, not evidence of duplicate pages. |
| VI public header and drawer | /vi “Trang chủ”; /vi/bang-gia “Bảng giá”; /vi/blog “Blog”; /vi/gioi-thieu “Giới thiệu”; /vi/chinh-sach-bao-mat “Chính sách bảo mật”; /vi/dieu-khoan-dich-vu “Điều khoản dịch vụ”; brand to /vi | Source S6; HTML VI home sample; targets 200 | Keep localized destinations. |
| EN public footer | The six general EN destinations above, plus /google-serp-rank-tracker “Google SERP Rank Tracker”, /daily-serp-tracker “Daily SERP Tracker”, /serp-tracking-for-agencies “SERP Tracking for Agencies” | SSR; 200 targets | A concise, relevant product directory. No expansion into keyword-heavy sitewide article links recommended. |
| VI public footer | The six general VI destinations above, plus /vi/cong-cu-kiem-tra-thu-hang-tu-khoa “Công cụ kiểm tra thứ hạng từ khóa”, /vi/theo-doi-thu-hang-tu-khoa-hang-ngay “Theo dõi thứ hạng từ khóa hàng ngày”, /vi/seo-rank-tracking-cho-agency “Theo dõi từ khóa cho SEO Agency” | SSR; 200 targets | Keep. Its existence must not be mistaken for a body-content hand-off. |
| EN Blog index and three EN articles; bottom CTA | /pricing “Explore rank-tracking Plans” | SSR; 200 | R2 adds a product-exploration option; retain Pricing. |
| VI Blog index and six VI articles; bottom CTA | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa “Tìm hiểu công cụ kiểm tra thứ hạng →”; /vi/bang-gia “Xem các gói dịch vụ” | SSR; both 200 | Already supports informational → commercial → plan evaluation. |
| Six product landing pages; hero, mid and final CTA | app origin /register using each page's action label; same-locale pricing using “View pricing” or “Xem bảng giá” | Anchors verified in SSR; public pricing 200 | Expected conversion endpoints. Account signup/checkout flow was not tested; no forms submitted. |
| Article/landing breadcrumbs | Locale homepage, plus locale Blog index on articles | SSR; targets 200 | Preserve descriptive navigation and current-page semantics. |
| Language control | Explicit mapped counterpart, or locale home fallback for unpaired pages | HTML anchors plus S1; mapped public targets 200 | Preserve current behavior; no fabricated translations. |

The public header/footer also link to app-origin /login and /register, using localized account labels. These are conversion/navigation links outside the audited public content graph; they are not missing commercial SEO pages.

### D3. Complete main-content link inventory for the relevant content cluster

The following **69 grouped source → destination → location relationships** were extracted from production HTML across the 19 home, product, index and article pages. Price/registration CTAs, breadcrumbs and repeated shell links are represented in D2; related posts are in D4. External reference links are identified after the table. Each existing row contains at least one actual anchor; repeated title/read links are grouped.

| Source URL | Destination URL | Existing anchor text | Current link status | Proposed improvement | Priority |
| --- | --- | --- | --- | --- | --- |
| / | /pricing | Compare Desktop and Mobile Plans → / Explore Plans | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| / | /google-serp-rank-tracker | Google SERP Rank Tracker / Explore Google SERP Rank Tracker → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| / | /daily-serp-tracker | Daily SERP Tracker / Explore Daily SERP Tracker → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| / | /serp-tracking-for-agencies | SERP Tracking for Agencies / Explore SERP Tracking for Agencies → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| /google-serp-rank-tracker | /blog/how-to-track-google-rankings | Read the Google ranking baseline guide → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /google-serp-rank-tracker | /daily-serp-tracker | Daily SERP Tracker → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /google-serp-rank-tracker | /serp-tracking-for-agencies | SERP Tracking for Agencies → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /daily-serp-tracker | /blog/how-to-monitor-keyword-ranking | Read the keyword monitoring guide → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /daily-serp-tracker | /google-serp-rank-tracker | Google SERP Rank Tracker → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /daily-serp-tracker | /serp-tracking-for-agencies | SERP Tracking for Agencies → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /serp-tracking-for-agencies | /blog/serp-tracking-for-agencies | Read the agency reporting workflow guide → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /serp-tracking-for-agencies | /google-serp-rank-tracker | Google SERP Rank Tracker → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /serp-tracking-for-agencies | /daily-serp-tracker | Daily SERP Tracker → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog | /blog/how-to-track-google-rankings | How to Track Google Rankings: A Practical Starting Guide / Read guide → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /blog | /blog/how-to-monitor-keyword-ranking | How to Monitor Keyword Ranking and Investigate Meaningful Changes / Read guide → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /blog | /blog/serp-tracking-for-agencies | SERP Tracking for Agencies: A Repeatable Client Reporting Workflow / Read guide → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi | /vi/bang-gia | So sánh các gói dịch vụ → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa / Tìm hiểu công cụ → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Theo dõi thứ hạng từ khóa hàng ngày / Tìm hiểu công cụ → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi | /vi/seo-rank-tracking-cho-agency | Theo dõi từ khóa cho SEO Agency / Tìm hiểu công cụ → | Existing; main; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi | /vi/blog | Đọc Blog tiếng Việt → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | /vi/blog/cach-theo-doi-thu-hang-google | Đọc hướng dẫn theo dõi thứ hạng Google → | Existing; guides; SSR; 200 | R3: primary help link to checking guide; baseline remains reachable from that guide. | P1 |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Theo dõi thứ hạng từ khóa hàng ngày → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | /vi/seo-rank-tracking-cho-agency | Theo dõi từ khóa cho SEO Agency → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | Đọc cách kiểm tra thứ hạng từ khóa → | Existing; guides; SSR; 200 | R3: use the dedicated daily/weekly decision guide. | P1 |
| /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/seo-rank-tracking-cho-agency | Theo dõi từ khóa cho SEO Agency → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/seo-rank-tracking-cho-agency | /vi/blog/cach-theo-doi-thu-hang-google | Đọc hướng dẫn theo dõi thứ hạng Google → | Existing; guides; SSR; 200 | R3: use the existing agency reporting guide. | P1 |
| /vi/seo-rank-tracking-cho-agency | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/seo-rank-tracking-cho-agency | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Theo dõi thứ hạng từ khóa hàng ngày → | Existing; guides; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog | /vi/blog/cach-theo-doi-thu-hang-google | Cách theo dõi thứ hạng Google cho một dự án SEO / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog | /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | Cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog | /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | Có nên theo dõi thứ hạng từ khóa Google hàng ngày? / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog | /vi/blog/cong-cu-rank-tracker-la-gi | Rank Tracker là gì? Cách theo dõi thứ hạng từ khóa hiệu quả / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | Cách kiểm tra thứ hạng từ khóa và đọc vị trí trên Google / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog | /vi/blog/serp-tracking-cho-agency | Theo dõi SERP cho agency: Quy trình báo cáo khách hàng nhất quán / Đọc hướng dẫn → | Existing; listing; SSR; 200 | Keep title + labeled read-guide link; no extra card required. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | /vi/blog/cong-cu-rank-tracker-la-gi | Rank Tracker là gì? | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | /vi/seo-rank-tracking-cho-agency | SERP SaaS dành cho SEO Agency | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | theo dõi thứ hạng từ khóa hàng ngày | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/blog/cong-cu-rank-tracker-la-gi | Rank Tracker là gì? | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cong-cu-rank-tracker-la-gi | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | công cụ kiểm tra thứ hạng từ khóa Google | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cong-cu-rank-tracker-la-gi | /vi/blog/cach-theo-doi-thu-hang-google | cách theo dõi thứ hạng Google cho một dự án SEO | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/blog/cach-theo-doi-thu-hang-google | cách theo dõi thứ hạng Google cho dự án SEO | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Công cụ kiểm tra thứ hạng từ khóa | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/bang-gia | Bảng giá | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Tìm hiểu lịch theo dõi thứ hạng hàng ngày | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | hướng dẫn kiểm tra thứ hạng từ khóa | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Khám phá công cụ kiểm tra thứ hạng từ khóa | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | Tìm hiểu theo dõi thứ hạng từ khóa hàng ngày | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/bang-gia | Bảng giá hiện hành | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/seo-rank-tracking-cho-agency | quy trình theo dõi từ khóa cho SEO Agency | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/blog/cach-theo-doi-thu-hang-google | hướng dẫn xây dựng mốc thứ hạng Google | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/seo-rank-tracking-cho-agency | SERP SaaS dành cho theo dõi thứ hạng agency | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/bang-gia | hạn mức gói và khả năng lên lịch / các gói SERP SaaS | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | cách kiểm tra thứ hạng từ khóa | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | công cụ kiểm tra thứ hạng | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /vi/blog/serp-tracking-cho-agency | /vi/theo-doi-thu-hang-tu-khoa-hang-ngay | quy trình kiểm tra theo lịch | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-monitor-keyword-ranking | /blog/how-to-track-google-rankings | how to track Google rankings | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-monitor-keyword-ranking | /pricing | Desktop and Mobile Plan limits | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-monitor-keyword-ranking | /daily-serp-tracker | recurring rank monitoring with SERP SaaS | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-monitor-keyword-ranking | /blog/serp-tracking-for-agencies | client reporting workflow | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-track-google-rankings | /pricing | current Plans / SERP SaaS Plans | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-track-google-rankings | /google-serp-rank-tracker | SERP SaaS Google rank tracker | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-track-google-rankings | /blog/how-to-monitor-keyword-ranking | how to monitor keyword ranking over time | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/how-to-track-google-rankings | /blog/serp-tracking-for-agencies | agency tracking workflow | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/serp-tracking-for-agencies | /blog/how-to-track-google-rankings | Google ranking baseline guide | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/serp-tracking-for-agencies | /serp-tracking-for-agencies | SERP SaaS for agency rank tracking | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/serp-tracking-for-agencies | /pricing | Plan limits and scheduling availability / SERP SaaS Plans | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |
| /blog/serp-tracking-for-agencies | /blog/how-to-monitor-keyword-ranking | how to monitor keyword ranking over time | Existing; body; SSR; 200 | Keep; destination matches this context. | Keep |

The EN baseline article also links to Google's Search Console performance documentation, and the EN monitoring article to Google's performance-data deep dive. These are relevant external references, not internal-link gaps. External-reference reachability was not used to infer anything about this site's indexation.

### D4. Actual related-post destinations

All destinations below are SSR links and returned 200. Each related card uses its actual article title plus a “Read guide” / “Đọc hướng dẫn” link with a specific aria-label.

| Source article | Current distinct related destinations |
| --- | --- |
| /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | /vi/blog/cach-theo-doi-thu-hang-google<br>/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay<br>/vi/blog/cong-cu-rank-tracker-la-gi |
| /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | /vi/blog/cong-cu-rank-tracker-la-gi<br>/vi/blog/cach-theo-doi-thu-hang-google<br>/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo |
| /vi/blog/cong-cu-rank-tracker-la-gi | /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay<br>/vi/blog/cach-theo-doi-thu-hang-google<br>/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo<br>/vi/blog/cach-theo-doi-thu-hang-google<br>/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay |
| /vi/blog/cach-theo-doi-thu-hang-google | /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay<br>/vi/blog/cong-cu-rank-tracker-la-gi<br>/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo |
| /vi/blog/serp-tracking-cho-agency | /vi/blog/cach-kiem-tra-thu-hang-tu-khoa<br>/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo<br>/vi/blog/cach-theo-doi-thu-hang-google |
| /blog/how-to-monitor-keyword-ranking | /blog/how-to-track-google-rankings<br>/blog/serp-tracking-for-agencies |
| /blog/how-to-track-google-rankings | /blog/how-to-monitor-keyword-ranking<br>/blog/serp-tracking-for-agencies |
| /blog/serp-tracking-for-agencies | /blog/how-to-monitor-keyword-ranking<br>/blog/how-to-track-google-rankings |

The definition and checking guides are not selected as related posts for each other. Their different tags/category and the exact-match scoring explain this; it does **not** imply that either article is undiscoverable. R4 solves the useful execution hand-off with one deliberate body link, without changing scoring or retagging every article.

## E. Search Intent Overlap Analysis

The three target pages are already substantially differentiated. They discuss similar concepts because they belong to one topic, but they have different reader jobs. There is no evidence supporting a merge, redirect, deletion or cross-page canonical.

| Page | Recommended primary intent / main keyword | Supporting concepts | Unique value to emphasize | Preserve | Clarify / differentiate | Natural next links |
| --- | --- | --- | --- | --- | --- | --- |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | Commercial investigation; “công cụ kiểm tra thứ hạng từ khóa Google” | phần mềm theo dõi thứ hạng, lịch sử, đối thủ, Desktop/Mobile, báo cáo | What the actual SERP SaaS product does, its limits, how to evaluate and start | Top 10 note, environment/device separation, stored comparisons, grouping, CSV/PDF and report-delivery caveats, Pricing/register CTAs | R1 product-identifying H1/lead; show one concrete feature/result example later; avoid becoming another generic definition or full manual tutorial | Checking tutorial for execution; Pricing for entitlement; optional definition guide for unfamiliar readers |
| /vi/blog/cong-cu-rank-tracker-la-gi | Informational definition/evaluation; “Rank Tracker là gì” | công cụ theo dõi thứ hạng là gì, cách hoạt động, Rank Tracker và GSC, cách chọn công cụ | Understanding the class of tool and when it is useful | Direct definition, manual-vs-tool motivation, measurement boundaries, GSC comparison, features and selection criteria | Keep operational summary short enough to hand execution detail to R4; the current title's “Cách theo dõi…” is a possible future copy refinement, not a demonstrated technical error | Existing contextual commercial link; proposed single-check tutorial; existing baseline guide for ongoing monitoring |
| /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | Informational task/how-to; “cách kiểm tra thứ hạng từ khóa” | kiểm tra vị trí Google, kiểm tra thủ công, URL khớp, trạng thái Top 10 | Executing and interpreting one configured or manual observation correctly | Preparation, incognito caveat, manual/tool steps, status table, URL/domain check, GSC difference | Keep its “one observation” framing. If adding an example, show query/environment/time/status/URL; do not add a second long Rank Tracker definition or product feature list | Existing commercial product link; baseline guide for history; daily product for recurring checks; Pricing |

**Observed overlap:** setup environment, manual versus tool checks, Top 10, history and GSC appear on several pages. These are necessary explanatory foundations. Preserve short shared caveats where a reader could otherwise draw the wrong conclusion.

**Possible ambiguity:** the commercial H1 uses a general tracking phrase, the definition title contains an instructional promise, and the product page has two history-oriented sections. These are candidates for clearer wording and section purpose. They do not show URL competition in Google.

**Evidence needed before calling cannibalization:** a dated, consistent query/page/device/country dataset showing persistent intent overlap, repeated URL substitution or measurable reader/traffic problems. Three impressions without a supplied time series, clicks or intent segmentation are inadequate. Keep all three URLs and their self-canonicals.

## F. New Content Opportunities

### Candidate: /vi/blog/serp-la-gi

**Editorial opportunity: justified. Demand size: unknown. Article creation: not part of this audit.**

The source inventory has no dedicated definition of SERP as a Google results page. Existing articles use SERP in the context of tracking, checking, competitor observations and reporting. A beginner asking what the acronym means does not receive a dedicated answer on /vi or in the Rank Tracker guide.

Proposed title/topic, for a separately approved milestone:

**“SERP là gì? Các thành phần của trang kết quả tìm kiếm Google và vai trò trong SEO”**

Potential topic targets, with **no claimed volume or difficulty**:

- Main: “SERP là gì”.
- Supporting: “trang kết quả tìm kiếm là gì”, “SERP Google”, “các thành phần SERP”, “kết quả tự nhiên và quảng cáo”, “phân tích SERP trong SEO”.
- Avoid turning it into a second commercial “công cụ kiểm tra thứ hạng từ khóa” landing or another full “Rank Tracker là gì” article.

Recommended editorial scope only:

1. Define the acronym and the concept of a search results page.
2. Explain how text results, ads, rich/visual elements and other result formats differ. Use Google's current [Visual Elements Gallery](https://developers.google.com/search/docs/appearance/visual-elements-gallery) as a primary factual reference; displays vary by query and context.
3. Explain how query intent, country, language and device affect what people see.
4. Distinguish SERP composition, one observed ranking and aggregated GSC performance.
5. Explain why SEO practitioners inspect SERPs, then hand readers to the appropriate tracking/checking guides.

The article must not imply that SERP SaaS tracks ads, maps, AI-generated answers or every visual SERP feature. Product examples must retain the implemented Top 10 checked scope, separate Desktop/Mobile contexts, stored observations and plan-dependent scheduling.

**Overlap boundary:** SERP = the results environment; Rank Tracker = a class of measurement tool; checking guide = executing one observation; competitor guide = comparing domains. A short cross-reference is useful; copied definitions, duplicated GSC tables or another full tool-selection tutorial are not.

| Proposed relationship, only after publication | Suggested anchor / reason |
| --- | --- |
| New SERP article → /vi/blog/cong-cu-rank-tracker-la-gi | “Rank Tracker là gì?” when introducing a tracking tool |
| New SERP article → /vi/blog/cach-kiem-tra-thu-hang-tu-khoa | “cách kiểm tra vị trí từ khóa trên Google” for the practical next task |
| New SERP article → /vi/cong-cu-kiem-tra-thu-hang-tu-khoa | A short, clearly labeled product-application paragraph; no repeated sales links |
| New SERP article → /vi/blog/cach-theo-doi-thu-hang-doi-thu-seo | “phân tích đối thủ từ dữ liệu SERP” only in the competitor-analysis context |
| Definition guide → new SERP article | Link the first genuinely useful explanation of SERP, not every acronym occurrence |
| /vi/blog → new article | Normal published card discovery; no hardcoded duplicate card |
| /vi → new article | Optional knowledge-section entry if it helps beginner navigation; retain current commercial links |

Do not add links to the candidate now: it returns 404. Do not invent an English equivalent or hreflang pair. Publication would require unique metadata, current dates, a single template H1, same-locale discovery and actual URL/link checks.

## G. Technical SEO Findings

### Verified current behavior (L1/L2 + cited source)

| Check | Result | Implication |
| --- | --- | --- |
| Sitemap | 200; 27 entries, 27 unique URLs; all 27 fetched successfully | No missing known published post in the current sitemap. Presence does not prove indexing. |
| Priority public status | All seven 200 | No current public status failure detected on priority pages. |
| Canonicals | Self-referencing across all 27, normalizing the equivalent root slash form | No demonstrated canonical conflict. Keep them. |
| Query variant | `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa?audit_probe=1` returns 200 with the clean canonical | Parameter variant is not canonically promoted. Only this sample parameter was tested. |
| Trailing slash | Product path with trailing slash returns 308 to the slashless path | Existing normalization works for the tested URL. |
| HTTP / www | Tested HTTP /vi returns 301 to HTTPS origin with explicit :443; www /vi returns 301 to non-www | These targets are equivalent to the intended commercial HTTPS host. Not a confirmed duplicate-content problem. |
| App origin | Public product path/query returns 307 to commercial origin with path/query preserved | Expected site/app separation. Temporary redirect status is existing architecture, not an urgent SEO defect established here. |
| Language preference | VI landing returns 200 despite English Accept-Language and locale=en cookie | No forced language redirect on the tested VI URL. |
| Indexability | No noindex X-Robots-Tag on the 27 sitemap pages; VI pages and commercial landings explicitly output index/follow | Some EN pages omit a robots meta tag, which is not equivalent to noindex and does not require a cosmetic “fix”. |
| Document language | 27/27 match the EN/VI route | Correct language signaling in fetched HTML. |
| Titles / descriptions | 27 distinct titles and 27 distinct descriptions | No duplicate-metadata issue detected among sitemap URLs. |
| H1 | Exactly one per fetched page | Shared article H1/frontmatter convention works. |
| Hreflang | 24 pages form 12 reciprocal en/vi/x-default sets; the 3 unpaired VI articles have no alternates | Preserve explicit pairing and fallback. Technical checks do not by themselves prove complete translation equivalence. |
| SSR links and content | Priority body/guide/listing/CTA links extracted from raw HTML; relevant text present without JS execution | Navigation is not dependent on client click handlers alone. |
| Internal targets | No unresolved same-origin content target in the extracted inventory; destinations covered by 200 crawl | No broken internal-content link found in the audited graph. |
| 404 behavior | Candidate SERP route, synthetic nonexistent VI article, and 3 untranslated English slugs all return 404 | Missing content is not being represented as an indexable “successful” article page. |
| RSS | 200; exactly 3 EN article items, no VI articles | No invented EN translations through the feed. |
| Structured data syntax | JSON parsed successfully for all present blocks | This validates JSON syntax and inspected fields, not all schema vocabulary rules or Google rich-result eligibility. |
| Relevant schema | Priority product pages use WebPage/SoftwareApplication/BreadcrumbList; all 9 articles use BlogPosting/BreadcrumbList; VI Blog index uses WebPage | Appropriate basic entity/content descriptions. EN Blog index has no JSON-LD; that is not an indexing blocker. |

Robots.txt is live and permits the public paths while excluding /app, /admin, /settings, /api and account routes. It advertises the commercial sitemap. None of these checks independently establish Google's selected canonical, current indexing state, rich-result appearance or position.

### Confirmed minor limitations and optional reviews

- **Software rich-result completeness:** the shared SoftwareApplication is a general entity description. It has no offers.price or genuine rating/review fields. Google's software-app rich result has additional requirements; current generic markup should not be described as verified rich-result eligibility. Do not invent prices, ratings or testimonials to satisfy a validator. This is P2, not an indexing outage. [Google software-app requirements](https://developers.google.com/search/docs/appearance/structured-data/software-app).
- **Article imagery:** no blog frontmatter currently supplies an image. Images can be useful recommended Article properties and product explanation assets; their absence is not proof that BlogPosting is invalid or that the page cannot rank. No Rich Results Test was run. [Google Article guidance](https://developers.google.com/search/docs/appearance/structured-data/article).
- **VI homepage breadcrumb redundancy:** S7's generic landing schema produces a locale-home item and a current-page item both pointing to /vi when called for the VI homepage. This is redundant semantic markup, not a confirmed Google validation failure. A later schema review can omit the homepage breadcrumb rather than manufacture a hierarchy.
- **Editorial alternate equivalence:** the explicit pair EN `/blog/how-to-monitor-keyword-ranking` ↔ VI `/vi/blog/cach-kiem-tra-thu-hang-tu-khoa` has different editorial emphasis: recurring monitoring versus one check. URLs and reciprocity are technically correct. Review translation/topic equivalence editorially if those articles are later revised; do not automatically unpair, redirect or change canonicals. [Google localized-version guidance](https://developers.google.com/search/docs/specialty/international/localized-versions).

### Not established by this audit

No confirmed penalty, crawl budget problem, sitewide indexing exclusion, harmful cannibalization, soft-404 pattern, JavaScript rendering failure, schema manual action or traffic loss. Current GSC account state, live Google rankings, backlinks, log-file crawl behavior and conversion performance were not available.

## H. Prioritized Recommendations

### P0 — no confirmed immediate technical problem

Do not create an emergency indexing/canonical/redirect project based on these findings. Preserve the functioning technical SEO while improving the reader journey.

### R1 — P1: Clarify the Vietnamese commercial product identity

- **Affected:** /vi/cong-cu-kiem-tra-thu-hang-tu-khoa; `frontend/src/features/marketing/vietnamese-content.ts:23–87`; existing landing/localization tests.
- **Exact proposal:** change the product H1 to “Công cụ kiểm tra thứ hạng từ khóa Google”. Make the lead explicitly identify SERP SaaS as the tool that checks the chosen keyword set and retains completed observations for review. Keep the current title, description, canonical, path and adjacent Top 10/device note. A concise candidate lead can be reviewed separately; no full page rewrite is needed.
- **Reason:** distinguish product evaluation from definitions and procedural guides.
- **Expected benefit:** clearer user expectations and a more recognizable commercial page role; no ranking/CTR guarantee.
- **Risk/trade-off:** existing copy changes can affect interpretation or snippets; keep a baseline and avoid expanding claims.
- **Acceptance:** one H1; introductory product purpose clear to a first-time visitor; no Top 100/real-time implication; original metadata/canonical and product boundaries retained; source/render checks updated only for intended copy.

### R2 — P1: Add an English product-exploration CTA beside Pricing

- **Affected:** /blog and three EN articles; `frontend/src/features/blog/blog-components.tsx:126–162`; `blog.test.tsx` and existing browser QA.
- **Exact proposal:** add one EN-only link to /google-serp-rank-tracker with anchor “Explore the Google rank tracker” in BlogCta, keeping the existing Pricing button. Match the useful product/pricing choice already offered by the VI CTA.
- **Reason:** EN hub readers currently have a main-content Pricing action but only a footer route to general product evaluation.
- **Expected benefit:** a clearer educational → product → pricing path.
- **Risk/trade-off:** one additional CTA competes for attention; keep it secondary and do not add generic body links to every article.
- **Acceptance:** new SSR href resolves 200 on EN index/articles; Pricing remains; VI CTA unchanged; no locale crossing; no new footer links.

### R3 — P1: Align the three Vietnamese landing guide slots with existing reader tasks

- **Affected:** `frontend/src/features/marketing/vietnamese-content.ts` (guide assignments near lines 87, 147 and 207); landing/localization tests.
- **Exact proposal:** use the existing single-guide API and update label/description/path together:
  - Core product → /vi/blog/cach-kiem-tra-thu-hang-tu-khoa, “Đọc cách kiểm tra thứ hạng từ khóa”.
  - Daily product → /vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay, “Khi nào nên theo dõi thứ hạng hàng ngày?”.
  - Agency product → /vi/blog/serp-tracking-cho-agency, “Đọc quy trình báo cáo thứ hạng cho agency”.
- **Reason:** the current generic baseline/checking destinations are valid, but more task-specific published guides now exist.
- **Expected benefit:** more relevant next reading, using current content rather than new pages.
- **Risk/trade-off:** the previous baseline/checking article loses a direct primary-guide link from that source. It remains discoverable through Blog, related posts and contextual links; this is an editorial trade-off, not a broken-link repair.
- **Acceptance:** all three new guide anchors appear in SSR HTML and return 200; labels describe destinations; product/pricing/sibling links remain; no shared renderer/type refactor or English mapping change is needed.

### R4 — P1: Hand execution detail from the definition guide to the checking tutorial

- **Affected:** `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`, “Rank Tracker hoạt động như thế nào?”; relevant blog tests.
- **Exact proposal:** add one contextual sentence linking to /vi/blog/cach-kiem-tra-thu-hang-tu-khoa using “cách kiểm tra thứ hạng từ khóa” when readers need a step-by-step single-check workflow. Keep the existing commercial link and GSC/Top 10 explanations.
- **Reason:** the tutorial is neither a body link nor a current related suggestion from this definition page.
- **Expected benefit:** readers can move from understanding the tool to doing the task without making the definition article duplicate the whole tutorial.
- **Risk/trade-off:** excessive interlinking can distract. Add the link at the hand-off, not repeatedly or in a forced reciprocal loop.
- **Acceptance:** one useful new same-locale body link; 200 destination; original product link retained; single H1; original publishedAt retained and only updatedAt set to the actual later edit date; source/product caveats preserved.

### R5 — P1: Disclose checked depth and illustrative preview on the English homepage

- **Affected:** `frontend/src/app/(en)/page.tsx`; EN public-page tests.
- **Exact proposal:** add a short visible Top 10 / separate-device-project note near the hero's existing plan note. Add a visible caption identifying the existing preview numbers and domains as illustrative interface data rather than customer performance or verified plan limits.
- **Reason:** Top 10 is absent from this page's main source copy, while its visible mockup includes numerical usage/position examples.
- **Expected benefit:** more accurate product expectations and clearer distinction between example UI and evidence.
- **Risk/trade-off:** extra hero copy can add visual weight. Keep it brief and test responsive wrapping.
- **Acceptance:** visible, accessible caption and Top 10 note in SSR; no claim of checking exact out-of-depth ranks or guaranteed real-time data; examples not labeled real; no changes to actual plans, account or billing behavior.

### R6 — P2: Add one genuine product example before expanding feature prose

- **Affected:** primarily the VI product landing; later the EN landing/checking guide if useful. Source integration would use existing marketing sections or blog image conventions, with a real asset supplied separately.
- **Exact proposal:** capture an authorized, anonymized completed-check or ranking-history example. Explain query, device, environment, timestamp, observed URL/status and Top 10 scope in a caption and short walkthrough. Prefer one useful example over a gallery.
- **Reason:** source and live priority pages have no main-content product screenshots; copy and illustrative tables carry the explanation alone.
- **Expected benefit:** readers can see how a product observation differs from an abstract feature claim.
- **Risk/trade-off:** privacy, asset weight, image maintenance and UI drift. No invented screenshot, testimonial or customer result; a safe demo asset is a dependency.
- **Acceptance:** image is genuine, authorized and redacted; alt/caption meaningful; dimensions/responsive rendering correct; small-screen use is legible; caption makes context/limits explicit.

### R7 — P2: Commission the dedicated SERP definition as a separate content milestone

- **Affected:** candidate `frontend/content/blog/vi/serp-la-gi.md`; contextual links only after publication.
- **Exact proposal:** approve the brief in F, then independently write/review/publish a distinct SERP definition article using existing blog conventions. Do not create an English pair without a genuine counterpart.
- **Reason:** confirmed topic gap, supported by a small historical query observation rather than proven demand volume.
- **Expected benefit:** a more appropriate beginner destination and a clearer conceptual entry to the existing content cluster.
- **Risk/trade-off:** demand may remain small; duplicated tool explanations could dilute the editorial distinction.
- **Acceptance:** editorial review confirms SERP-vs-tool distinction; no fabricated volume or feature claims; unique metadata, actual publication dates, single H1, working contextual links, one listing/sitemap entry and correct unpaired behavior.

### R8 — P2: Keep technical/schema refinement separate and evidence-led

- **Affected:** `frontend/src/features/marketing/seo.ts`, `public-locales.ts` and the two differently emphasized paired articles only if a later review justifies edits.
- **Exact proposal:** document current SoftwareApplication as general entity markup; do not promise software rich results. Consider removing redundant VI homepage breadcrumbs in a small schema-only change. Review the monitoring/checking language pair's editorial equivalence before any future translation revisions, without automatically changing URLs or alternates.
- **Reason:** syntax/reciprocity checks are not the same as semantic completeness or translation equivalence.
- **Expected benefit:** more accurate structured-data and localization expectations.
- **Risk/trade-off:** premature schema or locale-map changes can regress otherwise correct SEO. Genuine offer/review evidence is required before rich-result work.
- **Acceptance:** no fabricated ratings/offers; affected JSON-LD revalidated if changed; all existing canonical/status/hreflang regression checks preserved; any alternate-map proposal reviewed separately.

## I. Proposed Implementation Milestone

**Milestone: “Clarify the existing product pages and contextual reader journeys.”**

A small, separately authorized implementation can address R1–R5:

1. Edit the VI commercial H1/lead, keeping measurement limits and current metadata.
2. Update the three existing VI guide assignments with matching labels/descriptions.
3. Add one product-exploration link to the EN Blog CTA while retaining Pricing.
4. Add one definition → checking-guide contextual body link.
5. Add the EN homepage Top 10 disclosure and illustrative-preview caption.
6. Update the existing focused content/marketing tests and verification notes.

Expected application/content edit targets are one VI content configuration file, one EN homepage, one shared Blog CTA component and one Markdown article, plus relevant tests. No new content model, global taxonomy rewrite or related-post algorithm change is needed.

**Excluded:** new SERP article, screenshot production, redirects, URL/canonical/hreflang changes, broad metadata rewriting, pricing/authentication/billing/SePay/backend/worker work, and deployment without separate authorization. R6–R8 remain optional follow-ups.

**Acceptance for the milestone:**

- All 27 current public paths retain their intended status, language and self-canonical; sitemap count remains 27 and English RSS remains three items.
- Three existing unpaired VI articles still have no invented English alternate; twelve explicit pairs remain reciprocal.
- The exact new/reassigned links are present in SSR HTML, point to 200 destinations and use same-locale meaningful anchors.
- The three keyword-tracking pages remain clearly commercial / definition / single-check respectively; their useful content is retained.
- No out-of-Top-10 position claims, guaranteed real-time language or unsupported scheduling promises.
- Existing content prebuild, relevant tests, lint, typecheck, format and production build pass in an appropriate Node environment. Check the changed areas at 375, 768, 1024 and 1440 px, including no-JS content and keyboard navigation; run existing axe coverage where available.
- Record outcomes honestly; do not infer traffic or ranking gains from a passing implementation.

For later measurement, preserve a dated GSC baseline with exact date/search-type/country/device/query filters and query-to-page data. Review comparable periods when sufficient observations accumulate, retaining click/impression denominators and anomalies. If counts remain tiny, keep conclusions descriptive. A separate URL Inspection check can verify current indexed/canonical state; a query table alone cannot do so.

## J. Verification and Limitations

### Evidence types

- **U1 — supplied GSC observations:** historical counts and indexing inspection assertions from the user's audit brief. Not independently accessed or re-exported.
- **S1–S10 — inspected current repository source:** paths identified in B and exact targets in H, all at the recorded baseline commit.
- **L1 — direct production HTML crawl, 2026-10-29:** sitemap fetched and parsed; 27 URLs fetched using Python 3.15 stdlib HTTPS requests, four concurrent read-only workers; HTML parsed without executing scripts. Extracted metadata, H1/H2/H3, main images, JSON-LD, anchors, locations and locale alternatives. The report embeds the relevant metadata and link inventory; no extra evidence files were written.
- **L2 — direct HTTP probes:** redirects disabled for inspection, with English language preference and locale cookie. Robots/RSS parsed; missing-route and duplicate-variant behavior recorded in G.
- **External primary documentation:** Google links cited where their semantics or eligibility rules are used. Google's web browsing connector could not open the site itself, but direct HTTPS requests succeeded; connector access failure was not treated as a site problem.

### Commands / checks performed

Read-only repository commands included:

~~~text
git status --short
git rev-parse HEAD
rg --files -g AGENTS.md -g !node_modules -g !.git -g !.next
rg -n <targeted patterns> <public route, content, SEO and link sources>
Get-Content -Raw -Encoding UTF8 <inspected source/content files>
Get-Command node*,npm*,python*,uv*
~~~

Inspected route wrappers for priority EN/VI landings, indexes and dynamic articles; homepage components and root layouts; shared public shell/language selector; metadata/schema helpers; all nine Markdown articles' content and links; parser, related scoring, sitemap, robots, RSS and proxy; and the narrow backend product-boundary sources listed in B. No repository AGENTS.md was found in the file search.

Additional direct-HTTP results:

| Probe | Observed result |
| --- | --- |
| /robots.txt | 200; public allowed; app/account paths excluded; canonical sitemap advertised |
| /feed.xml | 200; three EN items |
| /vi/blog/serp-la-gi | 404 |
| /vi/blog/nonexistent-seo-audit-20261029 | 404 |
| /blog/cong-cu-rank-tracker-la-gi | 404 |
| /blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay | 404 |
| /blog/cach-theo-doi-thu-hang-doi-thu-seo | 404 |
| /vi/cong-cu-kiem-tra-thu-hang-tu-khoa/ | 308 → /vi/cong-cu-kiem-tra-thu-hang-tu-khoa |
| Product URL with ?audit_probe=1 | 200; clean self-canonical |
| http://serpsaas.com/vi | 301 → https://serpsaas.com:443/vi |
| https://www.serpsaas.com/vi | 301 → https://serpsaas.com/vi |
| App-origin product URL with ?audit_probe=1 | 307 → commercial product URL with query preserved |
| VI product URL with Accept-Language: en and locale=en | 200; no forced locale redirect |

The HTML inventory found no unresolved same-origin content href and no unexpected cross-language link in the extracted body/main/guide/related/CTA locations. Language controls were assessed separately as intentional locale navigation. An HTML parse confirms an href's presence, not visual accessibility or a completed conversion.

### Local runtime limitations

Node and npm were not available on PATH. The former temporary Node executable from the earlier deployment session was no longer present. A direct invocation of that old path failed before any build/check ran. No new runtime was installed and no source or dependency file was changed to work around it.

Accordingly **npm prebuild/tests/lint/typecheck/build and local browser rendering were not rerun during this audit**. The existing validation and rendering code was inspected, and current production SSR/status/link checks were performed instead. The earlier October 21 deployment/test evidence is historical and is not claimed as a fresh October 29 run.

No authenticated app workflow, real product account, SERP-provider request, client report, live keyword check, GSC API, Google URL Inspection, Rich Results Test, full schema validator, Core Web Vitals, axe run, screen-reader test or JS hydration regression was performed. Pricing catalog behavior and checkout were outside scope; only public link presence and public page responses were inspected.

Sitemap coverage is the crawl boundary, supplemented by the explicit variant/missing-page probes. It does not exhaust every possible parameter, hostname, path case or route outside the public sitemap. The crawl does not establish Google's selected canonical or that all public URLs are indexed.

### Audit-only change verification

The working tree was clean at the start. Only `docs/verification-seo-content-internal-link-audit.md` was created for this task. Repository source, editorial files, metadata, routes and infrastructure remain unchanged. No deployment, indexing request, commit or push was performed.
