# Milestone 7E — Reports & Export

**Project:** SERP SaaS
**Audience:** Codex implementation agent
**Status:** Implementation specification
**Dependencies:** M1–M7A and M7B completed; M7C Keyword Organization implemented. M7C final visual QA and M7B.1 performance optimization are independent follow-ups.
**Deliberately deferred:** M7D Alerts, M7F Competitor Analytics, Payment Gateway, Developer API, API Keys, API Docs.

---

## 1. Objective

Enable a customer to turn existing persisted ranking observations into useful reports without inspecting every keyword. Implement three report delivery modes in order:

1. **CSV export** of ranking comparison rows and history.
2. **Downloadable PDF report** summarizing project ranking performance for a selected reporting period.
3. **Scheduled PDF reports by email** (weekly/monthly), sent to verified account email and optional explicitly authorized recipients, using an independently configurable email-delivery adapter.

M7E is a **read-only reporting layer** on top of existing analytics. Viewing, generating, downloading, scheduling, or emailing reports must never trigger SERP checks, create RankCheck Jobs, consume customer keyword-check quota, or consume SERP provider credits.

The first usable vertical slice is manual CSV and PDF. Scheduled delivery follows after those are correct and tested. Do not let missing production email credentials block manual exports.

## 2. Product scope and user journeys

### 2.1 Project reports

Add a **Reports** entry within an existing Project context, following current navigation patterns. Preferred route:

```text
/app/projects/{projectId}/reports
```

The page shows:

- Project name, fixed search environment/device, reporting period, tracked-site selector, optional Group/Tag filters, and report timezone explanation.
- A reporting preview with period summary, ranking distribution, movements, and a small sample of included keywords.
- `Export CSV` and `Generate PDF` actions.
- Report generation status and recently generated reports for that Project.
- A **Scheduled reports** section when delivery infrastructure is configured; otherwise an honest configuration-unavailable state, not a fake success state.

### 2.2 Manual reports

Flow:

```text
Open Project → Reports
→ select preset period or custom UTC date range
→ optionally select Tracked Site / Group / Tags
→ preview report parameters
→ export CSV or request PDF
→ download finished artifact
```

Do not make a SERP provider request to “freshen” a report. Display `Data as of` and the latest successful observation timestamp.

### 2.3 Recurring reports

Flow:

```text
Configure weekly/monthly report
→ select destination and filters
→ save schedule
→ scheduler enqueues a durable report job
→ render using persisted ranking data
→ email link or attachment, per configured delivery policy
→ show last run, next run, status, and history
```

A report schedule is separate from the Project's **rank-check schedule**. Its existence does not imply new rankings will be collected. State this clearly in the UI.

## 3. Explicit non-goals

Do **not** implement in M7E:

- Stripe, PayPal, crypto, automatic recurring billing, invoices, taxes, refunds.
- Public Developer API, customer API Keys, or API Docs.
- M7D threshold alerts, Slack/Telegram notifications, or generic notification center.
- Competitor share-of-voice reports or new competitor tracking logic.
- Keyword research, search volume, keyword difficulty, backlinks, crawl/site audit, AI SEO recommendations.
- White-label/domain-branded customer portals or public report sharing.
- Excel/XLSX export or Google Sheets integration; CSV is required.
- New SERP provider calls or changes to M4/M5 rank-check execution.
- A new report-specific subscription/usage quota unless the existing Plan catalog already defines one. Report generation must not debit keyword-check quota.

## 4. Architectural invariants

Preserve existing stack and conventions:

- FastAPI + Pydantic v2 + SQLAlchemy 2 async + PostgreSQL; repository/service/router separation.
- Next.js App Router, TypeScript, TanStack Query, M6.5 design-system components.
- User-only tenancy; **no Organization/Workspace/Team** additions.
- Ownership is derived exclusively from `current_user.id`; never accept client-supplied `user_id` as authorization.
- Reuse M7A/M7B canonical successful-ranking comparison logic and M7C Group/Tag filters. Do not implement a conflicting report-only ranking calculation.
- Distinguish an absent observation from a successful “not found within checked depth” observation and from a failed check.
- Use stored check depth and effective-depth-aware terminology. Current standard depth is generally Top 10, so display `Top 3`, `4–10`, `Not found in Top 10`, and `Entered/Left Top 10` when appropriate. Never invent Top 20/Top 100 or global “lost ranking.”
- Reuse existing background job/queue infrastructure where appropriate, but keep report job types/attempts separate from RankCheck Jobs and customer ranking usage.
- Do not store generated files in PostgreSQL blobs. Use a storage abstraction (local development filesystem; cloud object storage implementation for production).

