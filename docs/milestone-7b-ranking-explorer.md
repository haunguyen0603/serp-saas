# Milestone 7B — Ranking Explorer

## 1. Objective

Implement the next analytics milestone after M7A.

M7B must turn the existing ranking analytics and history data into an efficient exploration workflow for users managing many Keywords.

The milestone focuses on:

1. Advanced ranking filters.
2. Date-to-date comparison.
3. Entered / left checked-depth views.
4. Ranking movement filtering.
5. Position-range filtering.
6. Search and sort.
7. Shareable URL state.
8. Efficient server-side pagination.
9. Smooth integration with existing inline Ranking History.

M7B is an exploration and analysis milestone.

It must not change SERP provider execution, rank-check scheduling, customer billing, usage accounting, Plan entitlements, Payment Gateway, Developer API, API Keys, or API Docs.

---

## 2. Existing Foundation

M7A is already implemented and verified.

Existing analytics endpoints include:

```text
GET /api/v1/projects/{project_id}/analytics/summary
GET /api/v1/projects/{project_id}/analytics/distribution
GET /api/v1/projects/{project_id}/analytics/movers
GET /api/v1/projects/{project_id}/keywords/{keyword_id}/ranking-history
```

M7A already established:

- tenant-safe analytics;
- successful persisted RankChecks only;
- bounded SQL aggregation/window queries;
- 7D / 30D / 90D;
- current/comparison semantics;
- checked-depth-aware ranking semantics;
- depth 10 as the current common persistence depth;
- Top 3 / 4–10 / Not found in Top 10 when applicable;
- no fake numeric positions;
- categorical entered/left checked-depth states;
- inline Keyword Ranking History;
- on-demand Keyword history loading.

M7B must reuse these semantics. Do not create a conflicting parallel ranking model.

---

## 3. Core Product Goal

The user should be able to answer:

```text
Which Keywords improved?
Which declined?
Which entered Top 10?
Which left Top 10?
Which are currently Top 3?
Which moved from #18 to #7?
Which Keywords contain "vinfast"?
Show only results for cafebiz.
What changed between two dates?
```

The user should not need to inspect every Keyword row manually.

---

## 4. Primary UX

Create a Ranking Explorer experience inside the Project context.

Preferred route:

```text
/app/projects/{projectId}/rankings
```

Alternative:

```text
/app/projects/{projectId}?tab=rankings
```

Follow current repository navigation conventions.

Recommended layout:

```text
Project Header

Ranking Explorer

[Search keyword...]

Date comparison:
[Current] vs [30 days ago]

Filters:
[Movement]
[Position]
[Tracked Site]
[Status]
[Device if applicable]

Active filter chips

Results summary

Ranking comparison table

Pagination
```

Avoid a major navigation redesign in M7B.

---

## 5. Backend Endpoint

Add a dedicated Explorer endpoint.

Recommended:

```text
GET /api/v1/projects/{project_id}/ranking-explorer
```

Suggested query parameters:

```text
q=
range=7d|30d|90d
compare_from=
compare_to=
movement=
position_bucket=
tracked_site_id=
status=
sort=
order=asc|desc
limit=
cursor=
```

Use cursor pagination if that is already the repository standard.

---

## 6. Default Comparison

Default behavior:

```text
Current
vs
30 days ago
```

Reuse M7A semantics:

```text
Current = latest successful comparable observation
Comparison = latest successful comparable observation at or before range boundary
```

If no observation exists at/before the boundary:

```text
comparison_basis = earliest_in_range
```

Do not silently choose arbitrary rows.

---

## 7. Custom Date Comparison

Support:

```text
7D
30D
90D
Custom
```

Custom mode:

```text
From date
To date
```

Recommended request:

```text
compare_from=2026-08-01
compare_to=2026-09-01
```

For each boundary, use the latest successful comparable observation at or before that date.

If none exists, report missing comparison state explicitly.

Use ISO dates.

If Project timezone does not exist, use UTC consistently.

Do not infer timezone from browser locale.

---

