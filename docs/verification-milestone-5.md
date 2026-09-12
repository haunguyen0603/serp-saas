# Milestone 5 verification

Verification date: 2026-09-12 (UTC and Asia/Ho_Chi_Minh).
Scope: M5 implementation already present in the working tree, followed by final
verification and documentation. No GCP deployment or real SERP
request was performed. This report distinguishes executed local checks from deployment
configuration that has only been inspected and contract-tested.

## Final result

- Final backend suite: **196 passed in 68.90s (0:01:08)** through `make check`,
  including M4.1 fixture preservation, HTTP retry/terminal and empty-schedule checks.
- Final frontend suite: **13 test files, 61 tests passed**, Vitest duration **8.99s**
  through `make check` (the direct local run also passed, duration 7.01s).
- Final Docker `make check`: **PASS — 196 backend tests in 68.90s; 13 frontend files / 61 tests in 8.99s; lint, formatting, strict typing and connectivity all passed**.
- Browser authentication, Project/Keyword/Tracked Site, and async ranking/schedule
  journeys passed. Zero browser exceptions and zero unexpected network failures.
- All seven M2–M5 smoke commands passed using fake/local or mocked infrastructure.
- Alembic head: `0007_async_rank_check_jobs`; upgrade to head succeeded;
  `alembic check`: **No new upgrade operations detected.**
- Backend production image built; production worker command passed live HTTP/DB probes.
- Frontend optimized production builds succeeded in Docker and direct `npm run build`.
- `npm audit --audit-level=high`: **found 0 vulnerabilities**.
- Final Docker/connectivity state: **all five services healthy; backend and frontend connectivity probes passed**.
- Real Cloud Tasks: **SKIPPED — real GCP Cloud Tasks environment not configured**.

## Implementation and architecture

Before M5, manual Project and Keyword POST requests awaited
`RankCheckExecutionService`, ProviderRouter, provider searches, domain matching and
history persistence before returning results. M5 user POST requests atomically create
Batch/Job rows, enqueue a bounded first chunk, and return HTTP 202. One Job represents
one Keyword. Cloud Tasks delivers a minimal versioned Job identifier to the private
worker; the local adapter uses the same durable jobs and execution service.

The ProviderRouter, provider selection/fallback policy and DomainMatcher behavior are
retained. The existing engine gains optional Job execution fencing and atomic Job →
RankCheck linkage, rather than a second matching/persistence pipeline. M4 engine
regression tests now call that service directly; M5 tests separately verify actual
HTTP enqueue and worker contracts. GET latest rankings and RankCheck history remain.

Detailed design and deployment instructions:

- [Asynchronous ranking architecture](architecture/async-ranking.md)
- [Batch/schedule API contract](api/rank-check-batches.md)
- [Cloud Tasks, Cloud Run, OIDC/IAM and recovery](architecture/cloud-tasks-deployment.md)

### Persisted models

| Model | Purpose and integrity |
| --- | --- |
| RankCheckBatch | User/project action, explicit manual_project/manual_keyword/scheduled trigger, requested count, lifecycle timestamps, schedule occurrence; composite tenant FK and history/status indexes |
| RankCheckJob | One Keyword, status, attempts/max attempts, queue name, retry time, lease/execution ID, RankCheck reference; unique batch/keyword and RankCheck linkage, tenant-consistent FKs |
| ProjectRankSchedule | One schedule per user/project, enabled, daily/weekly, local time, weekday, IANA timezone, UTC next_run_at and last_enqueued_at; due-schedule index |

Counters are derived from Job status, not duplicated mutable integers on Batch. Batch
state reconciliation takes a Batch lock before Job transitions. Queued count means
currently queued jobs. Terminal jobs determine progress percentage. Schedule deletion
sets historical Batch.schedule_id to null and retains Batch/Job/RankCheck history.

### Queue, worker, idempotency and retry

`RankCheckTaskQueue` separates business logic from the Google SDK. LocalTaskQueue
accepts deterministic identifiers and the local runner reads committed PostgreSQL
jobs. CloudTasksRankCheckQueue constructs SDK HTTP tasks, JSON `{version:1,job_id}`,
OIDC identity/audience, schedule time, deadline and deterministic UUID-based names.
Enqueue exceptions are normalized; AlreadyExists is acceptance, never proof of results.
Pending rows survive partial enqueue failures and are drained by recovery.