## 5. Reporting semantics — specify before coding

The reporting period describes a **comparison window**, not evidence that checks were performed every day.

Supported presets:

```text
Last 7 days
Last 30 days (default)
Last 90 days
Custom UTC start/end dates
```

A weekly email report covers the previous **completed** seven-day reporting window; a monthly email report covers the previous completed calendar month in the configured report timezone. Use a documented calendar boundary and convert to UTC for queries. Default timezone `UTC` until a per-user or per-report timezone field is explicitly supported; do not infer from browser locale or deployment server.

Reuse M7A/M7B comparison selection for manual reports when semantically equivalent:

- Current/end observation: latest successful comparable observation at or before the report end boundary.
- Baseline observation: latest successful comparable observation at or before report start boundary.
- If baseline is missing, preserve existing M7A fallback (`earliest_in_range`) where appropriate and expose `comparison_basis` to UI, PDF, CSV metadata, and tests. Never silently present it as a complete-period comparison.
- If the end observation is missing, explicitly mark no data for that keyword/Tracked Site.
- Failed RankChecks are excluded; they must not become `not_found_in_depth` or a decline.
- Desktop and Mobile are isolated by the Project's fixed device/environment.
- When multiple successful checks exist on one date, use a deterministic policy consistent with M7A daily charts; never silently count each as a distinct keyword in aggregate totals.
- Existing M7C archive semantics apply: default report scope is **active Keywords and active Tracked Sites** unless there is an explicit product decision to include archived items. Label the scope in metadata. Do not erase historical data.

**Important:** Audit the actual repository's M7A/M7B comparison APIs and depth logic first. Where this document offers a preferred behavior that conflicts with the implemented canonical semantics, surface that discrepancy before coding and use one documented canonical approach, not duplicate report logic.

## 6. Filters and report definition

A report definition supports:

```text
project_id                   required; tenant-owned
period                      7d | 30d | 90d | custom
start_date, end_date        only for custom
tracked_site_id             optional, tenant-owned
keyword_group_id            optional, same Project
keyword_tag_ids             optional, same Project
tag_match                   any | all
include_keyword_details     default true for CSV; configurable for PDF
```

Re-use M7B filters and M7C ANY/ALL Tag semantics. Reject cross-Project Group/Tag combinations rather than silently broadening scope. Persist the **resolved filters and period boundaries** in the immutable generated report metadata so a subsequent Group rename or filter change does not rewrite what the report claimed.

Reports should indicate `No matching Keywords` separately from `Matching Keywords with no ranking observations`.

## 7. Metrics and report structure

### 7.1 Shared metrics

Compute from the canonical comparison dataset:

- Total included active Keywords, distinct Tracked Sites represented, reporting period, effective observed checked depth, latest successful check timestamp.
- Rank distribution for supported buckets only.
- Improved / Declined / Unchanged numeric movements.
- Entered / Left checked depth (categorical).
- `no_previous_data` / `never_checked` distinctly.
- Biggest Winners and Biggest Losers where both comparison and current numeric positions exist.
- Optional keyword ranking trend series for charts, using actual successful observations (no interpolation).

Every summary count must reconcile against the documented row grain. **Choose and state the grain**: preferably one row per Keyword × selected Tracked Site, since a Keyword can match multiple user-owned Tracked Sites. Avoid presenting per-site match rows as a count of distinct Keywords. If no site filter is selected, label report totals clearly and include both `distinct_keywords` and `keyword_site_pairs` when needed.

### 7.2 PDF sections

Recommended PDF order:

