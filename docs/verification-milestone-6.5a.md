# Milestone 6.5A verification

**Final verification passed:** 215 backend tests; 75 frontend tests in 16 files; all quality/build/connectivity checks passed; all five Docker services healthy; five Chrome journeys and 90 viewport/screen checks passed.

Verification date: 2026-09-13. This milestone continues the existing M6A implementation. It redesigns the authenticated application and preserves M1–M6A business behavior. No public marketing, public API, API keys, payment gateway or M7 analytics were added.

## Implementation and architecture

The shared system lives in `frontend/src/design-system/`: semantic light-theme tokens, reusable UI components and AppShell. The shell runs inside the existing authentication and TanStack Query providers. Desktop sidebar, contextual topbar, account menu, active-route indicators, skip link and modal mobile navigation share one navigation definition. Public/auth/health pages retain their existing layout.

See [design-system.md](design-system.md) for tokens/component contracts and [ux-app-architecture.md](ux-app-architecture.md) for routing, data flow and ownership.

Tokens cover surface/background/border, primary/secondary/muted text, brand and semantic status colors; typography, a 4px spacing scale, 6/10/16px radii and restrained shadows. Feature styling uses semantic colors. Shared component styles own button/control/table behavior; features retain their existing API calls and state transitions.

Actual adoption includes:

| Primitive | Screens using it |
| --- | --- |
| Button/Input/Select/Textarea | Projects/Keywords, Tracked Sites, batch/schedule, Billing Admin, account actions |
| Card/StatCard | Overview, project cards, Billing device cards, ranking detail |
| StatusBadge | Overview, Projects/Keywords, Rankings, batches, schedules, Billing/account |
| Table/DataTable | Keyword positions, batch history, rankings/history, Admin lists and Overview recent batches |
| Tabs | Rankings view filters, with arrow/Home/End keyboard support |
| Dialog/ConfirmDialog/Drawer | Destructive deletion/cancellation, Admin replacement and mobile navigation |
| Alert/Toast | Persistent errors and transient mutation success across the main features |
| Skeleton | Loading Overview, Projects, sites, rankings/history, batches/schedules and Billing |
| EmptyState/ErrorState | Overview, Projects, Keywords, Rankings and empty batch history/recoverable fetch failures |
| CursorPagination | Rankings project selection; existing cursor controls retain shared Button styling elsewhere |

Other reusable primitives include IconButton, native Checkbox/Radio/Switch/Combobox, FormField/FormError, DropdownMenu/Popover/Tooltip, Spinner and UsageMeter. Not every exported optional primitive needs a dedicated product workflow. Existing field validation and server errors remain authoritative.

## Screen-by-screen

- **Overview `/app`:** active project/keyword/site counts, committed checks, separate Desktop/Mobile allowance cards, six recent ranking batches and four onboarding links. No trend, delta, chart analytics or invented metrics. The site step reflects whether an active site exists; other links remain a simple setup guide.
- **Projects:** search and status filters, device/country/language/location/keyword counts, shared cards/status, create action and expandable Activity & actions. Latest-batch and schedule metadata load only when expanded, avoiding requests for every row at initial load.
- **Project detail/Keywords:** environment header, section links, keyword controls first, latest positions/history, explicit pause/resume and delete confirmation. Existing create/edit/bulk/check behavior remains.
- **Rankings:** project selection using existing cursor APIs, current positions, Tracked Sites, timestamps and readable Never checked/Ranked/Not found/failed states. All/Ranked/Needs attention filters operate on the existing latest response.
- **Rank Check detail:** search-environment snapshot, status/timestamps, top organic results and matched-site badges. Provider routing metadata stays out of customer presentation.
- **Tracked Sites:** existing primary/previous-alias registry and 301 guidance, shared form/actions, visible statuses and confirmation before deletion/deactivation.
- **Batch/Job:** history, completed/running/failed counts, progress, terminal polling behavior, job details and confirmation before cancelling unstarted work.
- **Schedule:** daily/weekly frequency, conditional weekday, local time/timezone, next run, update/delete and clear Free disabled-by-Plan guidance. Starter weekly and Pro daily/weekly remain server-controlled. An entitlement change refreshes the form's initial enabled state.
- **Billing & Usage:** device-separated prices/subscription periods, projects/keywords/checks, progress including reservations, remaining/reset information and manual upgrade guidance. No self-activation or payment-state controls.
- **Account/settings:** existing account/session information and logout moved to `/app/settings`.
- **Admin:** existing customer search, Plan activation/extension/cancellation, device separation, history, usage adjustment and audit use shared controls. Immediate replacement requires confirmation and retains the existing payload/authorization semantics.

