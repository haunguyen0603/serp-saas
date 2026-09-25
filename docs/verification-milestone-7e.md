# Milestone 7E — Reports & Export verification

Verified on 2026-09-25 in the local Docker environment. All rank-check QA used
`SERP_PROVIDER=fake`, `SERP_ENABLED_PROVIDERS=fake`, the fixed fake-provider
strategy, and `TASK_QUEUE_PROVIDER=local`. No real SERP request or external email
was sent.

## Completion status

- Manual exports: **complete**.
- Scheduled delivery: **complete** for the documented verified-account-only mode.
- Visual/browser QA: **complete** at 375, 768, 1024, 1280, and 1440 px.
- Production adapters: SMTP email and private Google Cloud Storage are implemented
  and configuration-driven. QA used only the fake email adapter and local private
  storage.

## Implementation inventory

The implementation adds Alembic revision `0011_reports` (parent
`0010_keyword_organization`) and the following durable records:

- `generated_reports`: immutable resolved period/filter snapshot, job state,
  lease/retry state, private artifact metadata, retention, and idempotency.
- `report_schedules`: UTC weekly/monthly calendar, filter snapshot, next/last run,
  pause state, and latest delivery state.
- `report_delivery_attempts`: recipient digest, bounded attempt number, provider
  delivery ID, timestamps, and sanitized error code.

Primary backend modules are `app/api/v1/reports.py`, `app/models/report.py`,
`app/repositories/report.py`, `app/services/reports.py`,
`app/services/report_worker.py`, `app/services/report_renderers.py`,
`app/services/report_storage.py`, and `app/services/report_email.py`. The existing
local/Cloud Tasks abstraction now has a separate report payload and handler.

Authenticated product routes:

```text
GET    /api/v1/projects/{project_id}/reports/preview
POST   /api/v1/projects/{project_id}/reports
GET    /api/v1/projects/{project_id}/reports
GET    /api/v1/projects/{project_id}/reports/{report_id}
GET    /api/v1/projects/{project_id}/reports/{report_id}/download
POST   /api/v1/projects/{project_id}/reports/{report_id}/retry
GET    /api/v1/projects/{project_id}/reports/{report_id}/delivery-attempts
GET    /api/v1/projects/{project_id}/report-schedules
POST   /api/v1/projects/{project_id}/report-schedules
PATCH  /api/v1/projects/{project_id}/report-schedules/{schedule_id}
DELETE /api/v1/projects/{project_id}/report-schedules/{schedule_id}
```

The frontend route is
`/app/projects/{projectId}/reports`, linked from Project navigation. It includes
preview, presets/custom dates, site/Group/Tags ANY/ALL filters, asynchronous
generation, authenticated downloads, recent-report pagination, bounded polling,
and create/edit/pause/delete schedule controls.

## Canonical report semantics

The selected grain is **one active Keyword × selected active Tracked Site**.
Reports expose both `distinct_keywords` and `keyword_site_pairs`; they do not label
pair counts as keyword counts. Active Keywords and active Tracked Sites are the
default scope.

Preset periods end at request time in UTC and use the canonical M7B comparison
query: current is the latest successful comparable observation before the end;
baseline is the latest successful observation at/before the range boundary, with
the existing `earliest_in_range` fallback. Custom dates use inclusive UTC calendar
dates, represented as `[start 00:00, day-after-end 00:00)`, and do not disguise a
missing baseline. `comparison_basis` is persisted and exposed as
`range_boundary`, `earliest_in_range`, `custom_dates`, or `none`.

Failed RankChecks are excluded. A successful check without a matching ranking is
`not_found_in_depth`; an absent successful observation is `never_checked`. For
the current Top 10 fixture the exact labels are `Top 3`, `Positions 4–10`,
`Not found in Top 10`, `Entered Top 10`, and `Left Top 10`. Distribution counts
reconcile over observed pairs; movement states reconcile over every included
pair. UI and PDF show `Data as of`, UTC, device, active scope, and methodology.

Weekly schedules cover the previous completed seven-day window. Monthly schedules
cover the previous completed UTC calendar month; a configured day 31 clamps to the
last valid day and resumes on day 31 in later months.

## CSV, PDF, storage, and retention

Comparison CSV exports every filtered pair, independent of Explorer pagination.
Its stable columns are:

```text
project_name,device,keyword,keyword_id,tracked_site_name,tracked_site_id,
report_start_utc,report_end_utc,comparison_checked_at_utc,
comparison_position,comparison_depth,current_checked_at_utc,current_position,
current_depth,current_status,movement_type,numeric_change,comparison_basis,
keyword_group,keyword_tags
```

