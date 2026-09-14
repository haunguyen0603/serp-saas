# Visual QA and UI consistency pass

Date: 14 September 2026

## Scope and evidence

This pass audited the current product without changing API contracts, authentication, billing rules, Plan data, ranking behavior, or provider infrastructure. The browser journeys used the local Docker stack, the fake ranking provider, and local task execution.

The complete evidence sets contain 100 screenshots each:

- [Before polish](screenshots/visual-qa/before/)
- [After polish](screenshots/visual-qa/after/)

The required 375px, 768px, 1024px, and 1440px widths were captured for all audited screens. The browser suites also checked 1280px where supported.

## Route coverage

| Area | Route or state | Screenshot names | Result |
| --- | --- | --- | --- |
| Overview | `/app` | `overview-*`, `overview-populated-*` | Passed |
| Projects | `/app/projects` | `projects-*`, `projects-populated-*` | Passed |
| Project Detail and Keywords | `/app/projects/:projectId#keywords` | `project-keywords-*` | Passed |
| Rankings | `/app/rankings` and populated project ranking state | `rankings-*`, `rankings-populated-*` | Passed |
| Tracked Sites | `/app/tracked-sites` | `tracked-sites-*`, `tracked-sites-populated-*` | Passed |
| Tracked Site Detail | `/app/tracked-sites/:siteId` | `tracked-site-domains-*` | Passed |
| Batch History and progress | Project Batch History section | `batch-daily-schedule-*`, `batch-weekly-schedule-*` | Passed |
| Schedule | Project Schedule section, daily/weekly/disabled states | `batch-daily-schedule-*`, `batch-weekly-schedule-*`, `project-keywords-*` | Passed |
| Billing & Usage | `/settings/billing` | `billing-*`, `billing-populated-*` | Passed |
| Account | `/app/settings` | `account-*` | Passed |
| Admin Customers | `/admin/customers` | `admin-customers-*` | Passed |
| Admin Billing | `/admin/customers/:userId` | `admin-billing-*` | Passed |
| Home | `/` | `home-*` | Passed |
| Pricing | `/pricing` | `pricing-*` | Passed |
| Login | `/login` | `login-*` | Passed |
| Register | `/register` | `register-*` | Passed |

## Inconsistencies and fixes

| Inconsistency found | Resolution | Fix level | Verification |
| --- | --- | --- | --- |
| Page titles and header actions used several unrelated flex layouts. | Added the shared `PageHeader` primitive with a consistent title, optional eyebrow/description, wrapping, spacing, and action group. Adopted it in Overview, Projects, Rankings, Tracked Sites, Account, and Admin Customers. | Shared component | Header/action placement remains aligned at 375–1440px. |
| Account shortcuts mixed a filled link, outlined link, underlined text links, and a separately styled Logout button. | Added the secondary link-button token variant and applied one shared size, padding, border, radius, and wrap behavior to the shortcut group. | Token level | Account screenshots show consistent controls on desktop and two-row wrapping at 375px. |
| Projects and Tracked Sites bypassed shared card, error, and empty-state primitives. | Projects now uses the base `Card` and `ErrorState`. Tracked Sites now uses `Card`, `StatusBadge`, `ErrorState`, and `EmptyState`. The existing header CTA remains the single empty-state action. | Shared component | Populated, empty, loading, error-capable markup, desktop, and mobile states verified. |
| The Tracked Site Detail header stretched `Archive Site` to the full heading block height. | Added wrapping and cross-axis start alignment to the unique detail header. | Page-specific layout | Button is 40px high at 1440px and remains aligned beside the title at 375px. |
| Tracked Site statuses and domain labels mixed plain text, custom colored text, and raw badge classes. | Reused `StatusBadge` and `Badge` tones for site status, Primary/Alias, and Active/Inactive labels. | Shared component | Badges have consistent size, radius, and non-color text labels. |
| Project settings and safe Admin mutations looked like secondary actions despite being form submissions. | Applied the shared primary `Button` variant to Save Project Settings, Extend subscription, Activate Plan, and Adjust usage. Destructive cancellation remains the danger variant. | Shared component usage | Project and Admin Billing screenshots show consistent blue primary and red danger actions. |
| Login/Register submit buttons differed from the public primary CTA, while reciprocal navigation needed lower visual emphasis. | Reused the primary `Button` for both submit actions and the shared inline `ui-text-link` style for Log in/Create account navigation. | Shared component usage | Login/Register desktop and mobile screenshots show full-width primary CTAs with muted inline secondary navigation and visible keyboard focus. |
| Tracked ranking matches were static text in the Project Keywords table. | Rendered an existing match as the shared `ui-text-link` to its corresponding Tracked Site; historical matches without a current site ID remain text. | Page-specific integration using shared token | Unit and browser ranking journeys passed; navigation target is tenant-scoped by the existing API data. |
| Schedule controls and footer actions were unevenly aligned. | Kept the previously accepted behavior and aligned the fields through the existing grid; Save uses primary and Delete uses danger at the bottom action row. | Page-specific layout using shared components | Daily, weekly, disabled-by-Plan, desktop, and mobile states passed. |

