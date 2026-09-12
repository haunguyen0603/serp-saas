# Milestone 3 verification

Verification date: 2026-09-10.

Milestone 3 was implemented on the existing Milestone 1 and Milestone 2
foundation. The authenticated user remains the only tenant boundary. Projects
belong directly to users, and Keyword ownership is always resolved through the
exact user-owned Project named in the request. No organization, workspace,
membership, team, role, billing, worker, provider, SERP retrieval, ranking, or
later-milestone model or behavior was added.

The workspace does not contain Git metadata. The changed-file inventory below
was derived from the existing Milestone 2 verification inventory, the inspected
pre-implementation tree, and the final filesystem. Generated dependencies,
caches, bytecode, build output, and the ignored local `.env` are excluded.

## Implementation summary

- Added user-owned Project persistence, API routes, validation, normalization,
  cursor pagination, search, archive/reactivate behavior, and permanent deletion.
- Added Project-owned Keyword persistence and nested APIs for single and bulk
  creation, listing, filtering, cursor pagination, complete configuration edits,
  pause/resume, and permanent deletion.
- Added Unicode-aware keyword and location normalization, IDNA domain
  normalization, country/language/device validation, Project default snapshots,
  and a PostgreSQL unique constraint for complete tracking configurations.
- Added set-oriented bulk insertion for at most 1000 submitted values. It removes
  empty entries, deduplicates normalized input, skips existing or concurrent
  conflicts, and reports exact result counts without logging keyword text.
- Added authenticated frontend routes at `/app/projects`,
  `/app/projects/new`, and `/app/projects/[projectId]`, using the existing
  memory-only access token and refresh/retry session implementation.
- Added Project list/create/settings/archive/delete UI and Keyword
  add/bulk-add/search/filter/edit/pause/resume/delete UI. The table displays only
  stored Milestone 3 fields and contains no generated ranking or SERP data.
- Added real-PostgreSQL backend tests, typed frontend tests, a two-user API smoke
  test, and a real-browser Project/Keyword journey.
- Preserved and reran the complete Milestone 1 and Milestone 2 suite and the
  authentication API/browser verification.

## Architecture and tenant ownership

```text
Authenticated user (the tenant)
  └── Project.user_id -> users.id (ON DELETE CASCADE)
        └── Keyword.project_id -> projects.id (ON DELETE CASCADE)
```

All Project repository reads and mutations include both the Project UUID and
`current_user.id`. Keyword repository reads, lists, updates, and deletes join or
filter through `Project.user_id` while also requiring the exact URL
`project_id`. Create and bulk-create first resolve that Project for the current
user. There is no unrestricted resource lookup used by an HTTP route.

Request schemas reject extra fields, so `user_id`, `owner_id`, and
`organization_id` cannot influence creation or authorization. Query parameters
and an `X-User-ID` header also cannot override the bearer-token identity.
Foreign, cross-project, and nonexistent resource IDs return the same stable 404
shape for their resource type.

The implementation keeps router, service, repository, schema, and model layers
separate. The frontend centralizes typed API paths and query keys. It reuses the
Milestone 2 authenticated request path, including one refresh and one retry, for
both reads and mutations.

Detailed design is documented in
[`project-keyword-model.md`](architecture/project-keyword-model.md). API
contracts are in [`projects.md`](api/projects.md) and
[`keywords.md`](api/keywords.md).

## Database migration

Revision `0003_projects_keywords` follows the unchanged
`0002_authentication` revision and creates only the two Milestone 3 tables.

`projects` contains a UUID primary key, UUID `user_id` cascade foreign key,
name, normalized domain, complete default tracking configuration, optional
location, constrained active/archived status, and timezone-aware timestamps.
It has indexes on `user_id`, `(user_id, status)`, and
`(user_id, created_at)`.

