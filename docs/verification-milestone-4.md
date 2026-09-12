# Milestone 4 verification

Verified on 2026-09-11 against the current Milestone 3.1 repository and the local
Docker Compose PostgreSQL 16.13/Redis 7.4.8 stack.

## Implementation status

Before the interruption, the provider-independent request/result types,
`SerpProvider` protocol, mocked `SerpApiProvider`, deterministic
`FakeSerpProvider`, and exact-host/domain matcher were complete. Twelve focused
provider/matcher tests were passing with no network calls. The rank schema,
execution/query services, APIs, frontend ranking components, and integration tests
had also been drafted, but the newest persistence tests and the live migration,
Docker, smoke, production-build, browser, and documentation work were not yet
fully verified.

After resuming, the persistence and migration tests were completed and run against
real PostgreSQL; history-safe foreign keys and OpenAPI responses gained explicit
assertions; structured provider/matcher events were completed; API/architecture
documentation and README guidance were written; all full test and quality suites
were run; the images and production targets were built; the live 0005 downgrade and
upgrade were exercised; all smokes and browser journeys were run; and the two
verification-script false positives caused by expected Next.js navigation aborts
were corrected. One production-settings test discovered by `make check` was fixed
to select the required production provider while retaining the separate fake-
provider rejection test.

## Architecture and provider abstraction

The authenticated User remains the only tenant. Projects remain one SERP
environment; Keywords remain query-only; Tracked Sites remain user-global. No
Organization, Workspace, Membership, Team, Role, or `organization_id` was added.

Core execution accepts the `SerpProvider` protocol and normalized internal types.
Only the adapter and provider factory import `SerpApiProvider`; a source audit found
no SerpApi response type or payload dependency in rank execution, persistence, or
matching. The SerpApi adapter maps `engine`, `q`, `gl`, `hl`, `device`, optional
`location`, and `num`, normalizes positive organic results, skips malformed rows,
and performs at most two attempts for transient timeout/network/429/5xx failures.
Stable internal errors replace upstream details. `httpx` is a production dependency,
confirmed in the production-only image.

The fake adapter follows the same protocol and performs no network I/O. Compose,
normal tests, zero-credit smoke, and browser verification use it. Production
configuration rejects `SERP_PROVIDER=fake`.

Structured events now include `rank_check_started`, `serp_provider_request`,
`serp_provider_error`, `domain_matches_found`, `rank_check_succeeded`, and
`rank_check_failed`. Their formatter admits identifiers and counts, while excluding
query strings, request bodies, provider URLs, credentials, and exception text.

## Domain matching

One owner-scoped joined query loads active aliases belonging to active Sites. The
matcher uses exact normalized hostname first and a single bidirectional `www.`
fallback second. It does not collapse arbitrary subdomains. Different Sites can
match the same SERP; multiple results/aliases for one Site collapse to the best
organic position. Rankings retain the exact alias selected and exact result URL.

Tests cover exact precedence, both `www` directions, arbitrary-subdomain rejection,
multiple Sites, best-position collapse, inactive aliases, archived Sites, and
cross-user exclusion.

## Database and migration design

New revision `0005_rank_tracking`, based on unchanged revision 0004, adds:

- composite Project `(id, user_id)` and Keyword `(id, project_id)` unique keys;
- `rank_checks` with ownership keys, lifecycle status, all query/environment
  snapshots, provider/depth/request-count metadata, timestamps, sanitized errors,
  history indexes, and a partial unique running-check index per Keyword;
- `rank_check_results` with one normalized organic row per check/positive position;
- `rankings` with one best match per Rank Check/Site, nullable current Site/domain
  references, and immutable display/result snapshots.

Rank Check composite foreign keys use `RESTRICT` to bind the exact owner Project and
exact project Keyword. Child results/rankings use `RESTRICT` to Rank Check. Current
Site/domain links use `SET NULL`, preserving snapshot text if administrative
deletion bypasses services. Service deletes return `HISTORY_EXISTS` for referenced
Projects, Keywords, Sites, and aliases. Unreferenced entities retain M3.1 deletion
behavior.

