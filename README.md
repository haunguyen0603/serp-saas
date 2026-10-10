# SERP SaaS

A foundation for a SaaS SERP rank tracking platform. Milestone 1 provides development
infrastructure, dependency connectivity, migrations, testing, and code quality.
Milestone 2 adds email/password accounts and authentication. Milestone 3.1 adds
SERP-environment Projects, query-only Keywords, and a user-global Tracked Site
domain registry. Milestone 4 adds manual provider-independent rank checks,
normalized Top-10 organic results, domain matching, and durable ranking history.
Milestone 4.1 adds internal Serper/SerpApi routing, safe fallback, persisted provider
attempts, and optional operational request budgets.
**The authenticated user is the tenant boundary.** Milestone 5 adds durable Batch/Job
queues, a private Cloud Run worker, progress/history, cancellation and daily/weekly
Project schedules. Milestone 6A adds device-scoped Plans, manual subscriptions,
logical usage limits and platform Admin billing.

## Architecture

```text
Browser → Next.js UI → HTTP → FastAPI → async SQLAlchemy → PostgreSQL
                                └──────────────────────→ Redis
```

Frontend and backend are independently executable. See
[architecture](docs/architecture/overview.md), [API](docs/api/health.md), and the
[milestone specification](docs/milestone-1-spec.md).

## Asynchronous ranking (M5)

Check Rankings and Check now return a queued batch immediately. The UI polls progress
and refreshes rankings on completion. Docker Compose starts a local PostgreSQL-backed
worker automatically; no GCP or Redis queue is needed. Use `SERP_PROVIDER=fake` for
zero-credit development and keep the enabled/fixed provider settings consistent.

- [Architecture and recovery](docs/architecture/async-ranking.md)
- [Batch and schedule APIs](docs/api/rank-check-batches.md)
- [Cloud Tasks / Cloud Run IAM and configuration](docs/architecture/cloud-tasks-deployment.md)
- [Cloud SQL initialization and migration job](docs/architecture/cloud-sql-deployment.md)
- [Deploy API and worker on Cloud Run, step by step](docs/architecture/cloud-run-deployment.md)
- [Deploy frontend and validate the website](docs/architecture/cloud-run-frontend-deployment.md)
- [GitHub / Developer Connect CI/CD for Cloud Run](docs/architecture/cloud-run-ci-cd.md)
- [M5 verification report](docs/verification-milestone-5.md)

```sh
make async-ranking-smoke
make cloud-tasks-contract-smoke
make recover-rank-jobs
```

Local worker command: `python -m scripts.rank_jobs --loop`. Private cloud worker:
`uvicorn app.worker_main:app --host 0.0.0.0 --port 8080`. Scheduled dispatch uses one
Cloud Scheduler job every five minutes, through the same private worker service.
Old synchronous rank-check POST routes are retired; GET ranking history is preserved.

## Billing and manual subscriptions (M6A)

Customers can open `/settings/billing` to view independent Desktop and Mobile Plans,
resource limits, monthly checks, reservations and reset dates. `/pricing` lists the
six seeded Plans. Paid activation requires external bank-transfer confirmation by
an administrator; there is no checkout or payment-provider integration.

An operator can grant platform Admin access to an existing account:

```sh
docker compose exec -T backend python -m scripts.platform_admin admin@example.com
# Revoke access:
docker compose exec -T backend python -m scripts.platform_admin admin@example.com --revoke
```

Log in again after granting access to refresh navigation. Open `/admin/customers`,
search for the customer, and select a device Plan, period, reference and internal note.
For an immediate change, select **Replace current Plan immediately**. For a future
change, set the start at or after the current subscription end. Extending a subscription
preserves the current monthly usage; an immediate replacement starts fresh quota.
Admin notes and payment references are hidden from customer billing responses.

All accounts have Desktop Free and Mobile Free fallback. Migration preserves existing
resources/history and disables schedules incompatible with Free, with audit events.
Over-limit resources remain readable; expansion requires reducing usage or changing Plan.
Monthly usage is subscription-anchored for paid Plans, calendar-month for Free.
Quota is reserved before enqueue; worker execution commits once and unused cancelled
or permanently failed work releases its reservation. Provider retries use the same
logical check. Temporary enqueue failures retain reservations for bounded recovery.

```sh
make billing-smoke
```

