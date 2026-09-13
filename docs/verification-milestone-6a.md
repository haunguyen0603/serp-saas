# Milestone 6A verification

Status: implementation complete. Final verification continuation: 2026-09-13.
No M6A business behavior was rewritten during the final verification continuation.

## Implementation and architecture

M6A adds six data-driven Plans, explicit device-scoped subscriptions, immutable
commercial snapshots, monthly logical usage periods, per-Job reservations, usage
ledger events and billing audit events. Models are consolidated in
`backend/app/models/billing.py`; repositories and billing services keep SQL out of
HTTP route handlers. `Project.device` selects the independent Desktop/Mobile scope.
There are no payment gateway calls or provider-pricing calculations.

| Plan            | Monthly USD | Projects | Keywords | Checks | Schedules |
| --------------- | ----------: | -------: | -------: | -----: | --------- |
| Desktop Free    |           0 |        1 |       50 |    100 | none      |
| Desktop Starter |          19 |        5 |      500 |  5,000 | weekly    |
| Desktop Pro     |         129 |       20 |    5,000 | 50,000 | daily     |
| Mobile Free     |           0 |        1 |       20 |     50 | none      |
| Mobile Starter  |          39 |        3 |      200 |  1,000 | weekly    |
| Mobile Pro      |         249 |       10 |    1,000 | 10,000 | daily     |

Prices are integer USD minor units. Enforcement reads subscription snapshots, not
Plan tier branches. Catalog edits do not alter existing commercial terms.

## Subscription transitions and manual workflow

An operator grants an existing account `is_platform_admin` using
`python -m scripts.platform_admin EMAIL`; `--revoke` removes it. Registration and
customer APIs cannot assign this flag. Log in again to refresh frontend navigation.
Backend authorization reads the database flag on every Admin request.

Admin confirms payment externally, opens `/admin/customers`, searches email, opens
a customer, selects a Plan, period and manual bank-transfer reference/internal note,
and activates. Device derives from Plan. Normal users have read-only billing APIs.
Paid Plans require `manual_bank_transfer`; Free requires no payment method.

One partial unique index enforces one active subscription per user/device. A
transaction-scoped user advisory lock serializes activations, resource expansion,
reconciliation and reservation creation without conflicting with authentication FK
reads. Default duplicate immediate activation returns `SUBSCRIPTION_CONFLICT`.
`replace_existing=true` explicitly requests an immediate upgrade/downgrade. Old
records, terms, activation/cancellation actors and timestamps remain intact.

Immediate replacement closes the previous usage period and starts fresh quota;
no financial proration occurs. Same-Plan extension changes `period_end` and extends
a clipped monthly window without resetting its counters. Future activation is
supported at/after the current paid subscription end; overlapping scheduled Plans
and extensions are rejected. Reconciliation flushes expiry before activating the
successor so ORM update ordering cannot violate the partial unique index.

Paid usage windows are anchored to subscription start. Month arithmetic always uses
the original anchor (January 31 → February 28 → March 31). Windows clip at subscription
end. Free fallback uses calendar-month windows and an ongoing explicit subscription.
Replacing/cancelling a paid Plan restores Free for that device only. Monthly rollover
creates a new UsagePeriod; in-flight Jobs settle against the originally reserved
period even after a Plan change or reset.

`reconcile_subscriptions(session, now)` expires ended subscriptions, activates due
scheduled subscriptions, creates Free fallbacks/current usage periods and disables
incompatible schedules with an audit reason. Entitlement reads reconcile lazily;
the existing M5 dispatcher runs reconciliation periodically. No new service is added.

## Usage enforcement and M5

Before Batch/Job creation, the service resolves entitlement and atomically updates
`reserved_keyword_checks` only when `limit + adjustment - committed - reserved`
covers the entire request. Insufficient capacity creates no Batch/Jobs or provider
work. All Job reservations are persisted in the same transaction before enqueue.
A reservation represents exactly one logical Job; a Batch has one per Keyword.

After ownership/active Project/Keyword validation, the ranking start transaction
commits the reservation. A unique Job identity and reservation event prevent retry,
fallback, redelivery or lease recovery from charging twice. Provider no-match counts.
Provider retry/fallback and infrastructure budgets remain separate and unchanged.

