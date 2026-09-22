# Milestone 7B Verification — Ranking Explorer

Date: 2026-09-22

## Implementation summary

Milestone 7B adds a Project-scoped Ranking Explorer at:

```text
/app/projects/{projectId}/rankings
```

The page provides server-side keyword search, 7D/30D/90D and custom UTC date
comparisons, movement/position/site/status filters, deterministic sorting,
URL-driven state, server pagination, filtered summaries, and on-demand inline
Ranking History. It reuses the M7A chart and history cache rather than loading
history per result row.

Backend changes are concentrated in the shared analytics repository plus the
new Ranking Explorer route, schema, and service. Frontend changes add the route
and feature module, the Project navigation link, targeted Explorer query
invalidation after terminal Rank Checks, responsive styles, and automated QA.

No provider execution, scheduling, billing, usage accounting, Plan, Payment,
Developer API, or API Docs behavior was changed.

## Endpoint

```text
GET /api/v1/projects/{project_id}/ranking-explorer
```

Supported query parameters:

```text
q
range=7d|30d|90d
compare_from=YYYY-MM-DD
compare_to=YYYY-MM-DD
movement
position_bucket
tracked_site_id
status
sort
order=asc|desc
limit=25|50|100
cursor
```

Stable validation errors include `INVALID_ANALYTICS_RANGE`,
`INVALID_MOVEMENT_FILTER`, `INVALID_STATUS_FILTER`,
`INVALID_POSITION_BUCKET`, `INVALID_SORT_FIELD`, `INVALID_SORT_ORDER`,
`INVALID_DATE_RANGE`, and `INVALID_CURSOR`. Foreign Projects and Tracked Sites
return the same tenant-safe not-found responses as absent resources.

## Comparison and filter semantics

- Only successful persisted Rank Checks for the Project's fixed device are
  comparable. Failed checks are excluded.
- Current is the latest successful observation. For custom dates, it is the
  latest observation through the end of the UTC `compare_to` date.
- A standard range compares with the latest observation at or before its range
  boundary. If unavailable, the earliest later observation other than current
  is used and `comparison_basis` becomes `earliest_in_range`.
- Custom comparison is the latest observation through the end of the UTC
  `compare_from` date. Missing observations remain explicit; dates are never
  swapped or inferred from browser locale.
- Search is trimmed, case-insensitive, partial, server-side, and compatible with
  filters and pagination.
- Rows are scoped to active Keywords and active Tracked Sites owned by the
  current user. Observations predating a Tracked Site are not treated as evidence
  for that site.
- Current status distinguishes `ranked`, `not_found_in_depth`, and
  `never_checked`.

Numeric movement is `comparison_position - current_position`: positive is
improved, negative is declined, and zero is unchanged. Transitions into or out
of stored depth are categorical `entered_checked_depth` and
`left_checked_depth`. `no_previous_data` and `never_checked` also remain
categorical. No categorical state receives a fabricated numeric delta.

The API returns authoritative `effective_depth` and
`supported_position_buckets`. At the current depth of 10 the UI exposes Top 3,
4–10, and Not found in Top 10, and renders Entered/Left Top 10 from that metadata.

## Sorting and pagination

Sorting supports keyword, current position, comparison position, and numeric
change in either direction. Null or categorical values have an explicit stable
placement. Every order then uses normalized keyword, Keyword ID, and Tracked
Site ID as deterministic tie-breaks.

Pagination is server-side with default size 50 and optional sizes 25 and 100.
The opaque URL-safe cursor currently carries a validated offset; the UI exposes
Next and First-page actions, and browser Back returns to the prior cursor URL.
Counts and rows are computed in bounded SQL queries rather than loading all
history into application memory.

The endpoint uses four SQL round trips normally (Project ownership, effective
depth, filtered counts, result page) and one additional ownership lookup when a
Tracked Site filter is supplied. Query count does not grow with the number of
Keywords or result rows. Inline history adds requests only after a Keyword is
expanded.

## Database and migration status

No migration was added. Existing indexes already cover the main access paths:

- `rank_checks(keyword_id, created_at)`;
- `rank_checks(project_id, created_at)`;
- `rank_checks(user_id, created_at)`;
- `rank_checks(status)`;
- `rankings(rank_check_id)`;
- `rankings(tracked_site_id, created_at)`.

