# Milestone 6.5B verification

**Final verification passed:** 80 frontend tests in 17 files; ESLint, Prettier, TypeScript strict, npm audit and production build passed; all five Docker services were healthy; public Home/Pricing and all authenticated regression journeys passed in Chrome.

Verification date: 2026-09-13. Verification used the current M6.5B worktree and preserved M1–M6.5A behavior. No backend source, schema or business rule changed in M6.5B.

## Implementation summary and architecture

The milestone adds a public Home, dynamic Pricing, `/register`, dedicated public header/footer/mobile navigation, canonical/ social metadata, `robots.txt` and `sitemap.xml`. [public-site-architecture.md](public-site-architecture.md) documents route ownership, data flow, responsive rules and future boundaries.

`PublicShell` is selected for `/`, `/pricing`, `/login`, `/register` and `/signup`. It reuses the M6.5A Drawer, icons, button styles and semantic tokens without rendering the authenticated sidebar. Authenticated `/app`, Billing and Admin routes continue to use `AppShell`. The footer contains only working Home, Pricing, Login and Register links.

Home is statically rendered. It contains the Hero and product preview, value strip, four-step workflow, customer-facing features, separate Desktop/Mobile explanation, Tracked Sites/domain alias continuity, Plan-qualified schedules, usage/Plan preview, truthful future API teaser and final CTA. Synthetic preview data uses `seo-demo.com`; no real customer, payment or provider data appears. Copy contains no real-time, unlimited, competitor analytics, automatic billing or available-public-API claim.

Pricing metadata is static while `PricingCatalog` loads `GET /api/v1/billing/plans` through the existing API client and TanStack Query. Desktop and Mobile are grouped independently and each group is ordered Free, Starter, Pro. Prices, limits, currency and schedule entitlement render directly from Plan objects. No UI fallback constant can replace backend prices. Loading uses the shared Skeleton; failure uses a retryable ErrorState and displays no prices.

## Plan catalog and CTA behavior

Chrome captured a successful catalog response and compared all six API records before checking the rendered cards:

| Device | Plan | Price/month | Projects | Keywords | Monthly checks | Scheduling |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Desktop | Free | $0 | 1 | 50 | 100 | None |
| Desktop | Starter | $19 | 5 | 500 | 5,000 | Weekly |
| Desktop | Pro | $129 | 20 | 5,000 | 50,000 | Daily |
| Mobile | Free | $0 | 1 | 20 | 50 | None |
| Mobile | Starter | $39 | 3 | 200 | 1,000 | Weekly |
| Mobile | Pro | $249 | 10 | 1,000 | 10,000 | Daily |

Logged-out Free cards say Start Free and route to `/register`. Logged-out paid cards say Request Activation and route to registration. After registration, Free routes to `/app` and paid Request Activation routes to `/settings/billing`. The page says paid Plans are manually activated by an administrator after bank-transfer payment confirmation. Browser assertions confirmed no Buy Now, Checkout, Subscribe, Stripe, PayPal or crypto wording.

The FAQ matches M6A: one logical keyword check is one customer usage unit; Desktop/Mobile scopes are independent and can coexist; periods reset according to Free calendar or subscription period; data remains readable at limits; paid activation is manual.

## SEO verification

Generated production output was inspected in Chrome:

- Home title: `Google Rank Tracker for Desktop & Mobile | SERP SaaS`.
- Home description mentions Google tracking across Desktop and Mobile, schedules and history.
- Pricing title and description identify Desktop/Mobile Plan comparison.
- Home and Pricing canonical and Open Graph URLs resolve from `NEXT_PUBLIC_SITE_URL`.
- Both pages include Open Graph and Twitter metadata.
- Home JSON-LD is an accurate `SoftwareApplication` without Offer, review or rating data.
- `/robots.txt` allows public pages and disallows `/app`, `/admin`, `/settings` and `/api`.
- `/sitemap.xml` contains exactly the intended public destinations: `/`, `/pricing`, `/login`, `/register`; no authenticated, settings or Admin URL is advertised.
- No Docs or Developer route link exists.

## Exact final commands and results

Run from the repository root. Toolchain paths are local to this workstation.

```sh
# Frontend quality, final source
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development NEXT_PUBLIC_SITE_URL=http://localhost:3000 npm --prefix frontend test
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development NEXT_PUBLIC_SITE_URL=http://localhost:3000 npm --prefix frontend run lint
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development NEXT_PUBLIC_SITE_URL=http://localhost:3000 npm --prefix frontend run format:check
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=development NEXT_PUBLIC_SITE_URL=http://localhost:3000 npm --prefix frontend run typecheck
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm --prefix frontend audit --audit-level=moderate

# Production Docker build and service readiness
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml up --build -d --wait
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml up --build -d --wait frontend
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml ps
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml exec -T backend python -c "import os; print({'DEBUG': os.environ.get('DEBUG'), 'TASK_QUEUE_PROVIDER': os.environ.get('TASK_QUEUE_PROVIDER'), 'SERP_PROVIDER': os.environ.get('SERP_PROVIDER'), 'SERP_ENABLED_PROVIDERS': os.environ.get('SERP_ENABLED_PROVIDERS'), 'SERPER_API_KEY_SET': bool(os.environ.get('SERPER_API_KEY')), 'SERPAPI_API_KEY_SET': bool(os.environ.get('SERPAPI_API_KEY'))})"
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:3000/health
```