Batch cancellation and terminal reconciliation release only still-reserved Jobs;
committed usage stays committed. Archived/paused work rejected before logical
execution releases quota. Permanent enqueue errors are terminally compensated;
transient enqueue failures keep their reservation while the durable M5 outbox retries.
Pending work past the configured retry horizon is failed and released. Cloud SDK
permission/configuration errors are classified as permanent without exposing SDK text.
Reconciliation queries only terminal Jobs with outstanding reservations.

All state transitions use Batch → Job lock ordering, including the ranking execution
fence, to avoid ledger FK lock inversion. Existing worker lease/idempotency, ranking
snapshots, ProviderRouter, DomainMatcher and provider accounting remain intact.
Pre-M6A pending/queued/running Jobs receive a grandfathered reservation on migration;
they remain executable without deleting or rewriting their Batch/Job/history.

Admin adjustments add signed, bounded changes to effective period allowance, retain
nonnegative limits, and write both UsageEvent and BillingAuditEvent with a reason.
Customer errors include safe limit/used/reserved/remaining/requested metadata.

## Resource and schedule enforcement

Project creation, bulk/single Keyword add, Keyword reactivation, Project reactivation
and device changes enforce active counts per device under the user lock. Duplicate
bulk inputs/existing Keywords do not consume extra resource slots. Bulk rejection is
atomic. Project state is refreshed after acquiring the lock so an earlier archived
read cannot bypass quota after another transaction reactivates it.

Over-limit resources remain readable and are marked on billing; expansion is blocked.
Downgrades never delete Projects, Keywords or rankings. Device changes with pending
work are rejected to preserve reservation scope. Incompatible schedules are disabled
on device changes, downgrade and expiry, with safe audit metadata.

Free cannot enable schedules, Starter permits weekly, Pro daily/weekly. Dispatcher
rechecks entitlement and full-batch quota; it skips the complete occurrence when
capacity is insufficient and advances the schedule, avoiding five-minute quota retries.

## API and UI

Customer: `GET /api/v1/billing/plans`, `/billing/me`, `/billing/me/usage`.
Admin: customer list (literal email search + cursor), billing detail, subscriptions
(history/create), subscription extend/cancel, usage history and usage adjustments.
All Admin routes use backend `ADMIN_REQUIRED` enforcement; foreign subscription IDs
under a different customer return not found. Extra request fields are forbidden.

`/settings/billing` displays each device Plan, price, period, status, Project/Keyword
counts, logical checks, reserved/remaining checks, reset date and schedule entitlement.
`/pricing` groups the six catalog entries and describes manual contact/payment.
`/admin/customers` and `/admin/customers/{id}` provide search/pagination, device cards,
activation/change, extension, cancellation, bank references, history, usage and audit.
Admin forms are absent for ordinary users. Internal notes and payment references are
excluded from all customer billing responses. React renders references as text.

## Migration and existing data

New revision: `0008_billing_usage_limits`, following actual M5 head
`0007_async_rank_check_jobs`. Earlier migrations are unchanged.
Creates plans/subscriptions/usage_periods/usage_reservations/usage_events/
billing_audit_events and the platform Admin flag (false by default).
Seeds all six Plans; backfills Desktop/Mobile Free subscriptions and current periods
for existing users, audits fallback, disables existing Free-incompatible schedules,
and meters grandfathered outstanding Jobs. Existing Projects/Keywords/ranking/provider
history are preserved. No existing account is automatically promoted to Admin.

Isolated migration fixtures cover fresh upgrade, M1–M5 historical data, M6A existing
user/schedule/pending-Job backfill, schema drift and downgrade/re-upgrade. Downgrades
are tested only in temporary schemas; the active developer database is upgraded only.

## Executed commands and results

Local tooling in this environment:

```sh
export PATH=/private/tmp/serp-tools/bin:/private/tmp/serp-node/node_modules/node/bin:$PATH
export DOCKER_CONFIG=/private/tmp/serp-tools/docker
# Backend tests run inside backend/ with:
DEBUG=false DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas \
  REDIS_URL=redis://127.0.0.1:6379/0 .venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
# Frontend commands run inside frontend/:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test
npm run lint
npm run format:check
npm run typecheck
npm audit --audit-level=high
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development npm run build
```

The final repository-wide command was:

```sh
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH \
  make COMPOSE='docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml' \
  CHECKS='docker compose -f docker-compose.yml -f docker-compose.checks.yml -f /tmp/m6a-compose.yml' \
  check > /tmp/m6a-final-check.txt 2>&1
```