1. Cover/header: product name, Project, device/environment, period, generated timestamp (UTC), `Data as of`, filters.
2. Executive summary KPI cards (accurately labelled).
3. Ranking distribution chart/table, checked-depth-aware.
4. Movement summary and Entered/Left checked-depth counts.
5. Biggest Winners and Biggest Losers (top 10 by deterministic movement sorting).
6. Historical trend chart **only if supported by real persisted time-series data**; provide a textual/data-table alternative for accessibility.
7. Keyword details (bounded paginated or appendix-style table with clear continuation across pages).
8. Methodology footnote: comparison selection, successful checks only, checked-depth limitations, timezone, active/archived scope, and `comparison_basis` fallback when used.

For a Project with no observations, generate a truthful empty report, not misleading zeros that imply a successful check. Show `No ranking observations available for this period`.

### 7.3 CSV exports

Provide at minimum two export types:

**Comparison CSV:** one row per Keyword × Tracked Site in the filtered result set. Stable columns:

```text
project_name,device,keyword,keyword_id,tracked_site_name,tracked_site_id,
report_start_utc,report_end_utc,comparison_checked_at_utc,
comparison_position,comparison_depth,current_checked_at_utc,
current_position,current_depth,movement_type,numeric_change,
comparison_basis,keyword_group,keyword_tags
```

**History CSV:** one row per successful Keyword × Tracked Site observation within the requested window, with `checked_at_utc`, `position`, `checked_depth`, `status`, `rank_check_id`; optional Group/Tag metadata. History must not invent daily records for unchecked dates.

Document whether comparison CSV exports all matching rows or only the current Explorer page: **M7E exports all filtered matching rows**, with explicit server-side safety limits and a job flow for large datasets; never silently export only the 50 visible rows. Both CSV types require a UTF-8 header row and consistent column order. Encode Tag lists deterministically (e.g., semicolon-separated within a quoted CSV field). Empty numeric positions remain empty cells with an explicit status column.

Protect spreadsheet users against CSV formula injection: prefix text cells beginning with `=`, `+`, `-`, `@`, tab or carriage return according to a tested spreadsheet-safe CSV policy while keeping downloaded data understandable. Properly quote delimiters/newlines and preserve Unicode Vietnamese Keywords.

## 8. Manual report API (internal authenticated product API)

The following routes are internal application APIs, **not** the future public Developer API.

Suggested routes, adapted to existing FastAPI route conventions:

```text
GET  /api/v1/projects/{project_id}/reports/preview
POST /api/v1/projects/{project_id}/reports
GET  /api/v1/projects/{project_id}/reports
GET  /api/v1/projects/{project_id}/reports/{report_id}
GET  /api/v1/projects/{project_id}/reports/{report_id}/download
POST /api/v1/projects/{project_id}/reports/{report_id}/retry
```

- `preview`: lightweight, bounded metadata and summary only; no artifact generation.
- `POST reports`: accepts validated report type (`comparison_csv`, `history_csv`, `project_pdf`) and filters/period; returns report/job ID plus `queued`/`ready` state. Add idempotency key support so a double-click/retry does not create duplicate equivalent jobs.
- `GET reports`: cursor-paginated recent reports, newest first, including type, resolved period, status, created time, expiry time, error-safe reason, and filters.
- `download`: ownership-authorized, artifact-ready only; either streams with correct headers or issues short-lived, scoped object-storage signed URL. Do not expose permanent public bucket URLs.
- `retry`: allowed only for well-defined failed/transient states with bounded attempts. Prevent duplicate concurrent jobs.

Use appropriate HTTP codes and stable error codes (`REPORT_NOT_FOUND`, `REPORT_NOT_READY`, `INVALID_REPORT_RANGE`, `REPORT_TOO_LARGE`, `REPORT_EXPIRED`, `REPORT_GENERATION_FAILED`, `REPORT_DELIVERY_UNAVAILABLE`, etc.). A cross-tenant report ID must be indistinguishable from an absent report.

## 9. Report data model

Inspect current schema before adding tables. Suggested new migration (`0011_reports` **only if** `0010_keyword_organization` remains the actual current head; never hard-code parent blindly):

### `generated_reports`

