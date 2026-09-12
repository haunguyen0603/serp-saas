# Milestone 1 verification

Verification date: 2026-09-10. The original workspace contained only
`docs/milestone-1-spec.md`; that specification was left unchanged. All other source
files in the inventory below were created for Milestone 1. Generated dependencies,
caches, build outputs, and the ignored local `.env` are excluded from the inventory.

## Implementation

- Independently executable Next.js App Router frontend and FastAPI backend.
- Central typed configuration, explicit CORS, JSON request logging, sanitized
  errors, and lifespan-owned async database and Redis resources.
- Health dashboards on `/` and `/health`, backed by a typed HTTP client and
  TanStack Query, with independent API/database/Redis connectivity states.
- PostgreSQL and Redis Compose services with health-gated startup, pinned
  dependencies, non-root application containers, and separate production/tooling
  Docker targets.
- Alembic baseline with no business tables, versioned API router, and reserved
  model/service/provider package locations.
- Tests, Makefile workflows, architecture/API documentation, and setup instructions.

## Executed commands

Standard repository verification commands:

```bash
cp .env.example .env
docker compose build
docker compose up --build -d --wait
make check
make db-upgrade db-downgrade
make db-upgrade
make format
docker compose ps
docker build --target production -f infrastructure/docker/backend.Dockerfile \
  -t serp-saas-backend-production:local .
```

`make check` expands to:

```bash
docker compose run --rm backend pytest
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm test
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend ruff format --check .
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm run lint
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --rm --no-deps frontend npm run format:check
docker compose run --rm --no-deps backend mypy
docker compose -f docker-compose.yml -f docker-compose.checks.yml run --build --rm --no-deps frontend npm run typecheck
make connectivity
```

Additional native checks executed during implementation:

```bash
# backend/
uv sync --python 3.12
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -m 'not integration'
.venv/bin/pytest --tb=short

# frontend/
npm install
npm audit --json
npm run format
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Native integration tests used the configured local-development URLs with
`localhost` in place of Compose service names. Public Next.js variables were
supplied for the native build. Temporary caches were used for dependency installs.

This host initially had no Docker and had older Node plus prerelease Python.
Verification used Docker CLI 28.3.3, Compose 2.39.2, Docker Engine 29.5.2 in Colima
0.10.3 on an ARM64 Linux VM, isolated Node 22.22.0, and Python 3.12.14. Container
tests use Python 3.12.12 and Node 22.22.0. Docker commands on this host were prefixed
with `PATH=/tmp/serp-tools/bin:$PATH DOCKER_CONFIG=/tmp/serp-tools/docker DEBUG=true`.
The explicit DEBUG value avoids an unrelated inherited shell variable. These
temporary tools are not repository dependencies or part of the standard setup.

## Results

| Check | Result |
| --- | --- |
| Native backend tests | 20 passed, including real database/Redis, migration cycle, and transactions |
| Native frontend tests | 12 passed across 3 test files |
| Native frontend production build | Passed; `/` and `/health` prerendered |
| Docker Compose application builds | Passed for both application images |
| Docker Compose startup | All four services healthy |
| Browser → API → dependencies | Passed on both pages in real headless Chrome; all three health responses observed; no browser exceptions |
| Migration CLI round trip | Upgrade → downgrade one revision → upgrade passed |
| npm dependency audit | Zero vulnerabilities after upgrading Vitest |
| Container backend tests | 20 passed |
| Container frontend tests | 12 passed across 3 test files |
| Ruff lint and formatting | Passed; 33 Python files formatted |
| ESLint and Prettier | Passed |
| mypy | Passed; 25 application source files checked in strict mode |
| TypeScript | Passed in strict mode |
| Container HTTP connectivity | Passed for health, dependency health, docs, OpenAPI, both frontend pages, and frontend-container → backend requests |
| Backend production Docker target | Built successfully with runtime dependencies only |
| `make format` | Passed with no source changes |
| Final Compose status | All four services healthy after rebuilding final sources |

The real-browser smoke check used an isolated Playwright script and the installed
Chrome executable, visiting `/` and `/health`, asserting all three connected
statuses, observing successful network responses for each health endpoint,
checking refresh interaction, and asserting no page exceptions. A screenshot was
visually inspected. No browser tooling was added to production dependencies.

Issues found and fixed during implementation: an existing npm cache permission
failure (isolated cache), the old npm resolver's internal error (isolated current
toolchain), a Vitest dependency advisory (patched version), Vitest's updated JSX
configuration, Redis/SQLAlchemy type mismatches, and the native Turbopack worker
port restriction (supported Webpack production builds). The Docker VM's initial
mount configuration was corrected before container verification.

## Definition of Done

- [x] Required monorepo structure exists.
- [x] Frontend and backend images build.
- [x] Docker Compose starts all four healthy services.
- [x] PostgreSQL and Redis run and are reachable from FastAPI.
- [x] FastAPI starts; all three health endpoints, docs, and OpenAPI work.
- [x] Configuration is environment-driven and validated.
- [x] Async SQLAlchemy sessions commit, roll back, and close correctly.
- [x] Alembic upgrades, downgrades one revision, and upgrades again.
- [x] Next.js starts and both pages render.
- [x] Real browser requests reach the backend and display dependency statuses.
- [x] Backend and frontend tests pass.
- [x] Lint, formatting, and strict type checking pass.
- [x] No application secrets are hard-coded; local example credentials are
  configuration-only and documented as placeholders.
- [x] README, environment example, architecture, and API documentation are complete.
- [x] The documented copy-environment/build/start workflow works with Docker alone.

All Milestone 1 Definition of Done items were verified. No later-milestone
business functionality was implemented.

## Assumptions and limitations

- The empty initial migration establishes Alembic history without business tables.
- Health endpoints remain unversioned; future business APIs use `/api/v1`.
- Redis is an ephemeral connectivity foundation; no queue or persistence contract
  is introduced.
- Public frontend settings are build-time values and require a rebuild to change.
- Production hosting/TLS, business features, and tenant ownership enforcement are
  outside this milestone. The Compose configuration is for local development.
- Verification covers ARM64 Linux containers on this host; other architectures
  were not separately executed.
- Install a persistent Docker runtime for ongoing development: verification tools
  under `/tmp` are temporary. The running Compose environment uses a dedicated
  local Colima VM.
- The supplied directory had no `.git` repository or remote. No commits or remote
  publication were performed.

## Complete source inventory

The tree below also serves as the complete created-file list, except for the
pre-existing unchanged milestone specification.

```text
serp-saas/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 0001_foundation.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   └── router.py
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   ├── logging.py
│   │   │   ├── middleware.py
│   │   │   └── redis.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── health.py
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── serp/
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_config.py
│   │   ├── test_health.py
│   │   ├── test_logging.py
│   │   ├── test_migrations.py
│   │   └── test_session.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
├── docs/
│   ├── api/
│   │   └── health.md
│   ├── architecture/
│   │   └── overview.md
│   ├── milestone-1-spec.md
│   └── verification.md
├── frontend/
│   ├── public/
│   │   └── .gitkeep
│   ├── src/
│   │   ├── app/
│   │   │   ├── health/
│   │   │   │   └── page.tsx
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── health-dashboard.test.tsx
│   │   │   ├── health-dashboard.tsx
│   │   │   └── providers.tsx
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── client.test.ts
│   │   │   │   └── client.ts
│   │   │   ├── config.test.ts
│   │   │   └── config.ts
│   │   ├── types/
│   │   │   └── health.ts
│   │   └── test-setup.ts
│   ├── .prettierignore
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   └── vitest.config.ts
├── infrastructure/
│   └── docker/
│       ├── backend.Dockerfile
│       └── frontend.Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── docker-compose.checks.yml
└── docker-compose.yml
```