This runs backend pytest, frontend Vitest, Ruff, Ruff formatting, ESLint, Prettier,
strict mypy/TypeScript, and connectivity. `npm audit --audit-level=high` was rerun
separately in `frontend/`, recorded in `/tmp/m6a-final-npm-audit.txt`.

Final `make check` exited **0**. Exact final results:

| Check                                                  | Final executed result                                                                                                 |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Backend full suite, Docker                             | **213 passed in 90.60s**                                                                                              |
| Frontend full suite, Docker                            | **66 passed across 14 files**, Vitest duration **9.34s**                                                              |
| Billing cases                                          | **15 passed**, included in the 213                                                                                    |
| Migration cases                                        | **5 passed**, included in the 213                                                                                     |
| Ruff lint                                              | `All checks passed!`                                                                                                  |
| Ruff formatting                                        | `157 files already formatted`                                                                                         |
| Strict mypy                                            | `Success: no issues found in 107 source files`                                                                        |
| ESLint                                                 | Passed, exit 0                                                                                                        |
| Prettier                                               | `All matched files use Prettier code style!`                                                                          |
| Strict TypeScript                                      | `tsc --noEmit` passed, exit 0                                                                                         |
| Latest npm audit                                       | `found 0 vulnerabilities`, exit 0                                                                                     |
| Connectivity                                           | All backend and frontend probes passed; aggregate command exit 0                                                      |
| Alembic current                                        | `0008_billing_usage_limits (head)`                                                                                    |
| Alembic upgrade                                        | Successful, idempotent upgrade to head                                                                                |
| Alembic check                                          | `No new upgrade operations detected.`                                                                                 |
| Docker health after final checks                       | backend, worker, frontend, PostgreSQL, Redis all **healthy**                                                          |
| Backend production build                               | Passed; final image `serp-saas-backend:milestone6a-production`                                                        |
| Production worker command, rerun in final continuation | Passed: health/DB/unknown-Job acknowledgment 200; public API/docs absent                                              |
| Frontend production build                              | Passed both Compose and native; native compile 5.0s, TypeScript 4.6s, static generation 14/14                         |
| M1–M5 + billing smokes                                 | Auth, business, sites, ranking, routing, async Jobs, mocked Cloud Tasks contract, billing and connectivity all passed |
| Reconciliation/recovery                                | Explicit local/fake override command exited 0                                                                         |
| Browser journeys                                       | Four recorded real-browser journeys passed; details and harmless event below                                          |

The backend count remains **213**, matching the user's checkpoint. The latest
container run above is the final authoritative count. The five billing frontend
cases are part of the 66 total, not additional to them.

The later Docker `make check` results supersede the 213-test native checkpoint
(111.26s) and intermediate Docker pytest run (213 in 127.11s). Counts in this report
refer to the final run, not the earlier milestone reports.

API and local worker configuration was checked through an explicit safe allowlist:
app_env=development, debug=false, task_queue_provider=local, serp_provider=fake,
serp_enabled_providers=fake, serp_fixed_provider=fake, strategy=fixed, priority=fake.
No secret values were printed. A read-only live catalog query matched all six rows
in the table above; a grouped active-subscription query found **0 duplicate active
user/device scopes**. Five services were confirmed healthy again after `make check`: backend, worker,
frontend, PostgreSQL and Redis.

Docker verification used `/tmp/m6a-compose.yml`, an environment-only override for
backend/worker setting DEBUG=false, local queue, fixed fake provider and blank provider
keys. It preserves `.env` and prevents real provider operations. Its full contents:

```yaml
services:
  backend:
    environment: &verification
      DEBUG: "false"
      TASK_QUEUE_PROVIDER: local
      SERP_PROVIDER: fake
      SERP_ENABLED_PROVIDERS: fake
      SERP_FIXED_PROVIDER: fake
      SERP_PROVIDER_STRATEGY: fixed
      SERP_PROVIDER_PRIORITY: fake
      SERPER_API_KEY: ""
      SERPAPI_API_KEY: ""
  worker:
    environment: *verification
```

```sh
docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml up -d --build --wait
docker build --target production -f infrastructure/docker/backend.Dockerfile \
  -t serp-saas-backend:milestone6a-production .
make auth-smoke business-smoke tracked-site-smoke ranking-smoke \
  provider-routing-smoke async-ranking-smoke cloud-tasks-contract-smoke billing-smoke
make connectivity
make COMPOSE='docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml' recover-rank-jobs
docker compose exec -T backend alembic current
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
docker compose ps
```