## 8. Ranking Explorer Row Model

Recommended row:

```json
{
  "keyword_id": "...",
  "keyword": "vinfast vf6",
  "status": "active",
  "tracked_site": {
    "id": "...",
    "name": "cafebiz"
  },
  "device": "desktop",
  "comparison": {
    "checked_at": "2026-08-22T...",
    "position": 18,
    "status": "ranked",
    "depth": 10
  },
  "current": {
    "checked_at": "2026-09-22T...",
    "position": 7,
    "status": "ranked",
    "depth": 10
  },
  "movement": {
    "type": "improved",
    "change": 11
  }
}
```

Possible movement types:

```text
improved
declined
unchanged
entered_checked_depth
left_checked_depth
no_previous_data
never_checked
```

Reuse existing enums if already present.

---

## 9. Movement Semantics

Numeric:

```text
18 → 7 = improved by 11
5 → 12 = declined by 7
8 → 8 = unchanged
```

Checked-depth transitions:

```text
Not found in Top 10 → #7
= entered_checked_depth
```

```text
#7 → Not found in Top 10
= left_checked_depth
```

No comparable observation:

```text
no_previous_data
```

Never checked:

```text
never_checked
```

Do not assign fake numeric changes to categorical states.

---

## 10. Movement Filter

Support:

```text
All
Improved
Declined
Unchanged
Entered checked depth
Left checked depth
No previous data
Never checked
```

Example:

```text
movement=improved
```

If multi-select is supported, validate every value server-side.

---

## 11. Position Filter

Filters must be checked-depth-aware.

If effective depth = 10:

```text
Top 3
4–10
Not found in Top 10
```

Do not display Top 20 / Top 50 / Top 100 unless stored data supports them.

Suggested query values:

```text
position_bucket=top_3
position_bucket=positions_4_10
position_bucket=not_found_in_depth
```

Backend metadata remains authoritative about supported buckets.

---

## 12. Current Status Filter

Support:

```text
Ranked
Not found in checked depth
Never checked
```

Do not simplify `Not found in Top 10` into `Not ranked`.

---

## 13. Tracked Site Filter

Support:

```text
tracked_site_id
```

Selectable Tracked Sites must belong to `current_user`.

If only one relevant Tracked Site exists, the UI may omit a redundant filter.

---

## 14. Keyword Search

Support:

```text
q=vinfast
```

Behavior:

- trim whitespace;
- case-insensitive;
- partial match;
- server-side;
- deterministic;
- pagination-compatible.

Do not load all Keywords and filter only client-side.

---

## 15. Sorting

Support at least:

```text
keyword
current_position
comparison_position
change
```

Add deterministic secondary sorting.

Suggested tie-break:

```text
primary sort
keyword normalized
keyword_id
```

Categorical movements must not be converted to fake numeric deltas.

---

## 16. Results Summary

Show compact context above results.

Example:

```text
428 Keywords

37 improved
21 declined
340 unchanged
12 entered Top 10
9 left Top 10
```

Keep distinction between:

- M7A overall Project summary;
- M7B filtered result count.

Do not show ambiguous duplicated metrics.

---

## 17. Active Filter Chips

Show active filters as removable chips:

```text
Improved ×
Top 10 ×
cafebiz ×
"vinfast" ×
```

Provide:

```text
Clear all
```

Reuse shared Badge/chip styling.

---

## 18. URL State

Reflect Explorer state in the URL where practical.

Example:

```text
/app/projects/{id}/rankings?range=30d&movement=improved&position_bucket=top_3&q=vinfast
```

Required behavior:

- refresh preserves filters;
- Back/Forward works;
- URLs are shareable;
- Project-specific filters do not leak to unrelated Projects.

---

## 19. Ranking Comparison Table

Recommended columns:

```text
Keyword
Tracked Site
Previous
Current
Change
Status
History
```

Example:

```text
Keyword        Site       Previous   Current      Change
vinfast vf6    cafebiz       #18        #7          +11
vinfast        cafebiz       #8         #8            0
vinfast vf8    cafebiz       #5      Not found    Left Top 10
```