Migration verification covered fresh base → 0005 head, a realistic M3 fixture
through 0004 → 0005 with all Users/Projects/Keywords/Sites/domains retained and
empty new rank tables, a live 0005 → 0004 → 0005 cycle, metadata comparison, and
Alembic autogeneration drift. The final state is `0005_rank_tracking (head)` and
`alembic check` reports `No new upgrade operations detected.`

## Persistence, snapshots, and retention

Transaction A validates user ownership plus active Project/Keyword state, creates
all snapshots, advances pending → running, and commits before provider I/O.
Transaction B atomically stores Top N results, best-per-Site rankings, and succeeded
status. A provider failure stores a failed status in a short transaction. A forced
ranking-persistence failure proved that results/rankings roll back and a later safe
transaction marks the check failed.

Snapshots preserve query, search engine, country, language, device, optional
location, provider, result depth, Site name, exact domain alias, position, result
URL/hostname, and title. Tests changed Project settings, Keyword text, Site name,
and alias state after a check and verified historical responses remained unchanged.
Positive-position and uniqueness constraints, timezone-aware timestamps, request
counts, zero-match success, failure history, and duplicate-running prevention were
also verified.

## API changes

- `POST /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks`
- `POST /api/v1/projects/{project_id}/rank-checks`
- `GET /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks`
- `GET /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}`
- `GET /api/v1/projects/{project_id}/rankings/latest`

Single and Project checks are synchronous. Project requests are capped at 25 by
default and use bounded concurrency. An optional `keyword_ids` subset is owner- and
active-state validated. History uses stable `(created_at DESC, id DESC)` cursor
pagination with status filtering. Latest-per-Keyword selection uses a PostgreSQL
window query and set-oriented child loads. Request schemas reject extra ownership
or provider fields. OpenAPI includes successful, authentication, ownership,
validation, conflict, and upstream failure responses as applicable.

## Frontend changes

Project detail now offers Project-level **Check Rankings**, per-row **Check now**,
running/loading feedback, provider-safe failures, and current states for Never
Checked, Not Found in Top N, failed checks, and all matched Sites. History and detail
views show snapshot configuration, result counts, match positions/domains, exact
result links, and ordered Top N organic results with tracked labels. Query cache
invalidation makes completed checks visible immediately, while persisted API history
survives reload. No generated or placeholder ranking is displayed.

## Files created

- `backend/alembic/versions/0005_rank_tracking.py`
- `backend/app/api/v1/rank_checks.py`
- `backend/app/api/v1/rankings.py`
- `backend/app/models/rank_check.py`
- `backend/app/models/rank_check_result.py`
- `backend/app/models/ranking.py`
- `backend/app/repositories/rank_check.py`
- `backend/app/repositories/rank_check_result.py`
- `backend/app/repositories/ranking.py`
- `backend/app/schemas/rank_check.py`
- `backend/app/services/domain_matching.py`
- `backend/app/services/rank_checks.py`
- `backend/app/services/serp/base.py`
- `backend/app/services/serp/factory.py`
- `backend/app/services/serp/fake.py`
- `backend/app/services/serp/serpapi.py`
- `backend/app/services/serp/types.py`
- `backend/scripts/smoke_rankings.py`
- `backend/scripts/smoke_serpapi.py`
- `backend/tests/test_domain_matching.py`
- `backend/tests/test_rank_checks.py`
- `backend/tests/test_serp_provider.py`
- `frontend/src/features/rankings/api.test.ts`
- `frontend/src/features/rankings/api.ts`
- `frontend/src/features/rankings/rank-check-detail.tsx`
- `frontend/src/features/rankings/rank-check-history.tsx`
- `frontend/src/features/rankings/rankings.test.tsx`
- `frontend/src/features/rankings/types.ts`
- `scripts/verify-rankings-browser.mjs`
- `docs/api/rank-checks.md`
- `docs/api/rankings.md`
- `docs/architecture/domain-matching.md`
- `docs/architecture/ranking-engine.md`
- `docs/architecture/serp-provider.md`
- `docs/verification-milestone-4.md`