## Backend scope and Overview security

Only `app/api/v1/overview.py`, `app/services/overview.py` and router registration are added for this milestone, plus `tests/test_overview.py`. The authenticated aggregation delegates billing to the existing BillingViewService, counts active sites by user and selects six batches filtered by the authenticated user with existing job counters. Tests check authentication and cross-customer resource isolation. Browser verification compares the populated summary with the project, keyword, site, logical usage and completed batch created during the journey.

No M6.5A migration or schema change is introduced; M6A Alembic head remains `0008_billing_usage_limits`. Existing M6A changes in the working tree are preserved.

## Safe verification environment

The local Docker stack uses this explicit override at `/tmp/m6a-compose.yml`:

```yaml
services:
  backend:
    environment: &verification
      DEBUG: "false"
      TASK_QUEUE_PROVIDER: local
      SERP_PROVIDER: fake
      SERP_ENABLED_PROVIDERS: fake
      SERP_FIXED_PROVIDER: fake
      SERP_PROVIDER_STRATEGY: fixed
      SERP_PROVIDER_PRIORITY: fake
      SERPER_API_KEY: ""
      SERPAPI_API_KEY: ""
  worker:
    environment: *verification
```

A final runtime assertion also confirmed fake SERP, local tasks, empty provider keys and DEBUG=false (`/tmp/m65-safe-env.log`).

Browser fixtures register synthetic local accounts and use guarded local operator fixtures for Admin/Pro. They exercise manual subscription records only: no Stripe, bank APIs, real Serper/SerpApi or real Cloud Tasks operations. Database suites use isolated test schemas.

## Exact commands and evidence

Run from the repository root unless stated otherwise. Toolchain paths are specific to this workstation.

```sh
# Production build and all-service readiness, final source
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml up --build -d --wait > /tmp/m65-release-build.log 2>&1

# Authoritative repository checks, final source
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH make COMPOSE='docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml' CHECKS='docker compose -f docker-compose.yml -f docker-compose.checks.yml -f /tmp/m6a-compose.yml' check > /tmp/m65-authoritative-check.log 2>&1

# Dependency audit
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend audit --json > /tmp/m65-audit.json
```

The `make check` target executes backend `pytest`; frontend `npm test`; backend `ruff check .` and `ruff format --check .`; frontend `npm run lint` and `npm run format:check`; backend `mypy`; frontend `npm run typecheck`; backend/frontend connectivity checks. Frontend checks run in the checks image; the running application uses the production Next.js image.

Additional local diagnostics actually executed:

```sh
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development npm --prefix frontend test
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend run lint
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend run format:check
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend run typecheck
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend run format
# In backend/
DEBUG=false DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serp_saas REDIS_URL=redis://127.0.0.1:6379/0 .venv/bin/pytest tests/test_overview.py -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

Browser commands use this exact environment prefix for each script:

```sh
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' DOCKER_BIN=/private/tmp/serp-tools/bin/docker DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-auth-browser.mjs
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' DOCKER_BIN=/private/tmp/serp-tools/bin/docker DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-projects-browser.mjs
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' DOCKER_BIN=/private/tmp/serp-tools/bin/docker DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-rankings-browser.mjs
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' DOCKER_BIN=/private/tmp/serp-tools/bin/docker DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-billing-browser.mjs
PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' DOCKER_BIN=/private/tmp/serp-tools/bin/docker DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-design-browser.mjs
```

Logs are `/tmp/m65-{auth,projects,rankings,billing,design}.log`. Responsive assertions shared by existing journeys live in `scripts/browser-responsive.mjs`. Screenshots are retained under [screenshots/milestone-6.5a](screenshots/milestone-6.5a).

## Corrections during verification

Earlier runs are diagnostic and do not supersede the final results below:

- Initial native frontend run lacked required public configuration; rerun used explicit API/environment values.
- Account tests still imported the old `/app` account placeholder; updated to `/app/settings`.
- jsdom lacks dialog methods; the test setup provides a narrow polyfill, with real Chrome checking actual modal behavior.
- Overview's new test compared to `/billing` instead of `/billing/me`; corrected the test URL. A test hook returned a mock as a cleanup callback; corrected the hook.
- Real keyboard verification found drawer focus could leave its controls; explicit wraparound now supplements native modality.
- A Plan changed while the schedule editor was open left its initial checkbox stale; entitlement changes now reset the appropriate initial form state.
- Browser locators were updated for title-cased status badges and accessible mobile column labels.
- Ruff found router import ordering; fixed formatting only. Muted caption contrast was slightly below 4.5:1 on the canvas and was darkened.

## Final results

`make check` exited **0** on the final source. These counts supersede all checkpoints and diagnostic runs.

| Check | Final executed result |
| --- | --- |
| Backend Docker full suite | **215 passed**, 73.50s |
| Frontend Docker full suite | **75 passed in 16 files** |
| Ruff | All checks passed |
| Ruff formatting | 160 files already formatted |
| mypy | Success, no issues in 109 source files |
| ESLint | Passed, exit 0 |
| Prettier | All matched files conform, exit 0 |
| TypeScript | `tsc --noEmit` passed with `strict: true` |
| npm audit | 0 info/low/moderate/high/critical vulnerabilities; 556 dependencies in audit metadata |
| Production frontend | `next build --webpack` passed, 16/16 static pages generated, standalone image built |
| Connectivity | Backend health/database/Redis/docs/OpenAPI and frontend-to-backend/own-page checks passed |
| Docker | backend, worker, frontend, PostgreSQL and Redis all healthy |
| Alembic | `0008_billing_usage_limits (head)`; `alembic check`: No new upgrade operations detected |

Docker migration/health commands actually executed:

```sh
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml exec -T backend alembic current > /tmp/m65-migration-current.log 2>&1
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml exec -T backend alembic check > /tmp/m65-migration-check.log 2>&1
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml ps > /tmp/m65-health.log
```

## Browser and responsive results

Authentication passed signup, session restoration/reload, login/logout, cookie flags, no browser token storage and M1 health pages. Projects/Keywords/Tracked Sites passed creation, alias promotion and retention, deduplication, environment updates, keyword add/pause and reload persistence. Billing/Admin passed customer quotas, separate device allowances, normal-user Admin denial, manual activations, extension/replacement, history, audited adjustment and hidden internal notes. M5 passed fake rankings, latest positions, history/detail, top results, batch/job progress, terminal polling stop, schedule create/update/delete and persisted results. Populated Overview resource/batch counts and its exact Billing summary were checked against current data.

All five final Chrome journeys passed on the final production build. Authentication, Projects and M5 reported zero browser exceptions/unexpected network failures; Billing/Admin reported zero browser exceptions; the design journey reported empty exception/failure lists. Mobile logout also returned to `/login`.

**90 viewport/screen checks passed**: 45 in the design journey plus 10 Projects/Tracked Site, 15 Billing/Admin and 20 M5/Overview/Rankings checks.

| Width | Shell | Main screens and populated data | Result |
| --- | --- | --- | --- |
| 375px | Drawer + compact topbar; active route; Escape/focus return; mobile logout | Overview, Projects/create/detail, Keywords, Tracked Sites/create/domain detail, Rankings, batch/history/detail, daily/weekly schedule, Billing, account, Admin customer list/billing | Passed; no critical page overflow or clipped form/action controls |
| 768px | Drawer + topbar; keyboard navigation and route-close | Same screen coverage, fluid cards and usable filters/controls | Passed |
| 1024px | Sidebar + context topbar | Same screen coverage; readable data and visible actions | Passed |
| 1280px | Sidebar + context topbar | Same screen coverage; readable data and visible actions | Passed |
| 1440px | Sidebar + context topbar | Same screen coverage; readable data and visible actions | Passed |

The 375px keyword, ranking, history and batch tables use labeled stacked records. Shared responsive checks assert page width and bounds of visible inputs/selects/textareas/buttons. Search was exercised on mobile; cursor pagination is covered by frontend regression tests and visible-control bounds on Admin/list screens. Native confirmation bounds fit 375px; drawer controls keep focus across repeated Tab presses, Escape restores focus, navigation closes the drawer and the page remains scrollable. The active Settings link was asserted in the drawer; Rankings keyboard selection has a visible focus outline.

Screenshots include all five Overview widths and desktop/mobile examples of populated Overview/Rankings, Keywords, Tracked Site domains, daily/weekly schedules, Billing/Admin, plus mobile drawer and confirmation. **27 screenshots** are retained. Representative desktop Overview, mobile Keywords, mobile Admin billing, mobile weekly schedule, drawer and confirmation images were visually inspected.

## Accessibility and regressions

The component suite executes deferred confirmation/cancel behavior, focus restoration, native cancel handling, keyboard Tabs, field-error association, mobile table labels, textual statuses, Retry and reservation-aware progress. Real Chrome verifies modal focus wrapping, Escape/return focus and mobile navigation; the responsive journey also tests focused-tab outlines and a small-screen confirmation's bounds. Icon buttons have explicit names and statuses carry text. Screenshots were inspected for hierarchy, readable stacked data and control placement.

Computed source-token contrast checks passed: primary text on white 15.53:1; secondary 6.27:1; muted on canvas 4.67:1; brand 6.36:1; success 6.68:1; warning 6.18:1; danger 6.33:1 (semantic colors measured on white). This is targeted contrast evidence, not a comprehensive WCAG certification.

The final complete backend suite retains M1 connectivity/configuration, M2 authentication/session/security, M3 Projects/Keywords and tracked-domain ownership, M4 provider-independent ranking/history and routing, M5 queue/replay/concurrency/scheduling and M6A billing/usage/Admin/migration tests. Frontend/API tests and browser journeys preserve these flows. No backend business behavior was changed to satisfy visual checks.

Harmless events are separate from failures: initial anonymous `/auth/refresh` 401 is expected; M5 reported **one successful DELETE 204 response-body abort** after the response status was asserted. The final design journey also recorded **one cancelled GET during route navigation** (`net::ERR_ABORTED`), with no unexpected network failures. npm printed an update notice. A diagnostic run with five concurrent Chrome processes during Docker work timed out on signup (backend logs still showed 201 responses taking over ten seconds); final journeys were run sequentially. These diagnostic failures are not reported as passes.

## Known limitations

- One light authenticated theme; dark mode is deferred.
- Chromium desktop automation with resized viewports was executed; no claim of Safari/Firefox, physical phone, screen-reader certification or a full WCAG audit.
- Native date/time/datalist appearance varies by OS. Dense records stack on mobile and can require vertical scrolling.
- Project activity metadata is deliberately expanded on demand. Rankings presents current API data and local filters, not new analytics.
- The existing M6A public pricing page remains unchanged; public marketing redesign, public docs/API/API keys, payment integration and advanced analytics remain deferred.
- Fake SERP/local-task tests verify application behavior without validating external paid services.

## Changed file groups

New: design-system folder; Overview feature and endpoint/service/tests; Rankings page; account settings route; project activity preview; design/architecture/report documents; responsive helper/design browser script and screenshots. Modified: authenticated root layout/globals, existing main feature components, confirmation/auth tests and existing browser scripts. M6A's pre-existing uncommitted billing/model/migration changes are not attributed to this redesign.

## Full Definition of Done

### Definition of Done — Design System

- [x] semantic color tokens
- [x] typography system
- [x] spacing system
- [x] radius/shadow system
- [x] shared form controls
- [x] Card/Table/Badge/Tabs/Dialog/Drawer
- [x] Toast/Alert
- [x] Skeleton
- [x] EmptyState
- [x] ErrorState
- [x] consistent status system

### Definition of Done — App Shell

- [x] authenticated app shell
- [x] sidebar navigation
- [x] responsive mobile navigation
- [x] top bar/context header
- [x] active navigation state
- [x] consistent page width/spacing

### Definition of Done — Overview

- [x] Overview screen exists
- [x] existing product summary data displayed
- [x] current usage summary
- [x] recent Batch summary
- [x] first-time checklist
- [x] no M7 analytics added

### Definition of Done — Core Screens

- [x] Projects redesigned
- [x] Project detail redesigned
- [x] Keywords redesigned
- [x] Tracked Sites redesigned
- [x] Rankings redesigned
- [x] Rank Check detail redesigned
- [x] Batch history/progress redesigned
- [x] Schedule UX redesigned
- [x] Billing & Usage redesigned
- [x] Account/settings aligned
- [x] M6A Admin screens use shared system

### Definition of Done — Responsive UX

- [x] desktop usable
- [x] laptop usable
- [x] tablet usable
- [x] mobile usable
- [x] no critical horizontal overflow
- [x] mobile navigation works
- [x] dense data remains readable

### Definition of Done — Accessibility

- [x] visible focus states
- [x] keyboard navigation
- [x] semantic labels
- [x] dialog focus management
- [x] accessible icon-only actions
- [x] status not color-only
- [x] contrast acceptable
- [x] heading hierarchy coherent

### Definition of Done — Behavior Preservation

- [x] auth unchanged
- [x] Project/Keyword behavior unchanged
- [x] Tracked Site behavior unchanged
- [x] ranking behavior unchanged
- [x] Batch/Job behavior unchanged
- [x] schedule behavior unchanged
- [x] Billing/Usage limits unchanged
- [x] Admin authorization unchanged
- [x] provider/cloud infrastructure remains hidden from normal UX

### Definition of Done — Quality

- [x] frontend full suite passes
- [x] backend regression suite passes if backend touched
- [x] ESLint passes
- [x] Prettier passes
- [x] TypeScript strict passes
- [x] npm audit acceptable
- [x] frontend production build passes
- [x] browser verification passes
- [x] responsive browser verification passes
- [x] Docker services healthy