Use concise wording.

---

## 20. Keyword Interaction

Keyword name must be a clickable text link.

Preferred:

```text
click keyword
→ expand inline Ranking History
```

or focus the corresponding Keyword row and open history if the current structure requires it.

Do not use filled CTA buttons.

---

## 21. Inline History Integration

Reuse M7A inline history:

```text
click Keyword
   ↓
expanded row directly below
   ↓
ranking chart
history table
7D / 30D / 90D
```

Only one history row should be open at a time.

Fetch history on demand.

Do not prefetch one history request per row.

---

## 22. Entered / Left Top 10 Wording

Because current default depth is typically 10:

```text
entered_checked_depth
→ Entered Top 10
```

```text
left_checked_depth
→ Left Top 10
```

If effective depth changes, wording must adapt.

Do not hard-code Top 10 independently of backend depth metadata.

---

## 23. Avoid Misleading “Newly Ranked / Lost Ranking”

With Top-10-only evidence:

```text
Not found in Top 10 → #7
```

does not prove the site was globally unranked.

Therefore prefer:

```text
Entered Top 10
Left Top 10
```

over:

```text
Newly Ranked
Lost Ranking
```

unless the stored data actually supports those stronger claims.

---

## 24. Pagination

Use server-side pagination.

Do not render thousands of rows at once.

Recommended default:

```text
50
```

Optional sizes:

```text
25
50
100
```

Follow the repository's established pagination model.

---

## 25. Query Performance

Support at least the M7A benchmark scale:

```text
1,000+ Keywords
multiple historical observations
```

Avoid:

```text
one DB query per Keyword
one API request per row
loading full history into application memory
```

Inspect query plans for:

- movement filtering;
- keyword search;
- tracked-site filtering;
- position filtering;
- sorting;
- pagination.

---

## 26. Database / Index Review

Do not add indexes blindly.

Inspect current indexes first.

Add only when query plans justify them.

Potential dimensions:

```text
project_id
keyword_id
tracked_site_id
checked_at
status
```

Any index migration must be reversible.

Do not create an analytics warehouse for M7B.

---

## 27. API Response Metadata

Recommended:

```json
{
  "project_id": "...",
  "range": "30d",
  "comparison_basis": "range_boundary",
  "effective_depth": 10,
  "supported_position_buckets": [
    "top_3",
    "positions_4_10",
    "not_found_in_depth"
  ],
  "page": {
    "limit": 50,
    "next_cursor": "..."
  },
  "items": []
}
```

Do not expose provider credits, provider cost, or Cloud Tasks internals.

---

## 28. Tenant Security

Every Explorer request must be scoped by:

```text
current_user.id
```

Validate:

- Project ownership;
- Keyword belongs to Project;
- Tracked Site belongs to current User;
- history expansion cannot cross tenant boundaries.

Cross-tenant requests must not leak resource existence.

---

## 29. Billing / Usage Isolation

Explorer is read-only.

Explorer requests must never:

```text
reserve usage
commit usage
enqueue RankCheck
create Batch
create Job
call SERP provider
```

Changing filters must consume zero customer quota.

---

## 30. Loading States

Use local loading states.

Recommended:

```text
initial load → table skeleton
filter change → preserve previous results while fetching where practical
history expansion → local history skeleton
```

Do not blank the entire Project page.

---

## 31. Empty States

No ranking data:

```text
No ranking data yet.
Run a rank check to start building ranking history.
```

No filter matches:

```text
No Keywords match these filters.
```

Provide:

```text
Clear filters
```

Do not automatically run a rank check.

---

## 32. Error States

Explorer:

```text
Unable to load ranking results.
Retry
```

History errors remain local to the expanded row.

Reuse shared `ErrorState`.

---

## 33. Frontend Query Keys

Recommended:

```text
rankingExplorer.list(projectId, params)
keywordRankingHistory(projectId, keywordId, trackedSiteId, range)
```