```text
id UUID PK
user_id UUID NOT NULL FK
project_id UUID NOT NULL FK
report_type ENUM/TEXT validated
status queued | running | ready | failed | expired
period_start_utc TIMESTAMPTZ
period_end_utc TIMESTAMPTZ
filters_snapshot JSONB
metrics_snapshot JSONB nullable  # limited, safe summary only
schema_version INTEGER
storage_key TEXT nullable        # internal opaque key, never public URL
mime_type TEXT nullable
byte_size BIGINT nullable
created_at, started_at, completed_at, expires_at
error_code TEXT nullable
attempt_count INTEGER
idempotency_key TEXT nullable
```

Add appropriate ownership, status, recent-history, and idempotency indexes/constraints. Consider retention and cleanup strategy from the start. Do not store full keyword arrays in `metrics_snapshot` when the source/artifact already exists.

### `report_schedules`

```text
id UUID PK
user_id UUID NOT NULL FK
project_id UUID NOT NULL FK
name TEXT
report_type project_pdf             # CSV optional later
frequency weekly | monthly
report_timezone TEXT                # default UTC
scheduled_hour INTEGER              # user-defined, not silently invented
weekday INTEGER nullable            # weekly
month_day INTEGER nullable          # monthly, define end-of-month policy
filters JSONB
recipient_emails JSONB/child table
active BOOLEAN
next_run_at_utc TIMESTAMPTZ
last_run_at_utc TIMESTAMPTZ nullable
created_at, updated_at
```

### `report_delivery_attempts`

Track `generated_report_id`, `report_schedule_id` (nullable), recipient or recipient-safe digest, provider delivery identifier (if available), status, attempt number, timestamps and **sanitized** errors. Do not store SMTP passwords, provider tokens or personal message content in audit rows.

A separate `report_jobs` table is optional if `generated_reports` safely captures durable job state and attempts; do not create redundant state machines.

## 10. Generation and storage architecture

Use one report-generation service for manual and scheduled reports:

```text
FastAPI (authenticated user) / scheduled dispatcher
→ ReportService validates access + resolved period/filters
→ durable GeneratedReport row (queued)
→ report task queue (local adapter in development; production adapter consistent with M5)
→ report worker fetches canonical analytics snapshot
→ CSV/PDF renderer
→ private artifact storage
→ mark ready / delivery enqueue if scheduled
```

Implementation rules:

- Use a **report-specific task type/handler**, separate from rank-check execution; do not reuse `RankCheckExecutionService` for a report.
- Treat queue as at-least-once. Use deterministic job identity or idempotency keys, transactional state transitions, leases and bounded retries. A repeated delivery must not produce multiple unrelated artifacts or duplicate customer email messages when avoidable.
- Generate from a consistent read snapshot where practical; store `data_as_of`/resolved observation boundary. Do not allow a report to change mid-render when new checks complete.
- Apply bounded output limits and timeouts. Large reports must run asynchronously rather than hold a web request open.
- Support cancellation or expiry of stale jobs when feasible; never leave `running` permanently after a worker crash.
- PDF rendering may use server-side HTML templates plus a single production-compatible PDF engine. Pin versions; ensure fonts support Vietnamese text. Do not rely on client browser printing for scheduled PDFs.
- Store artifacts privately under opaque per-tenant paths; never construct public paths directly from user-supplied names.
- Provide dev/test storage under a documented local directory or mounted volume; production implementation should use the deployment's private object-storage service. Never depend on ephemeral Cloud Run container filesystem for durable artifacts.

## 11. Report retention and limits

Define explicit configurable defaults (not baked into pricing):

```text
REPORT_MAX_RANGE_DAYS=365
REPORT_MAX_CSV_ROWS=100000
REPORT_MAX_PDF_DETAIL_ROWS=1000
REPORT_ARTIFACT_RETENTION_DAYS=30
REPORT_MAX_CONCURRENT_PER_USER=2
```

These are **proposed engineering safeguards**, not Plan entitlements. Validate product needs and provider constraints during implementation. Enforce backend-side. If a report is truncated by a documented PDF appendix cap, visibly disclose it and offer full CSV instead; never silently truncate. If CSV exceeds permitted size, return a clear error with guidance to narrow filters/period. A expired download should return an actionable state and allow regeneration.

## 12. Scheduled delivery and email

