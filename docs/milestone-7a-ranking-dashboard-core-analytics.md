# Milestone 7A — Ranking Dashboard & Core Analytics

## 1. Objective

Implement the first analytics milestone for the SERP SaaS product.

M7A must turn the ranking history already collected by M4/M4.1/M5 into a useful project-level analytics experience without changing SERP provider behavior, customer billing, scheduling, or rank-check execution.

The milestone focuses on six capabilities:

1. Project ranking summary.
2. Ranking distribution.
3. Improved / Declined / Unchanged counts.
4. Biggest Winners / Biggest Losers.
5. Ranking history line chart.
6. 7D / 30D / 90D time ranges.

Do not implement Payment Gateway, Developer API, API Keys, API Docs, keyword research, search volume, backlinks, site audit, AI recommendations, or competitor analytics in this milestone.

---

# 2. Existing Architecture Constraints

Preserve the current architecture and domain boundaries.

Current stack:

- Frontend: Next.js + TypeScript + App Router.
- TanStack Query for server state.
- Shared design system from M6.5A.
- Backend: FastAPI.
- SQLAlchemy 2 async.
- PostgreSQL.
- User-only tenant model.
- No organizations, workspaces, teams, or project memberships.
- `current_user.id` is the ownership boundary.
- Never trust a client-supplied `user_id`.
- Existing rank-check execution, provider routing, Cloud Tasks, schedules, billing, and quota behavior must remain unchanged.

Relevant existing concepts:

```text
User
├── Projects
│   └── Keywords
└── Tracked Sites
    └── Domain Aliases
```

Ranking data already exists through:

```text
RankCheck
RankCheckResult
Ranking
```

Use existing persisted ranking history as the source of truth.

M7A must not trigger extra SERP provider requests.

---

# 3. Core Product Principle

M7A is analytical and read-only.

```text
Existing rank checks
      ↓
Persisted ranking snapshots
      ↓
Analytics queries
      ↓
Dashboard / charts / movement
```

Opening the dashboard, changing date ranges, expanding a chart, or viewing winners/losers must never enqueue a new rank check.

Customer usage must not increase because analytics pages are viewed.

Provider usage must not increase because analytics pages are viewed.

---

# 4. Definitions

## 4.1 Current Ranking

For a Keyword + Tracked Site, `current ranking` is the latest successful persisted ranking observation that falls within the relevant Project/environment scope.

Do not treat failed rank checks as a ranking position.

If no successful ranking exists:

```text
Not ranked
```

## 4.2 Previous Ranking

For movement calculation, `previous ranking` means the immediately preceding successful comparable observation before the current observation.

The observation must be comparable on the same:

```text
Project
Keyword
Tracked Site
device/environment
```

Do not compare Desktop ranking with Mobile ranking.

## 4.3 Improved

Lower numeric SERP position is better.

Example:

```text
Previous: 18
Current:   7

Improved by 11
```

## 4.4 Declined

Example:

```text
Previous: 5
Current:  12

Declined by 7
```

## 4.5 Unchanged

Example:

```text
Previous: 8
Current:  8
```

## 4.6 Newly Ranked

Previous observation:

```text
Not ranked
```

Current:

```text
position 37
```

Preferred M7A behavior:

```text
movement = newly_ranked
```

Keep it distinct from numeric improvement.

## 4.7 Lost Ranking

Previous:

```text
position 22
```

Current:

```text
Not ranked
```

Preferred movement:

```text
movement = lost_ranking
```

Keep it distinct from numeric decline.

## 4.8 No Previous Data

If only one successful ranking observation exists:

```text
movement = no_previous_data
```

Do not classify it as unchanged.

---

# 5. Ranking Distribution

For the latest comparable snapshot, calculate Keyword ranking buckets for the selected Project and environment.

Canonical buckets when data depth supports them:

```text
Top 3
4–10
11–20
21–50
51–100
Not found in checked depth
```

Recommended response:

```json
{
  "effective_depth": 100,
  "buckets": {
    "top_3": 42,
    "positions_4_10": 94,
    "positions_11_20": 69,
    "positions_21_50": 73,
    "positions_51_100": 39,
    "not_found_in_depth": 111
  }
}
```

No Keyword may appear in more than one canonical bucket.