`keywords` contains a UUID primary key, UUID `project_id` cascade foreign key,
display and normalized keyword text, complete copied/overridden tracking
configuration, display and normalized location, active state, and timezone-aware
timestamps. It has indexes on `project_id`, `(project_id, active)`,
`(project_id, created_at)`, and `(project_id, keyword_normalized)`.
PostgreSQL enforces uniqueness across Project, normalized keyword, search engine,
country, language, device, and normalized location.

The required live CLI sequence completed successfully:

```text
0002_authentication -> 0003_projects_keywords
0003_projects_keywords -> 0002_authentication
0002_authentication -> 0003_projects_keywords
```

The integration migration test also upgraded a disposable PostgreSQL schema to
head, downgraded through Milestones 2 and 1 to base, then upgraded back to head.
The live final drift command reported `No new upgrade operations detected.`

## Commands actually executed

Final repository and container workflow:

```bash
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make db-upgrade
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make db-downgrade
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make db-upgrade
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose up --build -d --wait
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make check
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make auth-smoke business-smoke
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose exec -T backend alembic check
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose ps
```

`make check` executed these repository commands against the final source:

```bash
docker compose run --rm backend pytest
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm test
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend ruff format --check .
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm run lint
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --rm --no-deps frontend npm run format:check
docker compose run --rm --no-deps backend mypy
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm run typecheck
docker compose exec -T backend python -c "import urllib.request; [urllib.request.urlopen('http://127.0.0.1:8000' + path) for path in ['/health', '/health/db', '/health/redis', '/docs', '/openapi.json']]"
docker compose exec -T frontend node -e "Promise.all(['http://backend:8000/health', 'http://backend:8000/health/db', 'http://backend:8000/health/redis', 'http://127.0.0.1:3000/', 'http://127.0.0.1:3000/health'].map(async url => { const r = await fetch(url); if (!r.ok) throw new Error(url); })).catch(() => process.exit(1))"
```

Production, dependency, and browser verification:

```bash
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-saas-backend:milestone-3-production .
cd frontend
export PATH=/tmp/serp-node/node_modules/.bin:$PATH
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=production npm run build
npm audit --json
cd ..
PLAYWRIGHT_MODULE=/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /tmp/serp-node/node_modules/.bin/node scripts/verify-auth-browser.mjs
PLAYWRIGHT_MODULE=/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /tmp/serp-node/node_modules/.bin/node scripts/verify-projects-browser.mjs
```

Implementation-stage checks also included:

```bash
# backend/
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest --tb=short -q
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest tests/test_business_invariants.py -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy

# frontend/
npm test
npm test -- src/features/projects/projects.test.tsx
npm run lint
npm run format:check
npm run typecheck
```

Two native frontend build attempts without the required public environment
configuration failed as intended with `Missing required configuration:
NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV must be development, test, or
production`. The fully configured native command above then passed. The first
dependency-audit attempt could not reach the npm registry from the restricted
sandbox; the permitted network retry shown above returned zero vulnerabilities.

The initial real-browser Project journey exposed that CORS still allowed only
the Milestone 2 `GET`/`POST` methods. Browser `PATCH` and `DELETE` support and
explicit preflight regression tests were added. Later runs exposed only verifier
locator/cancellation issues and an unnecessary deleted-Project cache refetch;
those were corrected before the final successful run.

## Exact verification results