Worker claims take PostgreSQL row locks, commit a fresh execution UUID/lease, and
increment attempts only on a successful claim. Active duplicate/backoff deliveries
return 503 without another claim; terminal replay returns 200 without provider work.
The engine links its RankCheck in the start transaction, reuses it across retries,
and checks execution ownership before persisting success/failure. Stale workers cannot
write ranking results. If RankCheck succeeded before Job completion was saved, replay
reconciles the existing success. Provider attempt numbering and request totals include
retry attempts while retaining router/provider accounting semantics.

Temporary provider/network/persistence/infrastructure errors retry. Configuration,
authentication, archived/paused entities, static budget exhaustion and unsupported/no
eligible provider errors terminate safely. Application max claims defaults to five;
Cloud Tasks transport retries are distinct and configured with 30–300s backoff and
3600s duration. Both Cloud Tasks attempt and duration conditions influence transport
termination; the application independently enforces claim limits and recovery age.
Cancelled pending/queued jobs never execute; running jobs may finish.

### Scheduler and recovery

One private dispatcher is intended for one Cloud Scheduler invocation every five
minutes. It uses SKIP LOCKED, a unique `(schedule_id, scheduled_for)` identity, and
advances to a future UTC occurrence. Downtime produces at most one catch-up batch.
An unfinished previous scheduled batch blocks overlap. Archived Projects disable
schedules; no-active-keyword Projects advance without provider calls. Daily/weekly,
IANA timezone and DST behavior are covered by tests.

Recovery drains pending work in bounded chunks, reclaims eligible local expired
leases, reconciles batches, and closes stranded cloud jobs after the last-update age
cutoff. Cloud redelivery reclaims expired leases before that cutoff. Completed results
are retained. The cloud recovery cutoff avoids treating task-name tombstones as fresh
work. Failed terminal deliveries require a new manual action after the cause is fixed.

### API and frontend changes

New 202 Project and single-Keyword batch endpoints replace synchronous POST routes.
Owner-scoped batch history/detail/jobs/cancel and schedule GET/PUT/DELETE are provided
with cursor pagination for lists. Unknown ownership/provider/search payload fields are
rejected. Internal task/dispatcher routes exist only on the worker app, with no user
routes or OpenAPI. CORS includes PUT for schedule updates.

The Project UI queues Check Rankings/Check now, disables duplicate pending submits,
shows progress and batch history, exposes per-Keyword job states, allows cancellation,
and refreshes latest/history on terminal completion. Polling stops when terminal.
Schedule controls support enabled/paused, daily/weekly, weekday, local time and timezone.
The old 25-keyword warning is removed. No provider selector or GCP identity/configuration
is shown to normal users.

## Exact commands and evidence

Commands below were executed from the repository root unless a directory is shown.
Local tool binaries were already provisioned outside the repository. Their prefixes
were needed because the normal shell PATH did not contain Docker or Node 22:

```sh
export DOCKER_HOST=unix:///Users/haunguyen/.colima/docker.sock
export DOCKER_CONFIG=/private/tmp/serp-tools/docker
export PATH=/private/tmp/serp-tools/bin:$PATH
export DEBUG=false TASK_QUEUE_PROVIDER=local
export SERP_PROVIDER=fake SERP_ENABLED_PROVIDERS=fake
export SERP_PROVIDER_STRATEGY=fixed SERP_FIXED_PROVIDER=fake SERP_PROVIDER_PRIORITY=fake
```

These exports represent the identical per-command environment assignments actually
used. `.env` was not printed or rewritten. Local test database credentials below are
the repository's development-only PostgreSQL credentials.

### Backend, frontend and quality