Derived totals may be calculated as:

```text
Top 10  = top_3 + positions_4_10
Top 20  = Top 10 + positions_11_20
Top 100 = Top 20 + positions_21_50 + positions_51_100
```

---

# 6. Project Ranking Summary

Add a project-level analytics summary.

Recommended route:

```text
GET /api/v1/projects/{project_id}/analytics/summary
```

Supported query parameters:

```text
device=desktop|mobile
range=7d|30d|90d
```

If the Project already has one fixed device/environment, do not introduce a redundant selector solely for M7A.

Response should include at least:

```json
{
  "project_id": "...",
  "device": "desktop",
  "range": "30d",
  "as_of": "2026-09-22T...",
  "total_keywords": 428,
  "ranked_keywords": 317,
  "not_found_in_depth": 111,
  "top_3": 42,
  "top_10": 136,
  "improved": 37,
  "declined": 21,
  "unchanged": 340,
  "newly_ranked": 12,
  "lost_ranking": 9,
  "no_previous_data": 9
}
```

Counts must reconcile.

Document the reconciliation invariant in code/tests.

If archived/inactive Keywords are excluded by existing product semantics, preserve that rule and document it.

---

# 7. Date Range Semantics

M7A supports:

```text
7D
30D
90D
```

The date range controls historical trend/chart data.

Recommended comparison behavior:

```text
Current = latest successful comparable observation
Comparison = latest successful comparable observation at or before range start
```

Example for 30D:

```text
Current: latest observation
Comparison: latest observation at or before current_time - 30 days
```

If no comparison observation exists at/before the range boundary, fall back to the earliest successful observation inside the selected range and mark the comparison basis clearly.

Do not silently compare arbitrary records.

---

# 8. Biggest Winners / Biggest Losers

Add endpoint:

```text
GET /api/v1/projects/{project_id}/analytics/movers
```

Query parameters:

```text
device=desktop|mobile
range=7d|30d|90d
limit=10
```

Recommended response:

```json
{
  "winners": [
    {
      "keyword_id": "...",
      "keyword": "vinfast vf6",
      "tracked_site_id": "...",
      "tracked_site_name": "cafebiz",
      "previous_position": 18,
      "current_position": 7,
      "change": 11
    }
  ],
  "losers": [
    {
      "keyword_id": "...",
      "keyword": "xe dien vinfast",
      "tracked_site_id": "...",
      "tracked_site_name": "cafebiz",
      "previous_position": 8,
      "current_position": 16,
      "change": -8
    }
  ]
}
```

Rules:

- Winners require both positions to be numeric.
- Losers require both positions to be numeric.
- `newly_ranked` and `lost_ranking` must not be mixed into numeric winner/loser sorting in M7A.
- Sort Winners by largest positive movement first.
- Sort Losers by largest negative movement first.
- Add deterministic tie-breaking.
- Enforce a safe server-side maximum for `limit`.

---

# 9. Ranking History Series

Add or extend an endpoint for chart-ready history.

Recommended:

```text
GET /api/v1/projects/{project_id}/keywords/{keyword_id}/ranking-history
```

Query parameters:

```text
tracked_site_id=<uuid>
device=desktop|mobile
range=7d|30d|90d
```

Response example:

```json
{
  "keyword_id": "...",
  "keyword": "vinfast vf6",
  "tracked_site": {
    "id": "...",
    "name": "cafebiz"
  },
  "device": "desktop",
  "range": "30d",
  "points": [
    {
      "checked_at": "2026-09-01T...",
      "position": 18,
      "status": "ranked",
      "rank_check_id": "..."
    },
    {
      "checked_at": "2026-09-08T...",
      "position": null,
      "status": "not_found_in_depth",
      "rank_check_id": "..."
    }
  ]
}
```

Do not invent position `101`, `999`, or another fake numeric position.

---

# 10. Multiple Checks Per Day

The system may allow manual and scheduled checks on the same day.

Preferred M7A rule:

```text
Use the latest successful comparable observation per calendar day for chart visualization.
```

Use deterministic time boundaries.

Prefer UTC unless the repository already defines an explicit Project timezone.

Do not infer timezone from browser locale.

---

# 11. Missing Dates

Do not interpolate rankings.

If no check occurred:

```text
no point
```