| Verification | Executed result |
| --- | --- |
| Final container backend suite | 110 passed in 17.36 seconds |
| Final container frontend suite | 47 passed across 8 files in 6.31 seconds |
| Focused CORS/database invariant suite | 7 passed in 1.90 seconds |
| Ruff lint | Passed: `All checks passed!` |
| Ruff formatting | Passed: 75 files already formatted |
| mypy strict | Passed: no issues in 52 source files |
| ESLint | Passed with no errors |
| Prettier | Passed: all matched files use Prettier style |
| TypeScript strict | Passed: `tsc --noEmit` returned zero |
| npm dependency audit | Passed: 0 total vulnerabilities across 556 dependencies |
| Migration CLI | Upgrade, one-revision downgrade, and re-upgrade passed |
| Migration integration test | Head to base to head passed in an isolated PostgreSQL schema |
| Schema drift | Passed: `No new upgrade operations detected.` |
| Compose image build | Backend and frontend images built successfully |
| Compose startup | `up --build -d --wait` completed with every service healthy |
| Backend production target | Built successfully with `--no-dev` dependencies |
| Frontend production target | Built successfully; all 9 application routes were generated |
| Connectivity | Backend health/database/Redis/docs/OpenAPI and frontend/backend requests passed |
| Authentication API smoke | Passed all 7 registration/session/rotation/logout/login checks |
| Project/Keyword API smoke | Passed all 11 CRUD, bulk, filter, ownership, and deletion checks |
| Authentication browser regression | Passed all 9 checks; 0 exceptions and 0 network failures |
| Project/Keyword browser journey | Passed all 11 checks; 0 exceptions and 0 unexpected network failures |
| Final Docker status | PostgreSQL, Redis, backend, and frontend all `Up (healthy)` |

The final API smoke output was:

```json
{"authentication_smoke":"passed","checks":["registration","current_user","rotation","replay_rejection","logout","repeat_logout","login"]}
{"project_keyword_smoke":"passed","checks":["two_users","project_create","keyword_create","bulk_create","keyword_list","keyword_update","keyword_pause","project_isolation","keyword_isolation","keyword_delete","project_delete"]}
```

The real-browser outputs were:

```json
{"browser_authentication":"passed","checks":["signup","protected_account","reload_restoration","logout","anonymous_redirect","login","cookie_flags","no_token_storage","milestone_1_health_pages"],"browserExceptions":0,"networkFailures":0}
{"project_keyword_browser":"passed","checks":["login","project_empty_state","project_create","keyword_create","bulk_create","search_filter","keyword_edit","keyword_pause","reload_restoration","keyword_delete","project_delete"],"browserExceptions":0,"networkFailures":0,"expectedNavigationOrNoContentAborts":2}
```

Chrome internally reports each successful `204 No Content` DELETE fetch as
`net::ERR_ABORTED`. The verifier accepts that condition only for a DELETE and
separately requires exactly two corresponding API 204 responses. All other
request failures remain fatal; the reported `networkFailures` count is the count
of unexpected failures.

The final service status was:

```text
backend    Up (healthy)    127.0.0.1:8000->8000/tcp
frontend   Up (healthy)    127.0.0.1:3000->3000/tcp
postgres   Up (healthy)    127.0.0.1:5432->5432/tcp
redis      Up (healthy)    127.0.0.1:6379->6379/tcp
```

## Security verification coverage

Automated tests and live smoke/browser checks cover:

- Project create/list/get/update/delete scoping by bearer-derived user ID;
- Keyword create/list/get/update/delete ownership through the exact user-owned
  Project in the URL;
- foreign Project, foreign Keyword, and cross-project Keyword attempts returning
  the same result as nonexistent IDs;
- rejection of client `user_id`, `owner_id`, and `organization_id`, and inability
  to override identity through query parameters or headers;
- response and OpenAPI exclusion of user IDs, Project IDs on Keyword responses,
  and internal normalized fields;
- PostgreSQL foreign keys, cascades, full tracking-configuration uniqueness,
  required indexes, timezone-aware timestamps, and model/migration agreement;
- normalization variants, different valid configurations, and concurrent
  duplicate insertion at the database boundary;
- bulk input normalization, empty-line handling, input deduplication, existing
  conflict skipping, 1000-entry rejection, and set-oriented insertion;
- log exclusion of keyword payload text, credentials, tokens, and private errors;
- credentialed `GET`, `POST`, `PATCH`, and `DELETE` browser CORS behavior;
- the complete Milestone 2 token, cookie, refresh-rotation, replay, disabled-user,
  no-store, Origin, JSON-content, and memory-only access-token test coverage.

