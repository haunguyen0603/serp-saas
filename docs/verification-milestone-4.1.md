# Milestone 4.1 verification

Date: 2026-09-12 (Asia/Ho_Chi_Minh)

## Implementation summary

Milestone 4.1 adds backend-only routing across Serper and SerpApi while preserving
the Milestone 4 ranking pipeline. A Rank Check now passes its provider-independent
request to `ProviderRouter`; the router applies `ProviderSelectionPolicy` to the
central `ProviderRegistry`, calls one eligible adapter, optionally performs one
safe fallback, and returns the existing normalized `SerpSearchResult` to the
unchanged DomainMatcher and ranking persistence flow.

End users still supply only Project search settings and Keyword queries. Rank Check
request schemas reject provider and budget input. No Organization, Workspace,
Membership, Team, Role, `organization_id`, worker, scheduler, queue, billing,
DataForSEO, or provider selector was added.

## Old and new provider architecture

Previously, the dependency factory selected one `SerpProvider` from the legacy
`SERP_PROVIDER` setting. It supported SerpApi and the deterministic fake.

The implemented flow is:

```text
End user → RankCheckExecutionService → ProviderRouter
                                      → ProviderSelectionPolicy
                                      → ProviderRegistry
                                      → SerperProvider or SerpApiProvider
                                      → SerpSearchResult
         → existing DomainMatcher → existing results/rankings/history
```

`SERP_PROVIDER` remains a compatibility fallback for an existing M4 environment
that has not configured the new variables. New deployments use
`SERP_ENABLED_PROVIDERS`, `SERP_PROVIDER_STRATEGY`,
`SERP_PROVIDER_PRIORITY`, and `SERP_FIXED_PROVIDER`.

## Serper adapter mapping

`SerperProvider` sends POST JSON to the backend-only `SERPER_BASE_URL`, adds the
key as `X-API-KEY`, and maps query → `q`, country → `gl`, language → `hl`, result
depth → `num`, and optional location → `location`. It maps `organic[].position`,
`title`, `link`, and `snippet` into the same `OrganicResult` used by SerpApi.
Malformed URLs, non-positive positions, duplicate positions, and rows beyond Top N
are skipped.

The official Serper playground request builder was inspected during implementation.
It exposes `q`, `location`, `gl`, `hl`, `num`, `autocorrect`, `tbs`, and `page`, and
uses POST plus `X-API-KEY`; it does not expose a device parameter. Serper is
therefore marked desktop-only. Mobile Project checks make Serper ineligible and
route to a capable provider, so `device` is never silently dropped. Location is
passed through unchanged.

Adapter-local transient retries are bounded at two attempts. Serper errors map to
sanitized generic timeout, unavailable, rate-limited, quota-exhausted,
authentication, invalid-request, and invalid-response codes. Provider-specific
response types and headers do not appear in the ranking service.

## Routing, eligibility, and strategies

`fixed` calls only the configured fixed provider. Missing credentials produce
`SERP_PROVIDER_NOT_CONFIGURED`; an unsupported environment produces
`SERP_PROVIDER_UNSUPPORTED_CONFIGURATION`; neither silently falls back.

`priority` evaluates configured names in order. A provider is eligible only when it
is enabled, has credentials, supports Google and every required request dimension,
and has available internal budget. No eligible provider produces the stable
`SERP_NO_PROVIDER_AVAILABLE` error. Tests cover configured/missing providers,
priority and fixed selection, mobile capability mismatch, budget exhaustion, and
maximum fallback enforcement.

## Request budgets and usage

`SERPER_REQUEST_BUDGET` and `SERPAPI_REQUEST_BUDGET` are optional monthly,
system-wide operational ceilings. Blank means no application ceiling. Values do
not represent provider balances, plan allowances, pricing, or user billing.

`provider_usage` persists provider, monthly period key, request/success/failure/
fallback counters, and timestamps. Each request is reserved immediately before the
adapter sends it. PostgreSQL row locking, an atomic increment, and a unique
provider/period key prevent concurrent overspend. Selection, validation rejection,
and a budget rejection before HTTP consume no request count. A 12-way concurrency
test against a budget of 3 allowed exactly 3 reservations.