Scheduled reports are not ranking alerts. Start with `weekly` and `monthly` PDF email delivery. Email should contain a concise project/period summary and either a PDF attachment (when below an explicit size cap) or a short-lived authenticated download link. Prefer authenticated download links when confidentiality/security requires them; never email a permanent public storage URL.

Email adapter:

```text
ReportEmailSender
├── FakeEmailSender (tests/local, no external sends)
└── ProductionEmailSender (configured provider or approved SMTP)
```

Do not pick an email provider or add credentials without an explicit configuration path. If production credentials are missing, manual generation remains functional; scheduling can show `Email delivery not configured` and must not falsely claim to have sent anything.

Recipients: default the account's verified email. If supporting additional recipients, require explicit user confirmation/verification and account-level access policy before exposing report content externally. For initial M7E, it is acceptable to **limit scheduled delivery to the verified account email** and defer arbitrary recipients to avoid accidental data leakage; document which mode was implemented.

Add minimal user-visible controls: create/edit/pause/delete schedule, show next run, last run, last delivery status, and sanitized failure reason. Limit number of active schedules per Project via a configurable safeguard.

Dispatcher:

- Consistent with M5 single-dispatcher design; leases/locking prevent duplicate dispatch under multiple replicas.
- Due schedules enqueue jobs using a deterministic `(schedule_id, period_start, period_end)` idempotency key.
- Define weekly/monthly calendar boundaries in selected timezone; handle DST if timezone configurable and month-end dates (e.g., day 31 in February) deterministically.
- Retry transient render/storage/email failures with bounded exponential backoff; distinguish permanent invalid-recipient/configuration errors.
- Delivery completion is not the same as artifact generation completion. Track them separately.
- Do not automatically regenerate an entire report for an email-only transient failure if a ready artifact is still valid.

## 13. Frontend UX and design

Use M6.5 shared design system. Proposed sections:

```text
Reports
 ├── Report configuration
 ├── Preview (summary and scoped keyword count)
 ├── Export CSV / Generate PDF
 ├── Recent reports [status, period, generated, Download / Retry]
 └── Scheduled reports [optional; configuration-aware]
```

UI requirements:

- Distinguish `Generate PDF` (primary CTA in report context) from secondary export/download text links where appropriate.
- `Generate` must enter loading/queued state and prevent accidental double submission; polling should be bounded and stop on ready/failure.
- Display `Report uses existing ranking data; no new rank check is run`.
- Show effective checked depth and methodology note directly in preview.
- Reuse existing Group/Tag filters and `ANY/ALL` behavior; correctly reset dependent selectors when Project changes.
- Empty, loading, error and retry states use existing primitives and do not blank the whole Project page.
- No horizontal overflow at 375px; mobile tables stack sensibly; PDFs are generated at print-friendly page dimensions independent of mobile viewport.
- Confirm before schedule deletion. Surface delivery disabled/misconfigured states without exposing secrets.
- Keep downloaded filenames safe and predictable, e.g. `project-slug-ranking-report-2026-09-01_2026-09-30.pdf`.

## 14. Security, privacy, and abuse resistance

- Authenticate **every** report, preview, schedule, and download endpoint. Re-check ownership at execution time, not only when enqueuing.
- Require Project ownership and same-Project Group/Tag membership; Tracked Site must be tenant-owned.
- Prevent insecure direct object references (IDOR), report enumeration and cross-tenant downloads.
- Generated artifacts must be stored privately and deleted or made unavailable after expiry; log access where useful.
- Never embed access tokens, internal storage keys, SMTP credentials or full private email addresses in user-visible logs.
- Sanitize user-created Project/Keyword/Tag names for HTML/PDF, email, CSV, and filenames. Guard against HTML/script injection and CSV formula injection.
- Rate-limit generation and schedule-management actions and enforce concurrency/output limits.
- Expose recipient emails and delivery logs only to the owning account (or platform Admin under existing authorized policies).
- Do not send project ranking data to a third party merely because an unverified email address was entered.

## 15. Performance requirements

M7B Explorer was reported around 1.5–2 seconds for broad local queries at 1,000 Keywords; M7B.1 optimization remains a separate incomplete milestone. **Do not interpret one successful M7C local benchmark as a completed M7B.1 optimization.**

