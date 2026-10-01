# Milestone 7F — Competitor Analytics verification

Verified on 2026-09-27 in the local PostgreSQL/Docker environment.

## Pre-implementation persistence audit and decision

The audit was completed before the migration or endpoints were written.

1. `rank_check_results` stores every normalized organic result returned within the bounded check: position, URL, hostname, title, displayed URL and snippet. `rankings` stores only matches for sites known at check time. The provider's raw response is not required or exposed by M7F.
2. `rank_checks` stores the query, Project SERP environment, checked depth, status and request/completion times. Successful checks can be compared from persisted data without contacting a provider. A zero-row or incomplete result set does not prove a site was absent.
3. The existing `tracked_domains` registry owns primary domains and aliases per User. A newly selected competitor can be matched retroactively against stored organic hostnames. Aliases have no effective-date history, so this is explicitly a recomputation using **current active aliases**, not proof of historical ownership.
4. M7A/M7B select successful observations per Keyword and Tracked Site with explicit current/baseline rules. M7F instead selects one latest successful `RankCheck` per Keyword in the selected window, then derives every selected site's position from that **same check ID**. M7B.1 remains pending.
5. Project had no configured primary-site association. Tracked Sites are reusable across the User's Projects, so M7F adds a Project-scoped selection without changing their global identity.
6. Only approved normalized URL/hostname/title/position fields reach the drill-down. Provider metadata, raw payloads, credentials, snippets and untrusted HTML are not rendered. HTTP(S) URLs are validated before rendering as links.
7. Existing rank-check indexes were inspected. The added composite window index and the 1,000-Keyword SQL plan are documented below. Group/Tag filters reuse the active-Keyword and Project-scoped assignment predicates.

**Path A** was selected. Historical results are derived on demand from full normalized organic snapshots. No historical RankCheck or Ranking row is rewritten, and no provider backfill is performed. Responses expose `selection_basis=current_selection` and `historical_alias_semantics=current_active_aliases`.

## Implementation

Migration `0012_competitor_analytics` follows the actual `0011_reports` head. It adds `project_competitor_sites`, composite Project/User and Site/User foreign keys, active-site and single-primary unique indexes, stable display order, archival history, and `ix_rank_checks_competitor_window`. Removing a selection archives only that association. The migration is reversible.

The backend implementation is in `app/models/project_competitor_site.py`, `app/repositories/competitor_analytics.py`, `app/services/competitor_analytics.py`, `app/schemas/competitor_analytics.py`, and `app/api/v1/competitor_analytics.py`. The router and dependency are wired into the existing API. The frontend route `/app/projects/{projectId}/competitors` is linked from Project navigation and implemented in `features/competitors/`.

Authenticated routes:

```text
GET  /api/v1/projects/{project_id}/competitor-sites
PUT  /api/v1/projects/{project_id}/competitor-sites
GET  /api/v1/projects/{project_id}/competitors/overview
GET  /api/v1/projects/{project_id}/competitors/keywords
GET  /api/v1/projects/{project_id}/competitors/trends
GET  /api/v1/projects/{project_id}/competitors/keywords/{keyword_id}/observations
```

The selection requires one active User-owned primary site and allows up to five distinct User-owned competitors. The API checks Project ownership before reading or changing a selection. A competitor can be selected independently in another Project.

## Comparison and completeness rules

- The overview/table use the latest successful check per active Keyword within the chosen UTC range and current Project environment. Trends use the latest successful check per Keyword per real UTC day. Failed checks are excluded; missing dates are not interpolated.
- Exact hostname/active-alias matching wins over the existing bidirectional `www` fallback. Arbitrary subdomains are not collapsed. A result with equally preferred matches for different selected sites is marked ambiguous and is not double-credited.
- Multiple matching pages for one site count once at the best (lowest) position. Drill-down lists all safe matched pages, the check timestamp, environment, depth and observation state.
- `ranked` requires an observed matching result. `not_found_in_checked_depth` requires a complete persisted result set (`row count >= depth` and maximum position `>= depth`) with no match. Partial/zero-row snapshots instead produce `not_observed`; ambiguous matches have their own state.
- `keyword_cohort` counts active filtered Keywords; `qualifying_keywords` counts those with a qualifying successful check. Top-3 and observed Top-N counts are distinct Keywords per site. `observed_top_n_coverage_pct = top_n / comparable_keywords * 100`, where comparable means `ranked` or evidence-backed `not_found_in_checked_depth`. N is capped by actual checked depth, normally 10. This is unweighted observed coverage, not market share or traffic.
- Head-to-head uses only pairs with two numeric positions in the same check. `primary_ahead + tied + competitor_ahead = both_numeric_ranked`; the remaining qualifying Keywords are `excluded_unpaired`. Position gap is competitor minus primary. An opportunity requires the primary to be confirmed absent and the selected opponent to have a numeric Top-N rank in that same complete snapshot.
- The keyword API validates range, Group, Tags ANY/ALL, selected opponent, comparison state, opportunity, sort/order, and 25/50/100-row cursor pagination. The UI keeps filters in the URL and fetches drill-down only when a row opens.