## Visual consistency results

- Button variants, height, padding, radius, and focus styles are consistent through `Button` and link-button tokens. Primary, secondary, ghost, disabled, and danger meanings remain distinct.
- Inputs and selects use the shared 42px app control height. Public authentication controls intentionally retain the existing 52px public-form size and match each other.
- Cards use the shared border, medium radius, white surface, padding, and small shadow. Nested data regions retain borders where their dense layout is unique.
- The app content container keeps the existing 1500px maximum width and responsive 40px/24px/20px/16px gutters.
- Section spacing and typography preserve the existing hierarchy. Page titles, section headings, captions, labels, and supporting text remain distinguishable.
- Table headers and values remain aligned at desktop widths. At 375px, shared tables expose each header through the stacked `data-label` layout and retain readable actions.
- Empty, loading, and error-capable states use `EmptyState`, `Skeleton`, and `ErrorState` on the main audited list pages.
- Dialog and drawer checks passed for viewport fit, Escape close, focus return, native focus trap, mobile navigation, and scroll behavior.
- No critical horizontal overflow was detected at any checked viewport. Action groups wrap without clipping, and primary actions remain visible.

## Exact final commands and results

The working directory used for each command is stated with its result.

```bash
NEXT_PUBLIC_API_BASE_URL=http://backend:8000 NEXT_PUBLIC_APP_ENV=test PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm test
```

Run from `frontend/`: **17/17 test files and 85/85 tests passed**.

```bash
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run lint
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run format:check
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm run typecheck
PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH npm audit --audit-level=high
```

Run from `frontend/`: ESLint passed, all files matched Prettier, TypeScript `tsc --noEmit` passed, and npm reported **0 vulnerabilities**. The first sandboxed audit attempt could not resolve `registry.npmjs.org`; the authoritative rerun with network access passed.

```bash
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml build frontend
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml up -d --no-deps frontend
```

The production Next.js build compiled successfully, passed its TypeScript phase, generated 19 routes, and produced the standalone production image.

The browser commands used the following common environment, plus `DOCKER_CONFIG` and the Docker wrapper path for suites that seed through Docker:

```bash
SCREENSHOT_DIR=docs/screenshots/visual-qa/after PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-design-browser.mjs
SCREENSHOT_DIR=docs/screenshots/visual-qa/after PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-projects-browser.mjs
DOCKER_CONFIG=/private/tmp/serp-tools/docker SCREENSHOT_DIR=docs/screenshots/visual-qa/after PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 PATH=/private/tmp/serp-node/node_modules/node/bin:/private/tmp/serp-tools/bin:$PATH node scripts/verify-rankings-browser.mjs
DOCKER_CONFIG=/private/tmp/serp-tools/docker SCREENSHOT_DIR=docs/screenshots/visual-qa/after PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 PATH=/private/tmp/serp-node/node_modules/node/bin:/private/tmp/serp-tools/bin:$PATH node scripts/verify-billing-browser.mjs
SCREENSHOT_DIR=docs/screenshots/visual-qa/after PLAYWRIGHT_MODULE=/private/tmp/serp-node/node_modules/playwright-core/index.mjs CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' FRONTEND_URL=http://localhost:3000 PATH=/private/tmp/serp-node/node_modules/node/bin:$PATH node scripts/verify-public-browser.mjs
```

Final browser results:

- Design/App Shell: passed 45 responsive views; no browser exceptions or network failures.
- Projects/Keywords/Tracked Sites: passed all journeys and responsive screens; no browser exceptions or network failures.
- Rankings/Batch/Schedule: passed all journeys; fake provider; zero real provider credits; no browser exceptions or unexpected network failures.
- Billing/Admin: passed all customer and admin journeys; zero real provider calls; no browser exceptions.
- Public: passed Home, Pricing, Login, Register, metadata, navigation, focus, contrast, and responsive checks; six Plans loaded; no browser exceptions or network failures.

```bash
DOCKER_CONFIG=/private/tmp/serp-tools/docker PATH=/private/tmp/serp-tools/bin:$PATH docker compose -f docker-compose.yml -f /tmp/m6a-compose.yml ps
```

Backend, worker, frontend, PostgreSQL, and Redis were all **healthy** in the final stack.

## Harmless browser events and limitations

- The final Design/App Shell run recorded four `net::ERR_ABORTED` requests to the current project route during deliberate client navigation. There were no failed assertions, browser exceptions, or unexpected network failures.
- The Rankings journey recorded one successful `204` response whose empty body was aborted by Chrome. The journey passed and no ranking request was double-run.
- A focused “Skip to content” control appears in a few full-page evidence screenshots because the accessibility journey intentionally uses keyboard focus. It is normally off-screen and is expected accessibility behavior.
- Screenshot comparison was performed by captured-state inspection and deterministic browser assertions; no pixel-diff threshold is enforced in CI.
