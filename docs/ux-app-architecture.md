# M6.5A application UX architecture

`AppShell` lives inside the existing AuthProvider and TanStack Query provider. It selects the authenticated layout by route and reads the existing session role for Admin navigation. Feature guards and backend authorization remain authoritative. Public home, pricing, signup, login and health keep their existing routing and presentation.

| Route | Purpose |
| --- | --- |
| `/app` | Overview: existing resource counts, per-device usage, six recent batches and onboarding |
| `/app/projects` | Search/filter projects, environment and keyword counts; expandable activity/actions |
| `/app/projects/new` | Existing atomic project + initial keyword creation |
| `/app/projects/[projectId]` | Search environment/settings, keywords/latest positions, history, batches and schedule |
| `/app/rankings` | Project selector and current positions with All/Ranked/Needs attention views |
| `/app/tracked-sites` | Customer domain registry |
| `/app/tracked-sites/new` | Create site with primary and previous/alias domains |
| `/app/tracked-sites/[siteId]` | Domain management, primary/alias/active labels and retained 301 guidance |
| `/settings/billing` | Independent Desktop/Mobile Plans, limits, progress, reset and manual upgrade guidance |
| `/app/settings` | Existing profile/session details and logout |
| `/admin/customers` | Admin-only search and customer selection |
| `/admin/customers/[userId]` | Existing manual subscription, adjustment/history/audit flows using shared controls |

## Data flow

The small authenticated `GET /api/v1/overview` endpoint aggregates BillingViewService's existing customer summary, active Tracked Site count and six recent user-owned batches with existing job counts. It adds no tables, migration, new billing rule or analytics. The bounded aggregation avoids multiple list requests just to draw Overview. Its query is user-scoped and polls only while a recent batch is pending/queued/running.

Projects load existing cursor pages. Secondary per-project latest-batch/schedule metadata is requested only when Activity & actions opens. Rankings uses existing project and latest-ranking APIs, with local view filters and project pagination. Project detail retains existing mutations, cache invalidation, async job polling and history queries. M6A limits, reservations and Admin security are preserved server-side.

## Interaction decisions

Project section links provide direct access to Keywords, Rankings, Batch History, Schedule and settings. Keywords precede secondary batch/schedule forms. Existing edit, pause/resume, bulk add, ranking/history, cancellation and schedule actions remain available. Failed jobs retain textual status and safe errors; retry actions remain explicit.

Free scheduling is explained and disabled, Starter offers weekly, Pro daily/weekly. Billing is read for entitlement presentation; backend enforcement stays unchanged. Existing incompatible schedules remain visibly disabled after reconciliation. Customer usage combines no device allowances: each card has its own counters and reset.

Deletion/cancellation controls open a shared confirmation describing consequences before dispatch. Admin replacement snapshots the validated form payload and requires confirmation. Errors remain near the workflow; success toasts dismiss automatically. Mobile navigation closes after route selection and restores focus on dismissal. Tables present readable labeled records on small screens rather than hiding columns.

## Scope

No new public marketing site, public API/API keys, developer docs portal, real payment integration, provider requests, Cloud Tasks operations or M7 analytics. The existing M6A public pricing page remains available and is not redesigned here. Existing login/signup business flows remain unchanged; account settings moved from the old `/app` placeholder to `/app/settings`.