The final Docker frontend build executed `npm run build` (`next build --webpack`): compilation and TypeScript passed, **19/19 static pages** were generated. Its route table includes `/`, `/pricing`, `/login`, `/register`, `/robots.txt` and `/sitemap.xml`. Dynamic customer detail routes remained buildable.

| Check | Latest authoritative result |
| --- | --- |
| Frontend full suite | **80 passed in 17 files** |
| ESLint | Passed, exit 0 |
| Prettier | All matched files conform, exit 0 |
| TypeScript strict | `tsc --noEmit` passed; project keeps `strict: true` |
| npm audit | **0 vulnerabilities** |
| Production Next.js build | Passed; 19/19 static pages generated |
| Backend `/health` | `{"status":"ok"}` |
| Frontend `/health` | HTTP success; production page returned |
| Docker | backend, worker, frontend, PostgreSQL and Redis healthy |

Backend code was not touched, so the backend suite, Ruff and mypy were not rerun for M6.5B. The accepted M6.5A checkpoint remains 215 backend tests, but it is not presented as a newly executed M6.5B result. No migration was added.

## Safe Docker environment

The final stack used the same explicit `/tmp/m6a-compose.yml` override as the accepted milestones:

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

No Stripe, bank API, Cloud Tasks, Serper or SerpApi operation ran. Browser accounts and catalog requests were local; ranking verification explicitly reported `provider: fake` and `realProviderCredits: 0`.

The final runtime assertion returned `DEBUG=false`, `TASK_QUEUE_PROVIDER=local`, `SERP_PROVIDER=fake`, `SERP_ENABLED_PROVIDERS=fake`, and both provider-key flags `False`.

## Public browser, responsive and accessibility verification

The final public command was:

```sh
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-public-browser.mjs
```

It passed Home content, Hero/footer links, public shell separation, six authoritative Plans, Desktop/Mobile grouping, exact API-to-card values, manual activation wording, logged-out and authenticated CTA behavior, metadata, JSON-LD, robots, sitemap and absence of customer-data API requests. Chrome clicked Hero Start Free to `/register`, public Login to `/login`, View Pricing to `/pricing` and a paid Request Activation action to registration. It reported zero browser exceptions, zero network failures and zero harmless events.

The command checked Home and Pricing at every required width, for **10 public page/viewport checks**:

| Width | Header/menu | Home | Pricing | Result |
| ---: | --- | --- | --- | --- |
| 375px | Mobile drawer, active route, focus trap, Escape/return focus | Stacked Hero, preview, sections, FAQ/footer/CTAs | Single-column Plan cards | Passed; no critical overflow |
| 768px | Desktop navigation at the configured 760px breakpoint | Stacked/adaptive sections | Two-column cards | Passed; no critical overflow |
| 1024px | Desktop navigation | Two-column Hero; adaptive cards | Three-card product lines | Passed; no critical overflow |
| 1280px | Desktop navigation | Full desktop composition | Three-card product lines | Passed; no critical overflow |
| 1440px | Desktop navigation | Full desktop composition | Three-card product lines | Passed; no critical overflow |

Eleven screenshots are retained in [screenshots/milestone-6.5b](screenshots/milestone-6.5b): Home and Pricing at all five widths plus the 375px navigation drawer. Desktop/mobile Home, desktop/mobile Pricing and the drawer were visually inspected. Visual inspection found one genuine issue in an earlier artifact: the final Home secondary CTA had insufficient contrast and left alignment. Its color and alignment were corrected, the production image was rebuilt, and the complete public journey passed again on the corrected image.

Accessibility assertions covered header/nav/main/footer landmarks, a coherent `h1`→`h2`→`h3` hierarchy, semantic links versus action buttons, textual Plan features, active route beyond color, named mobile-menu controls, repeated Tab focus containment, Escape close/focus return, unlocked page scrolling, visible focus outline and at least 4.5:1 contrast for Hero body text. This is targeted browser evidence, not a full WCAG certification or screen-reader audit.

The pricing-load failure, retry action, no-fallback message, public menu, Plan grouping and both auth CTA states are also covered by the frontend suite.

## Authenticated regression

These exact Chrome commands were run after the public production build:

```sh
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-auth-browser.mjs
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-projects-browser.mjs
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:/private/tmp/serp-tools/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-rankings-browser.mjs
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-node/node_modules/node/bin:/private/tmp/serp-tools/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-billing-browser.mjs
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 node scripts/verify-design-browser.mjs
```

