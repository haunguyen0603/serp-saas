# Milestone 3.1 verification

Verification date: 2026-09-11.

Milestone 3.1 was implemented as a refactor of the existing Milestone 3
application. The authenticated user remains the only tenant boundary. Projects
now contain one complete SERP environment and own query-only Keywords. Tracked
Sites and their Domain Aliases belong directly to the user and remain independent
of Projects.

No Organization, Workspace, Membership, Team, Role, `organization_id`, Project to
Tracked Site mapping, SERP provider, rank check, ranking history, domain matcher,
worker, scheduler, billing, or other Milestone 4 behavior was added.

The workspace does not contain Git metadata. The changed-file inventory was
derived from the inspected Milestone 3 tree, the prior verification inventory,
and the final filesystem. Generated dependencies, caches, bytecode, build output,
and the ignored local `.env` are excluded.

## Implementation summary

- Removed the Project domain and renamed every `default_*` SERP field to its
  Project-level name: `search_engine`, `country_code`, `language_code`, `device`,
  and `location`.
- Reduced Keywords to query data: display text, normalized text, active state,
  timestamps, and their Project foreign key. Per-Keyword SERP overrides are no
  longer accepted or stored.
- Made Project creation accept one to 1000 keyword lines. Input cleanup,
  normalization, deduplication, Project insertion, and initial Keyword insertion
  run in one database transaction.
- Preserved the separate single and bulk Keyword workflows with their existing
  filtering, search, cursor pagination, status changes, and deletion behavior.
- Added user-global Tracked Sites and Domain Aliases, including normalized-domain
  uniqueness per user, exactly one active primary domain per Site, alias
  activation/deactivation, primary promotion, archive/reactivate, and deletion.
- Added a semantic `0004` migration. It creates one Site for every distinct
  user/domain pair and deterministically splits old Projects by their Keywords'
  effective tracking configurations before removing obsolete columns.
- Refactored the frontend Project and Keyword screens and added Tracked Site list,
  creation, detail, alias management, and primary-domain switching screens.
- Added backend, frontend, migration-fixture, API smoke, and real-browser coverage
  for the new model while retaining the Milestone 1, 2, and still-valid Milestone
  3 regression suites.

## Architecture changes

```text
Authenticated user (the tenant)
├── Project.user_id -> users.id
│   └── Keyword.project_id -> projects.id
└── TrackedSite.user_id -> users.id
    └── TrackedDomain.(tracked_site_id, user_id)
        -> tracked_sites.(id, user_id)
```

Project repository operations always include `current_user.id`. Keyword
operations first resolve or join through the exact user-owned Project in the URL.
Tracked Site and Domain operations include both the authenticated user ID and the
parent Site ID. The composite Domain-to-Site foreign key also prevents a Domain
row from crossing tenant boundaries at the database layer.

The API never accepts ownership as input. Strict request schemas reject unknown
`user_id`, `owner_id`, and `organization_id` fields. Foreign and nonexistent IDs
produce the same external 404 behavior.

## Old and new data model

| Concern | Milestone 3 | Milestone 3.1 |
| --- | --- | --- |
| Target domain | One `projects.domain` | User-global `tracked_sites` and `tracked_domains` |
| SERP environment | Project `default_*` values plus Keyword overrides | One complete environment on Project |
| Keyword data | Query plus copied/overridden environment | Query and active state only |
| Keyword uniqueness | Query plus complete environment per Project | `(project_id, keyword_normalized)` |
| New Project | Project could be created empty | Project and at least one Keyword created atomically |
| Domain changes | Required editing/recreating Project ownership context | Add alias and promote a new primary on the Site |

## Database migration

Revision `0004_project_refactor_sites` follows `0003_projects_keywords`. Its
Alembic version identifier is `0004_project_refactor_sites`, which fits the
existing 32-character version column.

### Existing Project-domain migration

The migration normalizes every old Project domain and groups it by
`(user_id, normalized_domain)`. It creates one active Tracked Site and one active
primary Tracked Domain for each distinct pair. Duplicate domains owned by the same
user collapse into one Site; the same domain owned by different users remains one
Site per user. Stable UUIDv5 identifiers and deterministic ordering make the
transformation repeatable. Project `domain` is removed only after backfill.

### Keyword configuration-group migration

For each Project, the migration groups Keywords by normalized effective
`(search_engine, country, language, device, location)` configuration. A group that
matches the old Project defaults remains on the original Project. If none matches,
the largest group remains; ties use deterministic configuration ordering. Every
other group moves to a deterministic derived Project with a readable, length-safe
configuration suffix. User, status, timestamps, Keyword IDs, Keyword active state,
and every effective SERP configuration are preserved. Empty Projects remain and
receive their old default environment.