## Milestone 1 and Milestone 2 regression status

All earlier tests remain part of the final suites and passed. The connectivity
workflow reached `/health`, `/health/db`, `/health/redis`, `/docs`, and
`/openapi.json` from the backend container and reached backend health plus `/`
and `/health` from the frontend container. The authentication smoke test passed
registration, current-user access, refresh rotation, replay rejection, logout,
repeat logout, and login. The authentication Chrome journey passed signup,
protected navigation, reload restoration, logout, anonymous redirect, login,
cookie flags, no browser token storage, and the Milestone 1 health pages.

Historical migrations `0001_foundation` and `0002_authentication`, their
specifications, existing API behavior, authentication architecture, lock files,
and container bases were not rewritten for Milestone 3.

## Complete changed-file inventory

Modified files:

```text
Makefile
README.md
backend/app/api/v1/router.py
backend/app/core/errors.py
backend/app/core/logging.py
backend/app/db/models.py
backend/app/main.py
backend/tests/test_auth_invariants.py
backend/tests/test_migrations.py
docs/architecture/overview.md
frontend/src/app/layout.tsx
frontend/src/features/auth/auth-provider.tsx
frontend/src/features/auth/protected-app.tsx
frontend/src/features/auth/session.ts
frontend/src/lib/api/client.ts
```

Created files:

```text
backend/alembic/versions/0003_projects_keywords.py
backend/app/api/v1/keywords.py
backend/app/api/v1/projects.py
backend/app/dependencies/business.py
backend/app/models/keyword.py
backend/app/models/project.py
backend/app/repositories/keyword.py
backend/app/repositories/project.py
backend/app/schemas/keyword.py
backend/app/schemas/project.py
backend/app/services/keywords.py
backend/app/services/normalization.py
backend/app/services/projects.py
backend/scripts/smoke_projects.py
backend/tests/business_helpers.py
backend/tests/test_business_invariants.py
backend/tests/test_keywords.py
backend/tests/test_projects.py
backend/tests/test_tenant_isolation.py
docs/api/keywords.md
docs/api/projects.md
docs/architecture/project-keyword-model.md
docs/verification-milestone-3.md
frontend/src/app/app/projects/[projectId]/page.tsx
frontend/src/app/app/projects/new/page.tsx
frontend/src/app/app/projects/page.tsx
frontend/src/features/projects/api.test.ts
frontend/src/features/projects/api.ts
frontend/src/features/projects/keyword-manager.tsx
frontend/src/features/projects/project-detail.tsx
frontend/src/features/projects/project-form.tsx
frontend/src/features/projects/project-list.tsx
frontend/src/features/projects/projects.test.tsx
frontend/src/features/projects/protected.tsx
frontend/src/features/projects/types.ts
scripts/verify-projects-browser.mjs
```

No source file was deleted. No dependency or lock file changed because Milestone
3 uses the existing Python and frontend dependency sets.

## Known limitations and intentionally deferred work

- Google is the only accepted search engine, as required for this milestone.
- Project and Keyword deletion is permanent. PostgreSQL cascades Project deletion
  to its Keywords, and the frontend requires confirmation.
- Cursor pagination moves forward only; previous-page navigation is not part of
  this milestone.
- Bulk entry accepts textarea/API values with a maximum of 1000 submitted items.
  CSV import/export, grouping, tags, quotas, and subscription limits are deferred.
- API and browser checks leave disposable user accounts in the local development
  database. Successful business/browser paths delete the Projects and Keywords,
  and no credentials are printed.
- Production TLS, hosting, secret provisioning, and orchestration were not
  deployed. Production images were built and tested locally.
- The workspace has no Git metadata, so no commit or remote publication was
  performed.

SERP retrieval, rank checks/history, provider integrations, workers, queues,
scheduling, billing, competitors, search-volume data, notifications, reports,
API keys, and multi-user tenant constructs remain deliberately deferred.