The benchmark and bounded-query review did not justify adding an index blindly.
Alembic current and head are both `0009_plan_catalog_audit`; schema invariants
remain covered by the complete backend test suite.

## Automated verification

Commands were run using the repository's Python 3.12 and Node 22 container
toolchains.

| Check | Result |
| --- | --- |
| Backend tests | PASS — 224 passed in 90.60s |
| Ranking Explorer backend tests | PASS — 3 passed |
| Frontend tests | PASS — 102 passed across 20 files |
| Ranking Explorer frontend tests | PASS — 6 passed |
| Ruff lint | PASS |
| Ruff format check | PASS — 172 files formatted |
| mypy strict | PASS — 117 source files |
| ESLint | PASS |
| Prettier check | PASS |
| TypeScript typecheck | PASS |
| npm audit (`--audit-level=high`) | PASS — 0 vulnerabilities |
| Production frontend build | PASS — 21 routes generated, including the Explorer route |
| Docker health | PASS — PostgreSQL, Redis, backend, worker, frontend healthy |
| Alembic | PASS — current/head `0009_plan_catalog_audit` |
| Schema drift | PASS — complete backend invariant suite |

Backend integration coverage includes every movement category, successful-only
observations, missing numeric positions, depth metadata, all depth-10 position
buckets, status/search/site filters, date validation, custom comparisons,
sorting, pagination/cursor validation, and Project/Tracked Site tenant isolation.

Frontend coverage includes URL state, 300 ms search debounce, filter chips,
Clear all, custom UTC dates, sort controls and directions, pagination, local
loading/empty/error/retry states, mobile filter disclosure, a text-link Keyword,
and switching the single expanded inline-history row.

## Browser evidence

The real Chrome journey passed against the production frontend image and live
backend/worker stack. The worker configuration was asserted as `fake` before
creating the one persisted observation used by the history fixture.

- Default 30D Explorer and Project navigation passed.
- Debounced search, removable chips, and Clear all passed.
- Every movement option, every depth-10 position option, Tracked Site, and
  current-status filters passed; categories absent from the focused visual
  fixture produced the filter-aware empty state.
- 7D, 30D, 90D, valid/invalid custom UTC dates, sorting, and server pagination
  passed.
- Shareable query parameters and browser Back/Forward passed.
- Inline Ranking History loaded only after expansion, and switching Keywords
  kept exactly one row expanded.
- Responsive checks passed at 375, 768, 1024, 1280, and 1440 pixels with no
  horizontal page overflow or clipped controls.
- 22 Explorer responses were observed: 21 expected HTTP 200 responses and one
  expected HTTP 422 for the invalid custom date range.
- Browser exceptions: 0; unexpected network failures: 0.
- Real provider credits consumed: 0.

Screenshots are stored in `docs/screenshots/milestone-7b/`. The browser journey
is reproducible with `scripts/verify-ranking-explorer-browser.mjs`.

## Performance evidence

The PostgreSQL integration benchmark seeded 1,000 active Keywords, two
successful observations per Keyword, and two active Tracked Sites (2,000
Explorer rows). Approximate local endpoint timings were:

| Operation | Time |
| --- | ---: |
| Default Explorer | 2,159.63 ms |
| Movement filter | 1,798.74 ms |
| Position filter | 2,085.03 ms |
| Exact narrow keyword search | 24.29 ms |
| Change sort | 2,119.98 ms |
| Next page | 2,141.19 ms |

The benchmark confirms bounded query count and no per-Keyword or per-row query.
The effective-depth lookup was separated from the comparison window, reducing
the initial default benchmark from about 3.28 seconds to about 2.16 seconds on
the local container stack.

## Known limitations

- The cursor is opaque to clients but offset-backed. This keeps the contract
  stable and deterministic for the current scale, while very deep pages may
  eventually warrant keyset cursor fields.
- Browser QA uses a focused persisted fixture, so every detailed movement
  transition and invalid query combination is asserted in PostgreSQL integration
  tests rather than duplicated as visual fixtures.
- Custom date inputs use native date controls with UTC labels; invalid URL date
  combinations are rejected by the API and shown through the local Explorer
  error state.