## Automated verification

| Check | Result |
| --- | --- |
| Backend Ruff check and format check | Pass |
| Backend mypy | Pass, 136 source files |
| Backend PostgreSQL pytest suite | **245 passed** in 163.92 s |
| Frontend TypeScript, ESLint, Prettier | Pass |
| Frontend Vitest suite | **109 passed** across 22 files |
| `npm audit --audit-level=high` | 0 vulnerabilities |
| Next.js production build | Pass; competitor route emitted |
| Alembic upgrade/downgrade and migration suite | Pass; local 0012 downgrade to 0011 and upgrade to 0012, disposable migration tests included in pytest |
| `alembic check` | No new upgrade operations detected |
| Docker health | backend, worker, frontend, PostgreSQL and Redis healthy |

The existing Rankings component tests print React Query warnings because unrelated background-query mocks return `undefined`. All tests pass.

### Performance guardrail

The PostgreSQL integration fixture has 1,000 active Keywords, two successful observations per Keyword, one primary plus three competitors, 10 Groups and 20 Tags. The measured local request totals include service and HTTP test-client work; timings vary by machine.

| Operation | Approx. latency | SQL queries |
| --- | ---: | ---: |
| Overview, including per-opponent head-to-head | 545 ms | 6 |
| Keyword table, first page | 276 ms | 5 |
| Next page | 388 ms | 5 |
| Opportunities | 348 ms | 5 |
| Group/Tag filtered table | 34 ms | 7 |
| Trends | 388 ms | 5 |
| One Keyword drill-down | 18 ms | 8 |

Query count is bounded independently of Keyword/competitor count. Representative `EXPLAIN (ANALYZE, BUFFERS)` over 2,000 checks used an Index Only Scan on `ix_rank_checks_competitor_window` followed by incremental sort; execution time was about 1.05 ms (the query had 2,000 heap fetches in the fresh fixture). The index supports the Project/User/successful-check window lookup and is dropped by the downgrade.

## Authenticated production-build browser journey

Backend and worker both reported `fake fake fake local disabled` for provider, enabled providers, fixed provider, task queue and email adapter. Five Keywords received deterministic same-check normalized organic snapshots on four UTC days. The journey verified login, selection and overview denominators, one numeric primary win and loss, opponent-specific opportunity, partial evidence, multiple matched pages, 7/30/90-day switches, Group/Tag ANY/ALL controls, URL state, no-match search, Back/Forward, refresh, two row drill-downs, and an injected 503 with Retry recovery.

At 375, 768, 1024, 1280 and 1440 px, `documentElement.scrollWidth` equaled the viewport width. Screenshots: [375 px](verification-artifacts/milestone-7f/competitors-375.png), [768 px](verification-artifacts/milestone-7f/competitors-768.png), [1024 px](verification-artifacts/milestone-7f/competitors-1024.png), [1280 px](verification-artifacts/milestone-7f/competitors-1280.png), [1440 px](verification-artifacts/milestone-7f/competitors-1440.png). No unexpected 5xx or browser page errors occurred. An unauthenticated refresh attempt returned the expected 401 before login; one 503 was deliberately injected to test Retry.

The browser fixture has 20 successful checks with total `provider_request_count=0` and zero `rank_check_jobs`; no real Serper/SerpApi request was made. Browser QA used no report email. The temporary QA account and fixture remain in the local database for manual inspection; no credential is stored in the repository.

## Limits and unexecuted checks

- Aliases have no effective dates; retroactive matching reflects their current active state. Existing historical snapshots with fewer than the checked-depth rows remain `not_observed` when no match is present. A valid zero-result SERP cannot be distinguished from a collection anomaly by the current persistence model, so it is never treated as confirmed absence.
- A numeric tie is structurally unavailable for two different sites in one valid SERP snapshot because `(rank_check_id, position)` is unique and one organic result is credited to at most one site. The tie branch is retained for defensive reconciliation, but no real browser tie was fabricated.
- Browser QA did not exercise production Cloud Tasks, live SERP providers, external SMTP, or cloud report storage. M7B.1 optimization remains separate.