The worker runtime probe uses `/tmp/m6a-production-override.yml` with backend image
`serp-saas-backend:milestone6a-production`, then:

```sh
docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml \
  -f /tmp/m6a-production-override.yml run --rm --no-deps -T backend python - \
  < scripts/verify-worker-runtime.py
```

The final continuation reran the actual production `uvicorn app.worker_main:app` command and reported health 200,
DB health 200, unknown-Job acknowledgment 200, and public API/docs absent (404).
This validates the image/command locally, not real Cloud Run IAM deployment.

## Browser verification

```sh
export PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
export DOCKER_BIN=/private/tmp/serp-tools/bin/docker
node scripts/verify-billing-browser.mjs
node scripts/verify-auth-browser.mjs
node scripts/verify-projects-browser.mjs
node scripts/verify-rankings-browser.mjs
```

All four real Chrome journeys passed during this implementation. The final
verification continuation confirmed the recorded outputs rather than claiming new
browser runs. Billing journey verified signup, both Free
Plans, allowed Project, Project/Keyword limits, one logical Desktop check, independent
Mobile usage, normal-user Admin denial; Admin login, customer search, Desktop and
Mobile Starter activations, references, Desktop extension/upgrade, independent Mobile
state, history, usage adjustment and audit. No browser exceptions.
Auth/health journey: 9 checks, zero exceptions/network failures. Project/Site journey:
14 checks, zero exceptions/network failures. Ranking/M5 journey: 20 checks, zero
exceptions/unexpected network failures, one separately reported successful-204 body
abort from Chromium. M5 schedule journey uses an explicit local-only Pro fixture.

Early verification failures were corrected, not counted as passes: legacy test
expectations needed the Admin response field/new tables/head; multi-Project and
schedule regressions now explicitly provision paid capability; concurrent worker
ledger locks exposed a lock-order inversion; scheduled expiry exposed ORM flush-order
sensitivity; two new test imports were fixed. Browser fixture registration cookies
were cleared before Admin login and the Plan selector was corrected. A smoke overlapped
a local rebuild and saw connection refusal; another exposed a legitimate lease held
by the background local worker, so the smoke now waits for terminal completion.
The recovery command initially used the personal environment's invalid DEBUG value;
verification reruns use the explicit override above.

## Requirement-to-evidence reconciliation

The final full backend suite includes 15 billing cases (one resource case is
parameterized by device), five migration cases, and the existing M1–M5 suites.
Frontend billing tests add five cases to the earlier 61 tests.

| Requirement                                                                                                             | Executed evidence                                                                            |
| ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Six Plan prices/limits, Free devices, unavailable Plans, Admin restrictions                                             | `test_catalog_free_and_security`                                                             |
| Manual activation, snapshots unchanged after catalog edit, extension, upgrade, cancellation, independent Mobile/history | `test_transitions_snapshots_extension_and_device_independence`                               |
| Concurrent activation, one active/device, future downgrade, expiry/Free fallback                                        | `test_activation_race_and_scheduled_expiry`; database partial unique index                   |
| Per-device Project/Keyword caps, atomic bulk rejection, reactivation/device change                                      | `test_resources_bulk_reactivation_and_device_change` (Desktop/Mobile); stale-read regression |
| Atomic quota race, monthly rollover, month-end anchor, audited adjustment                                               | `test_atomic_reservation_race_and_reset_adjustment`                                          |
| Reservation before enqueue, one commit, replay, proportional cancellation/release, permanent compensation               | `test_m5_partial_cancel_replay_and_compensation`                                             |
| Free blocked, Starter weekly, Pro daily, downgrade schedule disabling, no partial scheduled Batch                       | `test_schedule_limits_downgrade_and_no_partial_batch`                                        |
| Provider fallback costs one logical check                                                                               | `test_fallback_and_retry_count_one_logical_check`; M5 retry/replay tests                     |
| Exhausted quota creates no Batch; unreserved task cannot invoke provider                                                | `test_no_quota_no_batch_and_forged_unreserved_job`                                           |
| Manual + scheduled quota race                                                                                           | `test_manual_scheduled_race_reserves_only_one_full_batch`                                    |
| Downgrade retains resources/readability and blocks expansion                                                            | `test_downgrade_preserves_over_limit_and_blocks_expansion`                                   |
| Customer search/cursor and concurrent Project cap                                                                       | `test_customer_search_cursor_and_resource_race`                                              |
| Non-executed archived work and expired enqueue recovery release quota                                                   | `test_archived_job_and_stranded_enqueue_release`                                             |
| Existing M1–M5 data, schema parity, existing-user Free fallback, schedule disabling and pending work                    | All five migration fixtures, especially `test_m6a_existing_users_schedules_and_pending_jobs` |
| Normal-user Admin route hiding, prices/reset/schedules, activation/reference, extension/cancel/adjustment               | Five frontend billing tests and real Billing/Admin browser journey                           |