## Files modified

- `.env.example`
- `Makefile`
- `README.md`
- `docker-compose.yml`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/app/api/v1/router.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/db/models.py`
- `backend/app/dependencies/business.py`
- `backend/app/models/project.py`
- `backend/app/models/keyword.py`
- `backend/app/repositories/keyword.py`
- `backend/app/repositories/tracked_domain.py`
- `backend/app/services/projects.py`
- `backend/app/services/keywords.py`
- `backend/app/services/tracked_sites.py`
- `backend/app/services/serp/__init__.py`
- `backend/tests/test_auth_invariants.py`
- `backend/tests/test_business_invariants.py`
- `backend/tests/test_config.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_security.py`
- `frontend/src/features/projects/keyword-manager.tsx`
- `frontend/src/features/projects/projects.test.tsx`
- `frontend/src/lib/api/client.ts`
- `scripts/verify-projects-browser.mjs`
- `docs/api/projects.md`
- `docs/architecture/overview.md`
- `docs/architecture/project-keyword-model.md`

Migrations 0001 through 0004 were not modified for Milestone 4.

## Commands and exact results

Focused checks before the interruption:

```text
.venv/bin/pytest -q tests/test_serp_provider.py tests/test_domain_matching.py
12 passed; no real HTTP requests or provider credits

.venv/bin/pytest -q tests/test_migrations.py tests/test_rank_checks.py tests/test_business_invariants.py
16 passed (earlier focused persistence checkpoint)

.venv/bin/pytest -q
139 passed (earlier full-suite checkpoint, before the final two assertions/tests)

npm test -- --run
12 files, 56 tests passed (earlier frontend checkpoint)
```

Commands executed after resuming are recorded below. `DEBUG=true`, Docker CLI
paths, and local database/Redis URLs are shown where they affected execution.

```text
DEBUG=true DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/serp_saas_test REDIS_URL=redis://localhost:6379/1 .venv/bin/pytest -q tests/test_rank_checks.py tests/test_migrations.py tests/test_business_invariants.py tests/test_serp_provider.py tests/test_domain_matching.py
17 setup errors + 12 passed; command used the wrong driver and did not exercise integration tests

DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas_test REDIS_URL=redis://localhost:6379/1 .venv/bin/pytest -q tests/test_rank_checks.py tests/test_migrations.py tests/test_business_invariants.py tests/test_serp_provider.py tests/test_domain_matching.py
15 setup errors + 2 failed + 12 passed; named database did not exist

DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/1 .venv/bin/pytest -q tests/test_rank_checks.py tests/test_migrations.py tests/test_business_invariants.py tests/test_serp_provider.py tests/test_domain_matching.py
29 passed in 8.13s

DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/1 .venv/bin/pytest -q tests/test_rank_checks.py tests/test_business_invariants.py tests/test_serp_provider.py tests/test_domain_matching.py
27 passed in 6.35s

.venv/bin/ruff check .
All checks passed
.venv/bin/ruff format --check .
107 files already formatted
.venv/bin/mypy
Success: no issues found in 75 source files

DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/1 .venv/bin/pytest -q
141 passed in 36.28s

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test npm test -- --run
12 files, 56 tests passed
npm run lint
passed
npm run format:check
All matched files use Prettier code style
npm run typecheck
passed, tsc --noEmit
npm audit --audit-level=high
found 0 vulnerabilities

docker compose build
backend and frontend built; frontend optimized production build generated 11 routes
docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-saas-backend:milestone4-production .
production backend image built successfully with 32 runtime packages
docker compose up --build -d --wait
PostgreSQL, Redis, backend, and frontend healthy