- Authentication passed registration, protected route, reload restoration, logout, anonymous redirect, login, secure cookie behavior, no browser token storage and `/health`.
- Projects/Keywords/Tracked Sites passed create/update/alias promotion, keyword deduplication/pause and persistence; populated Project and Site screens passed all five widths.
- Rankings passed fake manual check, current/history/detail results, Batch/Job progress, polling, daily/weekly schedule update/delete and persistence. Four populated screen groups passed all five widths.
- Billing/Admin passed separate device limits, logical usage, normal-user Admin denial, Desktop/Mobile manual activation, bank reference, extension, upgrade, history and audited adjustment. Three populated screen groups passed all five widths.
- M6.5A design journey passed Overview, all customer routes, mobile navigation/dialog focus, mobile table, Free schedule disabled, search, keyboard rankings tabs and logout across **45 responsive views**.

There were zero browser exceptions in every final journey. Auth, Projects and design reported zero network failures; Rankings reported zero unexpected failures and Billing reported zero real provider calls. The design journey recorded two harmless cancelled route-navigation GETs (`net::ERR_ABORTED`) separately. Rankings recorded one successful DELETE 204 body-abort event after response success; this is not a failed request.

One diagnostic Rankings invocation failed before Plan setup because its process `PATH` omitted the local Docker binary (`spawnSync docker ENOENT`). The corrected exact command above passed; the diagnostic is not claimed as an application pass or failure.

One diagnostic public rerun read the Pricing CTA before AuthProvider had completed session restoration. The verifier now waits for the authenticated Open App state before asserting the billing destination; the final rerun passed. This was a verifier timing race, not a browser exception, request failure or product defect.

## M1–M6.5A regression status

M1 health, M2 auth/session, M3 Projects/Keywords, M3.1 Tracked Sites/aliases, M4 ranking/history, M5 async Batch/Job/scheduling, M6A Plans/usage/manual Admin activation and M6.5A Overview/AppShell/responsive behavior all passed their production browser journeys. The M6A public Plan endpoint remained unchanged and supplied all Pricing values. Public routes never rendered `.app-sidebar`, and logged-out Home/Pricing did not request Projects, Tracked Sites, Rankings or `/billing/me`.

## Known limitations

- Verification used installed Chrome with resized viewports; Safari, Firefox, physical phones and a screen reader were not tested.
- Accessibility checks are targeted and do not constitute full WCAG certification.
- `NEXT_PUBLIC_SITE_URL` must be set to the production HTTPS origin before deployment; local Docker intentionally uses `http://localhost:3000`.
- Pricing depends on live availability of the backend catalog. Failure has a safe retryable state and intentionally shows no cached hard-coded prices.
- Public Docs, customer API, API Keys, payment gateway, automatic recurring billing, advanced analytics, blog/CMS, localization and dark public theme remain deferred.

## Full M6.5B Definition of Done

### Public Shell

- [x] public header
- [x] public mobile navigation
- [x] public footer
- [x] login CTA
- [x] register/start CTA
- [x] public shell visually matches M6.5A language

### Home

- [x] Hero
- [x] product value proposition
- [x] How It Works
- [x] core features
- [x] Desktop vs Mobile explanation
- [x] Tracked Sites / alias section
- [x] scheduling section
- [x] usage/Plans preview
- [x] API/developer teaser is truthful
- [x] final CTA
- [x] responsive

### Pricing

- [x] six Plans render
- [x] Desktop and Mobile are separate sections
- [x] prices sourced from authoritative backend data
- [x] Project limits shown
- [x] Keyword limits shown
- [x] monthly checks shown
- [x] scheduling shown
- [x] Free CTA correct
- [x] paid CTA reflects manual activation
- [x] no fake checkout
- [x] FAQ aligns with M6A

### SEO

- [x] Home metadata
- [x] Pricing metadata
- [x] canonical URLs
- [x] Open Graph
- [x] robots.txt
- [x] sitemap.xml
- [x] no private routes advertised in sitemap

### Responsive

- [x] 375px passed
- [x] 768px passed
- [x] 1024px passed
- [x] 1280px passed
- [x] 1440px passed
- [x] no critical overflow
- [x] mobile navigation usable
- [x] Pricing cards readable
- [x] CTAs visible

### Accessibility

- [x] semantic landmarks
- [x] coherent headings
- [x] keyboard public navigation
- [x] focus visible
- [x] mobile menu accessible
- [x] buttons/links semantically correct
- [x] contrast acceptable

### Quality

- [x] frontend tests pass
- [x] ESLint passes
- [x] Prettier passes
- [x] TypeScript strict passes
- [x] npm audit acceptable
- [x] production build passes
- [x] browser Home journey passes
- [x] browser Pricing journey passes
- [x] responsive verification passes
- [x] Docker services healthy
- [x] authenticated app regression passes