M7E must therefore avoid making multiple heavyweight Explorer requests per PDF section. Prefer one canonical bounded report query/snapshot, then derive charts and tables from it or perform a small documented number of bounded set-based queries.

Benchmark at minimum:

```text
1,000 Keywords
2 Tracked Sites
2 successful observations per Keyword (minimum)
10 Groups
20 Tags with mixed assignments
CSV comparison export
CSV history export
PDF report (including an appendix)
filtered report by Group + Tags ANY/ALL
```

Record query count, generation time, peak memory where feasible, artifact size and email queue/delivery latency in local tests. No per-Keyword database calls or network calls. Streaming CSV is preferred for large exports; PDF detail rows must be bounded and explicit.

## 16. Migration and compatibility

Before coding, inspect current Alembic head and existing background job, storage, email, and report components. `0010_keyword_organization` is the M7C reported head, but choose the actual next migration ID and parent from the repository state. Add migration only for genuinely new durable data. Preserve all existing subscription, ranking and Keyword organization data. Upgrade/downgrade/upgrade and schema-drift tests must pass.

Do not change public Pricing, billing limits, existing manual bank transfer behavior or M7A/M7B metric definitions. The Reporting route is an authenticated product feature, **not a public Developer API**.

## 17. Test plan — backend

Cover at least:

- Preview for empty Project, observed Project, no matching filters, and filters with no observations.
- Successful-only RankChecks; failed provider calls excluded.
- Correct depth-aware distribution and entered/left terminology; no fake positions.
- Distinct Keyword vs Keyword×Tracked Site metric grain and reconciliation.
- Preset/custom period boundaries; baseline fallback; missing baseline/end observations; UTC date semantics.
- Group/Tag `ANY/ALL`, same-Project constraints, archived/inactive defaults.
- Exact CSV column schema/order, Unicode, delimiter/newline escaping, formula injection, stable ordering, status for empty positions.
- Full filtered CSV across multiple Explorer pages; safety-limit behavior; no silent truncation.
- PDF render success, meaningful empty PDF, long names/Vietnamese fonts, multi-page layout, page numbers, methodology text and honest appendix cap.
- Idempotent creation; repeated task delivery; transient retry; crashed-worker lease recovery; expiration and cleanup.
- Missing/expired artifacts; authenticated download headers; foreign-user Project/report/schedule/site/group/tag access.
- Weekly/monthly schedule due calculations (including month end and timezone/DST if supported), repeat dispatch idempotency, pause/delete behavior.
- Fake email sender, transient/permanent delivery errors, no duplicate send on retry where enforceable, missing provider configuration.
- Analytics GET/exports do not enqueue RankChecks, reserve quota, or call SERP providers.

## 18. Test plan — frontend and browser

Frontend component/integration tests:

- Filters and report preview; date validation; Group/Tag ANY/ALL; selected Tracked Site.
- Preview checked-depth language; zero/no-data distinction.
- CSV and PDF action behavior, duplicate-click protection, queued/running/ready/failed/expired status handling.
- Download authorization/error handling and regeneration prompt.
- Recent reports pagination and download links.
- Schedule creation/edit/pause/delete (if scheduling implemented); delivery-unavailable state.
- Accessible form labels, loading announcements, keyboard navigation, focus management, file action semantics.

Browser verification on **375, 768, 1024, 1280, and 1440px**:

```text
Create Project or load deterministic fixture
→ populate successful ranking observations using fake provider / direct test fixtures
→ open Reports
→ preview 7D/30D/90D and custom dates
→ apply site/group/tags filters
→ generate and download comparison CSV
→ generate and download history CSV
→ generate PDF, wait for ready, download, inspect content
→ create/modify/pause schedule with fake email adapter
→ verify due scheduled report and delivery log (if scheduling implemented)
→ test empty/error/expired conditions
```

Inspect real PDF output visually and verify Unicode rendering, charts/tables/page breaks. Record screenshots, downloads, checksums or text assertions, and actual browser outcomes; do not claim interactive responsive QA passed if Chromium/Playwright is unavailable. **Before any local QA, assert both backend and worker use a fake SERP provider and local task queue.** Zero real provider credits is required.