## Fallback and attempt history

Fallback is allowed only after adapter retries end with timeout, temporary
unavailability, rate limiting, or identifiable quota exhaustion. Authentication,
invalid request, unsupported semantics, parsing/schema, and unexpected internal
failures do not fallback. `SERP_MAX_PROVIDER_FALLBACKS` bounds provider fallback;
the default is one.

`rank_check_provider_attempts` stores each provider that actually received one or
more upstream requests, attempt number, succeeded/failed status, timestamps,
sanitized error code, and request count. `rank_checks.provider` is updated to the
provider whose response generated persisted results. Its
`provider_request_count` totals all adapter HTTP attempts across retries and
fallback. API summaries/details expose ordered `provider_attempts`. Legacy M4
checks have an empty attempt list; the migration does not invent attempts.

## Migration

Migration `0006_multi_provider_routing` creates `provider_usage` and
`rank_check_provider_attempts`, including non-negative/positive checks, uniqueness,
the requested indexes, and an attempt-to-RankCheck cascading FK. Migrations 0001
through 0005 were not edited.

The automated migration fixtures passed for fresh base → head, head → 0005 → head,
the existing M3/M3.1 semantic migration, and a realistic M4 fixture containing a
SerpApi RankCheck, RankCheckResult, and Ranking. The M4 snapshots, provider, request
count, result, and ranking remained unchanged; new attempt/usage tables were empty.
The live database also passed 0006 → 0005 → 0006 and both pre/post `alembic check`
runs. Final revision is `0006_multi_provider_routing (head)`.

Existing Project/Keyword/Site/Alias history protections remain. Attempt rows can
cascade only if their RankCheck is deleted; business deletion of Project, Keyword,
Site, or Alias history remains protected exactly as in M4.

## API and frontend

Rank Check routes and request bodies are unchanged. Responses add
`provider_attempts`; `provider` retains its existing meaning as final data source.
Strict schemas explicitly rejected `provider`, `user_id`, and provider-budget input
in integration tests.

History/detail render `Serper`, `SerpApi`, or `Test Provider` as informational data
source metadata and show an attempt count after fallback. Project creation and Rank
Check actions contain no provider control. Frontend API tests verify POST bodies
contain no provider field. No provider secret is present in frontend configuration
or responses.

## Security verification

- Tenant ownership remains authenticated-user-only throughout Project, Keyword,
  RankCheck, Site, and alias repositories.
- Domain matching still loads only the current user's active Sites and aliases.
- Provider selection and budgets cannot be influenced by Rank Check payloads.
- `SERPER_API_KEY` and `SERPAPI_API_KEY` remain backend-only and are never placed in
  `NEXT_PUBLIC_*`.
- A Serper authentication-failure integration test verified the test key was absent
  from logs, API output, stored attempt fields, and model representation.
- Structured router logs include only RankCheck ID, provider, attempt, and safe code;
  request headers, bodies, raw responses, URLs with credentials, and exceptions are
  excluded.
- Normal automation used only FakeSerpProvider or `httpx.MockTransport`; zero real
  Serper and SerpApi credits were consumed.

## Files created

- `backend/alembic/versions/0006_multi_provider_routing.py`
- `backend/app/models/provider_usage.py`
- `backend/app/models/rank_check_provider_attempt.py`
- `backend/app/repositories/provider_usage.py`
- `backend/app/repositories/rank_check_provider_attempt.py`
- `backend/app/services/serp/policy.py`
- `backend/app/services/serp/registry.py`
- `backend/app/services/serp/router.py`
- `backend/app/services/serp/serper.py`
- `backend/scripts/smoke_provider_routing.py`
- `backend/scripts/smoke_serper.py`
- `backend/tests/test_provider_routing.py`
- `backend/tests/test_serper_provider.py`
- `docs/architecture/provider-routing.md`
- `docs/verification-milestone-4.1.md`

## Files modified