Do not fabricate a ranking.

---

# 12. Ranking History Line Chart

Add a chart to the inline Ranking History experience already implemented in the Project Keywords table.

When the user clicks a Keyword:

```text
Keyword row
  ↓
Expanded Ranking History
  ├── 7D | 30D | 90D
  ├── line chart
  └── existing ranking history table
```

The existing history table must remain.

Required chart behavior:

- X-axis: date/time.
- Y-axis: ranking position.
- Position `1` appears visually at the top.
- Higher numeric positions appear lower.
- Tooltip shows date/time, position/status, and tracked site.
- Responsive.
- No viewport overflow at 375px.
- Keyboard-accessible range controls.
- Do not rely on color alone.

Use an existing chart library if one already exists. If none exists, choose one lightweight React chart library with strong TypeScript support. Do not introduce multiple chart libraries.

---

# 13. Dashboard UI

Enhance the Project Detail page with analytics.

Recommended order:

```text
Project Header

Analytics range
[7D] [30D] [90D]

Summary KPI cards

Ranking Distribution

Biggest Winners | Biggest Losers

Keywords table
```

Avoid a major navigation redesign in M7A.

---

# 14. KPI Cards

Display at least:

```text
Tracked Keywords
Top 3
Top 10
Improved
Declined
Not found in checked depth
```

Only display Top 20 / Top 100 if persisted depth supports them.

Use existing Card and typography primitives.

Use semantic design-system tokens for movement states.

---

# 15. Ranking Distribution Visualization

Prefer a horizontal bar chart.

Requirements:

- labels readable;
- values visible;
- accessible text equivalent;
- responsive;
- no hover-only comprehension;
- exact backend bucket semantics.

---

# 16. Winners / Losers UI

Use compact tables/cards.

Keyword names should be clickable text links, not filled buttons.

Preferred behavior:

```text
click keyword
→ navigate/focus to keyword in Keywords section
→ optionally expand Ranking History
```

Reuse shared text-link styling.

---

# 17. Loading / Empty / Error States

Use existing:

```text
Skeleton
EmptyState
ErrorState
```

An analytics failure must not make the full Project page unusable.

Empty state:

```text
No ranking data yet.
Run a rank check to start building ranking history.
```

Do not automatically run a check.

---

# 18. Backend Service Layer

Do not place aggregation SQL directly in routers.

Recommended structure:

```text
router
  ↓
ProjectAnalyticsService
  ↓
analytics repository/query layer
```

Suggested methods:

```text
get_summary()
get_distribution()
get_movers()
get_keyword_history()
```

---

# 19. Query Performance

Design for thousands of Keywords.

Do not:

```text
load all Rankings into Python
then aggregate in application memory
```

Prefer SQL aggregation/window functions.

Avoid N+1 queries.

Dashboard summary and movers must use bounded query counts.

---

# 20. Database Changes

Prefer no schema migration if existing data supports M7A.

Indexes may be added when justified.

Before adding indexes:

- inspect existing indexes;
- avoid duplicates;
- document the query;
- verify upgrade/downgrade.

Do not introduce a background analytics warehouse in M7A.

---

# 21. Tenant Security

All endpoints must enforce ownership via `current_user.id`.

Verify:

```text
Project belongs to current user
Keyword belongs to Project
Tracked Site belongs to current user
```

Never trust client `user_id`.

Add cross-tenant tests.

---

# 22. Rank Check Failures

Failed provider calls or failed RankChecks must NOT be interpreted as:

```text
Not ranked
lost ranking
decline
```

Only successful SERP observations may change analytics.

---

# 23. Critical Checked-Depth Semantics

The current product commonly checks Top 10 to control provider quota.

Therefore:

```text
Not found in Top 10
```

does NOT mean:

```text
Not ranked globally
```

and does NOT prove:

```text
position > 100
```

Before implementing Top 20 / Top 100 analytics, inspect the actual persisted rank depth.

If current checks are Top 10, M7A must render:

```text
Top 3
4–10
Not found in Top 10
```

Do NOT fabricate:

```text
Top 20
Top 100
```

The analytics UI must only claim what stored data proves.

---

# 24. Depth-Aware Distribution

If effective depth is 10:

```json
{
  "effective_depth": 10,
  "buckets": {
    "top_3": 42,
    "positions_4_10": 94,
    "not_found_in_depth": 292
  }
}
```

If effective depth is 100:

```json
{
  "effective_depth": 100,
  "buckets": {
    "top_3": 42,
    "positions_4_10": 94,
    "positions_11_20": 69,
    "positions_21_50": 73,
    "positions_51_100": 39,
    "not_found_in_depth": 111
  }
}
```

The frontend renders only supported buckets.

---

# 25. Movement with Limited Depth

Example:

```text
Previous: #7
Current: Not found in Top 10
```

Do not claim a numeric drop.

Represent a categorical state such as:

```text
left_checked_depth
```

Similarly:

```text
Previous: Not found in Top 10
Current: #7
```

represent:

```text
entered_checked_depth
```

Do not fabricate numeric movement.

---

# 26. Frontend Data Access

Use TanStack Query.

Recommended query keys:

```text
projectAnalytics.summary(projectId, device, range)
projectAnalytics.movers(projectId, device, range)
keywordRankingHistory(projectId, keywordId, trackedSiteId, device, range)
```

Avoid broad invalidation.

A completed rank check should invalidate only relevant analytics/history queries.

---

# 27. Caching

Normal client-side caching is sufficient.

Do not add Redis analytics caching unless profiling demonstrates a need.

---

# 28. URL / State

Default range:

```text
30D
```

If practical, persist it in the URL:

```text
?range=30d
```

---

# 29. Responsive Requirements

Verify at:

```text
375px
768px
1024px
1440px
```

Required:

- KPI cards stack/wrap cleanly.
- Distribution chart stays readable.
- Winner/loser tables adapt.
- Ranking chart has no page overflow.
- Expanded history remains directly below its keyword row/card.

---

# 30. Accessibility

Required:

- keyboard-accessible range selector;
- visible focus styles;
- accessible chart text/table equivalent;
- movement not communicated only by color;
- semantic headings;
- tooltip-only data available elsewhere.

---

# 31. Design System

Reuse current shared primitives:

```text
PageHeader
Card
Button
TextLink / shared link style
Badge / StatusBadge
Skeleton
EmptyState
ErrorState
```

Do not introduce page-specific button colors or a new visual language.

---

# 32. API Error Behavior

Use stable repository-consistent errors, for example:

```text
PROJECT_NOT_FOUND
KEYWORD_NOT_FOUND
TRACKED_SITE_NOT_FOUND
INVALID_ANALYTICS_RANGE
INVALID_DEVICE_SCOPE
```

Cross-tenant access must not leak resource existence.

---

# 33. Backend Tests

Add focused tests for:

- summary counts;
- depth-aware distribution;
- improved;
- declined;
- unchanged;
- entered checked depth;
- left checked depth;
- no previous observation;
- failed RankCheck exclusion;
- Desktop/Mobile isolation;
- date range boundary;
- multiple checks same day;
- tenant isolation;
- movers ordering;
- safe limit validation;
- no fake numeric position for not-found.

---

# 34. Frontend Tests

Add tests for:

- summary cards;
- distribution rendering;
- dynamic checked-depth labels;
- range selector;
- loading;
- empty;
- error/retry;
- winners;
- losers;
- keyword navigation;
- ranking chart mapping;
- not-found rendering;
- inline Ranking History.

---

# 35. Browser Verification

Cover:

```text
Project with data
Project with no ranking data
7D
30D
90D
winner
loser
unchanged
entered checked depth
left checked depth
```

Keyword journey:

```text
click keyword
expand
chart appears
switch range
history table preserved
collapse
open another keyword
```

Viewports:

```text
375
768
1024
1440
```

Verify:

- no browser exceptions;
- no unexpected network failures;
- no horizontal overflow;
- no real SERP provider calls caused by analytics;
- no customer quota consumed by analytics.

---

# 36. Performance Verification

Seed or generate a realistic Project with at least:

```text
1,000 Keywords
multiple historical observations
```

Verify:

- bounded summary queries;
- bounded movers queries;
- no one-request-per-keyword frontend pattern;
- no N+1 database pattern;
- keyword history fetched on demand.

Record approximate local timings in the verification report.

---

# 37. Migration Verification

If no migration:

```text
confirm Alembic current head
confirm no schema drift
```