Normal verification uses `SERP_ENABLED_PROVIDERS=fake`, `SERP_PROVIDER=fake`,
`SERP_FIXED_PROVIDER=fake`, `SERP_PROVIDER_STRATEGY=fixed`,
`SERP_PROVIDER_PRIORITY=fake`, `TASK_QUEUE_PROVIDER=local`, and `DEBUG=false`.
See [M6A verification](docs/verification-milestone-6a.md) for architecture, commands,
security coverage and limitations.

## Requirements

- Git
- Docker Engine/Desktop with Docker Compose v2.24+ (`docker compose`)
- About 6 GB of available Docker memory for builds
- Make for the optional command shortcuts

The standard workflow requires no local Python or Node installation.

## Setup

```bash
git clone <repository>
cd serp-saas
cp .env.example .env
docker compose up --build
```

For background operation use `make up` or `docker compose up --build -d --wait`.
PostgreSQL initializes its database automatically. The backend waits for healthy
PostgreSQL and Redis, applies Alembic migrations, and starts. The frontend waits
for a healthy backend. No manual database setup is needed.

| Service | Local URL / address | Purpose |
| --- | --- | --- |
| frontend | http://localhost:3000 | Home dashboard |
| frontend | http://localhost:3000/health | Service health dashboard |
| frontend | http://localhost:3000/signup | Create an account |
| frontend | http://localhost:3000/login | Log in |
| frontend | http://localhost:3000/app | Protected account page |
| frontend | http://localhost:3000/app/projects | Project list |
| frontend | http://localhost:3000/app/projects/new | Create a Project |
| frontend | http://localhost:3000/app/projects/:id | Project settings and Keywords |
| frontend | http://localhost:3000/app/tracked-sites | Tracked Site list |
| frontend | http://localhost:3000/app/tracked-sites/new | Add a Tracked Site |
| frontend | http://localhost:3000/app/tracked-sites/:id | Domain alias management |
| backend | http://localhost:8000 | Redirect to API docs |
| backend | http://localhost:8000/docs | Swagger UI |
| backend | http://localhost:8000/openapi.json | OpenAPI schema |
| postgres | localhost:5432 | PostgreSQL database |
| redis | localhost:6379 | Cache/messaging foundation |

All published ports bind to loopback for local development. PostgreSQL and Redis
must not be exposed publicly in production. PostgreSQL persists in the
`postgres_data` named volume. `make down` preserves that data. Redis contains no
durable application state in this milestone.

## Configuration

Copy `.env.example` to `.env`; `.env` is ignored and excluded from Docker images.
The example PostgreSQL credentials are public local-development placeholders,
not production credentials. Supply real secrets through deployment configuration.