## Definition of Done

### Database

- [x] `projects` table exists.
- [x] `keywords` table exists.
- [x] UUID IDs are used.
- [x] `projects.user_id` foreign key exists.
- [x] `keywords.project_id` foreign key exists.
- [x] User-to-Project and Project-to-Keyword cascade behavior is correct.
- [x] Tracking-configuration uniqueness is database-enforced.
- [x] Required Project and Keyword indexes exist.
- [x] All Project and Keyword timestamps are timezone-aware.
- [x] Migration upgrade works.
- [x] Migration downgrade works.
- [x] Migration re-upgrade works.
- [x] Alembic reports no schema drift.

### Tenant security

- [x] The authenticated user remains the only tenant boundary.
- [x] No Organization model exists.
- [x] No `organization_id` storage or ownership field exists.
- [x] All Project queries are user-scoped.
- [x] All Keyword queries are ownership-scoped through Project.
- [x] Cross-user Project access fails.
- [x] Cross-user Keyword access fails.
- [x] Cross-project Keyword access fails.
- [x] Client-provided user identifiers cannot influence authorization.
- [x] Foreign and nonexistent resources are externally indistinguishable.

### Projects

- [x] Create Project works.
- [x] List Projects works.
- [x] Get Project works.
- [x] Update Project works.
- [x] Archive Project works.
- [x] Reactivate Project works.
- [x] Delete Project works.
- [x] Domain normalization works, including IDNA input.
- [x] Search works.
- [x] Status filter works.
- [x] Cursor pagination works.
- [x] Project defaults work.
- [x] Updating defaults does not modify existing Keywords.

### Keywords

- [x] Single Keyword creation works.
- [x] Project defaults are copied at creation.
- [x] Per-Keyword override works.
- [x] Keyword normalization works.
- [x] Location normalization works.
- [x] Duplicate protection works.
- [x] Concurrent duplicate protection works.
- [x] Bulk creation works.
- [x] Bulk input deduplication works.
- [x] Existing duplicate skipping works.
- [x] The 1000-Keyword request limit works.
- [x] List works.
- [x] Search works.
- [x] Filters work.
- [x] Cursor pagination works.
- [x] Get works.
- [x] Update works.
- [x] Pause works.
- [x] Resume works.
- [x] Delete works.

### Frontend

- [x] Projects navigation exists.
- [x] Project list renders.
- [x] Project empty state works.
- [x] Project creation works.
- [x] Project editing works.
- [x] Project archive/reactivation works.
- [x] Project deletion confirmation works.
- [x] Project detail renders.
- [x] Keyword table renders only real Milestone 3 data.
- [x] Single Keyword addition works.
- [x] Bulk Keyword textarea works.
- [x] Bulk result counts display.
- [x] Keyword search works.
- [x] Keyword filtering works.
- [x] Pagination works.
- [x] Keyword editing works.
- [x] Pause/resume works.
- [x] Keyword deletion confirmation works.
- [x] Browser reload preserves the authenticated session and saved state.

### Quality and regression

- [x] Backend tests pass.
- [x] Frontend tests pass.
- [x] Database integration tests pass.
- [x] Ownership security tests pass.
- [x] Project/Keyword API smoke passes against the real stack.
- [x] Real-browser Project/Keyword verification passes.
- [x] Ruff lint passes.
- [x] Ruff formatting passes.
- [x] mypy strict passes.
- [x] ESLint passes.
- [x] Prettier passes.
- [x] TypeScript strict passes.
- [x] npm audit reports zero vulnerabilities.
- [x] Frontend production build passes with all Milestone 3 routes.
- [x] Backend production build passes.
- [x] Milestone 1 regression passes.
- [x] Milestone 2 regression passes.
- [x] Docker build/start/connectivity and final service health pass.
- [x] API and architecture documentation is complete.

Every Milestone 3 Definition of Done condition is satisfied by verification that
was actually executed during this implementation.