- `.env.example`
- `Makefile`
- `README.md`
- `docker-compose.yml`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/db/models.py`
- `backend/app/dependencies/business.py`
- `backend/app/repositories/rank_check.py`
- `backend/app/schemas/rank_check.py`
- `backend/app/services/rank_checks.py`
- `backend/app/services/serp/__init__.py`
- `backend/app/services/serp/base.py`
- `backend/app/services/serp/factory.py`
- `backend/app/services/serp/fake.py`
- `backend/app/services/serp/serpapi.py`
- `backend/scripts/smoke_rankings.py`
- `backend/tests/test_auth_invariants.py`
- `backend/tests/test_business_invariants.py`
- `backend/tests/test_config.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_rank_checks.py`
- `backend/tests/test_serp_provider.py`
- `docs/api/rank-checks.md`
- `docs/architecture/overview.md`
- `docs/architecture/ranking-engine.md`
- `docs/architecture/serp-provider.md`
- `frontend/src/features/projects/projects.test.tsx`
- `frontend/src/features/rankings/api.test.ts`
- `frontend/src/features/rankings/rank-check-detail.tsx`
- `frontend/src/features/rankings/rank-check-history.tsx`
- `frontend/src/features/rankings/rankings.test.tsx`
- `frontend/src/features/rankings/types.ts`
- `scripts/verify-rankings-browser.mjs`

Generated caches/build output are not implementation files. The supplied workspace
does not contain `.git`, so this inventory was assembled from the inspected working
tree and files changed during implementation.

## Commands executed and exact results

Successful focused and final checks:

```text
cd backend
.venv/bin/ruff format app alembic tests
.venv/bin/ruff check app alembic tests --fix
.venv/bin/mypy app --strict
20 focused config/SerpApi/matcher tests passed; mypy initially found integration annotations, which were fixed

DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas .venv/bin/alembic current
0005_rank_tracking
... .venv/bin/alembic upgrade head
upgrade 0005_rank_tracking -> 0006_multi_provider_routing succeeded
... .venv/bin/alembic current
0006_multi_provider_routing (head)

... .venv/bin/pytest -q tests/test_rank_checks.py
6 passed in 4.59s

... .venv/bin/pytest -q tests/test_serper_provider.py tests/test_provider_routing.py tests/test_rank_checks.py
24 passed in 9.11s

... .venv/bin/pytest -q tests/test_config.py tests/test_serp_provider.py tests/test_serper_provider.py tests/test_provider_routing.py tests/test_migrations.py tests/test_business_invariants.py tests/test_rank_checks.py
58 passed in 13.06s

... .venv/bin/pytest -q tests/test_migrations.py
3 passed in 2.07s, including complete M4 history fixture

... .venv/bin/pytest -q tests/test_provider_routing.py
14 passed in 6.60s, including exact usage success/failure/fallback counters

... .venv/bin/pytest -q tests/test_provider_routing.py tests/test_rank_checks.py
20 passed in 10.39s after the final no-provider metadata correction; mypy passed

.venv/bin/ruff check .
All checks passed
.venv/bin/ruff format --check .
120 files already formatted
.venv/bin/mypy
Success: no issues found in 83 source files
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas REDIS_URL=redis://127.0.0.1:6379/0 .venv/bin/pytest -q
169 passed in 47.36s
```

Frontend checks:

```text
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test -- --run
12 test files, 57 tests passed
npm run lint
passed
npm run format:check
All matched files use Prettier code style
npm run typecheck
passed (tsc --noEmit)
npm audit --audit-level=high
found 0 vulnerabilities
```

Migration and schema-drift checks:

```text
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas .venv/bin/alembic check
No new upgrade operations detected.
... .venv/bin/alembic downgrade 0005_rank_tracking
0006_multi_provider_routing -> 0005_rank_tracking succeeded
... .venv/bin/alembic upgrade head
0005_rank_tracking -> 0006_multi_provider_routing succeeded
... .venv/bin/alembic check
No new upgrade operations detected.
... .venv/bin/alembic current
0006_multi_provider_routing (head)
```

Build, Docker, and complete check:

```text
SERP_PROVIDER=fake SERP_ENABLED_PROVIDERS= docker compose build
backend development image built; frontend optimized production build succeeded and generated 11 routes
SERP_PROVIDER=fake SERP_ENABLED_PROVIDERS= docker compose up -d --force-recreate --wait
postgres, redis, backend, and frontend became healthy

docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-saas-backend:milestone4.1-production .
backend production image built successfully; final rebuild after smoke assertions also passed

make check
backend: 169 passed in 34.35s
frontend: 12 files / 57 tests passed
Ruff: passed; Ruff format: 120 files formatted
mypy strict: 83 source files passed
ESLint, Prettier, TypeScript strict: passed
backend and frontend connectivity probes: passed

docker compose exec -T backend alembic current
0006_multi_provider_routing (head)
docker compose exec -T backend alembic check
No new upgrade operations detected.
docker compose ps
postgres, redis, backend, frontend: Up and healthy

docker compose up -d --force-recreate --wait backend
backend restored to current .env after fake browser verification; healthy
docker compose exec -T backend python -c "...print non-secret strategy/enabled/key booleans..."
fixed/serpapi; Serper key false; SerpApi key true; no secret value printed
docker compose ps
all four services healthy
make connectivity
all backend and frontend HTTP probes passed after the final backend rebuild
```

Smoke and browser verification:

```text
make auth-smoke
passed: registration, current user, rotation, replay rejection, logout, repeat logout, login
make business-smoke
passed: two users, atomic Project create, query-only Keywords, CRUD, settings, isolation, deletion
make tracked-site-smoke
passed: aliases, promotion, duplicate handling, cross-user reuse, isolation
make ranking-smoke
passed: fake provider, normalized Top N, best Site position, no-match, history, snapshots; 0 credits
make provider-routing-smoke
passed: fake primary rate limit → fake fallback success, 2 actual requests,
persisted attempts/final provider/Top-N Ranking; 0 credits

