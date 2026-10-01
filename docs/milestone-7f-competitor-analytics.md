# Milestone 7F — Competitor Analytics

**Implementation specification for Codex**
**Status:** Proposed; implement after the accepted M7A, M7B, M7C and M7E foundations.
**Scope:** Competitor comparisons using existing successful, persisted SERP observations. No additional SERP requests.

## 1. Objective

Enable a customer to select their own Tracked Site and competitor websites within a Project, then understand their relative organic search positions for the Project's Keywords and SERP environment. Deliver a useful overview, keyword-by-keyword comparison, change-over-time views and drill-down into the underlying observations, while accurately communicating the current **Top 10 collection depth** and data completeness.

The M7F user should be able to answer:

- Which selected competitors appeared in the observed Top 10 for my tracked Keywords?
- For which Keywords did my site rank above/below a competitor in the **same successful check**?
- Which Keywords had competitor visibility but no appearance by my site within the checked depth?
- How did relative rankings change during 7D, 30D or 90D, where historical observations support comparison?
- Which pages/domains were matched, and what observations underlie each comparison?

**Non-goals:** Do not implement keyword discovery, a full market-wide share-of-voice estimate, traffic or click forecasts, search volume, paid ads, backlink analysis, a new crawler, provider-specific capabilities, competitor alerts, email delivery or report integration in M7F. Leave M7E formats unchanged unless a tiny shared regression fix is necessary. No Payment Gateway, Developer API, API Keys or API Docs.

## 2. Repository context and invariants

Preserve the implemented architecture:

- User-only multitenancy: `current_user.id` is authoritative. No Organization/Workspace/Team.
- Project defines the SERP environment (device, location/language and other existing dimensions); Keyword holds the query, not a website.
- Tracked Sites are reusable across Projects for the same User; Domain Aliases match exact hostname first, with only the existing bidirectional `www` fallback. Never collapse arbitrary subdomains.
- M4/M4.1 providers, M5 jobs and Cloud Tasks, M6A quota/subscriptions, M7A comparison semantics, M7B Explorer, M7C Group/Tags and M7E Reports must not regress.
- Only persisted **successful** rank-check observations count. Failed checks are missing evidence, not `not ranked`.
- Analytics GETs and competitor-management operations must neither enqueue new checks nor reserve/commit user usage or consume provider credits.
- Current common checked depth is 10; do not fabricate rankings outside observed depth.

## 3. Mandatory pre-implementation audit (STOP gate)

Before writing migrations or endpoints, inspect the real repository and publish a short audit in the final report:

1. Does `rank_check_results` or another persisted snapshot retain **every organic SERP result** (host/URL, position, title as permitted), or only matches for existing Tracked Sites?
2. Is the snapshot tied immutably to the rank-check time, device, environment and checked depth? Can the source be reconstructed without calling a provider?
3. How are matched site/domain alias IDs stored? Can a previously unknown competitor be matched **retroactively** from historical snapshots?
4. Are the existing M7A/M7B canonical comparison queries operating per Keyword × Tracked Site, and is their current/baseline selection explicitly defined?
5. Does Project already have a configured primary/owned site? Is one Project allowed to compare multiple owned sites? Review existing Tracked Site usage before introducing a competing association.
6. Does the schema retain raw provider responses or URLs with sensitive fields? If yes, expose only approved normalized organic result fields.
7. Inspect current indexes and realistic SQL plans, M7B.1 status, and whether organization filters can be safely reused.

**Implementation decision:**

- **Path A — full normalized organic results persist:** Permit matching newly added competitors against old snapshots, after verifying alias-effective-date semantics and deterministic matching. Document exactly what is and is not backfilled.
- **Path B — only matched Tracked Sites persist:** Build M7F strictly from previously stored match observations. Newly configured competitors have historical `not_observed` until a future already-authorized regular check includes them. If collection needs new normalized organic-result persistence for future checks, add a small versioned migration and populate only future observations from results **already fetched** by existing checks. Do not invent past results, re-call providers, or promise retroactive coverage.
- **Path C — insufficient SERP evidence:** Report the gap and stop broad competitor analytics implementation for confirmation. It is acceptable to ship a clearly labeled existing-site-only subset, but never label missing data `not found in Top 10`.