History CSV exports only actual successful persisted observations with:

```text
project_name,device,keyword,keyword_id,tracked_site_name,tracked_site_id,
checked_at_utc,position,checked_depth,status,rank_check_id,keyword_group,
keyword_tags
```

Both use UTF-8, CRLF CSV records, deterministic semicolon-separated Tags, empty
numeric cells, and an explicit status. Text beginning with `=`, `+`, `-`, `@`,
tab, or carriage return is neutralized. Automated coverage validates all six
prefixes, Vietnamese Unicode, stable order, and the exact header.

PDF uses pinned ReportLab 4.5.1 plus DejaVu Sans installed in the image. It contains
cover metadata, KPI table, checked-depth distribution, movement summary,
winners/losers, bounded details, explicit truncation guidance, page numbers, and
methodology. It truthfully handles no matching rows and matching rows without
observations. A trend chart is intentionally omitted because it is optional; the
History CSV is the accessible actual-observation time series.

Artifacts use opaque `{user_uuid}/{report_uuid}.{ext}` keys and are never public.
Local Docker mounts `/var/lib/serp-saas/reports`; production can select
`REPORT_STORAGE_PROVIDER=gcs` with a private bucket and prefix; production startup
rejects local artifact storage. Downloads always
re-check ownership and stream with `private, no-store` and `nosniff`. Default
retention is 30 days; the worker removes expired objects and regeneration remains
available.

Engineering safeguards are backend-enforced: 365-day range, 100,000 CSV rows,
1,000 PDF details, two concurrent reports per user, five active schedules per
Project, three job attempts, and a 300-second lease. They are configuration, not
Plan entitlements.

## Scheduled delivery and security

Scheduling is available only when an email adapter is configured and only for the
owning account's verified email. Arbitrary recipients are deliberately deferred.
The SMTP adapter reads configuration only; missing credentials leave manual
exports available and the UI shows delivery unavailable.

The dispatcher locks due schedules and uses deterministic
`(schedule_id, period_start, period_end)` idempotency. Report artifacts and
delivery attempts are separate state machines. Cloud Task identity includes the
report attempt number, so a completed prior task cannot suppress a later retry.
Expired worker leases are recovered, transient generation/storage/email failures
use bounded exponential backoff, pending email leases are recovered, and a valid
ready artifact is reused for delivery-only retry. A recipient is stored only as a
SHA-256 digest; errors are stable sanitized codes.

End-to-end local evidence used a due weekly fixture with the fake email adapter:
generated report `ready`, delivery attempt `sent`, schedule
`last_delivery_status=sent`, and provider ID prefixed `fake-`. The UI showed
`Last delivery: sent`, last run, and next run. The stack was returned to
`REPORT_EMAIL_PROVIDER=disabled` after QA.

Ownership is checked at preview, creation, execution, detail, download, retry,
schedule, and delivery history. Cross-tenant IDs are returned as not found.
Group/Tag filters must belong to the same Project and Tracked Sites to the same
user. Project/user composite foreign keys protect durable rows.

## Automated verification

Commands were executed from the repository root unless noted.

| Check | Result |
|---|---|
| `docker compose run --rm backend pytest -q` with fake SERP/email disabled | **242 passed in 118.98s** |
| Reports + task queue focused tests | **25 passed in 4.68s** |
| `ruff format --check backend` / `ruff check backend` | passed |
| `mypy backend/app` | **131 source files**, no issues |
| Frontend `npm test` | **21 files, 106 tests passed** |
| Frontend `npm run typecheck` | passed |
| Frontend `npm run lint` | passed |
| Frontend Prettier check | passed |
| Frontend host production build | passed; Reports dynamic route emitted |
| `docker compose build backend worker frontend` | passed |
| Backend Docker `--target production` build | passed |
| `git diff --check` | passed |

The full suite exercises fresh upgrade, migration round trips, preservation tests,
and `test_migration_matches_models`; all passed. The running database reported
`0011_reports (head)`. Backend, worker, frontend, PostgreSQL, and Redis all reported
healthy after the final rebuild.

Report tests cover observed/unobserved data, exact depth metrics, history success
rows, failed-check exclusion, CSV limits and injection, Unicode, PDF generation,
idempotent creation, tenant-isolated detail/download, expiry, verified email,
transient email backoff, no duplicate immediate send, weekly/month-end boundaries,
Cloud Tasks retry identity, stale-lease recovery, and the invariant that report
operations create no `RankCheckJob`.