After placement is complete, the migration removes Keyword environment columns,
changes uniqueness to `(project_id, keyword_normalized)`, removes Project domain,
and renames the Project environment columns.

### Forward-only boundary

Revision `0004` is intentionally irreversible. A later alias edit cannot be
mapped safely to one historical Project domain, and split Projects cannot be
losslessly merged after new edits. Its `downgrade()` raises a clear
`intentionally irreversible` error and leaves the database at `0004`. This is the
forward semantic migration expressly allowed by the specification.

### Fixture proof

The mandatory real-PostgreSQL fixture starts at `0003` with two users, three
Projects, duplicate same-user domains, the same domain across users, default
Keyword configurations, overridden configurations, and repeated normalized query
text under different configurations. Upgrade through `0004` verifies:

- all four Keyword IDs remain and their active states are unchanged;
- the override group produces a fourth, deterministic Project;
- the two same-user domain values deduplicate while the other user's value stays
  isolated, producing two Sites and two Domain rows;
- old and derived Projects hold the correct environment and Keywords;
- Project domain and old Keyword environment columns are absent;
- the new query-only uniqueness and all registry constraints hold.

The second migration integration test creates an empty schema, upgrades base to
head, verifies all expected tables, invokes the documented forward-only boundary,
and confirms the revision remains at head.

## Tracked Site and Domain schema

`tracked_sites` stores UUID `id`, UUID `user_id`, name, active/archived status,
and timezone-aware timestamps. It has a cascade user foreign key, a composite
`(id, user_id)` key for tenant-safe child references, and user/status/time indexes.

`tracked_domains` stores UUID `id`, UUID `user_id`, UUID `tracked_site_id`, a
normalized ASCII hostname, `is_primary`, `active`, and timezone-aware timestamps.
PostgreSQL enforces:

- uniqueness of `(user_id, domain)`;
- a composite cascade foreign key to the Site and its owner;
- at most one primary Domain per Site through a partial unique index;
- `is_primary` implies `active` through a check constraint.

Service transactions and row locking enforce the remaining lifecycle invariant:
an active Site always has exactly one active primary Domain. Domain inputs accept
bare hostnames or HTTP(S) URLs, normalize IDNA/case/trailing dots, discard URL
path/query/fragment/port, retain exact subdomains, and reject credentials or
invalid hostnames.

## API changes

- `POST /api/v1/projects` now accepts Project settings and `keywords`, returns the
  Project plus submitted/created/skipped counts, and commits atomically.
- Project list/get/patch/delete no longer expose or accept domain or `default_*`
  fields. List responses include Keyword counts.
- Nested Keyword create/bulk/list/get/patch/delete routes remain. Keyword create
  accepts query text; patch accepts only query text and active state.
- Added `POST/GET /api/v1/tracked-sites`,
  `GET/PATCH/DELETE /api/v1/tracked-sites/{site_id}`,
  `POST /api/v1/tracked-sites/{site_id}/domains`, and
  `PATCH/DELETE /api/v1/tracked-sites/{site_id}/domains/{domain_id}`.
- Stable errors cover missing resources, same-user domain conflicts, primary
  deletion/deactivation, invalid domain input, and Site lifecycle invariants.

The contracts are documented in [Projects API](api/projects.md),
[Keywords API](api/keywords.md), and [Tracked Sites API](api/tracked-sites.md).
The ownership and transaction rules are documented in
[Project/Keyword architecture](architecture/project-keyword-model.md) and
[Tracked Site architecture](architecture/tracked-sites.md).

## Frontend changes

- `/app/projects/new` contains no domain field and accepts one-keyword-per-line
  input with live counts, empty-line cleanup, duplicate cleanup, validation,
  loading/error state, and redirect to the created Project.
- Project list and detail show the Project environment and Keyword count. Project
  setting edits display the required all-Keywords warning.
- Keyword forms and rows contain no country, language, device, location, or search
  engine controls. Single add, bulk add, search, state filter, edit, pause/resume,
  delete, pagination, and reload persistence remain.
- The protected navigation now includes Tracked Sites. List, add, and detail routes
  support Site lifecycle actions, initial aliases, adding aliases, activation,
  deactivation, deletion, and primary promotion.
- The real-browser 301 journey adds a new domain, makes it primary, confirms the
  old domain remains an active alias, and does not modify a Project or Keyword.

