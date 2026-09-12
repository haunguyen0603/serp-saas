# SERP SaaS — Milestone 1

## Project Foundation & Development Infrastructure

## 1. Objective

Build the initial production-oriented monorepo foundation for a multi-tenant SaaS SERP rank tracking platform.

The application will use:

* Frontend: Next.js + TypeScript
* Backend API: Python + FastAPI
* Database: PostgreSQL
* Cache / messaging foundation: Redis
* Containerization: Docker
* Local orchestration: Docker Compose
* API documentation: OpenAPI via FastAPI
* Testing: Pytest + frontend test framework
* Code quality: Ruff + Black-compatible formatting + ESLint + TypeScript strict mode

Milestone 1 must establish a clean, reproducible development environment and a minimal end-to-end application connection:

Browser → Next.js → FastAPI → PostgreSQL

Redis must also be running and reachable from the backend, although no business job queue is required in this milestone.

---

# 2. Important Scope Boundary

Milestone 1 is infrastructure only.

DO NOT implement:

* User registration
* Login
* OAuth
* Organizations
* Multi-tenancy logic
* Projects
* Keywords
* SERP providers
* Rank tracking
* Background workers
* Celery
* Billing
* Subscription
* Notifications
* Competitor tracking
* SEO analytics
* Production payment integration

Those belong to later milestones.

The architecture must, however, be designed so these features can be added without restructuring the project.

---

# 3. Repository Structure

Create the repository as a monorepo:

```text
serp-saas/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── ...
│
├── infrastructure/
│   ├── docker/
│   └── ...
│
├── docs/
│   ├── architecture/
│   └── api/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

Keep frontend and backend independently executable.

---

# 4. Technology Requirements

## 4.1 Frontend

Use:

* Next.js
* TypeScript
* App Router
* Strict TypeScript
* ESLint
* Tailwind CSS
* TanStack Query

Do not introduce unnecessary frontend libraries.

The frontend should communicate with the backend through HTTP APIs only.

Do not connect the frontend directly to PostgreSQL.

---

# 5. Backend

Use:

* Python 3.12+
* FastAPI
* Uvicorn
* SQLAlchemy 2.x
* Pydantic 2.x
* pydantic-settings
* PostgreSQL driver
* Alembic
* Pytest
* HTTPX for API tests
* Ruff

Use async FastAPI endpoints where appropriate.

Use SQLAlchemy 2.x style APIs.

Do not use deprecated SQLAlchemy 1.x patterns.

---

# 6. Database

Use PostgreSQL.

For local development:

```text
Database: PostgreSQL 16+
```

Create a database connection layer with clear separation between:

```text
database configuration
database engine
session management
models
migrations
```

The application must NOT create database tables automatically on startup.

Schema creation must be managed through Alembic migrations.

---

# 7. Redis

Provide Redis in Docker Compose.

The backend must have:

* Redis URL configuration
* Redis connection utility
* Health check connectivity

No Celery or worker processing is required in Milestone 1.

Create the abstraction in a way that future queue implementation can reuse the Redis connection.

---

# 8. Environment Configuration

Create:

```text
.env.example
```

Example variables:

```text
APP_ENV=development
APP_NAME=serp-saas
APP_VERSION=0.1.0
DEBUG=true

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/serp_saas

REDIS_URL=redis://redis:6379/0

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Never hard-code secrets in source code.

Do not commit `.env`.

The application must fail with a clear configuration error when required environment variables are missing.

---

# 9. Backend Configuration

Create a central settings module, for example:

```python
app/core/config.py
```

Use `pydantic-settings`.

Expose strongly typed settings.

Example:

```python
class Settings(BaseSettings):
    app_name: str
    app_version: str
    app_env: str
    debug: bool

    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
```

Do not access environment variables directly throughout the application.

All configuration must go through the settings object.

---

# 10. FastAPI Application

Create:

```text
backend/app/main.py
```

The FastAPI application must provide:

```text
GET /health
GET /health/db
GET /health/redis
```

Expected response:

```json
{
  "status": "ok"
}
```

For individual checks, return enough information to determine whether the dependency is reachable.

Do not expose credentials or internal connection strings.

---

# 11. API Versioning

All business APIs must use:

```text
/api/v1/...
```

Even though Milestone 1 has no business endpoints yet, establish the routing structure now.

Example:

```text
app/api/
├── router.py
└── v1/
    └── router.py
```

Future APIs should be mounted under:

```text
/api/v1
```

Health endpoints may remain at:

```text
/health
```

---

# 12. CORS

Configure CORS through environment variables.

For local development allow:

```text
http://localhost:3000
```

Do not use:

```text
allow_origins=["*"]
```

as the default production configuration.

Create an explicit configurable list of allowed origins.