## 19. Definition of Done

### Manual export — mandatory

- [ ] Project Reports route and filters implemented.
- [ ] Correct and clearly documented report grain, period selection, and checked-depth semantics.
- [ ] Comparison CSV exports all filtered matching rows; not just current Explorer page.
- [ ] History CSV exports actual persisted successful observations.
- [ ] CSV escapes Unicode/special cells and neutralizes formula injection.
- [ ] PDF contains accurate summary, distribution, movement, winners/losers, optional trend, details/methodology.
- [ ] Manual generation works without production email configuration.
- [ ] Jobs are durable/idempotent; downloads are authenticated and private; artifacts expire.
- [ ] No SERP/RankCheck usage is incurred by report views/exports.

### Scheduled delivery — mandatory for full M7E acceptance

- [ ] Weekly and monthly scheduled PDF reports supported.
- [ ] Schedule is independent of rank-check schedule.
- [ ] Verified-account email delivery or explicitly authorized recipient policy documented.
- [ ] Due dispatcher is idempotent, retry-aware and safe for multiple replicas.
- [ ] Delivery attempts, last run, next run, and failure states are visible.
- [ ] Fake adapter is used for testing; production email adapter is configuration-driven.
- [ ] No email is sent externally during automated QA.

### Engineering and QA

- [ ] Tenant-isolation and report-download authorization tests pass.
- [ ] SQL query-count/performance evidence recorded for 1,000+ Keywords.
- [ ] Migration upgrade/downgrade/upgrade and schema drift pass where applicable.
- [ ] Backend tests, Ruff, mypy, frontend tests, ESLint, Prettier, TypeScript and production build pass.
- [ ] Docker backend/worker/frontend/PostgreSQL/Redis healthy in verification environment.
- [ ] Browser QA at required widths completed or reported as incomplete, not assumed.
- [ ] PDFs visually inspected; local CSV files validated.
- [ ] Zero real SERP provider credits consumed.
- [ ] No Payment Gateway, Developer API or API Docs work introduced.

## 20. Required verification artifact

Create:

```text
docs/verification-milestone-7e.md
```

Include:

1. Files/routes/models/migrations changed.
2. Actual report row grain, date-boundary and comparison semantics.
3. Checked-depth behavior and exact labels used at depth 10.
4. CSV schemas, PDF sections/sample artifact and retention policy.
5. Scheduled delivery architecture, actual email adapter/configuration, security policy and delivery retry/idempotency evidence.
6. Exact executed command results: backend/frontend tests, lint, formatting, static typechecks, audit, production build, Docker health, Alembic and schema drift.
7. Performance benchmark with dataset size, query count, runtime and memory when available.
8. Browser/screenshots at all requested widths, CSV/PDF inspection and test fixtures.
9. Real provider request count and email delivery mode used during testing.
10. Known gaps with a clear status: `manual exports complete`, `scheduled delivery complete`, `visual QA complete` or `pending`—never flatten partial completion into a blanket PASS.

## 21. Implementation sequence for Codex

**Phase 0 — audit, before editing:** inspect canonical M7A/M7B queries, M7C filters/schema, actual migration head, current job queue adapters, available object storage/email integration and frontend Project navigation. Report conflicts or missing foundations succinctly.

**Phase 1 — reporting core:** reusable scoped canonical report dataset; preview endpoint; comparison/history CSV; tenant-safe async generation, job status, local private storage and authenticated download.

**Phase 2 — PDF:** deterministic renderer, print design using current visual language, charts/tables, methodology, Vietnamese font support, PDF inspection and large-report limits.

**Phase 3 — scheduled delivery:** persistence, dispatcher, reliable report job reuse, configured email abstraction, tested fake sender, UI and delivery history. Production email credentials are deployment configuration, not hardcoded values.

**Phase 4 — verification:** full automated suite, migration round-trip, local 1,000+ Keyword performance, browser screenshots, real PDF/CSV assertions, zero-credit confirmation, final report.

**Do not begin M7D Alerts, M7F Competitor Analytics, Payment Gateway, Developer API or API Docs as part of this task.**