Do not silently choose Path A. This audit is a release gate.

## 4. Domain model and roles

A Project may select **one primary site** and up to a configurable, product-level number of comparison competitors (proposed initial UI cap: 5; treat it as a configurable non-billing safety limit, not a Plan entitlement). Reuse existing user-owned Tracked Sites; do not create globally shared competitors or tenant-crossing references.

Suggested logical model (adapt names to the existing code):

```text
Project (user-owned, fixed SERP environment)
  ├── Project primary TrackedSite (user-owned)
  └── Project competitor TrackedSites (0–5, user-owned)
        └── Domain Aliases (existing user-global aliases)
```

Recommended persisted association if none already exists:

```text
project_competitor_sites
- project_id
- user_id or verified composite ownership relation
- tracked_site_id
- role: primary | competitor
- created_at
- archived_at nullable
- optional effective_from if temporal membership is needed
```

Enforce same-user associations through service ownership checks and database integrity where the current schema permits. At most one active primary site per Project; prevent duplicate active competitor entries. A competitor cannot simultaneously be the active primary for that Project. Allow a user to configure the same Tracked Site differently in separate Projects without changing its global identity. Deleting/removing a comparison association **does not delete** the site, aliases, Keywords, RankChecks or historical Rankings.

**Temporal caveat:** Current role is a user-selected comparison lens; it is not proof that a site was a competitor historically. Retain the association/audit history needed to reconstruct displayed historical scopes, or label historical results as compared using the **current selection**. Avoid retroactive role assertions.

## 5. Historical domain matching and ambiguity

Apply the existing matching algorithm to normalized hostnames:

1. Exact hostname match.
2. Explicit alias match where valid at observation time, if aliases have effective dates; otherwise state the limitation and do not imply historical ownership certainty.
3. Existing bidirectional `www` fallback only.
4. No suffix matching, eTLD+1 collapse, or automatic wildcard subdomain matching.

If one result URL could match multiple selected sites because of overlapping aliases, use an explicit deterministic policy: preferably reject overlapping active aliases at configuration time where feasible; for historical ambiguity, mark the result `ambiguous_match`, exclude it from head-to-head aggregates and surface the ambiguity for review. Never double-credit a single organic result. Preserve source URL and observed hostname in safe drill-down when available.

## 6. Canonical comparison grain

For a specific Project, each comparison unit is:

```text
Keyword × selected site × one successful RankCheck observation
```

Head-to-head comparisons must use **the same RankCheck ID**, not independently latest observations for each site. This prevents comparing one site's Tuesday position with a competitor's Thursday position and presenting it as one SERP snapshot.

At each successful check, record or derive for each selected site:

```text
ranked(position, matched_url, matched_hostname)
not_found_in_checked_depth(depth)
not_observed (insufficient persisted coverage)
ambiguous_match
```

A successful checked-depth snapshot that contains complete organic results and no match supports `not_found_in_checked_depth`. Missing result rows or a partial old snapshot **do not** support that status.

A check that yielded no organic results because of an API anomaly must remain invalid/insufficient, not a blanket competitor absence. Define how a valid zero-results SERP is distinguished, if the persistence model supports it.

If multiple pages from the same site occur within one check, the site's primary rank for that check is its **best (lowest) observed organic position**. A separate drill-down may show all matched URLs; do not count multiple URLs as multiple Keywords.

## 7. Metrics and honest terminology

For a given period/selected filters, use a clearly documented observation cohort. Default current snapshot for each Keyword is the **latest successful Project check** at or before `as_of`; derive all selected sites from that same check. If a site lacks reliable coverage in that check, mark `not_observed` and exclude it from direct rank comparisons.

Required metrics:

- **Keywords observed:** distinct active Keywords with at least one qualifying successful check in the selected scope.
- **Top 3 / Top 10 appearances:** distinct Keywords per site with best observed position in the corresponding bucket, with actual checked-depth metadata.
- **Not found in Top 10:** only when depth >= 10 and full available evidence proves no site match in the checked Top 10; use checked-depth-specific wording at other depths.
- **Head-to-head wins/ties/losses:** paired comparable Keywords at the same successful check where **both sites have numeric ranks**. Lower position wins. Display the denominator and excluded counts. Do not treat non-appearance as a numeric loss.
- **Visibility coverage:** `Keywords where site appears in the observed Top N / comparable observed Keywords × 100`. Label it **Observed Top-N coverage**, never Google market share or traffic share. Show N and sample denominator; do not claim search-volume weighting.
- **Keyword opportunities:** my site `not_found_in_checked_depth` while a selected competitor is numerically ranked in that **same complete** snapshot. Distinguish these from cases where my site was never observed.
- **Position gap:** `competitor_position - my_position` for pairs with two numeric ranks; positive means my site has a better numeric position. Never impute non-appearance to N+1.

M7F should avoid a generic “Visibility Score” formula unless there is an explicitly documented, named, unweighted formula with its denominator and dataset limitations. Do not imply broader SEO visibility, market share or estimated traffic.

## 8. Scope and filters

Use the Project's fixed device/environment. Filter by:

```text
primary tracked site
1–5 selected competitor tracked sites
range = 7d | 30d | 90d (default 30d)
optional custom UTC start/end if existing M7B date control can be reused
keyword search
Group / Tags ANY|ALL (reuse M7C canonical predicates)
comparison state: all | both_ranked | my_site_ahead | competitor_ahead | tied
opportunity state: competitor_in_top_n_my_site_not_found
```

Ensure that Group/Tag filters apply to the same active Keyword cohort across all sites. Never compare two sites using different filtered Keyword sets without prominently showing the difference.

## 9. Backend API design

Prefer a Project-scoped backend service/repository layer that reuses existing M7A/M7B rank-check window selection and M7C organization predicates. Suggested API routes (adapt to current conventions):

```text
GET    /api/v1/projects/{project_id}/competitor-sites
PUT    /api/v1/projects/{project_id}/competitor-sites
GET    /api/v1/projects/{project_id}/competitors/overview
GET    /api/v1/projects/{project_id}/competitors/keywords
GET    /api/v1/projects/{project_id}/competitors/trends
GET    /api/v1/projects/{project_id}/competitors/keywords/{keyword_id}/observations
```

`PUT` should atomically replace Project selection (primary plus bounded competitors) with optimistic concurrency if that is the repository's pattern. All selected `tracked_site_id` values must be owned by the signed-in User, and all aliases must belong to the corresponding sites.

Query parameters on analytical endpoints should use the same canonical filter validation, date semantics and stable errors as M7A–M7C. Keyword result tables must be server-paginated (default 50; 25/50/100 according to current conventions), with stable sorting and deterministic ties. Avoid unbounded history responses.

Illustrative overview payload:

```json
{
  "project_id": "...",
  "device": "desktop",
  "range": "30d",
  "as_of": "2026-09-27T00:00:00Z",
  "effective_depth": 10,
  "keyword_cohort": 420,
  "qualifying_keywords": 400,
  "partial_or_unobserved_keywords": 20,
  "primary_site": {"tracked_site_id": "...", "name": "My Site"},
  "sites": [
    {"tracked_site_id": "...", "name": "My Site", "top_3": 30, "top_10": 85, "observed_top_n_coverage_pct": 21.25},
    {"tracked_site_id": "...", "name": "Competitor A", "top_3": 42, "top_10": 110, "observed_top_n_coverage_pct": 27.5}
  ],
  "comparison": {
    "opponent_site_id": "...",
    "both_numeric_ranked": 52,
    "primary_ahead": 18,
    "tied": 2,
    "competitor_ahead": 32,
    "excluded_unpaired": 348
  }
}
```

Illustrative values are **examples only**; calculate real denominators from stored data. Return relevant `coverage_quality` / `insufficient_data` metadata, rather than making clients infer completeness from nulls.

## 10. Overview UX

Preferred route:

```text
/app/projects/{projectId}/competitors
```