docker compose exec -T backend alembic current
0005_rank_tracking (head)
docker compose exec -T backend alembic downgrade -1
0005_rank_tracking -> 0004_project_refactor_sites succeeded
docker compose exec -T backend alembic current
0004_project_refactor_sites
docker compose exec -T backend alembic upgrade head
0004_project_refactor_sites -> 0005_rank_tracking succeeded
docker compose exec -T backend alembic current
0005_rank_tracking (head)
docker compose exec -T backend alembic check
No new upgrade operations detected

make check
first run: 140 passed, 1 failed in production-settings test; test corrected
make check
final run: backend 141 passed; frontend 12 files/56 tests passed; Ruff, Ruff format,
mypy strict, ESLint, Prettier, TypeScript strict, and all connectivity probes passed

make auth-smoke
passed: registration, current user, rotation, replay rejection, logout, repeat logout, login
make business-smoke
passed: two users, atomic Project create, query-only Keywords, bulk CRUD, settings,
tenant isolation, and deletion
make tracked-site-smoke
passed: aliases, primary promotion, duplicate handling, cross-user reuse, isolation
make ranking-smoke
passed with fake provider and 0 real credits: Top N, best Site position, no-match,
history, and configuration snapshot

PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /private/tmp/serp-node/node_modules/node/bin/node scripts/verify-auth-browser.mjs
passed; 9 checks, 0 browser exceptions, 0 network failures
... node scripts/verify-projects-browser.mjs
initial run exposed expected aborted Next.js route navigation; verifier corrected
final run passed; 14 checks, 0 browser exceptions, 0 unexpected network failures
... node scripts/verify-rankings-browser.mjs
two diagnostic runs exposed the same route-navigation abort and expected anonymous
refresh 401; verifier corrected
final run passed; 11 checks, fake provider, 0 credits, 0 browser exceptions,
0 unexpected network failures

docker compose exec -T backend python -c "from app.core.config import get_settings; s=get_settings(); print({'provider': s.serp_provider, 'serpapi_key_configured': bool(s.serpapi_api_key)})"
{'provider': 'fake', 'serpapi_key_configured': False}
RUN_REAL_SERP_SMOKE=true make serpapi-smoke
SKIPPED — SERPAPI_API_KEY not configured