```sh
cd backend
DEBUG=false DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas \
  REDIS_URL=redis://127.0.0.1:6379/0 .venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

Final local suite: 196 passed in 84.42s. Earlier post-config-fix run was 194 passed in
76.61s; two added verification tests explain the increase. Ruff passed, format check
reported 142 files formatted, and strict mypy reported no issues in 97 source files.

```sh
cd frontend
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH \
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test -- --run
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run lint
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run format:check
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run typecheck
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm audit --audit-level=high
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH \
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development npm run build
```

13 files / 61 tests passed, Vitest total duration 7.01s. ESLint, Prettier and strict
TypeScript passed; audit found zero vulnerabilities. Direct production build exited 0:
Next.js 16.3.4 webpack compilation succeeded in 2.9s, TypeScript finished in 2.2s,
and static generation completed 11/11 entries in 226ms. Frontend polling test verifies
no additional batch requests after terminal state and ranking cache invalidation.

```sh
docker compose build
docker compose up -d --build --wait
docker compose build backend
make check
docker build --target production -f infrastructure/docker/backend.Dockerfile \
  -t serp-saas-backend:milestone5-production .
```

The first build/up attempts exposed environment DEBUG and provider-setting mismatches;
the explicit consistent fake/local configuration above corrected the verification
environment. No provider-engine change was needed. Final build/up succeeded. The
final `make check` exited 0: backend 196 passed in 68.90s, frontend 13 files / 61 tests
in 8.99s, all quality checks and connectivity passed.

### Smoke and browser commands

```sh
make auth-smoke business-smoke tracked-site-smoke ranking-smoke \
  provider-routing-smoke async-ranking-smoke cloud-tasks-contract-smoke
```

| Smoke | Executed result |
| --- | --- |
| Authentication | PASS: register/current user/rotation/replay rejection/logout/login |
| Business | PASS: two tenants, Project create/settings, Keyword bulk/edit/pause/delete |
| Tracked Site | PASS: aliases, primary promotion, uniqueness and tenant isolation |
| Ranking | PASS: fake normalized results, best site match, no-match, snapshots/history |
| Provider routing | PASS: mock safe fallback, two mock upstream requests, zero real credits |
| Async ranking | PASS: two jobs, duplicate delivery, completed progress, zero external credits |
| Cloud Tasks contract | PASS: real SDK serialization with mocked client; name/URL/OIDC/payload |

```sh
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs \
CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
/private/tmp/serp-node/node_modules/node/bin/node scripts/verify-auth-browser.mjs
# Same environment and Node executable:
node scripts/verify-projects-browser.mjs
node scripts/verify-rankings-browser.mjs
```

| Journey | Executed result |
| --- | --- |
| Authentication / M1 | PASS: signup, protected account, reload/refresh, logout/login, cookie flags, no browser token storage, API/DB/Redis health pages |
| Project / Tracked Site | PASS: site/alias creation, primary promotion, old alias retained, Project creation, keyword deduplication/add/pause, settings and reload persistence |
| Ranking / M5 | PASS: 202 queue response, Job success, latest rank, history/detail, tracked labels, polling observed and stopped, batch history, schedule create/update/delete/timezone, no provider selector or cloud details |

All journeys reported zero browser exceptions and zero **unexpected** network failures.
Chromium reported one `ERR_ABORTED` for a successful bodyless schedule DELETE. The
script accepts this only when the matching response was 204 and the UI confirmed the
schedule was deleted; other failures remain fatal. It reports this separately as
`successful204BodyAborts: 1`, not as an unqualified absence of all request events.

### Worker runtime, schema and data preservation

Production-image probe used a temporary Compose override setting backend image to
`serp-saas-backend:milestone5-production`, then:

```sh
docker compose -f docker-compose.yml -f /private/tmp/m5-production-override.yml \
  run --rm --no-deps -T backend python - < /private/tmp/m5-verify-worker-runtime.py
