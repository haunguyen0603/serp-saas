# Milestone 7A Verification — Ranking Dashboard & Core Analytics

Date: 2026-09-22

## Implementation

Added tenant-safe, read-only analytics endpoints:

- `GET /api/v1/projects/{project_id}/analytics/summary`
- `GET /api/v1/projects/{project_id}/analytics/distribution`
- `GET /api/v1/projects/{project_id}/analytics/movers`
- `GET /api/v1/projects/{project_id}/keywords/{keyword_id}/ranking-history`

The repository uses successful persisted RankChecks only. Summary and movers use
bounded SQL window/aggregation queries. Keyword chart history uses the latest
successful observation per UTC calendar day and does not interpolate missing
dates.

No migration was added. The existing schema contains all required data and the
current indexes cover the initial M7A query paths.

## Semantics

- The Project's fixed device is the analytics device scope. A mismatched device
  returns `INVALID_DEVICE_SCOPE`.
- Current is the latest successful observation.
- Comparison is the latest successful observation at or before the selected
  range boundary. If absent, the earliest successful observation inside the range
  is used and `comparison_basis` reports `earliest_in_range`.
- Numeric positions classify as improved, declined, or unchanged.
- Entering/leaving the checked depth remains categorical and is not included in
  numeric winner/loser ordering.
- A Keyword without a comparable observation is `no_previous_data`.
- The movement counts reconcile to active `total_keywords`; never-checked
  Keywords are explicitly reported in `never_checked` and count as
  `no_previous_data`.
- Current persistence defaults to depth 10. The UI therefore renders Top 3,
  4–10, and Not found in Top 10. It does not claim Top 20/Top 100.
- No fake numeric position is created for not-found observations.

## Automated verification

Commands were run against Python 3.12 and Node 22 containers where the host
runtime did not match the repository engines.

| Check | Result |
| --- | --- |
| Backend tests | PASS — 221 passed in 58.17s |
| Frontend tests | PASS — 96 passed across 19 files |
| Ruff lint | PASS |
| Ruff format check | PASS — 168 files formatted |
| mypy strict | PASS — 114 source files |
| ESLint | PASS |
| Prettier check | PASS |
| TypeScript typecheck | PASS |
| npm audit (`--omit=dev`) | PASS — 0 vulnerabilities |
| Production frontend build | PASS — 21 routes generated |
| Docker health | PASS — PostgreSQL, Redis, backend, worker, frontend healthy |
| Alembic | PASS — current/head `0009_plan_catalog_audit` |
| Schema drift | PASS — covered by the full backend invariant suite |

## Browser evidence

The real-browser ranking journey passed using the fake provider with:

- responsive checks at 375, 768, 1024, 1280, and 1440 pixels;
- the analytics-enabled Project Detail page;
- inline history and the chart container;
- no browser exceptions;
- no unexpected network failures;
- zero real provider credits in the successful verification run.

The first browser attempt inherited the developer `.env` provider selection and
performed one manual Serper rank check before timing out on its deterministic
fixture assertion. Analytics GET requests did not cause that provider call. The
backend and worker were then explicitly restarted with the fake provider before
the successful run. This incident consumed one real Serper request and is
recorded here for transparency.

## Performance evidence

The focused integration benchmark seeded 1,000 active Keywords with two
successful observations each in an isolated PostgreSQL schema:

- summary: approximately 93.83 ms;
- movers (10 winners and 10 losers maximum): approximately 450.40 ms.

The frontend issues one summary request and one movers request, and fetches a
single Keyword history series only when its inline history is expanded.

## Known limitations

- The SVG chart intentionally uses native browser tooltips and an accessible
  text equivalent instead of introducing another chart dependency.
- Browser automation covered empty/observed Project states, range controls,
  responsive layout, and inline history. Detailed winner/loser/entered/left
  semantics are covered by the PostgreSQL integration tests rather than separate
  visual fixtures.