Add a lightweight Project navigation item `Competitors`. Initial empty state prompts user to select one owned primary site and up to five owned competitor sites. Do not silently designate a competitor using another customer's data or assign competitors based on SERP positions.

Recommended hierarchy:

```text
Project Header
Competitors
Primary site [select]   Compare with [multi-select up to 5]
Date range [7D] [30D] [90D]  [Group] [Tags]
Data coverage notice / as-of timestamp / checked depth
Comparison KPI cards
Site coverage chart
Head-to-head table
Keyword opportunities
Comparison keyword table
```

For multiple selected competitors, present a separate head-to-head summary **per competitor**, not one pooled win/loss count. Use the existing light-first design system, shared `PageHeader`, `Card`, `TextLink`, `Skeleton`, `EmptyState`, `ErrorState`, responsive tables and semantic badges. Keep primary CTAs for primary actions only.

## 11. Comparison table and drill-down

Columns:

```text
Keyword | My Site | Competitor A | Competitor B ... | Position Gap | Status
```

For more than two competitor columns, use a mobile-friendly competitor selector or responsive stacked row, not overflowing fixed-width tables.

Cell states:

```text
#3
Not found in Top 10
No comparable observation
Ambiguous match
```

When multiple competitors are selected, Position Gap and status should be per selected opponent (or show these only after selecting one opponent). Do not display one ambiguous aggregate gap.

Click a Keyword name (text link) to expand inline detail directly below the row. Show the exact `RankCheck` timestamp, environment, checked depth, matched URLs/hostnames if persisted, source status for each selected site and a link to the existing M7A ranking history. Do not fetch the full history for every table row.

## 12. Opportunity view

Surface the Keywords where at least one selected competitor appears in Top N while the primary site is **confirmed absent within the same checked depth**, sorted by competitor's best observed position then Keyword. Default N = actual observed depth (usually Top 10); do not imply that absence means the primary site is globally unranked.

No invented search volume, conversion potential or automated SEO recommendation. Opportunity is strictly an observed SERP comparison, not a forecast of business impact.

## 13. Trends and time series

Trend charts use real successful observation dates and a consistent Keyword cohort/denominator. Prefer a time series of **Observed Top-N coverage** per selected site rather than average position that treats non-appearances as numeric values.

- Range: 7D / 30D / 90D; UTC day buckets by default, or reuse the Project timezone if already explicit.
- Per Keyword, use latest qualifying successful observation per day; all site positions derived from the **same** observation.
- Never interpolate missing days as observations; visualize gaps clearly.
- Show coverage denominator per point and note if the observed Keyword cohort varies across dates.
- Do not connect an incomplete day's snapshot to a complete day without a visible coverage warning.
- Default to line chart plus accessible table. Position 1 is visually above position 10 in any per-Keyword rank chart.

If existing storage cannot establish complete same-check coverage for historical dates, restrict trends to supported observations or show `insufficient_data`. Do not plot invented backfill.

## 14. Matching and data lineage

Every analytical number must be traceable to a successful rank-check observation and its checked-depth metadata. Prefer immutable rank-check snapshots for historical charts; do not reclassify old checks from current mutable aliases without recording/displaying that the view is a recomputation. If a site is added later and historical raw observations exist, backfill derived matches only via a controlled idempotent **local database computation**, preserving provenance and auditability. Never call SERP providers to backfill without a separate explicit product decision.

## 15. Performance and pagination

M7B's general Explorer previously measured around 1.5–2.2 seconds for a local 1,000-Keyword fixture; M7B.1 may still be pending. Do not use M7F as a reason to duplicate the expensive canonical comparison CTE for every competitor or every displayed row.

Required:

- SQL set-based queries or bounded batch queries; no N+1 per Keyword or competitor.
- Performance fixture: at least 1,000 active Keywords, two or more observations per Keyword, 1 primary + 3 competitors, 10 Groups and 20 Tags where supported.
- Measure overview, head-to-head, opportunities, trends, filtered table, next page and single Keyword drill-down; capture query count and approximate local latency.
- Inspect `EXPLAIN (ANALYZE, BUFFERS)` for representative heavy queries where feasible. Any new index must have a documented query justification and reversible migration.
- Paginate comparison rows server-side. Fetch per-Keyword details only when expanded.
- Limit competitor count and chart point cardinality on the server.
- If cross-competitor query performance is unacceptable, optimize or clearly isolate the blocker; do not claim M7F meets the performance guardrail based only on tests passing.

