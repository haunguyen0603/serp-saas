# Admin Plan catalog

Implemented and verified on 2026-09-20.

## Using the editor

Sign in with a platform administrator account and open **Administration → Plans & Pricing** (`/admin/plans`). Each Desktop and Mobile Free/Starter/Pro Plan has its own form and Save action:

- Monthly price in USD, with up to two decimal places.
- Max projects, max keywords, and monthly logical keyword checks, as nonnegative whole numbers.
- Free prices remain $0; paid Plans require a positive price. Free resource limits are editable.

Saving updates the authoritative database catalog used by public Pricing and new subscription activations. Per the user's selected policy, **existing subscription snapshots remain unchanged**, including existing Free subscriptions and extensions of existing subscriptions. A newly created subscription (including a newly created Free fallback) takes the current catalog terms. Existing usage periods, reservations, schedules, and ranking data are not rewritten.

Catalog changes do not collect money or activate a subscription. Manual bank-transfer activation remains the existing separate Admin workflow. Currency, Plan identity, device scope, schedule entitlements, and active status are not editable here.

## Architecture and safeguards

- Shared AppShell navigation links to the new protected Next.js page. The editor uses existing Card, Input, Button, Skeleton, EmptyState, and ErrorState components and TanStack Query.
- `GET /api/v1/admin/plans`, `PATCH /api/v1/admin/plans/{code}`, and `GET /api/v1/admin/plans/history` all require the existing platform-admin dependency. The public catalog endpoint is unchanged.
- PATCH accepts only four editable fields plus `expected_updated_at`. Validation rejects fractional limits, booleans, negative values, unknown fields, and values beyond signed 32-bit storage bounds. Prices are stored as integer minor units.
- A row lock and version comparison prevent one administrator from silently overwriting another's changes. A stale save returns 409; the UI retains edits and offers an explicit catalog reload that discards drafts.
- Every effective change records the administrator UUID, timestamp, and before/after Plan terms in `plan_changes`, in the same transaction. The UI displays the latest 20 entries; older entries remain in the database. No-op saves create no audit entry.
- Migration `0009_plan_catalog_audit` adds only the audit table/index. No seed prices or existing subscription snapshots are updated by this migration.
- Public Pricing now preserves fractional prices (for example $29.50) instead of rounding them to whole dollars.

## Verification

Latest authoritative results:

| Check | Result |
| --- | --- |
| Backend full suite | 219 passed |
| Ruff lint / format | Passed; 163 files formatted correctly |
| mypy | Passed; 110 source files |
| Frontend full suite | 94 passed in 18 files |
| ESLint / Prettier / strict TypeScript | Passed |
| npm audit | 0 vulnerabilities |
| Production Next.js build | Passed, including `/admin/plans` |
| Local Docker services | backend, worker, frontend, PostgreSQL, Redis all healthy after deployment |
| Isolated database | Head `0009_plan_catalog_audit`; `alembic check`: no new upgrade operations |

Backend integration coverage includes anonymous/user denial, validation, device separation, authoritative public values, exact fractional prices, concurrent save conflict, audit creation, preserved existing snapshots/usage periods, preserved extension terms, and updated terms for new activations and new Free subscriptions. Existing migration invariants were updated to include the new audit table and head. An initial full run reported two outdated schema/head assertions; the final rerun above passed.

Chrome browser verification ran against a separate compose project (`serp-plan-qa`), fresh database `plans_qa`, fake provider configuration, API port 18000, and frontend port 13000. No live catalog prices were edited by verification. Executed checks:

- Admin login and sidebar navigation; all six editor forms.
- Desktop Starter: save $29.50 and limits 7/777/7777; Mobile Starter: save $39.75 and limits 8/888/8888; reload persistence.
- Public Pricing renders the exact saved prices; catalog API returns all six Plans.
- Expanded audit history displays before/after values.
- Two open Admin pages: a later conflicting save receives 409, keeps draft input, and explicit reload restores the current values.
- Normal user receives API 403 and the Admin-required screen without an Administration navigation link.
- Screenshots at 1440px, 768px, and 375px; no document horizontal overflow. Desktop and mobile captures were visually inspected. Zero uncaught page errors.

The initial browser run caught a missing JSON Content-Type on PATCH. This was fixed, asserted in the frontend test, and the browser journey and frontend checks/build were rerun successfully. Browser functional verification used the development QA frontend; production compilation was checked separately. No real provider searches, payment requests, or Cloud Tasks were triggered by these tests.

Local browser script, isolated compose configuration, and screenshot evidence are retained under `.tools/admin-plan-catalog/` (ignored local artifacts). This was a focused feature verification, not a rerun of every historical browser journey.

## Commands executed

Commands below ran from the repository root; `/opt/homebrew/bin/docker` is the local Docker executable.

```sh
DEBUG=false SERP_ENABLED_PROVIDERS=fake SERP_PROVIDER_PRIORITY=fake SERP_FIXED_PROVIDER=fake SERPER_API_KEY= SERPAPI_API_KEY= TASK_QUEUE_PROVIDER=local /opt/homebrew/bin/docker compose run --rm --no-deps -v /Users/haunguyen/Desktop/serp-saas/backend/app:/app/app:ro -v /Users/haunguyen/Desktop/serp-saas/backend/tests:/app/tests:ro -v /Users/haunguyen/Desktop/serp-saas/backend/alembic:/app/alembic:ro backend sh -c 'pytest -q && ruff check . && ruff format --check . && mypy'

/opt/homebrew/bin/docker run --rm -e NEXT_PUBLIC_API_BASE_URL=http://backend:8000 -e NEXT_PUBLIC_APP_ENV=test -v /Users/haunguyen/Desktop/serp-saas/frontend/src:/app/src:ro serp-saas-frontend-test sh -c 'npm test && npm run lint && npm run format:check && npm run typecheck && npm audit'

/opt/homebrew/bin/docker compose -p serp-plan-qa -f /private/tmp/serp-plan-qa.yml up -d --wait
/opt/homebrew/bin/docker compose -p serp-plan-qa -f /private/tmp/serp-plan-qa.yml exec -T backend sh -c 'alembic current && alembic check'
node /private/tmp/verify-plan-catalog.mjs

env -u DEBUG /opt/homebrew/bin/docker compose build backend worker frontend
env -u DEBUG /opt/homebrew/bin/docker compose build frontend
env -u DEBUG /opt/homebrew/bin/docker compose run --rm --no-deps backend alembic upgrade head
env -u DEBUG /opt/homebrew/bin/docker compose up -d --no-build --wait backend worker frontend
```

The second frontend build includes the final browser-discovered fix. The local application migration and deployment preserve `.env` and its configured providers; QA edits used the separate database only.