---

# 13. Database Session Management

Create an async SQLAlchemy setup.

Expected architecture:

```text
app/db/
├── base.py
├── session.py
└── models.py
```

The exact file organization may be improved if there is a strong reason, but keep responsibilities separated.

Provide a dependency:

```python
async def get_db():
    ...
```

for FastAPI endpoints.

Correctly handle:

* session creation
* commit
* rollback
* close

Do not leak database sessions.

---

# 14. Initial Database Schema

Milestone 1 must NOT implement the full business schema.

However, create the migration framework and verify that Alembic can:

```text
upgrade head
downgrade one revision
upgrade head again
```

Create one minimal initial migration if needed to validate the system.

Do not prematurely create:

```text
users
organizations
projects
keywords
rankings
subscriptions
```

Those belong to later milestones.

---

# 15. Frontend

Create a clean Next.js application using App Router.

Initial pages:

```text
/
```

and:

```text
/health
```

The home page should show:

```text
SERP SaaS
Environment: development
API: connected / unavailable
Database: connected / unavailable
Redis: connected / unavailable
```

The frontend may call the backend health endpoints to display the status.

No authentication is required yet.

---

# 16. Frontend API Layer

Do not scatter raw `fetch()` calls throughout components.

Create a reusable API client such as:

```text
frontend/src/lib/api/
```

The API base URL must come from:

```text
NEXT_PUBLIC_API_BASE_URL
```

Provide at least:

```typescript
getHealth()
getDatabaseHealth()
getRedisHealth()
```

Keep the API client typed.

---

# 17. Docker

Create Dockerfiles for:

```text
frontend
backend
```

Docker images must:

* build successfully
* run without manual modification
* use non-root users where practical
* avoid unnecessary packages
* use appropriate production-friendly base images

Do not optimize prematurely for ultra-small images.

Correctness and maintainability are more important at this stage.

---

# 18. Docker Compose

Create:

```text
docker-compose.yml
```

Services:

```text
frontend
backend
postgres
redis
```

Expected ports:

```text
Next.js     3000
FastAPI     8000
PostgreSQL  5432
Redis       6379
```

PostgreSQL and Redis ports may be exposed for local development, but document that they should not be publicly exposed in production.

Use Docker health checks.

Backend must wait until PostgreSQL is actually healthy before starting application initialization.

---

# 19. Local Development

A new developer should be able to clone the repository and run:

```bash
docker compose up --build
```

Then access:

```text
http://localhost:3000
http://localhost:8000
http://localhost:8000/docs
```

The entire local environment must start without requiring manual database setup.

---

# 20. Alembic

Configure Alembic correctly for the async SQLAlchemy application.

Provide commands documented in README:

```bash
alembic upgrade head
alembic downgrade -1
```

Also provide a convenient command through Makefile if useful:

```bash
make db-upgrade
make db-downgrade
```

Do not put schema creation logic in application startup.

---

# 21. Logging

Create structured application logging.

At minimum:

```text
timestamp
level
logger
message
```

For HTTP requests, log:

```text
method
path
status_code
duration
```

Do not log:

* passwords
* API keys
* database credentials
* access tokens
* sensitive request payloads

---

# 22. Error Handling

Create a consistent API error format.

Example:

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred."
  }
}
```

Do not expose stack traces in production responses.

In development, detailed errors may be available through server logs.

---

# 23. Testing

Backend tests must include:

### Unit test

Configuration loading.

### Integration test

`GET /health`

### Integration test

`GET /health/db`

### Integration test

`GET /health/redis`

### Database migration test

Verify Alembic upgrade works.

### Frontend

At minimum test that the application renders successfully and the health dashboard can display backend status.

Tests must be deterministic.

---

# 24. Code Quality

Backend:

```text
Ruff
Pytest
Type hints
```

Frontend:

```text
ESLint
TypeScript strict mode
```

Do not leave:

```text
TODO
FIXME
temporary debug code
print(...)
console.log(...)
```

in production paths unless explicitly justified.

---

# 25. Makefile

Create useful commands such as:

```text
make up
make down
make build
make logs
make backend-test
make frontend-test
make lint
make format
make db-upgrade
make db-downgrade
```

Commands should work consistently on a normal developer machine with Docker installed.

---

# 26. README

Create a comprehensive README containing:

## Project overview

Explain that this is a multi-tenant SaaS SERP tracking platform.

## Architecture

Document:

```text
Next.js
   ↓
FastAPI
   ↓
PostgreSQL

FastAPI
   ↓