docker compose ps
all four services healthy
```

The final repeated Alembic commands again reported 0005 head and no drift after all
smokes. The final M3.1 browser command also passed after the verifier-only change.

## Security verification

- Every Rank Check read/write is filtered by authenticated `user_id`, exact Project,
  and Project-owned Keyword; foreign IDs return 404.
- Cross-user Tracked Domains do not enter matching.
- Strict request bodies reject `user_id`, provider, and other extra fields.
- API key configuration is backend-only; no `NEXT_PUBLIC_*` secret exists.
- Adapter tests prove raw credential/provider/timeout details do not enter safe errors.
- Structured logs omit query strings, bodies, headers, provider URLs, credentials,
  connection strings, and raw exceptions.
- Concurrent checks use a database unique predicate, preventing duplicate provider
  consumption for one Keyword.
- History uses `RESTRICT`, service guards, nullable current references, and immutable
  snapshots to avoid silent cascade loss.
- Existing authentication, cookie, origin/CORS, token-rotation, and tenant-isolation
  regressions passed in the complete suite and browser smoke.

## Regression status

- Milestone 1: health endpoints, DB/Redis connectivity, docs/OpenAPI, builds,
  migrations, Docker health, and health browser pages passed.
- Milestone 2: all authentication tests, auth smoke, and the complete auth browser
  journey passed.
- Milestone 3/3.1: Project/Keyword and Tracked Site suites, both business smokes,
  realistic migration fixture, and the complete M3.1 browser journey passed.
- Scope audit returned no Organization/Workspace/Membership/Team/Role,
  `organization_id`, worker, scheduler, queue, or billing implementation.

## Real SerpApi smoke

**SKIPPED — SERPAPI_API_KEY not configured.**

The guarded command was actually executed with `RUN_REAL_SERP_SMOKE=true`; the
script detected the missing key before constructing a provider request. This is not
reported as passed and consumed zero credits.

## Known limitations

- Checks are manual and synchronous; there is no scheduler, worker, or queue.
- SerpApi is the only production adapter; there is no automatic provider failover.
- Default retained depth is Top 10 (configurable up to 100).
- There is no competitor entity, redirect resolver, charting, automated daily
  checking, retention/partitioning policy, billing, quota enforcement, or Project ↔
  Tracked Site mapping.
- A manual Project request is capped at 25 Keywords by default because it executes
  inside one HTTP request.
- A real SerpApi response was not exercised because no credential was configured.

## Definition of Done

### Provider layer

- [x] Generic `SerpProvider` interface exists.
- [x] `SerpApiProvider` implements it.
- [x] Core rank service is independent of SerpApi types.
- [x] Project-to-provider parameter mapping works.
- [x] Timeout and provider errors map to stable safe codes.
- [x] API key remains backend-only.
- [x] Deterministic fake provider exists.
- [x] Normal automated tests consume zero real credits.

### Domain matching

- [x] Active user domains are loaded efficiently in one joined query.
- [x] Exact hostname matching and exact-match precedence work.
- [x] Bidirectional `www` fallback works.
- [x] Arbitrary subdomains do not collapse.
- [x] Archived Sites and inactive aliases do not match.
- [x] Multiple Sites can match one SERP.
- [x] Same-Site aliases/results collapse to the best position.
- [x] Cross-user domains never match.

### Rank checks

- [x] Single-Keyword and Project manual checks work.
- [x] Project cap and bounded concurrency work.
- [x] Pending/running/succeeded/failed lifecycle is persisted.
- [x] Provider failures produce durable failed checks.
- [x] Valid zero-match and empty SERPs succeed.
- [x] Duplicate concurrent checks are prevented before duplicate provider use.
- [x] Provider request count and result depth are stored.

### Historical data

- [x] Query, search engine, country, language, device, location, provider, and depth
  snapshots are stored.
- [x] Normalized Top N organic results are stored.
- [x] Best matched-Site ranking, exact alias, result URL/hostname, and Site name are
  stored.
- [x] Project, Keyword, Site-name, and alias changes do not rewrite history.

### APIs

- [x] Single, Project, history, detail, and latest endpoints work.
- [x] Stable cursor pagination and status filtering work.
- [x] Tenant isolation works for execution and every query endpoint.
- [x] OpenAPI documents the routes and status contracts.

### Frontend

- [x] Project and Keyword check actions exist.
- [x] Loading/running state works.
- [x] Latest positions and multiple Sites display.
- [x] Never Checked, Not Found in Top N, and Failed states render.
- [x] History, detail, Top N results, tracked labels, and links render.
- [x] No fake client-side ranking data is shown.
- [x] Reload preserves server-backed history.

### Data integrity

- [x] History cannot be silently cascade-deleted.
- [x] Project/Keyword and Site/domain deletion behavior is history-safe.
- [x] Migration from realistic 0004 state preserves M3.1 data.
- [x] Alembic reports no schema drift.
- [x] Timestamps are timezone-aware.

### Quality and regression

- [x] Backend full suite, provider, fake-pipeline, matcher, persistence, snapshot,
  tenant, and migration tests pass.
- [x] Frontend full suite passes.
- [x] Auth, business, Tracked Site, and zero-credit ranking smokes pass.
- [x] Authentication, M3.1, and ranking browser journeys pass.
- [x] Ruff, Ruff formatting, strict mypy, ESLint, Prettier, and strict TypeScript pass.
- [x] npm audit reports zero vulnerabilities.
- [x] Backend and frontend production builds pass.
- [x] M1, M2, M3, and M3.1 regression checks pass.
- [x] PostgreSQL, Redis, backend, and frontend are healthy.

### Optional real provider

- [ ] One real request/normalization/key-leak smoke: **SKIPPED —
  SERPAPI_API_KEY not configured.** This optional external check is not required by
  the normal Milestone 4 suite when no key is available.

All mandatory Milestone 4 Definition of Done requirements are satisfied. The only
unexecuted behavior is the explicitly optional credit-consuming real SerpApi call.