## Performance benchmark

PostgreSQL benchmark fixture: 1,000 active Keywords, two active Tracked Sites,
two successful observations per Keyword, ten Groups, twenty Tags with mixed
assignments. Measurements cover worker generation and Python allocations; query
count was captured with SQLAlchemy events.

| Report | SQL queries | Generation | Peak Python memory | Artifact |
|---|---:|---:|---:|---:|
| Comparison CSV, 2,000 pairs | 15 | 6,191.68 ms | 7.52 MiB | 661,011 B |
| History CSV, 4,000 observations | 15 | 6,356.29 ms | 6.46 MiB | 517,860 B |
| PDF, 1,000-row capped appendix | 21 | 15,050.36 ms | 9.88 MiB | 83,728 B |
| Group + Tags ANY comparison | 17 | 205.52 ms | 2.37 MiB | 33,281 B |
| Group + Tags ALL comparison | 17 | 223.60 ms | 2.17 MiB | 33,281 B |

Query counts are set-based and independent of keyword count; no per-keyword SQL or
network request occurred. Fake email has no meaningful provider latency, so no
external-delivery latency is claimed.

## Browser and artifact verification

Chrome headless used the real production frontend image and real local API with a
deterministic fake-provider fixture. Browser flow covered login, 7D/30D/90D/custom
preview, invalid custom-date blocking, site/Group/two-Tag ALL filters, all three
generation/download flows, create/edit/pause schedule, due fake-email delivery,
and an expired report showing `REPORT_EXPIRED` plus `Regenerate`.

| Width | document/body width | Horizontal page overflow |
|---:|---:|---|
| 375 | 375 / 375 | none |
| 768 | 768 / 768 | none |
| 1024 | 1024 / 1024 | none |
| 1280 | 1280 / 1280 | none |
| 1440 | 1440 / 1440 | none |

After authenticated navigation, the Reports page produced zero console errors.
Initial anonymous refresh returned the expected 401 before login and was excluded
from the authenticated page result.
`Content-Disposition` was exposed through CORS and Chrome confirmed the final
download name
`bao-cao-responsive-qa-ranking-report-2026-08-26_2026-09-25.csv`.

Artifacts:

- [375 px screenshot](verification-artifacts/milestone-7e/reports-375.png)
- [768 px screenshot](verification-artifacts/milestone-7e/reports-768.png)
- [1024 px screenshot](verification-artifacts/milestone-7e/reports-1024.png)
- [1280 px screenshot](verification-artifacts/milestone-7e/reports-1280.png)
- [1440 px screenshot](verification-artifacts/milestone-7e/reports-1440.png)
- [Paused schedule](verification-artifacts/milestone-7e/schedule-paused-1280.png)
- [Delivered schedule](verification-artifacts/milestone-7e/schedule-delivered-1280.png)
- [Comparison CSV](verification-artifacts/milestone-7e/browser-comparison.csv) —
  3 data rows, SHA-256
  `cba372ae388bfdf883873989f55ac6c37b2567d365aa539d8b0e5eea27ca229e`
- [History CSV](verification-artifacts/milestone-7e/browser-history.csv) — 3 actual
  observation rows, SHA-256
  `007023e33751bfe9b2720735025488513aed84fb44e38bcc9653248203523d51`
- [PDF](verification-artifacts/milestone-7e/browser-report.pdf) — 2 pages,
  26,311 bytes, SHA-256
  `9e4016fd13e61a0975894fa96195f5b46aba72a289dbdb7a766839fd8f9bde8f`

The real PDF was rasterized and visually inspected: Vietnamese Project/filter text,
Top 10 tables, page number, spacing, section continuity, and A4 boundaries rendered
correctly. CSV files were opened as text and checked for header, Unicode, row count,
status, group, and deterministic Tags.

## Provider and scope audit

- Real SERP provider requests: **0**.
- Real provider credits consumed: **0**.
- External emails sent: **0**.
- QA email mode: fake adapter only; final running stack uses disabled email.
- No Payment Gateway, public Developer API, API Keys, API Docs, Alerts, or
  Competitor Analytics work was introduced.

Known deployment-only gap: GCS and SMTP implementations were production-built but
not exercised against real cloud credentials. This is intentional; deployment
secrets and external sends were outside local QA. It does not block manual exports
or the verified fake-adapter schedule acceptance path.