PLAYWRIGHT_MODULE=... CHROME_EXECUTABLE=... node scripts/verify-auth-browser.mjs
passed: 9 checks, 0 browser exceptions, 0 network failures
... node scripts/verify-projects-browser.mjs
passed: 14 checks, 0 browser exceptions, 0 network failures
... node scripts/verify-rankings-browser.mjs
passed: 13 checks including no selector and provider metadata; fake provider, 0 credits, 0 browser exceptions, 0 network failures
```

Optional smoke guards were executed without opt-in:

```text
make serper-smoke
SKIPPED — RUN_REAL_SERPER_SMOKE is not true
make serpapi-smoke
SKIPPED — RUN_REAL_SERP_SMOKE is not true
```

No real-provider request was made. Browser/smoke verification used a temporary
fixed/fake container. The backend was then recreated from the current `.env`; final
Docker verification reported fixed/SerpApi, Serper key not configured, and SerpApi
key configured. No key value was printed.

Intermediate command issues that were corrected:

- The workspace has no `.git`, so `git status --short` returned “not a git
  repository”; source inspection continued directly.
- Native Alembic initially inherited an invalid `DEBUG` value and then the Docker
  hostname `postgres`; rerunning with `DEBUG=true` and localhost succeeded.
- The first native frontend test lacked required `NEXT_PUBLIC_*` variables (11 files
  and 51 tests passed, one suite failed to load); rerunning with explicit variables
  passed all 57 tests.
- One frontend format check identified `rank-check-detail.tsx`; Prettier fixed it and
  the final check passed.
- An early native backend suite used Docker's `redis` hostname and finished 162
  passed / 1 Redis health failure; the correct localhost URL produced 169 passed.
- Ruff and mypy findings during incremental development were fixed before the final
  successful runs.

## Regression results

- Milestone 1: health endpoints, database/Redis connectivity, Docker health,
  migrations, builds, lint, formatting, and strict typing passed.
- Milestone 2: authentication backend tests, auth smoke, and full browser auth
  journey passed.
- Milestone 3/M3.1: owner-scoped Project/Keyword and Tracked Site/Alias tests,
  business/tracked-site smokes, migration fixture, and browser journey passed.
- Milestone 4: provider-independent pipeline, DomainMatcher tests, normalized Top N,
  ranking snapshots/history, deletion protections, tenant isolation, fake ranking
  smoke, UI history/detail, and browser ranking journey passed.

## Real provider status

- Real Serper: **SKIPPED — `SERPER_API_KEY` not configured.** The guard was also
  executed without `RUN_REAL_SERPER_SMOKE=true`, so it made no request.
- Real SerpApi: **SKIPPED — `RUN_REAL_SERP_SMOKE` was not enabled.** A key is present
  in the local backend environment, but the optional credit-consuming request was
  deliberately not made without explicit opt-in.

## Known limitations

- Rank Checks remain manual and synchronous; there is no scheduler, worker, queue,
  recurring execution, or distributed circuit breaker.
- The two production adapters are Serper and SerpApi; DataForSEO and provider
  result merging/consensus are absent.
- Serper is eligible for desktop only because its verified synchronous Search
  contract provides no device parameter. Mobile requires another capable provider.
- Budgets are static backend configuration and persisted application counters; they
  do not synchronize provider pricing, balances, or free-plan allowances.
- There is no provider admin UI, user provider control, dynamic performance scoring,
  provider-health polling, or internal usage API.
- One Rank Check uses one successful provider response and one Top-N page; it does
  not compare providers or collect multiple pages.
- Real provider behavior was not exercised because both credit-consuming smokes
  remained opt-in.

## Definition of Done

### Serper adapter

- [x] SerperProvider exists and implements SerpProvider.
- [x] Supported Project settings map correctly; unsupported mobile is ineligible.
- [x] Organic results normalize to the existing type; malformed/empty results work.
- [x] Timeout, HTTP, quota, auth, and invalid-response mappings are tested.
- [x] API key remains backend-only and Serper-specific types do not leak.

### Routing

- [x] ProviderRegistry, ProviderSelectionPolicy, and ProviderRouter exist.
- [x] Fixed and priority strategies work and priority is configurable.
- [x] Missing credentials, capability mismatch, and budget exhaustion remove
  eligibility.
- [x] No eligible provider returns a stable error.
- [x] End users cannot choose a provider or budget.

### Budgeting

- [x] Optional persisted internal budgets work across restarts.
- [x] Concurrent reservations are race-safe.
- [x] Request count reflects actual upstream attempts.
- [x] Success/failure/fallback counters work.
- [x] Budget exhaustion routes to the next eligible provider.
- [x] Pricing and free allowances are not hard-coded.

### Fallback

- [x] Timeout, unavailable, rate-limit, and identifiable quota fallback work.
- [x] Authentication, invalid-request, and parsing defects do not fallback.
- [x] Maximum fallback count is enforced.

### Attempt history

- [x] Every actual provider attempt can persist name, ordinal, status, timestamps,
  request count, and safe error code.
- [x] Final successful provider remains on RankCheck.
- [x] RankCheck request count totals all upstream calls.
- [x] Existing M4 checks remain readable with an empty attempt list.

### Existing ranking behavior

- [x] Exact-host matching, bidirectional `www` fallback, and arbitrary-subdomain
  exclusion are unchanged.
- [x] Active aliases work, archived Sites are ignored, and best Site position wins.
- [x] Top-N persistence, snapshots, latest rankings, and history remain intact.

### Frontend

- [x] Project and Check Rankings UI have no provider selector.
- [x] Rank checks work normally and provider is informational metadata.
- [x] Fallback attempt metadata renders safely.
- [x] Frontend never receives provider keys.

### Quality and regressions

- [x] Backend and frontend full test suites pass.
- [x] Serper adapter, routing, budget/concurrency, fallback, and migration tests pass.
- [x] Zero-credit ranking and routing smokes pass.
- [x] Auth, business, Tracked Site, and browser verification pass.
- [x] Ruff, Ruff format, mypy strict, ESLint, Prettier, and TypeScript strict pass.
- [x] npm audit reports zero vulnerabilities.
- [x] Backend and frontend production builds pass.
- [x] Alembic round trip and schema-drift checks pass.
- [x] M1, M2, M3/M3.1, and M4 regressions pass.
- [x] All Docker services are healthy.

### Optional real providers

- [ ] One real Serper query — SKIPPED: `SERPER_API_KEY` not configured.
- [ ] One real SerpApi query — skipped because explicit opt-in was not enabled.

All mandatory Milestone 4.1 Definition of Done requirements are verified. Optional
real-credit smokes remain truthfully skipped.
