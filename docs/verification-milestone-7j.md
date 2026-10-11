# Milestone 7J — Change Plan UI verification

Implemented and verified locally on **2026-10-11**. Production deployment and
verification with a real account have **not** been performed.

## Route, navigation and account safety

`/app/change-plan` renders the new authenticated Change Plan page. The app sidebar
and mobile drawer include **Change Plan** under Usage & billing, after Billing &
Usage and before Settings. The active link and breadcrumb identify the page.
Public navigation has no new item.

Anonymous users redirect to `/login`; unverified users redirect to `/verify-email`.
Both catalog and subscription queries stay disabled until the session is
authenticated and the user has verified email. This gate also works when the
page is rendered independently of AppShell. Session loading/error/retry reuse the
existing protected-page components.

Current account information comes from authenticated `GET /api/v1/billing/me`,
without a client-supplied user ID. Its query key includes the session user ID;
account changes cannot reuse another user's subscription result. Backend account
ownership, entitlement logic and expiry reconciliation are unchanged.

## Shared catalog, prices and current plan

The app and public Pricing use the shared `planCatalogQuery` in
`frontend/src/features/billing/plan-catalog.ts`: `GET /api/v1/billing/plans`, query
key `public-plans`, and the existing 60-second stale time. Existing public
`groupPlans` ordering and `planPrice` formatting are extracted unchanged into the
same module. Public Pricing rendering, copy, links and behavior remain unchanged;
there is no new catalog configuration or fallback pricing.

Desktop/Mobile tabs filter the catalog by `device_scope`. They keep subscriptions
independent and support ArrowLeft/ArrowRight/Home/End through the existing Tabs
primitive. Desktop is initially selected; each tab shows its own current account
plan, subscription status and the backend expiry when present. Expiry is formatted
as a UTC date and explicitly labeled UTC. A missing expiry is not inferred.

Backend subscription snapshots contain **code and scope, without catalog ID**.
Cards are marked current by matching their code and product line to the matching
billing device. The summary displays the saved subscription plan name; cards show
current catalog values. An explicit **Current Plan** badge and a real disabled
**Current Plan** button identify the matching card. No current plan is guessed
when subscription lookup fails or a scope is absent.

Cards render backend plan name, currency, monthly price, max projects, max
keywords, monthly keyword checks, schedule enablement/frequency and product line.
The backend exposes `price_monthly_minor_units`, so the billing period is monthly;
no separate interval is fabricated. No description, recommendation or entitlement
is invented. Cards have icons, dividers, aligned entitlement rows, subtle borders
and shadows, with one column on narrow mobile screens, two at intermediate widths
and three where app content space permits (1280px viewport and above).

## Select and informational modal

`onPlanSelect(planId, productLine)` only stores local selection state and opens
**Plan upgrade coming soon**. The dialog explains that online payment and automatic
upgrades are being prepared and that the current subscription has not changed.
Close, Escape and backdrop dismissal use the existing native Dialog primitive.
Focus is trapped while open and returns to the initiating Select button on close.

There is no checkout, payment-provider code, redirect or billing mutation handler.
Unit and browser assertions verify **zero additional API requests on Select**,
including zero billing/subscription mutation requests. Browser checks also close
and reopen the dialog, switch scopes, refresh the page and confirm the original
current plan remains selected. The existing backend may reconcile expired
subscriptions during its normal reads; this milestone does not alter that logic.

## Loading, error and empty states

- Catalog loading shows three skeleton cards; subscription loading has a separate
  skeleton.
- Catalog failure shows **Unable to load plans.** with Retry. No catalog cards or
  fallback prices appear during failure.
- Subscription failure shows an independent Retry and explicitly states that the
  current plan could not be identified. Catalog comparison remains available.
- Empty catalogs show **No plans are currently available.** for the selected scope.
- Missing subscription scopes are reported without assuming a Free plan.

## Automated gates

Node **22.22.0**, Next **16.3.8**; no dependency or lockfile changes.

| Check                  | Result                                                             | Evidence                                                             |
| ---------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------- |
| `npm test`             | 287 passed, 32 files                                               | [Tests](verification-artifacts/milestone-7j/tests.txt)               |
| `npm run lint`         | Pass                                                               | [Lint](verification-artifacts/milestone-7j/lint.txt)                 |
| `npm run typecheck`    | Pass                                                               | [TypeScript](verification-artifacts/milestone-7j/typecheck.txt)      |
| `npm run format:check` | Pass                                                               | [Formatting](verification-artifacts/milestone-7j/format-check.txt)   |
| `npm run build`        | Pass; `/app/change-plan` prerendered, 50 static pages generated    | [Build](verification-artifacts/milestone-7j/build.txt)               |
| `npm audit --omit=dev` | Exit 0; zero runtime vulnerabilities, including zero high/critical | [Audit](verification-artifacts/milestone-7j/runtime-audit.json)      |
| `git diff --check`     | Pass                                                               | [Diff check](verification-artifacts/milestone-7j/git-diff-check.txt) |