## Commands actually executed

Repository/container workflow:

```bash
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose up --build -d --wait
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build backend
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build frontend
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose up -d --wait frontend
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make check
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make auth-smoke
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make business-smoke
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make tracked-site-smoke
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose run --rm backend alembic upgrade head
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose run --rm backend alembic current
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose run --rm backend alembic check
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose ps
```

`make check` executed:

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
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-saas-backend:milestone-3-1-production .
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build frontend
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm audit --json
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /private/tmp/serp-node/node_modules/node/bin/node scripts/verify-auth-browser.mjs
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /private/tmp/serp-node/node_modules/node/bin/node scripts/verify-projects-browser.mjs
```

Incremental native checks were also executed from `backend/` and `frontend/`:

```bash
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest -q tests/test_migrations.py tests/test_projects.py tests/test_keywords.py tests/test_tracked_sites.py tests/test_tenant_isolation.py tests/test_business_invariants.py
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest -q
.venv/bin/ruff format .
.venv/bin/ruff check --fix .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
npm test
npm run lint
npm run format:check
npm run typecheck
```

Early implementation-stage failures were fixed before the final runs. These
included an Alembic revision value longer than the existing version column, stale
Docker source during one Ruff run, frontend assertions based on the old M3 model,
an unsupported old native Node runtime, a Project-detail success message cleared
by an unnecessary React remount, and an ambiguous Playwright `Active` selector.
The final Docker-based test/runtime checks use Node 22 and all passed.

## Exact verification results

| Verification | Executed result |
| --- | --- |
| Final `make check` | Passed with exit code 0 |
| Backend suite | 122 passed in 22.97 seconds |
| Frontend suite | 52 passed across 10 files in 5.19 seconds |
| Migration fixture tests | 2 passed as part of the backend suite; fresh base to head and realistic `0003` fixture covered |
| Tenant isolation | 7 dedicated tests passed, with additional ownership cases in Project, Keyword, and Site suites |
| Ruff lint | `All checks passed!` |
| Ruff formatting | 85 files already formatted |
| mypy strict | No issues in 59 source files |
| ESLint | Passed with no errors |
| Prettier | All matched files use Prettier style |
| TypeScript strict | `tsc --noEmit` returned zero |
| npm audit | 0 info, low, moderate, high, critical, or total vulnerabilities across 556 dependencies |
| Live Alembic revision | `0004_project_refactor_sites (head)` |
| Schema drift | `No new upgrade operations detected.` |
| Compose build | Backend and frontend images built successfully |
| Compose startup | `docker compose up --build -d --wait` completed successfully |
| Backend production target | Built successfully |
| Frontend production target | Built successfully; all 11 application routes generated, including three Tracked Site routes |
| Connectivity | Backend health/database/Redis/docs/OpenAPI and frontend/backend HTTP checks passed |
| Authentication API smoke | Passed 7 checks |
| Project/Keyword API smoke | Passed 10 M3.1 checks |
| Tracked Site API smoke | Passed 9 checks |
| Authentication browser regression | Passed 9 checks; 0 exceptions and 0 network failures |
| Milestone 3.1 browser journey | Passed 14 checks; 0 exceptions and 0 network failures |
| Final Docker status | PostgreSQL, Redis, backend, and frontend all `Up (healthy)` |

API smoke outputs:

```json
{"authentication_smoke":"passed","checks":["registration","current_user","rotation","replay_rejection","logout","repeat_logout","login"]}
{"project_keyword_smoke":"passed","checks":["two_users","atomic_project_create","query_only_keywords","bulk_create","project_setting_update","keyword_unchanged","keyword_edit_pause","tenant_isolation","keyword_delete","project_delete"]}
{"tracked_site_smoke":"passed","checks":["two_users","site_create","initial_alias","add_alias","promote_primary","aliases_retained","same_user_conflict","cross_user_domain_allowed","tenant_isolation"]}
```

Browser outputs:

```json
{"browser_authentication":"passed","checks":["signup","protected_account","reload_restoration","logout","anonymous_redirect","login","cookie_flags","no_token_storage","milestone_1_health_pages"],"browserExceptions":0,"networkFailures":0}
{"milestone_3_1_browser":"passed","checks":["signup","tracked_site_empty","tracked_site_create","alias_create","primary_promotion","old_alias_retained","project_empty","atomic_project_create","keyword_deduplication","project_settings_update","keyword_unchanged","keyword_add","keyword_pause","reload_persistence"],"browserExceptions":0,"networkFailures":0}
```

Final Docker status:

```text
backend    Up (healthy)    127.0.0.1:8000->8000/tcp
frontend   Up (healthy)    127.0.0.1:3000->3000/tcp
postgres   Up (healthy)    127.0.0.1:5432->5432/tcp
redis      Up (healthy)    127.0.0.1:6379->6379/tcp
```

## Security verification coverage

Automated tests and live checks cover:

- bearer-derived ownership for all Project and Tracked Site operations;
- Keyword ownership through the exact user-owned Project in the URL;
- Domain ownership through the exact user-owned Site and composite database key;
- indistinguishable foreign and missing Project, Keyword, Site, and Domain IDs;
- rejection of request-body `user_id`, `owner_id`, `organization_id`, old Project
  domain/default fields, and old per-Keyword environment fields;
- same-user domain collision rejection and legal cross-user reuse;
- one active primary, primary activation, promotion, deletion/deactivation guards,
  and atomic Site creation with all requested aliases;
- Project and initial Keyword rollback after an unexpected insertion failure;
- query and domain normalization, duplicate races, 1000-input limits, pagination,
  filtering, indexes, constraints, cascades, timestamps, OpenAPI contracts, CORS,
  and sanitized logging;
- the complete Milestone 2 password, JWT, HttpOnly cookie, refresh rotation,
  replay rejection, Origin/JSON-content, disabled-user, no-store, and memory-only
  access-token coverage.

## Regression status

Milestone 1 remains green through its configuration, health, PostgreSQL, Redis,
logging, security headers, OpenAPI, Docker build/health, production build, and
connectivity tests. The authentication browser journey also revisited the home and
health pages.

Milestone 2 remains green through registration, login, current-user, refresh
rotation, replay rejection, logout, cookie, CORS, session restoration, tenant
identity, and browser authentication tests.

Still-valid Milestone 3 behavior remains green: owner-scoped Project CRUD,
Project search/status/cursor listing, Keyword single/bulk create, normalization,
deduplication, search/status/cursor listing, edit, pause/resume, delete, cascades,
stable error responses, OpenAPI typing, and frontend persistence. Tests that
encoded removed M3 concepts were intentionally rewritten for the M3.1 model.

## Complete changed-file inventory

Modified files:

```text
Makefile
README.md
backend/app/api/v1/keywords.py
backend/app/api/v1/projects.py
backend/app/api/v1/router.py
backend/app/core/errors.py
backend/app/core/logging.py
backend/app/db/models.py
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
backend/tests/test_auth_invariants.py
backend/tests/test_business_invariants.py
backend/tests/test_keywords.py
backend/tests/test_migrations.py
backend/tests/test_projects.py
backend/tests/test_tenant_isolation.py
docs/api/keywords.md
docs/api/projects.md
docs/architecture/overview.md
docs/architecture/project-keyword-model.md
frontend/src/app/layout.tsx
frontend/src/features/auth/protected-app.tsx
frontend/src/features/projects/api.test.ts
frontend/src/features/projects/api.ts
frontend/src/features/projects/keyword-manager.tsx
frontend/src/features/projects/project-detail.tsx
frontend/src/features/projects/project-form.tsx
frontend/src/features/projects/project-list.tsx
frontend/src/features/projects/projects.test.tsx
frontend/src/features/projects/types.ts
frontend/src/lib/api/client.ts
scripts/verify-projects-browser.mjs
```

Created files:

```text
backend/alembic/versions/0004_project_refactor_tracked_sites.py
backend/app/api/v1/tracked_sites.py
backend/app/models/tracked_domain.py
backend/app/models/tracked_site.py
backend/app/repositories/tracked_domain.py
backend/app/repositories/tracked_site.py
backend/app/schemas/tracked_site.py
backend/app/services/tracked_sites.py
backend/scripts/smoke_tracked_sites.py
backend/tests/test_tracked_sites.py
docs/api/tracked-sites.md
docs/architecture/tracked-sites.md
docs/verification-milestone-3.1.md
frontend/src/app/app/tracked-sites/[siteId]/page.tsx
frontend/src/app/app/tracked-sites/new/page.tsx
frontend/src/app/app/tracked-sites/page.tsx
frontend/src/features/tracked-sites/api.test.ts
frontend/src/features/tracked-sites/api.ts
frontend/src/features/tracked-sites/site-detail.tsx
frontend/src/features/tracked-sites/site-form.tsx
frontend/src/features/tracked-sites/site-list.tsx
frontend/src/features/tracked-sites/tracked-sites.test.tsx
frontend/src/features/tracked-sites/types.ts
```

## Known limitations

- Migration `0004` is deliberately forward-only because a truthful, lossless
  downgrade is impossible after users edit aliases or split Projects.
- Tracked Sites are user-global and have no Project relationship yet.
- Alias management is manual. The application does not resolve HTTP redirects,
  match SERP result domains, or discover canonical/301 changes.
- SERP retrieval, providers, rank checks, result/history storage, workers,
  scheduling, billing, quotas, CSV, reports, notifications, and analytics remain
  outside this milestone.
- As inherited from Milestone 2, logout revokes the refresh session; an already
  issued access JWT remains valid until its short expiry because no access-token
  deny list exists.

## Full Definition of Done checklist

### Project refactor

- [x] Project no longer has domain.
- [x] `default_*` fields are renamed.
- [x] Project owns the complete SERP environment.
- [x] Project creation accepts initial Keywords.
- [x] Project and Keyword creation is transactional.
- [x] At least one Keyword is required.
- [x] The 1000-input safety limit works.
- [x] Separate Keyword add still works.
- [x] Bulk Keyword add still works.
- [x] Project configuration updates apply to every Keyword conceptually.

### Keyword refactor

- [x] Keyword contains query-level data only.
- [x] Keyword no longer stores search engine, country, language, device, or location.
- [x] Uniqueness is `(project_id, keyword_normalized)`.
- [x] Keyword PATCH supports only keyword text and active state.
- [x] Old per-Keyword override API input is rejected.

### Tracked Sites

- [x] `tracked_sites` exists.
- [x] `tracked_domains` exists.
- [x] Tracked Site belongs to user.
- [x] Domain Alias belongs to Site and user.
- [x] The same domain can exist for different users.
- [x] The same domain cannot exist twice for one user.
- [x] Site requires a primary domain.
- [x] Exactly one primary exists.
- [x] Primary is always active.
- [x] Alias can be added.
- [x] Alias can be disabled.
- [x] Alias can be reactivated.
- [x] Alias can become primary.
- [x] Primary deletion invariant works.
- [x] Site archive/reactivate works.
- [x] Site deletion works.

### Migration

- [x] Existing Project domains are preserved as Tracked Sites.
- [x] Same-user duplicate domains are deduplicated.
- [x] Existing Keyword overrides are preserved through deterministic splitting.
- [x] No Keyword is silently lost.
- [x] No SERP configuration is silently lost.
- [x] Old Keyword configuration columns are removed.
- [x] Project domain is removed.
- [x] Fresh base to head works.
- [x] The realistic `0003` to `0004` fixture works.
- [x] Alembic reports no schema drift.

### Tenant security

- [x] User remains the only tenant boundary.
- [x] Project queries remain user-scoped.
- [x] Keyword queries remain user-scoped through Project.
- [x] Tracked Site queries are user-scoped.
- [x] Tracked Domain queries are user-scoped.
- [x] Foreign IDs behave externally like missing IDs.
- [x] `user_id`, `owner_id`, and `organization_id` cannot override ownership.
- [x] No Organization or Workspace model was introduced.

### Frontend

- [x] Add Project has no domain field.
- [x] Add Project accepts multiple Keywords.
- [x] Project list has no domain.
- [x] Project detail shows the SERP environment.
- [x] Keyword table has no repeated SERP configuration columns.
- [x] Keyword Add and Bulk Add are simplified.
- [x] Tracked Sites navigation exists.
- [x] Tracked Site list works.
- [x] Site creation works.
- [x] Domain Alias management works.
- [x] Primary-domain switching works.
- [x] The 301 workflow works without modifying Project.
- [x] Reload preserves saved state.

### Quality

- [x] Backend tests pass.
- [x] Frontend tests pass.
- [x] Migration fixture tests pass.
- [x] Tenant isolation tests pass.
- [x] Project/Keyword smoke passes.
- [x] Tracked Site smoke passes.
- [x] Browser verification passes.
- [x] Ruff passes.
- [x] Ruff formatting passes.
- [x] mypy strict passes.
- [x] ESLint passes.
- [x] Prettier passes.
- [x] TypeScript strict passes.
- [x] npm audit is acceptable with zero vulnerabilities.
- [x] Backend production build passes.
- [x] Frontend production build passes.
- [x] Milestone 1 regression passes.
- [x] Milestone 2 regression passes.
- [x] All still-valid Milestone 3 behavior passes.
- [x] Docker services are healthy.

All applicable Milestone 3.1 Definition of Done requirements were implemented and
verified successfully.
