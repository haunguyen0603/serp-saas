# Milestone 7D — Ranking Alerts verification

Implementation and local verification on 2026-10-26 (Asia/Ho_Chi_Minh).
Production deployment: **completed**, with 23 public HTTP smoke checks and 3 anonymous browser checks passed. See [production rollout evidence](deployment-milestone-7d.md). Staging and real SMTP deliverability remain **unverified**.

## Implementation

- `backend/alembic/versions/0017_ranking_alerts_ranking_alerts.py`: revision `0017_ranking_alerts`, parent `0016_sepay_payments` (head inspected before creating revision). Four tables, constraints/indexes and nullable `rank_checks.alert_context`; no historical data rewrite.
- `backend/app/models/ranking_alert.py`, `app/schemas/ranking_alert.py`, `app/repositories/ranking_alert.py`, `app/api/v1/ranking_alerts.py`: persistence and tenant-scoped API.
- `backend/app/services/ranking_alerts.py`, `ranking_alert_email.py`: evaluation and optional email workers. `rank_checks.py` captures matching/configuration identity when a check starts and inserts its evaluation marker in the result transaction.
- Existing queue adapters, private worker entry point, local worker script, settings, logging, Docker Compose and Cloud Run configuration generator extended for alerts. Auth SMTP transport extracted into a shared helper; account verification/password message composition remains the same.
- `frontend/src/features/ranking-alerts/*`, `/app/ranking-alerts`, AppShell navigation/unread badge and Project Details preferences.
- New backend and frontend tests, `backend/scripts/seed_ranking_alerts_qa.py` and `scripts/verify-ranking-alerts-browser.mjs`. The QA seed refuses non-test environments, non-fake providers and enabled outbound alert email.
- Next.js and eslint-config-next pinned to `16.4.3`, with updated lockfile, to satisfy the runtime security gate. The prior `16.3.8` was affected by [GHSA-2464-fhr4-w9xw](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw), [GHSA-p3m5-59mp-jv5r](https://github.com/vercel/next.js/security/advisories/GHSA-p3m5-59mp-jv5r) and [GHSA-673q-mjm6-r5xr](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr).

## Observation/comparison contract

An observation is eligible only when the persisted check is `succeeded`, its requested depth is **exactly 10**, normalized results contain **every position 1–10**, parsing warnings are zero and metadata does not explicitly mark the response incomplete. This conservative gate does not change ranking execution or provider behavior: a short/empty result can remain a successful ranking check while being **unknown for alerting**. No claim is made about provider completeness beyond the validated persisted data. Legitimately short SERPs are deliberately excluded until the provider contract can prove completeness.

At check start, `alert_context` hashes project search dimensions/version and the complete active user-owned site/domain matching registry (IDs, domain strings and modification versions). Persistence requires the same context. A configuration/alias change during an attempt suppresses that observation. Query text is additionally included in the evaluation environment. Project, user, keyword IDs remain separate keys. Desktop/Mobile, engine, country, language, location, query and domain identity changes therefore rebaseline safely, including A → B → A edits. Renaming a project/site or changing an unrelated active alias also conservatively resets the baseline.

Each marker snapshots all active user-owned Tracked Sites, including explicit null positions for complete missing matches. Positions come from existing persisted Rankings and DomainMatcher, preserving alias matching, exact-host precedence and bidirectional www fallback. Project competitor selections are not used to infer new tracked identities. No SERP requests are made by evaluation, inbox or email processing.

Compare with the immediately preceding eligible succeeded check marker for the same user/project/keyword, ordered by `(requested_at, check_id)`. Require identical environment fingerprints and the same immutable site identity. Incomplete/failed attempts have no eligible marker and do not reset history. Existing pre-migration checks have no context/marker: the first post-release eligible check is a new baseline; there is no historical backfill.

| Previous | Current | Threshold | Result |
|---|---|---|---|
| Complete missing Top 10 | #7 | 3 | entered_top10 |
| #6 | Complete missing Top 10 | 3 | left_top10 |
| #9 | #4 | 3 | rank_improved, +5 |
| #2 | #6 | 3 | rank_declined, −4 |
| #6 | #4 | 3 | none |
| #6 | #3 | 3 | rank_improved, +3 |
| No eligible baseline | #4 | 3 | none |
| #5 | Failed / partial / unknown | 3 | none |
| #9, then failed/partial attempt | #4 complete | 3 | rank_improved, +5 |
| Another device/configuration/site identity | #4 | 3 | none; rebaseline |

A marker arriving after a newer canonical observation is already persisted is marked `suppressed`: it cannot emit a historical alert or replace the latest baseline. Ordinary pending evaluations are processed even if newer checks have since completed, so a queue backlog does not discard valid intermediate changes. A subsequently arriving older check never recomputes an existing alert. Future checks still select the latest canonical eligible predecessor, not the last task to finish. Stable IDs break timestamp ties.

## Durability, concurrency and recovery

```text
RankCheckExecutionService
  └─ transaction: normalized results + Rankings + succeeded check + evaluation marker
       └─ best-effort, coalesced Cloud Tasks sweep
            ├─ AlertEvaluationService transaction: alert + optional delivery outbox
            └─ AlertEmailWorker: claim/commit → SMTP → fenced outcome commit
```

- Each check has one marker (`check_id` PK). Matching-registry snapshots and marker creation share the ranking transaction. A rollback produces neither a successful observation nor a marker.
- Result persistence locks the project. Evaluation uses a transaction-level `FOR UPDATE SKIP LOCKED` on its marker and a project lock, shared with preference writes. DB-only evaluation has no external I/O; process death releases locks and rolls back all effects. This replaces a separately committed processing lease for evaluation.
- Alert uniqueness: `(current_observation_id, site_identity, alert_type)`; conflicts are ignored. The site identity remains immutable even if the site is deleted. Delivery uniqueness: `(alert_id, channel)`.
- Evaluation failure rolls back alert/outbox inserts, then records a safe error, retry count and exponential due time. Five attempts maximum; terminal `failed` rows require an operator to investigate and explicitly reset to pending/attempts=0 after repair. A fatal infrastructure failure before recording retry state leaves a durable pending marker for the next sweep.
- Cloud Tasks names are `ranking-alerts-<UTC-minute>`, coalescing checks into one bounded sweep per minute. Task payload is only `{version: 1}`. The existing scheduler dispatch always retries alert enqueue, so a missing/failed enqueue or completed-task tombstone cannot strand markers permanently. The next minute has a fresh deterministic task identity.
- A sweep evaluates up to 100 pending checks and handles up to 10 email deliveries. The local runner executes the same services directly. Queues/schedulers must be provisioned and monitored; delivery latency depends on their cadence and backlog. No production Redis dependency is introduced.
- Private endpoints reuse service OIDC identity validation: tasks caller for `POST /internal/tasks/ranking-alerts`; scheduler caller for `GET /internal/ranking-alerts/status`. The latter returns aggregate counts/statuses, oldest pending work timestamps, unread total and counts by alert type. It exposes no keyword, site or email text.
- Structured logs include check/user/project IDs, alert type, attempts, delivery ID/status and sweep counts. Enqueue failure, evaluation failure, duplicate suppression and delivery outcomes have separate safe event names. Aggregate metrics can be exported from these logs/status snapshots; no external monitoring dashboard is claimed provisioned.

## Preferences and eligibility

Defaults: in-app enabled; all four types enabled; threshold 3 (strict integer 1–10); email **off**. Preferences are a complete PUT representation. Missing rows read as safe defaults without creating DB writes. A unique user/project key and project lock serialize first writes.

Preferences are read at **evaluation transaction time**, serialized against writes by the project lock. A settings change before evaluation affects the pending observation; one committed afterward affects later evaluations. Changes do not recompute stored alerts. Disabled evaluations are consumed without alerts, so reenabling does not replay them. The separate `RANKING_ALERTS_ENABLED` global switch suppresses detection on evaluation while allowing durable markers to continue providing complete baselines.

Eligibility is active User, active Project, active Keyword and active user-owned Tracked Site. Billing entitlement remains enforced by the existing rank execution path; alert processing uses already-authorized observations and introduces no subscription or SePay changes. A historical alert remains readable after archiving.

Existing history protections still reject project/keyword hard deletion with 409; users archive/pause instead. Tracked Site deletion sets the inbox site FK to null, preserves snapshot text/immutable identity, suppresses unsent email and offers a Project link instead of a broken site-filtered history link. Other history/audit references use RESTRICT. Preferences cascade only when an otherwise deletable history-free Project is removed. No new automatic retention/deletion policy is introduced; markers/alerts/delivery evidence follow retained ranking history and require an explicit privacy/retention migration before purging. Site registry snapshots are retained as ranking evidence.

## API and application

All APIs use existing `/api/v1` auth/error handling and verified-email gate. Ownership is derived from the session; unknown/foreign project/alert IDs return 404. No recipient, email or user ownership is client writable.

| Method/path | Behavior |
|---|---|
| GET `/ranking-alerts` | Optional `project_id`, `unread_only`; `limit` 1–100 (default 25); opaque `cursor`, deterministic `(created_at DESC, id DESC)`; items/next_cursor/has_more |
| GET `/ranking-alerts/unread-count` | `{count}` for current user |
| PATCH `/ranking-alerts/{id}/read` | Server timestamp, idempotent; returns alert |
| POST `/ranking-alerts/mark-all-read` | Optional owned project filter; 204 |
| GET `/projects/{id}/ranking-alert-preferences` | Defaults/current settings plus server `email_available` |
| PUT `/projects/{id}/ranking-alert-preferences` | Validated complete preferences; unknown fields rejected |

Inbox rows contain persisted snapshot text and identifiers, never raw SERP data/provider credentials. Listing uses a single bounded alert query, with no per-row lookups. Project filters are paginated independently, including a Load more projects control. Inbox supports loading/empty/error/retry, All/Unread/project filters, next/previous pages, mark read/all read, device/site context, explicit “Not found in Top 10”, history links and browser-local time with IANA timezone. AppShell links to Ranking Alerts and displays an unread badge (focus refetch; 120-second foreground interval). Alert/preferences/project-option caches include account identity, and existing session changes clear the QueryClient.

## Optional email

`RANKING_ALERT_EMAIL_ENABLED=false` by default; per-project `email_enabled=false` independently. Reuse `AUTH_EMAIL_PROVIDER`, `AUTH_EMAIL_FROM`, `AUTH_SMTP_*`, existing TLS/SSL settings and bounded shared SMTP transport. No new credentials or arbitrary recipients are accepted. Production settings already require SMTP/TLS; fake transport is confined to non-production tests.

An outbox entry is created transactionally only for an opted-in type and verified account at evaluation time. Before a send claim the worker rechecks global availability, verified account address/status, project/keyword/site eligibility and current project/type/email preferences. Ineligible/disabled work becomes terminal `suppressed`, with no later replay if email is reenabled. Disabling email after a committed claim can allow that one already-claimed send to finish; later claims are suppressed.

Delivery rows use `sending`, a random fencing token and a 300-second lease. Concurrent live claims are skipped; expired claims are recoverable. Sender outcomes update only the matching token. Transient failures retry at bounded exponential delays (60, 120, 240, 480 seconds); five claims maximum. Permanent recipient failures are terminal. Expired fifth claims become failed without another send. A fake sender and injected transient/permanent failures exercise this lifecycle.

V1 sends one compact plaintext + escaped HTML email per alert; subject strips line breaks and is length bounded. Stable Message-ID is based on delivery ID. Recipient is always the freshly loaded verified account's address. Per-user cap is 20 send attempts/hour by default (1–100 configurable), serialized with a user lock across projects. Summing attempts on rows last attempted in the preceding hour is conservative: retries can overcount old attempts, reducing volume rather than exceeding the cap. Throttled work is postponed one hour; in-app detail remains intact.

SMTP has no provider idempotency guarantee. A crash after provider acceptance and before the sent-state commit can lead to a repeated email after lease expiry; stable Message-ID may help downstream dedupe but is **not exactly-once delivery**. No production delivery, sender/domain validation or SPF/DKIM/DMARC success is claimed.

## Verification results

All final gates below passed against current workspace code. Backend tests used Python 3.12.12 in the existing backend image, a dedicated PostgreSQL 16.13 container and Redis 7.4.8 container, with isolated per-test schemas/migrations. Final regression used a private Docker network for direct database connections. Frontend used Node 22.22.0 and the production standalone build (Next.js 16.4.3); API/worker configuration was test-only with fake transports. No production credentials or database were used.

| Gate | Result |
|---|---|
| Backend `python -m pytest -q` | **402 passed**, 221.92s |
| Focused M7D/migration/queue/auth regression | **57 passed**, 48.24s |
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS, 240 files |
| `python -m mypy app` | PASS, 162 source files |
| Alembic fresh upgrade, M7D downgrade/upgrade, metadata parity, indexes/constraints | PASS as PostgreSQL integration tests; `alembic check` also detected no changes |
| Frontend `npm test` | **333 passed**, 37 files |
| `npm run lint`, `npm run typecheck`, `npm run format:check` | PASS |
| `npm run build` | PASS, includes `/app/ranking-alerts`; validated 9 published blog articles |
| `npm audit --omit=dev` | **0 total / 0 high / 0 critical** |
| `python3 -m unittest discover -s infrastructure/gcp/tests -v` | **56 passed**, no GCP or payment calls |
| `git diff --check` | PASS |

Evidence: [backend tests](verification-artifacts/milestone-7d/backend-tests.txt), [focused tests](verification-artifacts/milestone-7d/focused-tests.txt), [frontend tests](verification-artifacts/milestone-7d/frontend-tests.txt), [production build](verification-artifacts/milestone-7d/frontend-build.txt), [runtime audit](verification-artifacts/milestone-7d/runtime-audit.json), [infrastructure regressions](verification-artifacts/milestone-7d/infrastructure-tests.txt), [browser report](verification-artifacts/milestone-7d/browser-qa.json).

Browser QA used actual local API/database sessions, persisted rank results/alerts and a fake SERP provider. It exercised anonymous/unverified redirects, populated/empty/other-account inboxes, next/previous pagination, unread/project filters, individual/all read mutations, preference persistence/enable-disable/threshold/email opt-in, unavailable-email copy, history links, injected 503/retry and held-request loading states. It also checked keyboard filter order and focus on the read-status announcement. Existing ranking/auth/billing/SePay frontend/backend regressions passed; no live payment or provider calls were made.

At **375, 768, 1024 and 1440px**: no horizontal overflow; **0 WCAG 2/2.1 A/AA axe violations**, **0 page errors**, **0 React hydration errors** in the tested cases. Both light/dark browser color-scheme preferences were exercised for the inbox using the application's existing palette. Full inbox screens (including shell) were audited; the Project Details accessibility audit was scoped to the new preferences section, with whole-page overflow checks. This does not claim an accessibility audit of every unrelated legacy Project panel.

Thirty screenshots are stored beside the browser report; representative views: [mobile inbox](verification-artifacts/milestone-7d/inbox-populated-viewport-375.png), [desktop inbox](verification-artifacts/milestone-7d/inbox-populated-viewport-1440.png), [mobile empty unread](verification-artifacts/milestone-7d/inbox-unread-empty-375.png), [project preferences](verification-artifacts/milestone-7d/project-preferences-1440.png).

To reproduce: configure disposable PostgreSQL/Redis endpoints and fake SERP/auth email in a test runtime, migrate head, start the API, build/start the frontend standalone with matching API/CORS origins, then run `scripts/verify-ranking-alerts-browser.mjs` with `PLAYWRIGHT_MODULE`, `AXE_MODULE`, optional `CHROME_EXECUTABLE` and `QA_CONTAINER`. The script seeds only the explicitly selected test container. Use the commands in the table for unit/integration gates. Real SMTP/DNS, staging, authenticated production flows and production-scale load remain unverified.

Temporary PostgreSQL/Redis/runtime containers, their test network and the frontend standalone QA server were removed/stopped after saving verification evidence. No test services are intentionally left running.

## Rollout checklist (release steps now executed; see deployment report)

1. Review this migration and back up the target database. Run `alembic upgrade head` once via the existing release migration job; never introduce concurrent production startup migrations.
2. Deploy backend and worker containing the new tables/handlers, preserving existing OIDC service identities/Cloud Tasks queue and scheduler dispatcher. New settings are supplied by the Cloud Run config generator; verify deployed values explicitly.
3. Deploy the frontend build with its matching API origin. Initially keep `RANKING_ALERT_EMAIL_ENABLED=false`; in-app evaluation may be enabled. Pre-release observations intentionally rebaseline.
4. On staging, use an isolated fake provider to verify the transition matrix, duplicate tasks, pending-work reconciliation, disabled settings, tenant isolation, inbox reads and outbox leases. This repository's local QA seed is **test-only** and must never be used in production.
5. Inspect private aggregate status and safe logs; alert on failed evaluations/deliveries, growing pending counts and oldest-work age. Confirm capacity relative to the 100 evaluations/10 email deliveries per sweep and scheduler frequency.
6. Configure existing AUTH SMTP credentials using Secret Manager, validate sender and SPF/DKIM/DMARC, and obtain authorization for controlled real-message delivery tests. Only then enable the global email switch; each user still opts in per project.
7. Operational controls: `RANKING_ALERTS_ENABLED=false` suppresses future evaluation output; `RANKING_ALERT_EMAIL_ENABLED=false` suppresses pending email at claim. Investigate terminal errors before explicitly retrying failed rows. A leased email may finish after disablement.
8. Rollback: disable email/detection and deploy compatible application code. Prefer retaining tables/evidence. The tested downgrade removes the four alert tables and check context, so it destroys alert evidence and requires a deliberate database maintenance decision.

Production migration/deployment completed through the existing Cloud Build release pipelines; public HTTP and anonymous browser verification passed. Remaining external validation: staging deployment, authenticated tenant flows in production, authenticated Cloud Tasks/scheduler recovery at runtime, live provider completeness, real SMTP delivery and DNS authentication, and throughput/load testing at production traffic. Public worker access was verified IAM-denied; no privileged worker invocation or real SERP/email/payment test was performed.