```

The executed probe is preserved as [verify-worker-runtime.py](../scripts/verify-worker-runtime.py).
It starts the actual `uvicorn app.worker_main:app --host 127.0.0.1 --port 8080` command
from the production image: health 200, DB health 200, unknown Job acknowledgment 200,
user API/docs/OpenAPI absent (404), zero provider calls. Probe environment is explicitly
local/fake; this validates the production image/command, not real Cloud Run IAM.
An initial `/private/tmp` bind mount was unavailable inside Colima; stdin execution
succeeded and left no extra long-running worker container.

```sh
docker compose exec -T backend alembic current
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
```

Current revision is 0007_async_rank_check_jobs. Upgrade to head is successful and
idempotent. No new upgrade operations detected. Four migration tests cover fresh
upgrade, the older forward-only boundary, M4 history fixtures, and M5 reversible
0006 → 0007 → 0006 → 0007 with schema drift checks. The M4 fixture also seeds
M4.1 provider usage/attempt data at 0006 and verifies it survives M5 upgrade and
round-trip, alongside original RankCheck/results/Rankings snapshots. Round-trip uses
isolated schemas; the developer's active ranking history is not downgraded/deleted.

### Final Docker configuration and recovery command

`docker compose ps` reported healthy backend, worker, frontend, PostgreSQL and Redis.
Only a safe allowlist of configuration fields was printed with `get_settings()`:
API and local worker both use app_env=development, DEBUG=false, queue=local,
enabled/fixed provider=fake. Batch ceiling is 5000, job attempts 5 and lease 300s.
Worker HTTP pool settings are 2/0. No database URL, JWT secret, provider key or service
identity token was printed. The local worker command is `python -m scripts.rank_jobs
--loop`; the separate production command was probed as described above.

`make recover-rank-jobs` also ran successfully (exit 0), exercising the added
maintenance command's dispatcher/recovery wiring against local infrastructure.
Final `make check` connectivity probes covered API health/DB/Redis/docs/OpenAPI and
frontend-to-backend health plus frontend root/health pages.

## Security, IAM and cost verification

Tests verify owner-scoped Batch/Job/Schedule access, composite tenant constraints,
unsupported/extra task fields, missing service authorization (401), wrong service
identity (403), task caller rejection on the scheduler route, and production rejection
of local queue configuration. Local task execution uses DB ownership, never an end-user
session fabricated by the worker. Source inspection confirms secrets remain backend-only.

OIDC signature/audience verification delegates to Google's verifier and per-endpoint
service email authorization. Actual signed Cloud Tasks → Cloud Run invocation is not
claimed verified without a GCP environment. Deployment documentation specifies private
Cloud Run, least-privilege queue enqueuer/actAs and worker invoker roles, Secret Manager,
one Scheduler job and workload identities. No Owner/Editor grants are required.

Cost defaults: 2 dispatches/s, 2 concurrent queue dispatches, worker concurrency 1,
max 2 worker instances, min 0, pool 2/overflow 0, batch ceiling 5000, five claims,
30–300s backoff, bounded pending enqueue and schedule catch-up. No production Redis
queue, Memorystore, always-on VM, Kubernetes or Pub/Sub requirement. Normal tests and
smokes used zero real Cloud Tasks operations and zero real Serper/SerpApi credits.

## Regression and limitations

M1 foundation/health, M2 authentication, M3 Projects/Keywords, M3.1 Tracked Sites/Aliases,
M4 matching/history and M4.1 routing/budgets/fallback are exercised by final suites,
smokes and browser journeys. API breaking change is intentional: old synchronous POST
routes are retired; existing ranking GET contracts remain.

Known limitations:

- Real GCP IAM/queue provisioning/delivery remains optional and unverified locally.
- Cloud Tasks is the only production queue; local loop is for development.
- Cloud pending work drains at most 100 jobs per dispatcher pass, ten enqueues at a
  time; very large batches may require multiple passes. This preserves responsiveness.
- Transport delivery counts may exceed Job claim counts; static budget/configuration
  errors terminate instead of retrying rapidly.
- Late crashed/reclaimed workers may already have consumed provider requests; fencing
  protects logical ranking history, not exactly-once upstream billing.
- One RankCheck is reused across retries, preserving its first search snapshot and
  cumulative provider attempt history. Job last_error_code tracks the latest failure.
- No manual idempotency key; UI disables pending duplicate submissions. Scheduled
  occurrences have mandatory database deduplication.
- Simple daily/weekly scheduling only; DST gap shifts forward and fold uses first run.
- No billing/plan quotas, notifications, competitor analytics, multi-page SERPs,
  automatic provider balances, advanced autoscaling optimizer or distributed tracing.
- Operational retention policy is deferred; no automatic history deletion.
- Development Compose worker health probe checks process liveness; worker DB correctness
  is separately tested through worker HTTP DB health and local smoke.

## Files created / modified

Created:

```text
backend/alembic/versions/0007_async_rank_check_jobs.py
backend/app/api/v1/rank_batches.py
backend/app/models/rank_job.py
backend/app/repositories/rank_job.py
backend/app/schemas/rank_job.py
backend/app/services/job_execution.py
backend/app/services/rank_batches.py
backend/app/services/rank_schedules.py
backend/app/services/rank_worker.py
backend/app/services/task_queue/__init__.py
backend/app/services/task_queue/base.py
backend/app/services/task_queue/cloud_tasks.py
backend/app/services/task_queue/factory.py
backend/app/services/task_queue/local.py
backend/app/worker_main.py
backend/scripts/rank_jobs.py
backend/scripts/smoke_async_rankings.py
backend/scripts/smoke_cloud_tasks.py
backend/scripts/smoke_cloud_tasks_contract.py
backend/tests/ranking_helpers.py
backend/tests/test_rank_jobs.py
backend/tests/test_task_queue.py
docs/api/rank-check-batches.md
docs/architecture/async-ranking.md
docs/architecture/cloud-tasks-deployment.md
docs/verification-milestone-5.md
frontend/src/features/rankings/batch-panel.test.tsx
frontend/src/features/rankings/batch-panel.tsx
frontend/src/features/rankings/batches.ts
infrastructure/configure-rank-queue.sh
scripts/verify-worker-runtime.py
```

Modified across the complete M5 implementation and verification:

```text
.env.example
Makefile
README.md
backend/app/api/v1/rank_checks.py
backend/app/api/v1/router.py
backend/app/core/config.py
backend/app/core/logging.py
backend/app/db/models.py
backend/app/main.py
backend/app/repositories/rank_check.py
backend/app/repositories/rank_check_provider_attempt.py
backend/app/services/rank_checks.py
backend/pyproject.toml
backend/tests/conftest.py
backend/tests/test_auth_invariants.py
backend/tests/test_business_invariants.py
backend/tests/test_config.py
backend/tests/test_migrations.py
backend/tests/test_provider_routing.py
backend/tests/test_rank_checks.py
backend/tests/test_security.py
backend/uv.lock
docker-compose.yml
docs/api/rank-checks.md
frontend/src/features/projects/keyword-manager.tsx
frontend/src/features/projects/projects.test.tsx
frontend/src/features/rankings/api.test.ts
frontend/src/features/rankings/api.ts
frontend/src/features/rankings/rank-check-detail.tsx
frontend/src/features/rankings/rankings.test.tsx
scripts/verify-rankings-browser.mjs
```

User-provided milestone specifications and personal `.env` were left untouched.
During the final continuation, changes were confined to verification tests/scripts and
documentation; no working M5 implementation was rewritten.

## Full M5 Definition of Done

### 150. Batch / Job Models

- [x] RankCheckBatch exists
- [x] RankCheckJob exists
- [x] ProjectRankSchedule exists
- [x] migrations created
- [x] tenant ownership enforced
- [x] indexes/constraints added
- [x] existing ranking history preserved

### 151. Async Execution

- [x] Project checks no longer execute SERP calls inside user HTTP request
- [x] single Keyword Check now is asynchronous
- [x] one Job represents one Keyword
- [x] API returns Batch/Job identity quickly
- [x] worker executes existing RankCheck service
- [x] Ranking persistence remains unchanged

### 152. Cloud Tasks

- [x] task queue abstraction exists
- [x] local adapter exists
- [x] Cloud Tasks adapter exists
- [x] deterministic task names used
- [x] payload contains only version + job_id
- [x] OIDC worker invocation supported
- [x] queue settings are configuration-driven
- [x] business logic contains no Google SDK dependency

### 153. Worker

- [x] Cloud Run-compatible worker exists
- [x] worker endpoint is internal
- [x] worker is stateless
- [x] atomic Job claiming works
- [x] execution lease works
- [x] duplicate delivery is idempotent
- [x] only one RankCheck is created per Job
- [x] terminal Jobs return success without duplicate execution

### 154. Retry

- [x] provider retry remains separate
- [x] provider fallback remains separate
- [x] task/job retry exists
- [x] retryable vs terminal errors are classified
- [x] Cloud Tasks retry behavior is intentional
- [x] max attempts enforced
- [x] static budget exhaustion does not create rapid useless retries

### 155. Progress

- [x] Batch counters are concurrency-safe
- [x] Batch status transitions are correct
- [x] progress API exists
- [x] Batch history exists
- [x] Job detail list exists or equivalent diagnostic path
- [x] Project UI shows queued/running/completed states
- [x] polling stops after terminal state

### 156. Scheduler

- [x] Project schedule CRUD exists
- [x] one schedule per Project
- [x] daily supported
- [x] weekly supported
- [x] IANA timezone persisted
- [x] next_run_at stored in UTC
- [x] due-schedule dispatcher exists
- [x] duplicate dispatcher calls are safe
- [x] one Cloud Scheduler job can dispatch all due Projects
- [x] one schedule occurrence creates at most one Batch
- [x] catch-up does not create an unbounded backlog

### 157. Cancellation / Recovery

- [x] Batch cancellation is best-effort and safe
- [x] cancelled queued Jobs do not execute
- [x] running Jobs may complete safely
- [x] stale running Jobs can recover
- [x] pending Jobs can be re-enqueued
- [x] Batch state can be reconciled

### 158. Security

- [x] worker production invocation requires authenticated service identity
- [x] scheduler dispatcher invocation requires authenticated service identity
- [x] task payload cannot override ownership or provider
- [x] tenant isolation remains intact
- [x] no GCP credentials reach frontend
- [x] no SERP keys reach frontend
- [x] secrets do not appear in logs
- [x] least-privilege IAM documented

### 159. Cost Safety

- [x] M5 does not require Memorystore
- [x] M5 does not require always-on VM workers
- [x] Cloud Run architecture supports scale-to-zero where practical
- [x] one Cloud Scheduler job can serve all Projects
- [x] queue rate limits configurable
- [x] batch size safety limit exists
- [x] task duplication protection exists
- [x] local development requires no paid GCP service

### 160. Testing

- [x] full backend tests pass
- [x] full frontend tests pass
- [x] queue adapter tests pass
- [x] worker idempotency tests pass
- [x] concurrency tests pass
- [x] retry tests pass
- [x] scheduler tests pass
- [x] migration tests pass
- [x] tenant isolation tests pass
- [x] browser verification passes
- [x] local async ranking smoke passes
- [x] Cloud Tasks contract smoke passes
- [x] normal tests consume 0 real Cloud Tasks operations
- [x] normal tests consume 0 real SERP credits

### 161. Quality

- [x] Ruff passes
- [x] Ruff format passes
- [x] mypy strict passes
- [x] ESLint passes
- [x] Prettier passes
- [x] TypeScript strict passes
- [x] npm audit acceptable
- [x] backend production image builds
- [x] worker production image/command builds
- [x] frontend production build passes
- [x] Alembic schema drift check passes
- [x] Docker services healthy

### 162. Regression

- [x] M1 health/foundation regression passes
- [x] M2 authentication regression passes
- [x] M3 Project/Keyword regression passes
- [x] M3.1 Tracked Sites/Aliases regression passes
- [x] M4 Ranking Engine regression passes
- [x] M4.1 Multi-provider routing regression passes
- [x] DomainMatcher behavior unchanged
- [x] provider budgets/fallback unchanged
- [x] ranking history/latest behavior unchanged

### 163. Optional real GCP verification

- [ ] One real Cloud Tasks enqueue/delivery — skipped.
- [ ] Real authenticated Cloud Run worker invocation — skipped.
- [ ] Real Cloud Tasks delivery reaches terminal Job state — skipped.

**SKIPPED — real GCP Cloud Tasks environment not configured**

The checked cloud architecture/security items above denote implemented contracts,
production guards, local/mock tests and deployment documentation. They do not assert
that GCP resources were provisioned or that real IAM delivery was executed.