The 14 new unit cases cover verified route/navigation, anonymous and unverified
gates, session recovery, skeletons, both product lines, Free/Paid current plan
matching without snapshot IDs, disabled current actions, backend fractional prices
and multiple currencies, numeric limits, schedule capabilities, keyboard switching,
modal close/Escape/focus return, zero API activity on Select, catalog error/retry,
subscription error/retry, empty catalogs, missing subscription and account-scoped
query caching. Existing auth, projects, analytics, reports, competitors, billing,
admin and public English/Vietnamese Pricing suites also pass.

The initial TypeScript run encountered obsolete duplicate generated types in
`.next/dev/types` referring to the former route layout. That generated cache was
removed; a fresh production build and TypeScript gate pass. The first audit attempt
had no registry access, and automatic approval review initially rejected escalation
because it sends dependency metadata externally. The user explicitly approved
`npm audit`; the authorized run then completed with zero vulnerabilities.

## Local production browser QA

Production standalone runs at `http://127.0.0.1:3014`. Chrome, Playwright and axe
come from existing external local QA tools; no QA dependency is added to the app.
Every API response is an intercepted synthetic fixture. No live account, backend,
provider, payment or production request is used.

At **375, 768, 1024 and 1440px**, the runner checks:

- Free Desktop, Paid Desktop, Free Mobile and Paid Mobile current-plan fixtures.
- Catalog failure with Retry, empty catalog and subscription failure with Retry.
- Both tabs, backend prices/currencies/limits/schedules, current badges, disabled
  actions and backend expiry presentation.
- One H1, no horizontal overflow, mobile card stacking, equal card heights in the
  three-column desktop row and active navigation on sidebar/mobile drawer.
- Informational Select with keyboard activation, forward/backward focus trapping,
  Escape, Close, trigger focus restoration and zero extra API requests.
- Unchanged current subscription presentation after page refresh.
- Zero browser exceptions/hydration errors and zero axe WCAG 2/2.1 A/AA violations
  for both tab contents, error/empty states and open informational dialogs.

**28 responsive fixture cases** (56 scope checks) and **8 auth redirect cases** pass.
[Browser evidence](verification-artifacts/milestone-7j/browser-qa.json) and
[runner output](verification-artifacts/milestone-7j/browser-qa.txt) include network
requests, scope results and mutation assertions. Full-page screenshots are stored
beside them; mobile and desktop captures were visually inspected.

The expanded app regression passes **41 cases** across anonymous, verified and
unverified sessions for Overview, Projects, Tracked Sites, Rankings, project detail,
Ranking Explorer, Reports, Competitors, Settings, Billing & Usage, Change Plan and
normal-user admin protection. It reports zero browser/hydration errors and zero
normal-user admin requests.
[Regression evidence](verification-artifacts/milestone-7j/app/app-browser-qa.json),
[runner output](verification-artifacts/milestone-7j/app-regression.txt).

## Reproduction and production status

Run frontend gates with Node 22.22.0. Build using:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=production \
  NEXT_PUBLIC_SITE_URL=https://serpsaas.com \
  NEXT_PUBLIC_APP_URL=https://app.serpsaas.com npm run build
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/
cp -R public .next/standalone/public
PORT=3014 HOSTNAME=127.0.0.1 node .next/standalone/server.js
```

In another frontend terminal, with optional local Playwright/axe and Chrome paths:

```bash
QA_BASE_URL=http://127.0.0.1:3014 \
  QA_TOOLS_DIRECTORY=/path/to/tools/node_modules \
  QA_CHROME_PATH='/path/to/Chrome' \
  node scripts/verify-change-plan-browser.mjs
QA_BASE_URL=http://127.0.0.1:3014 \
  QA_ARTIFACT_DIRECTORY=../docs/verification-artifacts/milestone-7j/app \
  QA_TOOLS_DIRECTORY=/path/to/tools/node_modules \
  QA_CHROME_PATH='/path/to/Chrome' \
  node scripts/verify-security-regression.mjs
```

**Not deployed.** No push, production revision or real-user verification was
performed. After authorized deployment, log in as a normal verified user at
`https://app.serpsaas.com/app/change-plan`, compare each catalog with the backend,
verify both current plans, click Select, confirm only information appears, inspect
network traffic for zero billing/subscription mutation requests, then refresh and
verify unchanged subscriptions. Local fixture QA does not claim that live
production verification has occurred or that payment functionality exists.
