# Milestone 2 verification

Verification date: 2026-09-10.

Milestone 2 was implemented on the existing Milestone 1 foundation. The
authenticated user is the only tenant boundary. This milestone adds no
organization, workspace, membership, team, role, project, keyword, tracking,
worker, billing, or other later-milestone model or feature.

The workspace did not contain Git metadata, so the file inventory below was
derived from a SHA-256 snapshot taken before Milestone 2 and a final filesystem
comparison. Generated dependencies, caches, bytecode, build output, and the
ignored local `.env` are excluded. The local `.env` received the missing
development authentication variables so that verification could run; no value
from that file is reproduced here.

## Implementation summary

- Added UUID user accounts with normalized unique email addresses, active and
  disabled states, server-generated UTC Terms timestamps, and future email
  verification preparation.
- Added Argon2id password hashing and minimal HS256 access JWTs with required
  claims, configured 15-minute expiration, and strict production configuration
  checks.
- Added cryptographically random opaque refresh tokens. PostgreSQL stores only
  SHA-256 hashes, expiration and revocation state, and last-use metadata.
- Added transactional registration, login, refresh rotation, idempotent logout,
  and current-user APIs through router, service, and repository layers.
- Added a reusable `get_current_user` dependency. It derives identity only from
  the validated Bearer token and rejects missing, malformed, expired, wrong-type,
  nonexistent-user, and disabled-user sessions.
- Added credentialed CORS, auth-origin checks, JSON-only auth mutations,
  HttpOnly/SameSite refresh cookies, environment-aware Secure cookies, and
  `Cache-Control: no-store` on authentication responses and errors.
- Added centralized frontend authentication state, signup and login forms,
  memory-only access-token handling, startup session restoration, single-flight
  refresh, one authenticated-request retry, protected `/app` navigation, and
  logout.
- Added database, repository, service, API, frontend, security, concurrency,
  migration-drift, HTTP smoke, and real-browser verification.
- Preserved all Milestone 1 health, dependency, documentation, migration,
  container, test, lint, formatting, and strict-type-check behavior.

## Architecture changes

```text
Browser
├── access JWT: application memory only
└── opaque refresh token: HttpOnly cookie
             │
             ▼
FastAPI router
             │
             ▼
Authentication / user service
             │
             ▼
User and refresh-token repositories
             │
             ▼
PostgreSQL
```

The ownership rule is `tenant_id = current_user.id`, represented as `user_id` on
future owned resources. A client-provided user identifier is never an
authorization source. Tests verify that query parameters and headers cannot
override the user identified by the access token. No ownership container or
membership abstraction exists.

Registration creates the user and refresh session in one request transaction.
Refresh locks the stored token row, validates it, revokes it, and creates the
replacement in one transaction. Concurrent replay therefore produces one
success and one rejection. If replacement persistence fails, transaction
rollback preserves the prior session. Authentication state is stored in
PostgreSQL and does not depend on Redis.

The frontend owns one `AuthSession` per mounted provider. It restores the session
through the HttpOnly cookie, stores the resulting access token only in memory,
shares concurrent refresh work, and retries a protected request at most once.
The protected page waits for authentication and `/users/me` before displaying
account data.

Detailed flow and security documentation is in
[`docs/architecture/authentication.md`](architecture/authentication.md), and the
API contract is in [`docs/api/authentication.md`](api/authentication.md).

## Database migration

Revision `0002_authentication` follows the unchanged `0001_foundation` revision.
It creates:

- `users`, with UUID primary key, unique normalized email, password hash,
  active/disabled constrained status, verification/Terms/login timestamps, and
  created/updated timestamps;
- `refresh_tokens`, with UUID primary key, `user_id` foreign key using
  `ON DELETE CASCADE`, unique 64-character token hash, expiration/revocation/use
  timestamps, and created timestamp;
- indexes covering refresh-token `user_id`, `token_hash` through its unique
  constraint, and `expires_at`.

All timestamps use timezone-aware PostgreSQL timestamp columns. Downgrading
revision `0002_authentication` drops only the two Milestone 2 tables and their
indexes. The existing baseline migration was not rewritten.

The live development-database CLI cycle completed as:

```text
0002_authentication -> 0001_foundation -> 0002_authentication
```

The migration test additionally exercised head to `0001_foundation`, then base,
then head inside a disposable PostgreSQL schema. `alembic check` reported
`No new upgrade operations detected.`

## Commands actually executed

Standard Docker and repository workflow:

```bash
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose build
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose up --build -d --wait
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make check auth-smoke
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make db-upgrade db-downgrade
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true make db-upgrade
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose exec -T backend alembic check
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker compose ps
```

`make check` executed the following real commands against the final source:

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
docker compose exec -T backend python -m scripts.smoke_auth
```

Production and browser verification:

```bash
PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-saas-backend:milestone-2-production .
PLAYWRIGHT_MODULE=/tmp/serp-node/node_modules/playwright/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' /tmp/serp-node/node_modules/.bin/node scripts/verify-auth-browser.mjs
```

Native implementation checks also executed:

```bash
# backend/
UV_CACHE_DIR=/tmp/serp-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/serp-python /tmp/serp-tools/bin/uv sync --python 3.12
DEBUG=true DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest --tb=short -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy

# frontend/
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm test
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm run lint
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm run format:check
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm run typecheck
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm run build
PATH=/tmp/serp-node/node_modules/.bin:$PATH npm audit --json
```

During implementation, checks found and led to fixes for native pytest package
discovery, strict SQLAlchemy result typing, one Prettier mismatch, and browser
network-abort reporting for an empty logout response. Logout now returns the
allowed 200 JSON result and the client consumes it. A backend production-build
attempt initially omitted the repository Dockerfile path and failed with
`Dockerfile: no such file or directory`; the corrected command shown above then
completed successfully.

## Results

| Verification | Executed result |
| --- | --- |
| Native backend suite | 74 passed in 10.24 seconds |
| Final container backend suite | 74 passed in 7.61 seconds |
| Native frontend suite | 37 passed across 6 files |
| Final container frontend suite | 37 passed across 6 files in 2.64 seconds |
| Ruff lint | Passed: `All checks passed!` |
| Ruff formatting | Passed: 56 files already formatted |
| mypy strict | Passed: no issues in 40 source files |
| ESLint | Passed with no errors |
| Prettier | Passed: all matched files use Prettier style |
| TypeScript strict | Passed: `tsc --noEmit` returned zero |
| npm dependency audit | Passed: zero vulnerabilities |
| Migration CLI | Upgrade, downgrade one revision, and re-upgrade passed |
| Migration test | Upgrade/downgrade-to-base/re-upgrade passed in isolated PostgreSQL schema |
| Schema drift | Passed: no new upgrade operations detected |
| Compose image build | Backend and frontend images built successfully |
| Compose startup | `up --build -d --wait` completed with all health checks passing |
| Backend production target | Built successfully with runtime dependencies only |
| Frontend production target | Built successfully; `/`, `/health`, `/signup`, `/login`, and `/app` generated |
| HTTP connectivity | Backend health/database/Redis/docs/OpenAPI and frontend/backend connectivity passed |
| Authentication API smoke | Registration, current user, rotation, replay rejection, logout, repeat logout, and login passed |
| Real browser | Signup, protected account, reload restoration, logout, anonymous redirect, login, cookie flags, token storage, and Milestone 1 health pages passed |
| Final service status | PostgreSQL, Redis, backend, and frontend all `Up (healthy)` |

The API smoke command returned:

```json
{"authentication_smoke":"passed","checks":["registration","current_user","rotation","replay_rejection","logout","repeat_logout","login"]}
```

The headless Chrome command returned:

```json
{"browser_authentication":"passed","checks":["signup","protected_account","reload_restoration","logout","anonymous_redirect","login","cookie_flags","no_token_storage","milestone_1_health_pages"],"browserExceptions":0,"networkFailures":0}
```

The final `docker compose ps` check was resumed after the interrupted run. It
reported PostgreSQL, Redis, backend, and frontend running and healthy. The latest
Milestone 2 source modification was at 16:23:10 +0700; the final `make check`
started at 16:28:09 +0700 and completed successfully, establishing that the
current source is the source that was tested. This report is the only source file
added after that successful run.

## Security verification coverage

Automated tests and smoke checks cover:

- Argon2id hashes, randomized salts, correct and incorrect verification, and no
  raw-password persistence;
- required JWT secret, fixed HS256 algorithm, minimal required claims, 15-minute
  expiry, bad signature, wrong algorithm/type, missing claims, future `iat`, bad
  subject, malformed token, and expired token handling;
- production rejection of debug mode, placeholder/low-diversity signing secrets,
  insecure cookies, and invalid SameSite/Secure combinations;
- random 48-byte opaque refresh credentials, deterministic SHA-256 storage hashes,
  inability to use the stored hash as the bearer credential, expiry, revocation,
  rotation, replay rejection, concurrent rotation, and rollback safety;
- normalized email uniqueness at both application and PostgreSQL levels,
  including simultaneous registration;
- equivalent unknown-email and wrong-password status, code, message, and response
  structure, with dummy Argon2 verification for unknown accounts;
- disabled-user rejection during login, refresh, and protected requests;
- rejection of client-supplied user identifiers and forbidden registration
  fields;
- HttpOnly, Path, SameSite, Max-Age, environment-aware Secure, credentialed CORS,
  trusted Origin, JSON-only mutation, no-store, and Bearer OpenAPI behavior;
- response/log exclusion of passwords, hashes, refresh credentials, access
  tokens, JWT secrets, private storage errors, Authorization headers, and Cookie
  headers;
- absence of access/refresh-token persistence in browser localStorage and
  sessionStorage;
- no authentication dependency on Redis.

## Milestone 1 regression status

All Milestone 1 tests remain in the suites and passed. The final HTTP connectivity
check reached `/health`, `/health/db`, `/health/redis`, `/docs`, and
`/openapi.json`; the frontend container reached the backend health endpoints and
rendered `/` and `/health`. The real browser also rendered both Milestone 1 pages
with API, database, and Redis connected. Existing structured logging,
configuration, async session commit/rollback, migration baseline, CORS, and
sanitized failure tests passed. The original Milestone 1 specification,
verification report, baseline migration, and frontend dependency lock were not
rewritten for Milestone 2.

## Complete changed-file inventory

Modified files:

```text
.env.example
Makefile
README.md
backend/alembic/env.py
backend/app/api/v1/router.py
backend/app/core/config.py
backend/app/core/errors.py
backend/app/db/models.py
backend/app/main.py
backend/pyproject.toml
backend/tests/conftest.py
backend/tests/test_health.py
backend/tests/test_migrations.py
backend/uv.lock
docker-compose.yml
docs/architecture/overview.md
frontend/src/app/layout.tsx
frontend/src/lib/api/client.ts
```

Created files:

```text
backend/alembic/versions/0002_authentication.py
backend/app/api/v1/auth.py
backend/app/api/v1/users.py
backend/app/core/auth_http.py
backend/app/core/security.py
backend/app/dependencies/__init__.py
backend/app/dependencies/auth.py
backend/app/models/refresh_token.py
backend/app/models/user.py
backend/app/repositories/__init__.py
backend/app/repositories/refresh_token.py
backend/app/repositories/user.py
backend/app/schemas/auth.py
backend/app/schemas/user.py
backend/app/services/auth.py
backend/app/services/users.py
backend/scripts/__init__.py
backend/scripts/smoke_auth.py
backend/tests/__init__.py
backend/tests/test_auth.py
backend/tests/test_auth_invariants.py
backend/tests/test_cookie.py
backend/tests/test_security.py
docs/api/authentication.md
docs/architecture/authentication.md
docs/verification-milestone-2.md
frontend/src/app/app/page.tsx
frontend/src/app/login/page.tsx
frontend/src/app/signup/page.tsx
frontend/src/features/auth/api.test.ts
frontend/src/features/auth/api.ts
frontend/src/features/auth/auth-form.tsx
frontend/src/features/auth/auth-provider.tsx
frontend/src/features/auth/auth.test.tsx
frontend/src/features/auth/protected-app.tsx
frontend/src/features/auth/session.test.ts
frontend/src/features/auth/session.ts
frontend/src/features/auth/types.ts
scripts/verify-auth-browser.mjs
```

No source file was deleted. `frontend/package-lock.json` remains present and was
unchanged because no frontend dependency was added. `backend/uv.lock` was updated
through the existing uv workflow for `argon2-cffi`, `PyJWT`, and
`email-validator`.

## Known limitations and intentionally deferred work

- Logout revokes the current refresh session. An already-issued access JWT can
  remain usable until its configured 15-minute expiration unless the user is
  disabled. Access-token deny lists are outside this milestone.
- Refresh single-flight coordination is per mounted browser application. Separate
  tabs do not coordinate rotation, so concurrent cross-tab refresh can cause one
  tab to lose its session and return to login.
- There is no refresh-session management UI, background cleanup job, session
  family revocation, or distributed auth rate limiter.
- Production TLS, hosting, secret provisioning, and orchestration were not
  deployed. Production configuration behavior is validated and production images
  were built locally.
- Public frontend environment settings are build-time values and require a
  frontend rebuild after changes.
- API and browser smoke checks create disposable `smoke-*` and `browser-*`
  accounts in the local development database. No credentials are printed.
- Verification used ARM64 Linux containers; other architectures were not
  separately executed. Docker/Node/Python tools installed under `/tmp` for this
  environment are temporary and are not project dependencies.
- The supplied workspace has no Git metadata, so no commit or remote publication
  was performed.

The following remain deliberately deferred: email verification workflow,
forgot/reset password, CAPTCHA, OAuth, MFA, projects, keywords, SERP tracking,
background workers, billing, subscriptions, API keys, teams, organizations,
workspaces, memberships, roles, and permissions management.

## Definition of Done

### Database

- [x] `users` table exists.
- [x] `refresh_tokens` table exists.
- [x] UUID keys are implemented.
- [x] Unique normalized email is enforced by PostgreSQL.
- [x] Refresh-token indexes are implemented.
- [x] Migration upgrade works.
- [x] Migration downgrade works.
- [x] Migration re-upgrade works.

### Security

- [x] Passwords use Argon2id.
- [x] Raw passwords are never stored.
- [x] JWT access tokens expire.
- [x] JWT secrets come from required configuration.
- [x] Refresh tokens are cryptographically random.
- [x] Raw refresh tokens are not stored in PostgreSQL.
- [x] Refresh tokens rotate.
- [x] Revoked refresh tokens fail.
- [x] Refresh cookies are HttpOnly.
- [x] Secure-cookie behavior is environment-aware and required in production.
- [x] Sensitive authentication responses use `Cache-Control: no-store`.

### Registration

- [x] Registration endpoint works.
- [x] Email normalization works.
- [x] Duplicate and racing registration are rejected safely.
- [x] The 10–128 character password policy is enforced.
- [x] Terms acceptance is required.
- [x] Successful signup creates an authenticated session.

### Authentication

- [x] Login works.
- [x] Invalid credentials are rejected without account enumeration in the API
  response.
- [x] Disabled users cannot log in.
- [x] Refresh works.
- [x] Refresh rotation works and replay fails.
- [x] Logout works and is idempotent.
- [x] Logout revokes the refresh session.

### Protected API

- [x] `/api/v1/users/me` requires authentication.
- [x] A valid access token succeeds.
- [x] An expired access token fails.
- [x] Invalid, malformed, wrong-type, and wrong-signature tokens fail.
- [x] A disabled user fails.
- [x] A reusable `get_current_user` dependency exists.

### Frontend

- [x] `/signup` works.
- [x] `/login` works.
- [x] `/app` is protected.
- [x] Confirm-password validation works and confirmation is not sent to the API.
- [x] The Terms checkbox works.
- [x] Successful signup redirects to `/app`.
- [x] Successful login redirects to `/app`.
- [x] Browser reload restores the authenticated session.
- [x] Logout works.
- [x] The access token is not persisted to localStorage or sessionStorage.
- [x] The refresh token is inaccessible to frontend JavaScript.

### Architecture

- [x] No Organization model exists.
- [x] No `organization_id` exists.
- [x] The user is documented as the tenant boundary.
- [x] User and refresh-token repository layers exist and have independent tests.
- [x] Router/service/repository separation is maintained.
- [x] The future ownership convention derives `user_id` from `current_user.id`.
- [x] No project, keyword, SERP tracking, worker, or billing functionality was
  introduced.

### Quality

- [x] Backend tests pass.
- [x] Frontend tests pass.
- [x] PostgreSQL/Redis/API integration tests pass.
- [x] Ruff lint passes.
- [x] Ruff formatting passes.
- [x] mypy strict passes.
- [x] ESLint passes.
- [x] TypeScript strict passes.
- [x] Backend and frontend production builds pass.
- [x] No production secret is hard-coded.
- [x] Authentication API smoke verification passes.
- [x] Real-browser authentication verification passes without exceptions,
  unexpected API failures, CORS failures, cookie failures, or redirect loops.
- [x] Alembic reports no model/migration schema drift.

### Regression

- [x] All Milestone 1 tests and verification endpoints continue to pass.
- [x] PostgreSQL, Redis, backend, and frontend are healthy in the final Compose
  state.
- [x] The existing Docker-only setup, build, check, migration, and connectivity
  workflows remain valid.

All Milestone 2 Definition of Done conditions are satisfied by checks actually
executed during this implementation.