Reuse the M7A history cache rather than duplicating it.

---

## 34. Query Invalidation

After a successful RankCheck invalidate only relevant:

```text
M7A summary
M7A distribution
M7A movers
M7B Explorer
relevant Keyword history
```

Do not invalidate unrelated Billing, Account, Admin, or public Pricing data.

---

## 35. Debounced Search

Debounce keyword search.

Recommended:

```text
250–400 ms
```

Do not request the API for every raw keystroke.

---

## 36. Filter Controls

Desktop:

```text
Search | Movement | Position | Site | Date
```

Mobile:

```text
Search
Filters
```

Filters may open in existing Drawer/Sheet patterns.

Do not create horizontally overflowing toolbars.

---

## 37. Responsive Requirements

Verify at:

```text
375px
768px
1024px
1440px
```

Required:

- search usable;
- filters wrap/collapse cleanly;
- existing mobile table/card pattern works;
- inline history stays attached to its Keyword;
- pagination is usable;
- no horizontal page overflow.

---

## 38. Accessibility

Required:

- labeled controls;
- keyboard-accessible filters;
- visible focus states;
- selected filter state exposed;
- sortable columns expose sort direction;
- movement not communicated by color only;
- `aria-expanded` for history;
- filter drawer focus behavior;
- no essential tooltip-only information.

---

## 39. Design System

Reuse:

```text
PageHeader
Card
Button
TextLink
Badge / StatusBadge
Input
Select
Skeleton
EmptyState
ErrorState
Drawer / Dialog
Table
```

Do not introduce page-specific colors or inconsistent button styling.

Filters and analytical navigation should remain visually secondary to primary product actions.

---

## 40. Stable Filter Errors

Validate all query parameters.

Suggested stable errors:

```text
INVALID_ANALYTICS_RANGE
INVALID_MOVEMENT_FILTER
INVALID_POSITION_BUCKET
INVALID_SORT_FIELD
INVALID_SORT_ORDER
INVALID_CURSOR
INVALID_DATE_RANGE
INVALID_DEVICE_SCOPE
```

Follow current API error conventions.

---

## 41. Date Validation

Require:

```text
compare_from <= compare_to
```

Reject malformed dates.

Do not silently swap dates.

---

## 42. Categorical Change Sorting

Do not assign fake numeric deltas to:

```text
entered_checked_depth
left_checked_depth
no_previous_data
never_checked
```

If `sort=change`, define and test a deterministic placement for categorical states.

---

## 43. Explicitly Out of Scope

Do not implement:

```text
Payment Gateway
Stripe
PayPal
crypto payments

Developer API
API Keys
API Docs

CSV/PDF export
scheduled reports

saved searches
saved views

keyword tags/groups
advanced keyword bulk organization

alerts
email notifications
Slack
Telegram

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

white-label reports
```

---

## 44. Browser Verification

Cover:

```text
Default 30D Explorer
Search keyword
Clear search
Improved
Declined
Unchanged
Entered Top 10
Left Top 10
Top 3
4–10
Not found in Top 10
Tracked Site selection
7D
30D
90D
Custom dates
Invalid custom dates
Sorting
Pagination
URL persistence
Back/Forward
Inline history expansion
Switch expanded Keyword
```

Use fake provider/local fixtures only.

Verify zero real provider calls caused by M7B.

---

## 45. Performance Verification

Seed at least:

```text
1,000 active Keywords
multiple observations per Keyword
multiple Tracked Sites when supported
```

Measure approximate local timings for:

```text
default Explorer
movement filter
position filter
keyword search
change sort
next page
```

Record query counts and confirm no N+1 behavior.

---

## 46. Backend Tests

Add tests for:

- default response;
- current/comparison semantics;
- improved;
- declined;
- unchanged;
- entered checked depth;
- left checked depth;
- no previous data;
- never checked;
- Top 3;
- 4–10;
- not found in depth;
- tracked-site filtering;
- keyword search;
- sorting;
- deterministic tie-break;
- pagination;
- custom date comparison;
- invalid date range;
- invalid filters;
- cross-tenant Project;
- cross-tenant Tracked Site;
- failed RankChecks excluded;
- no fake numeric positions;
- depth metadata.