## 16. Database migration

Inspect Alembic head first (M7E verification reported `0011_reports`; other work may have advanced it). If project-site role associations or future normalized organic-result fields are needed, add a migration **on the actual current head**; do not hard-code a revision number in advance.

Requirements:

- User/project/site referential integrity where possible.
- Unique active primary per Project and unique active `(project, tracked_site)` selection.
- Reversible upgrade/downgrade verified against a disposable database.
- No destructive alteration of historical Keywords, RankChecks, Rankings, M7E Reports or subscription state.
- Historical missing observations are never backfilled with guesses.
- Preserve current domain-alias data and its documented matching semantics.

## 17. Security and authorization

- All routes use authentication and tenant-safe Project lookup.
- Project and all selected Tracked Sites must belong to `current_user.id`.
- Cross-tenant IDs return not-found without existence leakage; include tests for both selection and analytics routes.
- Enforce server-side competitor count and valid normalized hostname/alias rules.
- If URLs are rendered in drill-down, sanitize them; avoid rendering arbitrary HTML from provider titles/snippets.
- Do not expose raw provider response bodies, credentials, internal costs, stored email addresses of third parties, or other tenants' analytics.
- User-supplied comparison filters must not alter query ownership scopes.
- Admin permissions do not bypass ownership for normal customer endpoints.

## 18. API, caching and invalidation

Use TanStack Query with keys including Project, selected site IDs, date range and organization filters. Suggested domains:

```text
competitors.selection(projectId)
competitors.overview(projectId, params)
competitors.keywords(projectId, params)
competitors.trends(projectId, params)
competitors.observations(projectId, keywordId, params)
```

Persist filter state in shareable URL query parameters, excluding secrets. Use debounce for Keyword search. Invalidate relevant competitor views when an authorized rank check completes or selection changes; do not invalidate Billing or Admin. Never refetch provider data as part of frontend navigation.

## 19. Empty, partial, error and responsive states

Distinct UI states:

1. No primary site selected.
2. No competitor selected.
3. No successful checks yet.
4. Competitor selected but not historically observed under **Path B**.
5. Current filtered cohort empty.
6. Partial/incomplete snapshot coverage.
7. API error with local retry.
8. Multiple matched pages for one site.
9. Ambiguous alias conflict.

Use precise explanations and recommended next actions. Do not merge `not_observed` and `not_found_in_checked_depth` into one badge. Test viewports 375, 768, 1024, 1280 and 1440 px. Ensure no horizontal **page** overflow, keyboard-accessible selectors, focus states, adequate contrast, accessible chart table, and non-color-only win/loss indicators.

## 20. Billing and schedule boundaries

No new billing Plan entitlements in M7F; the 5-competitor limit is an initial UI/API safety constraint only. Do not introduce competitor-specific keyword checks or optional paid add-ons in this milestone. Scheduled checks retain their current cadence. Existing resource limits remain authoritative. Merely adding an existing Tracked Site as a competitor must not consume ranking-check quota.

## 21. Backend test matrix

Use deterministic PostgreSQL integration tests, not mocks alone:

- User A cannot select User B's site or access User B's Project/analytics.
- At most one primary and no duplicate active competitor within a Project.
- Add/remove competitor without deleting shared Tracked Site, aliases or historical rankings.
- Site roles independent between two Projects.
- Same successful RankCheck used for every site's head-to-head pair.
- One site checked Tuesday and another Thursday cannot be paired as a single observation.
- Two URLs from the same site yield one best-position presence per Keyword/check.
- Exact alias, `www` fallback and no arbitrary subdomain collapse.
- Overlapping aliases never double-credit an organic result.
- Top-10 absence vs not-observed, failed check vs valid checked-depth absence.
- Historical competitor added later: test the actual audited storage Path A/B/C.
- Top 3 / Top 10 counts and denominator reconciliation.
- Numeric wins/losses/ties; categorical non-appearance excluded from numeric pair counts.
- Opponent-specific opportunity results.
- Group/Tag ANY/ALL consistent across sites.
- UTC ranges and missing-date gaps.
- Pagination, deterministic sorting, malformed IDs and invalid filters.
- No new provider calls, RankCheckJobs, usage reservations or report email sends.
- Migration round-trip, metadata consistency and legacy data preservation.