Expiry uses the same `disable_schedules` reconciliation path as downgrade; inspection
confirms this wiring. Expiry/Free transitions and schedule disabling are separately
covered by the tests above; a standalone browser expiry-time-travel test was not run.
M1–M5 data preservation is established by isolated historical migration fixtures,
not an unsupported claim of a before/after dump comparison of the developer database.

## Security and zero-cost verification

Tests cover non-Admin reads/mutations, self-grant/activation denial, forbidden device
or payment fields, cross-customer subscription mutation, hidden internal notes and
references, unavailable Plans, safe quota errors, usage idempotency, and unreserved
Job rejection before provider calls. Admin account state is backend-authoritative.
Auth/tenant/worker payload/service identity tests remain in the complete regression
suite. Secrets and provider costs are not returned by billing APIs or printed by
verification scripts. No `.env` secrets were changed or logged.

Normal verification used zero payment-provider calls, zero real Cloud Tasks operations,
zero Serper credits and zero SerpApi credits. Cloud contract tests use mocked clients;
ranking/browser journeys use fake provider + local queue. No payment gateway exists.

## Known limitations

- Payment collection/confirmation and payment differences remain manual. No automatic
  recurring billing, invoice/tax/refund/proration engine, coupons, overage billing,
  annual pricing automation, enterprise entitlement overrides or self-service activation.
- No Stripe, crypto, PayPal, payment webhooks, bank-account API or provider price/balance
  synchronization. Real payment/GCP integrations are outside M6A verification.
- Usage/audit views return the latest 100 periods/200 events; complete durable history
  remains in the database. Subscription history is retained separately.
- Reconciliation scans users through the existing maintenance dispatcher; large-scale
  incremental maintenance/retention is future operational work.
- Immediate replacements intentionally grant fresh quota. Operators handle commercial
  payment differences externally; same-Plan extension does not reset monthly usage.
- No automated downgrade default or automatic checkout; Admin explicitly chooses
  immediate replacement or a future start at/after subscription end.
- Old outstanding work is grandfathered even if its reservation exceeds new Free quota;
  new requests remain blocked until capacity exists. Pre-M6A completed history is not
  retroactively charged or modified.

## Files changed

```text
Makefile
README.md
backend/alembic/versions/0008_billing_usage_limits.py
backend/app/api/v1/billing.py
backend/app/api/v1/router.py
backend/app/core/errors.py
backend/app/db/models.py
backend/app/models/billing.py
backend/app/models/user.py
backend/app/repositories/billing.py
backend/app/repositories/rank_job.py
backend/app/schemas/billing.py
backend/app/schemas/user.py
backend/app/services/billing/__init__.py
backend/app/services/billing/entitlements.py
backend/app/services/billing/reconciliation.py
backend/app/services/billing/subscriptions.py
backend/app/services/billing/usage.py
backend/app/services/billing/views.py
backend/app/services/job_execution.py
backend/app/services/keywords.py
backend/app/services/projects.py
backend/app/services/rank_batches.py
backend/app/services/rank_checks.py
backend/app/services/rank_schedules.py
backend/app/services/rank_worker.py
backend/app/services/task_queue/base.py
backend/app/services/task_queue/cloud_tasks.py
backend/scripts/platform_admin.py
backend/scripts/smoke_async_rankings.py
backend/scripts/smoke_billing.py
backend/scripts/verification_plan.py
backend/tests/business_helpers.py
backend/tests/test_auth.py
backend/tests/test_auth_invariants.py
backend/tests/test_billing.py
backend/tests/test_migrations.py
backend/tests/test_projects.py
backend/tests/test_provider_routing.py
backend/tests/test_rank_jobs.py
backend/tests/test_task_queue.py
docs/verification-milestone-6a.md
frontend/src/app/admin/customers/[userId]/page.tsx
frontend/src/app/admin/customers/page.tsx
frontend/src/app/pricing/page.tsx
frontend/src/app/settings/billing/page.tsx
frontend/src/features/admin/billing/customer-billing.tsx
frontend/src/features/admin/customers/customer-list.tsx
frontend/src/features/auth/protected-app.tsx
frontend/src/features/auth/types.ts
frontend/src/features/billing/billing-page.tsx
frontend/src/features/billing/billing.test.tsx
frontend/src/features/billing/types.ts
frontend/src/lib/api/client.ts
scripts/verify-billing-browser.mjs
scripts/verify-rankings-browser.mjs
```