If index migration is added:

```text
upgrade
downgrade
upgrade
check head
check schema drift
```

---

# 38. Existing Behavior Regression

Regression-test at least:

```text
Auth
Projects
Keywords
Tracked Sites
Rankings
Manual rank check
Batch History
Schedule
Billing & Usage
Admin Customers
Home
Pricing
Login
Register
```

M7A must not modify provider routing, queue semantics, subscription enforcement, usage reservation, or public pricing behavior.

---

# 39. Out of Scope

Do NOT implement:

```text
Payment Gateway
Stripe
PayPal
crypto payment

Developer API
API keys
API Docs

alerts / email / Slack / Telegram
CSV/PDF reports
scheduled reports

keyword tags/groups
advanced keyword bulk management

competitor analytics
share of voice

search volume
keyword difficulty
keyword research

backlinks
site audit
crawler

AI SEO recommendations
AI content generation

Google Search Console
Google Analytics

public analytics sharing
white-label reports
```

---

# 40. Suggested Future Milestones

```text
M7B — Ranking Explorer
- advanced filters
- date comparison
- threshold entry/drop views
- newly ranked / lost ranking

M7C — Keyword Organization
- tags
- groups
- bulk organization
- tag analytics

M7D — Alerts
- in-app notifications
- email

M7E — Reports
- CSV
- PDF
- scheduled reports

M7F — Competitor Analytics
```

---

# 41. Definition of Done — Backend

- [ ] Project analytics service exists.
- [ ] Tenant-safe analytics endpoints exist.
- [ ] 7D / 30D / 90D supported.
- [ ] Distribution is checked-depth-aware.
- [ ] No fake ranking positions.
- [ ] Comparison semantics documented.
- [ ] Movement states deterministic.
- [ ] Winners/Losers implemented.
- [ ] Keyword history chart-ready.
- [ ] Failed RankChecks excluded.
- [ ] Desktop/Mobile isolation maintained.
- [ ] Queries avoid N+1.
- [ ] Cross-tenant tests pass.

---

# 42. Definition of Done — Frontend

- [ ] Project analytics summary visible.
- [ ] Ranking distribution visualization exists.
- [ ] Winners/Losers visible.
- [ ] 7D / 30D / 90D selector works.
- [ ] Expanded Keyword Ranking History includes line chart.
- [ ] Existing history table remains.
- [ ] Checked-depth wording is correct.
- [ ] Shared loading/empty/error primitives used.
- [ ] Responsive layouts pass.
- [ ] Accessibility requirements pass.

---

# 43. Definition of Done — Integrity

- [ ] Analytics does not run SERP checks.
- [ ] Analytics does not consume customer quota.
- [ ] Analytics does not consume provider credits.
- [ ] M5 jobs/batches unchanged.
- [ ] M6A subscription/usage enforcement unchanged.
- [ ] No Payment/API/Docs functionality introduced.
- [ ] Existing ranking history is not destructively migrated.

---

# 44. Definition of Done — Verification

Run and report exact results for:

```text
backend tests
frontend tests
lint
format check
TypeScript typecheck
npm audit
production frontend build
Docker health
Alembic head / drift
browser verification
analytics performance check
```

Final report must include:

```text
files changed
migration status
endpoints added
movement semantics
checked-depth semantics
test counts
browser evidence
performance evidence
known limitations
```

Do not claim PASS for commands not actually run.

---

# 45. Important Pre-Implementation Audit

Before coding, inspect the current persistence model and answer:

```text
What ranking depth is actually persisted today?
```

If current checks only persist Top 10, M7A must use:

```text
Top 3
4–10
Not found in Top 10
```

and must NOT show fake Top 20 / Top 100 metrics.

This requirement takes precedence over conceptual mockups.

---

# 46. Final Instruction to Codex

Implement M7A using current repository conventions rather than creating a parallel analytics architecture.

Before editing code:

1. inspect existing ranking models, services, repositories, routes, tests, and UI;
2. inspect how rank depth and `not found` are persisted;
3. inspect existing indexes;
4. report any conflict between this specification and the current data model;
5. then implement the smallest coherent solution.

Prefer reuse over duplication.

Do not change unrelated business behavior.

Do not spend real SERP provider credits during development or verification.