| Variable | Meaning |
| --- | --- |
| `APP_ENV` | `development`, `test`, or `production` |
| `APP_NAME`, `APP_VERSION` | API title and version |
| `DEBUG` | Boolean; must be false in production |
| `BACKEND_HOST`, `BACKEND_PORT` | Uvicorn bind address and container port |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database initialization configuration |
| `DATABASE_URL` | Required `postgresql+asyncpg://` connection URL |
| `REDIS_URL` | Required `redis://` or `rediss://` connection URL |
| `CORS_ORIGINS` | JSON array of explicit origins, e.g. `["http://localhost:3000"]` |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-reachable API URL, not Docker's `backend` hostname |
| `NEXT_PUBLIC_APP_ENV` | Public environment label; keep aligned with `APP_ENV` |
| `NEXT_PUBLIC_SITE_URL` | Public website origin used for canonical, sitemap and robots URLs |
| `JWT_SECRET_KEY` | Required signing secret, at least 32 bytes; replace the local placeholder for production |
| `JWT_ALGORITHM` | `HS256` only |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access JWT lifetime, default 15 (1–60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-session lifetime, default 30 (1–90) |
| `AUTH_COOKIE_NAME` | Default `serp_refresh_token` |
| `AUTH_COOKIE_SECURE` | False for local HTTP; must be true in production |
| `AUTH_COOKIE_SAMESITE` | `lax` by default; `strict` or `none` supported (`none` requires Secure) |
| `SERP_ENABLED_PROVIDERS` | Backend provider allow-list, e.g. `serper,serpapi` |
| `SERP_PROVIDER_STRATEGY` | `priority` or backend-only `fixed` routing |
| `SERP_PROVIDER_PRIORITY` | Ordered priority list; default `serper,serpapi` |
| `SERP_FIXED_PROVIDER` | Provider used by `fixed` strategy |
| `SERP_MAX_PROVIDER_FALLBACKS` | Maximum fallback providers per check; default 1 |
| `SERPER_API_KEY`, `SERPAPI_API_KEY` | Backend-only provider credentials; never use `NEXT_PUBLIC_*` |
| `SERPER_BASE_URL`, `SERPAPI_BASE_URL` | Provider search endpoints |
| `SERPER_REQUEST_BUDGET`, `SERPAPI_REQUEST_BUDGET` | Optional monthly application request ceilings; blank means unlimited |
| `SERP_REQUEST_TIMEOUT_SECONDS` | Timeout for each provider request |
| `SERP_DEFAULT_RESULT_LIMIT` | Persisted organic result depth, default 10 (1–100) |
| `SERP_MAX_CONCURRENT_REQUESTS` | Bounded concurrency for a manual Project check |
| `SERP_MANUAL_PROJECT_KEYWORD_LIMIT` | Maximum Keywords in one manual Project check, default 25 |

Backend settings load `../.env`, then `.env`, with exported environment variables
taking precedence. All application configuration goes through typed settings.
Missing required values fail with a clear validation error. Wildcard origins are
rejected; an empty origins list disables cross-origin browser access.

Next.js public variables are embedded at build time. Rebuild the frontend after
changing them. They must contain no secrets. The dashboard's environment is the
deployment label, independent of Next.js's production build mode.

The Compose file is for local development. For production set `APP_ENV=production`,
`DEBUG=false`, `NEXT_PUBLIC_APP_ENV=production`, explicit HTTPS origins and API URL,
and deployment-provided credentials. Use the backend Dockerfile's `production`
target (without development tools); its command runs only the API. Apply migrations
as a release step. The default frontend image is already a non-root standalone
production build. TLS, hosting, and production orchestration are outside Milestone 1.

When upgrading an existing Milestone 1 checkout, copy the new authentication keys
from `.env.example` into your existing `.env`, preserving your other settings.
Do not overwrite an existing deployment's signing secret. For a new production
secret, use a cryptographic generator, for example
`python -c 'import secrets; print(secrets.token_urlsafe(48))'` in a trusted terminal.
Production rejects the example placeholder, weak configuration, insecure refresh
cookies, and DEBUG=true. Never put authentication secrets in `NEXT_PUBLIC_*`.

## Authentication

See [email verification](docs/architecture/email-verification.md) for signup, resend,
expiry, SMTP/TLS settings and production requirements. Existing unverified accounts
can log in to request an email; their resources and history are preserved.

Visit `/signup`, enter an email and a 10–128 character password, confirm the
password, and accept the Terms checkbox. Registration starts a limited session
and opens `/verify-email`. Open the verification email, then confirm the address
to access `/app`. Local mail is captured at `http://localhost:8025` (Mailpit).
`/login` signs in existing active accounts. Email is trimmed and lowercased
without removing plus aliases or dots. The Terms checkbox links to `/terms`.

Use **Forgot password?** on `/login` to request a password reset email. The link
opens `/reset-password` and expires after 30 minutes by default. Only the latest
link works, and each link can be used once. Requests return the same confirmation
for unknown, disabled and rate-limited accounts. Defaults allow one email per
minute and five per hour, configured with `AUTH_PASSWORD_RESET_EXPIRE_MINUTES`,
`AUTH_PASSWORD_RESET_RESEND_SECONDS`, and `AUTH_PASSWORD_RESET_MAX_EMAILS_PER_HOUR`.
Resetting a password signs out all previous sessions and requires a new login;
it does not bypass email verification.

Signed-in users can select **Settings → Change password** at `/app/settings`,
enter their current password, and confirm a new 10–128 character password.
The current session is renewed; all other sessions and pending reset links are
revoked. Apply migration `0014_password_management` before running the updated
backend. Both email flows use the existing auth SMTP configuration; local messages
are available in Mailpit at `http://localhost:8025`.

Passwords use Argon2id. A 15-minute signed access JWT lives only in frontend memory.
A cryptographically random refresh token lives only in an HttpOnly cookie, with
its SHA-256 hash stored in PostgreSQL. The frontend sends credentialed requests,
restores the session after reload, and shares one refresh operation across
concurrent expired requests. Each protected request retries at most once.
Neither token is persisted in localStorage or sessionStorage.

Refresh rotates the token atomically. Logout revokes the current refresh session,
expires its cookie, and clears frontend memory and user query data. Existing
access JWTs can remain valid until expiry; there is no token deny list in this
milestone. Disabled accounts are rejected on every protected request and refresh.
Authentication does not call Redis.

The local cookie is HttpOnly, SameSite=Lax, scoped to `/api/v1/auth`, and works
across localhost ports 3000/8000. Production requires HTTPS and Secure cookies.
Prefer a same-site frontend/API deployment; cross-site deployments require
`AUTH_COOKIE_SAMESITE=none` plus Secure and explicit trusted CORS origins.
All auth POST requests require `Content-Type: application/json` (send `{}` for
refresh/logout). Origin checks and the non-simple JSON request requirement guard
cookie mutations against cross-site forms. Allowed origins are explicit, with
credentialed CORS; Swagger's own API origin is also allowed.

Protected API example using an access token returned by registration/login:

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access-token>"
```

See [authentication API](docs/api/authentication.md) for endpoint/error details and
[authentication architecture](docs/architecture/authentication.md) for flows and
the mandatory authenticated-owner repository convention.

## Projects and Keywords

Open `/app/projects` after signing in. Each Project is one complete Google SERP
environment: country, language, desktop/mobile device, and optional location. Add
Project accepts one to 1000 keyword lines and creates the Project and cleaned,
deduplicated Keywords in one transaction. Project settings apply to every Keyword
for future checks.

Each Keyword stores query text and active state only. Keyword lists support
database-backed search, state filtering, and cursor pagination. Separate single
and bulk add, edit, pause/resume, and delete operations remain available.

Bulk add accepts up to 1000 textarea lines per request. It removes empty lines,
normalizes and deduplicates repeated phrases, inserts new rows in one PostgreSQL
operation, skips existing/concurrent duplicates, and reports exact counts. It does
not implement CSV import or subscription quotas.

The API uses `/api/v1/projects` and project-scoped
`/api/v1/projects/{project_id}/keywords` routes. It never accepts ownership from a
request body. Foreign and nonexistent resources return the same 404 behavior.
See [Projects API](docs/api/projects.md), [Keywords API](docs/api/keywords.md), and
[Project/Keyword architecture](docs/architecture/project-keyword-model.md).

## Tracked Sites and domain aliases

Tracked Sites belong globally to the authenticated user and represent logical SEO
assets independently of Projects. Each active Site has exactly one active primary
domain and can retain multiple active or inactive old/current aliases. For a 301
change, add the new hostname and promote it to primary; the old hostname remains an
alias. The application does not resolve redirects or map Projects to Tracked Sites.
See [Tracked Sites API](docs/api/tracked-sites.md) and
[Tracked Site architecture](docs/architecture/tracked-sites.md).

## Manual ranking checks

On an active Project, **Check Rankings** checks all active Keywords up to the
configured cap; each active Keyword also has **Check now**. The page shows every
matched Tracked Site at its best organic position, as well as Never Checked, Not
Found in Top N, running, and failed states. History and check detail preserve the
query, Project environment, matched Site name/domain, exact result URL, and the
normalized Top N even after current records change.

Provider selection is automatic and cannot be supplied by a user or Project. With
the example priority configuration, configured desktop checks try Serper first;
mobile checks skip Serper because its verified Search contract has no device
parameter and use another capable provider. Safe timeout, availability, rate-limit,
or quota failures may use one fallback. Authentication, invalid request, unsupported
configuration, and parsing failures do not spend fallback credits.

Put `SERPER_API_KEY` and/or `SERPAPI_API_KEY` in `.env`. Optional request budgets are
internal safety ceilings, not authoritative plan balances or billing limits.
`SERP_PROVIDER` remains supported only as a compatibility setting for existing M4
deployments that have not added the new routing variables.

Automated checks, browser verification, `make ranking-smoke`, and
`make provider-routing-smoke` use fake or mocked providers and consume zero Serper
and SerpApi credits. Explicit real smokes each make at most one request:

```bash
RUN_REAL_SERPER_SMOKE=true make serper-smoke
RUN_REAL_SERP_SMOKE=true make serpapi-smoke
```

See [Rank Check API](docs/api/rank-checks.md), [Rankings API](docs/api/rankings.md),
[provider architecture](docs/architecture/serp-provider.md),
[routing architecture](docs/architecture/provider-routing.md), and
[ranking architecture](docs/architecture/ranking-engine.md).

## Database migrations

```bash
make db-upgrade
```

Equivalent commands:

```bash
docker compose run --rm backend alembic upgrade head
```

When running the backend locally, run `alembic upgrade head` from `backend/` with
its virtual environment activated.
Alembic reads database-only settings and requires only `DATABASE_URL`. The API and
worker continue to require their complete runtime configuration. Cloud Run socket
URLs are supported; see the Cloud SQL initialization runbook above.
The initial revision is intentionally empty and tracks only migration history.
Revision `0002_authentication` creates `users` and `refresh_tokens`. Downgrading
that revision removes those tables and their account/session data. Revision
`0003_projects_keywords` creates user-owned Projects, project-owned Keywords,
constraints, and required indexes. Revision `0004_project_refactor_sites` moves old
Project domains into user-global Tracked Sites, deduplicates same-user domains, and
deterministically splits Projects to preserve per-Keyword SERP settings before
removing old columns. Revision 0004 is intentionally forward-only because later
alias edits cannot be mapped safely back to the old data model. Back up deployment
data before upgrading. Revision `0005_rank_tracking` adds snapshot-bearing Rank
Checks, normalized organic results, matched rankings, concurrency protection, and
history-safe foreign keys. Its downgrade removes only Milestone 4 history and
restores the exact 0004 schema.
Application startup never calls `create_all`. Future model imports belong in
`app/db/models.py` before using `alembic revision --autogenerate -m "description"`.

## Build, tests, and quality

```bash
make build
make up
make backend-test
make frontend-test
make lint
make typecheck
make connectivity
make auth-smoke
make business-smoke
make tracked-site-smoke
make ranking-smoke
make provider-routing-smoke
```

`make check` runs the tests, lint/format checks, type checks, and HTTP connectivity
checks against a running stack. `make format` applies Ruff's Black-compatible
formatter and Prettier to the source files. `make logs` follows service logs.

Backend tests include environment validation, real PostgreSQL/Redis health,
authentication, owner-scoped Project/Keyword and Tracked Site/Domain CRUD,
normalization, duplicate races, filtering, pagination, constraints, sanitized
logging, and realistic semantic migration fixtures. Rank tests cover the mocked
SerpApi and Serper mocked adapters, provider eligibility/routing/fallback/budget
accounting, fake pipeline, matcher, snapshots, atomic persistence, history
retention, concurrency, pagination, and tenant isolation without real provider
calls. Frontend tests cover health, authentication, Projects, Keywords, aliases,
ranking states, provider-attempt metadata, history, and organic-result detail.

Docker-based frontend quality commands use `docker-compose.checks.yml` to build
a separate tooling image; the running production frontend remains available.
No local language toolchains are required. After source edits rebuild the services
with `make up`; the default Compose workflow does not bind-mount source for reload.
Production builds use Next.js's supported Webpack builder for portability across
restricted development environments; the development server uses Turbopack.

## Optional native development

Use Python 3.12–3.14, uv, and Node 22.22+ when developing outside Docker:

```bash
docker compose up -d --wait postgres redis
cd backend
uv sync --frozen
# Override the Docker service names with host addresses. Keep your configured credentials.
export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/serp_saas'
export REDIS_URL='redis://localhost:6379/0'
uv run alembic upgrade head
uv run python -m app
```

In another terminal:

```bash
cd frontend
cp ../.env .env.local
npm ci
npm run dev
```

Native checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
and `uv run mypy` from `backend/`; `npm test`, `npm run lint`,
`npm run format:check`, `npm run typecheck`, and `npm run build` from `frontend/`.
For backend unit tests without dependency connectivity use
`uv run pytest -m 'not integration'` after configuring the required settings.

## Public Blog (Milestone 7G)

`/blog` and three static guides use repository-controlled Markdown, validated
frontmatter, public navigation, canonical metadata, Article/Breadcrumb JSON-LD,
`/sitemap.xml`, and `/feed.xml`. Drafts are excluded and return 404.
See [Blog authoring](docs/blog-authoring.md) and
[Milestone 7G verification](docs/verification-milestone-7g.md).

## SEO landing pages (Milestone 7H)

`/google-serp-rank-tracker`, `/daily-serp-tracker`, and
`/serp-tracking-for-agencies` are static commercial pages with distinct product,
recurring-monitoring, and agency workflows. They share PublicShell, include
canonical/OG/Twitter metadata and WebPage/SoftwareApplication/Breadcrumb JSON-LD,
and are connected through the homepage, footer, relevant Blog guides and the
existing sitemap. Copy preserves Top 10 measurement, Plan-dependent scheduling
and user-based ownership. See [M7H verification](docs/verification-milestone-7h.md)
for local checks and deployment status.

## Dependency versions

`backend/uv.lock` and `frontend/package-lock.json` lock all resolved dependencies.
Docker bases and runtime dependencies are pinned by release version. Main versions:

| Component | Version |
| --- | --- |
| Python container | 3.12.12 |
| Node container | 22.22.0 |
| Next.js / React | 16.3.8 / 19.3.0 |
| TypeScript / Tailwind CSS | 5.9.3 / 4.3.3 |
| TanStack Query | 5.102.8 |
| FastAPI / Uvicorn | 0.141.1 / 0.52.4 |
| SQLAlchemy / asyncpg | 2.0.52 / 0.31.0 |
| Pydantic / pydantic-settings | 2.13.5 / 2.15.0 |
| Alembic / redis-py | 1.19.2 / 7.4.1 |
| PostgreSQL / Redis containers | 16.13 / 7.4.8 |
| Pytest / Vitest | 9.1.1 / 4.1.11 |
| Ruff / mypy / ESLint | 0.16.6 / 1.20.2 / 9.39.4 |

See [verification](docs/verification.md) for executed checks and the complete
source file inventory.

Milestone 2 adds Argon2id (`argon2-cffi` 25.1.0), PyJWT 2.13.0, and
email-validator 2.3.0, all locked in `uv.lock`. No frontend dependencies were added.
See [Milestone 2 verification](docs/verification-milestone-2.md) for its exact results
and created/modified file inventory.

Milestones 3 and 3.1 add no runtime dependency. See
[Milestone 3 verification](docs/verification-milestone-3.md) for its exact results
and created/modified file inventory.

`make auth-smoke` exercises actual registration, current-user access, refresh
rotation/replay rejection, logout, and login through the running HTTP server.
It creates a disposable `smoke-*` development account and never prints credentials.
Authentication tests use isolated PostgreSQL schemas and do not modify local
accounts. Tests also verify metadata/migration agreement and concurrent operations.

`make business-smoke` uses two real accounts against the running stack and verifies
atomic Project/Keyword creation, query-only Keywords, Project settings, cross-user
404 isolation, and deletion. `make tracked-site-smoke` verifies aliases, primary
promotion, duplicate protection, cross-user domain reuse, and tenant isolation.
Both create disposable smoke accounts and print no credentials.

For optional browser verification, install Playwright outside the repository and run:

```bash
export PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs
export CHROME_EXECUTABLE=/absolute/path/to/chrome
node scripts/verify-auth-browser.mjs
node scripts/verify-projects-browser.mjs
node scripts/verify-rankings-browser.mjs
```

The authentication browser script verifies signup → `/app` → reload → logout →
anonymous redirect, login, cookie/storage behavior, and both Milestone 1 health
pages. The Milestone 3.1 script verifies Tracked Site creation and primary
promotion plus atomic Project creation, setting changes, query-only Keywords,
pause, and reload. Each creates a disposable
`browser-*` account. `FRONTEND_URL` defaults to `http://localhost:3000`. Browser
tooling is optional for normal Docker development and is not installed in
production images.

Deferred: email verification workflow, forgot/reset password, CAPTCHA, OAuth,
MFA, scheduling/frequency, queues, workers, billing, subscriptions/usage limits,
provider result merging, redirect resolution, charts, competitors, keyword
groups/tags, CSV import/export, notifications, reports, search volume, API keys,
teams, organizations, roles, and permissions. No workspace or membership model is
introduced.
Future rate limiting should target `/register`, `/login`, and `/refresh`.