The user-supplied M6A specification and personal `.env` were not modified. The final
verification continuation changed this report only; it did not alter M6A behavior.

## Full M6A Definition of Done

Checked items below refer to implemented behavior plus the executed evidence above.

## 87. Definition of Done — Plans

- [x] six initial Plans seeded
- [x] Desktop and Mobile product lines are separate
- [x] prices stored as data
- [x] entitlements stored as data
- [x] no Plan numbers hard-coded into enforcement

---

## 88. Definition of Done — Subscription

- [x] manual subscription source
- [x] manual bank-transfer metadata
- [x] one active subscription per user/device
- [x] Desktop + Mobile can coexist
- [x] activation
- [x] extension
- [x] upgrade
- [x] downgrade
- [x] cancellation
- [x] expiration
- [x] Free fallback
- [x] commercial snapshots/history

---

## 89. Definition of Done — Admin

- [x] platform Admin authorization
- [x] customer list
- [x] customer Billing detail
- [x] activate/change Desktop Plan
- [x] activate/change Mobile Plan independently
- [x] bank-transfer reference
- [x] extend/cancel
- [x] subscription history
- [x] usage view
- [x] audited usage adjustment
- [x] normal users cannot access

---

## 90. Definition of Done — Usage

- [x] monthly logical Keyword checks enforced
- [x] Desktop/Mobile usage separate
- [x] atomic reservation
- [x] commit/release
- [x] replay idempotency
- [x] remaining includes reservations
- [x] Batch cancellation reconciliation
- [x] provider retry/fallback does not double-charge
- [x] adjustments audited

---

## 91. Definition of Done — Resource Entitlements

- [x] max_projects enforced per device
- [x] max_keywords enforced per device
- [x] bulk operations atomic
- [x] schedule enabled enforced
- [x] schedule frequency enforced
- [x] Project device change cannot bypass limits
- [x] downgrade never deletes customer data
- [x] over-limit user cannot expand resources

---

## 92. Definition of Done — M5 Integration

- [x] entitlement check occurs before enqueue
- [x] usage reserved before enqueue
- [x] insufficient quota creates no provider work
- [x] scheduled checks enforce Plan + quota
- [x] task replay does not double-charge
- [x] enqueue failure releases unused reservation
- [x] existing Batch/Job progress remains intact

---

## 93. Definition of Done — Customer UI

- [x] Billing & Usage page
- [x] Desktop Plan
- [x] Mobile Plan
- [x] price
- [x] status
- [x] period
- [x] Project usage
- [x] Keyword usage
- [x] monthly checks
- [x] next reset
- [x] schedule entitlement
- [x] no Admin mutation actions

---

## 94. Definition of Done — Quality

- [x] backend full suite passes
- [x] frontend full suite passes
- [x] billing tests pass
- [x] usage concurrency tests pass
- [x] subscription transition tests pass
- [x] M5 integration tests pass
- [x] customer browser flow passes
- [x] Admin browser flow passes
- [x] Ruff passes
- [x] Ruff format passes
- [x] mypy strict passes
- [x] ESLint passes
- [x] Prettier passes
- [x] TypeScript strict passes
- [x] npm audit acceptable
- [x] production builds pass
- [x] migration tests pass
- [x] alembic check passes
- [x] Docker services healthy

---

## 95. Definition of Done — Regression

- [x] M1 regression
- [x] M2 regression
- [x] M3/M3.1 regression
- [x] M4 regression
- [x] M4.1 regression
- [x] M5 regression
- [x] ProviderRouter unchanged
- [x] DomainMatcher unchanged
- [x] ranking history unchanged
- [x] worker idempotency unchanged
- [x] schedules continue working for entitled Plans

---