---

## 47. Frontend Tests

Add tests for:

- initial Explorer rendering;
- URL-driven state;
- search debounce;
- movement filter;
- position filter;
- site filter;
- date selector;
- custom date validation;
- filter chips;
- clear filters;
- sorting;
- pagination;
- loading;
- empty;
- error/retry;
- Keyword TextLink;
- inline history;
- mobile filter UI.

---

## 48. Regression Coverage

Re-run:

```text
Auth
Projects
Keywords
Tracked Sites
M7A Analytics
Rankings
Manual Rank Check
Batch History
Schedule
Billing & Usage
Admin
Home
Pricing
Login
Register
```

M7B must not regress M7A semantics.

---

## 49. Migration Verification

If no migration:

```text
confirm Alembic current head
confirm no schema drift
```

If an index migration is added:

```text
upgrade
downgrade
upgrade
verify head
verify schema drift
```

---

## 50. Definition of Done — Backend

- [ ] Ranking Explorer endpoint exists.
- [ ] Tenant-safe.
- [ ] Server-side keyword search.
- [ ] Movement filters.
- [ ] Position filters.
- [ ] Checked-depth-aware semantics.
- [ ] Tracked Site filter.
- [ ] 7D / 30D / 90D.
- [ ] Custom date comparison.
- [ ] Stable sorting.
- [ ] Server-side pagination.
- [ ] No fake ranking positions.
- [ ] Failed RankChecks excluded.
- [ ] No provider calls.
- [ ] No usage accounting.
- [ ] Performance verified.

---

## 51. Definition of Done — Frontend

- [ ] Ranking Explorer UI exists.
- [ ] Search works.
- [ ] Movement filters work.
- [ ] Position filters work.
- [ ] Site filter works.
- [ ] Date comparison works.
- [ ] Filter chips work.
- [ ] URL preserves state.
- [ ] Sorting works.
- [ ] Pagination works.
- [ ] Keyword names use text links.
- [ ] Inline Ranking History works.
- [ ] Responsive requirements pass.
- [ ] Accessibility requirements pass.

---

## 52. Definition of Done — Integrity

- [ ] Explorer is read-only.
- [ ] No RankCheck created by viewing/filtering.
- [ ] No Batch/Job created.
- [ ] No provider request.
- [ ] No customer quota usage.
- [ ] Billing behavior unchanged.
- [ ] Plan behavior unchanged.
- [ ] Payment/API/Docs remain untouched.

---

## 53. Final Verification Report

Create:

```text
docs/verification-milestone-7b.md
```

Include:

```text
implementation summary
files changed
endpoint(s)
filter semantics
date comparison semantics
checked-depth semantics
pagination model
sorting semantics
migration status
backend tests
frontend tests
lint / format / typecheck
npm audit
production build
Docker health
Alembic head
browser evidence
performance evidence
known limitations
```

Do not claim PASS for commands not actually run.

---

## 54. Important Pre-Implementation Audit

Before coding:

1. inspect M7A analytics service/query layer;
2. inspect existing movement enums and ranking-history behavior;
3. inspect Project Keywords inline-history implementation;
4. inspect pagination conventions;
5. inspect shared filter/table components;
6. inspect current indexes;
7. identify M7A logic that can be reused directly.

Do not duplicate movement calculations into a second incompatible implementation.

Prefer one canonical ranking comparison model.

---

## 55. Final Instruction to Codex

Implement M7B as an extension of M7A.

The key architecture is:

```text
one canonical ranking comparison model
+
server-side exploration
+
checked-depth-aware wording
+
URL-driven filters
+
efficient pagination
```

Do not create an alternative ranking-semantics layer.

Do not change provider execution, billing, usage, scheduling, Payment Gateway, Developer API, or API Docs.

Use fake provider/local fixtures during development and verification.

Do not spend real SERP provider credits during QA.