## 22. Frontend and real-browser verification

Add component tests for initial setup, competitor selection, top-N charts, opportunity states, no-data/partial-data warnings, filter URL behavior, pagination and inline drill-down.

With an explicitly verified fake provider and local task adapter, execute an authenticated production-build browser journey:

```text
create Project / primary site / 3 competitor sites
seed deterministic same-check organic observations
configure competitor selection
check overview Top 3/Top 10 and coverage denominator
compare one numeric win / one numeric loss / one tie
verify opponent-specific opportunity
filter Group and Tags ANY/ALL
switch 7D / 30D / 90D
open one Keyword row, close it, open another
refresh URL and browser Back/Forward
check no-data, not-observed, error and partial-data states
verify 375 / 768 / 1024 / 1280 / 1440 px
```

Seed snapshots directly in test fixtures if fake provider does not naturally produce multi-domain controlled results. **Do not issue manual checks against real Serper/SerpApi**. Assert effective provider configuration both on backend and worker before browser tests. Report real external requests as an incident if any occur.

## 23. Verification and acceptance

Produce `docs/verification-milestone-7f.md` with:

- Exact pre-implementation persistence audit and selected Path A/B/C.
- Actual routes, models, migration and changed files.
- Canonical same-check pairing and matching semantics.
- Honest checked-depth and observation-completeness semantics.
- Exact definitions/denominators for coverage and head-to-head metrics.
- Backend test counts, frontend test counts, Ruff, mypy, ESLint, Prettier, TypeScript, npm audit, production build, Docker health, Alembic upgrade/downgrade/drift.
- Browser journey outcomes and screenshots at all five viewports.
- Query-count and latency table for 1,000 Keywords × 4 selected sites and the SQL-plan findings.
- Zero real provider usage evidence; any exception disclosed.
- Known limitations, especially existing snapshots missing organic data, alias history certainty, incomplete checked depths, and production-only services not tested.

**Do not claim PASS for commands, cloud integrations or browser journeys that were not executed.**

## 24. Definition of Done

- [ ] Persistence evidence audit completed before implementation; Path A/B/C documented.
- [ ] Project-scoped primary/competitor site selection is tenant-safe and durable.
- [ ] Same-check competitor comparison is canonical and used throughout.
- [ ] No `not_observed` state is silently interpreted as a checked-depth absence.
- [ ] Overview Top-N coverage and head-to-head denominators reconcile.
- [ ] Opponent-specific Keyword opportunities available.
- [ ] Group/Tag filters, date ranges, search, sorting and pagination work.
- [ ] Competitor trends show only real observations and coverage-quality metadata.
- [ ] Keyword drill-down is on demand, contextual and accessible.
- [ ] Mobile/responsive and browser verification executed.
- [ ] No RankCheck scheduling/billing/provider behavior changed.
- [ ] Existing M7A–M7E regressions pass.
- [ ] Performance guardrail measured; no N+1 behavior.
- [ ] Migration round-trip and schema invariant checks pass where applicable.
- [ ] Verification report records actual evidence and limitations.

## 25. Final instruction to Codex

Before editing code, inspect existing models and sample persisted organic-result data. **Do not assume the database holds all Top 10 competitor domains merely because the provider returned them during a check.** Make the persistence-path decision explicit; do not invent historical competitors or spend provider credits for backfill. Reuse M7A/M7B comparison logic and M7C organization predicates, preserve M7E Reports, and implement the smallest coherent tenant-safe Competitor Analytics slice supported by actual stored evidence.