Redis
```

## Requirements

Document:

* Docker
* Docker Compose
* Git

Local Python/Node installations should not be required for the standard Docker workflow.

## Setup

Provide exact commands.

## Services

Document:

```text
frontend
backend
postgres
redis
```

## URLs

Document local URLs.

## Database migrations

Document migration commands.

## Testing

Document test commands.

## Environment variables

Document `.env.example`.

---

# 27. Git Hygiene

Create `.gitignore` covering:

```text
.env
.env.*
!.env.example

__pycache__
.pytest_cache
.mypy_cache
.ruff_cache

node_modules
.next

coverage
dist
build

*.log
.DS_Store
```

Do not commit:

* secrets
* credentials
* local databases
* node_modules
* generated build artifacts

---

# 28. Architecture Principles

The following principles are mandatory.

## Separation of concerns

Do not place:

* SQL queries directly in route handlers
* business logic directly in API routers
* configuration logic throughout the application
* external provider logic directly in the route handlers

Use clear layers.

Preferred backend flow:

```text
Router
  ↓
Service
  ↓
Repository / Database layer
  ↓
PostgreSQL
```

For Milestone 1 there may be little business logic, but establish the structure.

---

# 29. Future Multi-Tenant Compatibility

Do not implement tenant logic yet.

However, the architecture must anticipate:

```text
Organization
    ↓
Project
    ↓
Keyword
    ↓
Ranking
```

Every business entity introduced in later milestones should be designed around explicit ownership.

Do not assume a global single-user application.

Avoid global mutable state.

---

# 30. Future SERP Provider Compatibility

Milestone 1 must not implement an actual SERP provider.

But the backend architecture should leave a clear place for:

```text
app/services/serp/
```

Future design:

```text
SERPProvider
├── ProviderA
├── ProviderB
└── InternalProvider
```

Do not couple the rest of the application directly to a specific provider.

---

# 31. Security Baseline

Implement the following baseline now:

* secrets only through environment/configuration
* CORS configuration
* no credentials in logs
* no credentials in API responses
* non-root Docker users where practical
* production DEBUG must be false
* explicit allowed origins
* dependency version pinning or lockfiles
* clear separation between development and production configuration

Do not implement advanced authentication yet.

---

# 32. Definition of Done

Milestone 1 is complete only when ALL of the following are true:

### Infrastructure

* [ ] Repository structure exists
* [ ] Frontend builds
* [ ] Backend builds
* [ ] Docker Compose works
* [ ] PostgreSQL runs
* [ ] Redis runs

### Backend

* [ ] FastAPI starts
* [ ] `/health` works
* [ ] `/health/db` works
* [ ] `/health/redis` works
* [ ] OpenAPI docs work
* [ ] Configuration is environment-driven
* [ ] SQLAlchemy async session works
* [ ] Alembic works

### Frontend

* [ ] Next.js starts
* [ ] Home page renders
* [ ] Frontend successfully calls backend
* [ ] API status is displayed

### Quality

* [ ] Backend tests pass
* [ ] Frontend tests pass
* [ ] Lint passes
* [ ] Type checking passes
* [ ] No hard-coded secrets
* [ ] README is complete

### Reproducibility

A clean machine with Docker installed must be able to run:

```bash
git clone <repository>
cd serp-saas
cp .env.example .env
docker compose up --build
```

and obtain a functioning:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
Docs:     http://localhost:8000/docs
```

---

# 33. Expected Final Output From Codex

After implementation, provide:

1. Summary of architecture created.
2. Complete repository tree.
3. Technologies and versions used.
4. Commands to start the project.
5. Commands to run tests.
6. Commands to run migrations.
7. List of files created/modified.
8. Any assumptions made.
9. Any known limitations.
10. Confirmation that the Definition of Done was verified.

Do not claim tests pass unless they were actually executed.

---

# 34. Implementation Strategy

Implement incrementally.

Recommended order:

```text
1. Repository structure
2. Backend skeleton
3. Configuration
4. PostgreSQL integration
5. Alembic
6. Redis integration
7. Health endpoints
8. Frontend skeleton
9. Frontend API client
10. Dockerfiles
11. Docker Compose
12. Tests
13. Lint/type checks
14. README
15. Final verification
```

After each major stage, run the relevant checks.

Do not make unrelated architectural changes.

Do not add features outside Milestone 1 scope.

---

# 35. Final Instruction To Codex

You are implementing Milestone 1 of a production-oriented multi-tenant SaaS SERP rank tracking platform.

Prioritize:

* correctness
* maintainability
* clean architecture
* reproducibility
* testability
* future scalability

Do not over-engineer features that are explicitly out of scope.

When a design choice is not specified, choose the simplest production-sensible solution that preserves future extensibility.

Before declaring completion:

```text
docker compose build
docker compose up
run backend tests
run frontend tests
run lint
run type checking
run database migration
verify health endpoints
verify frontend → backend connectivity
```

Only report successful checks that were actually executed.