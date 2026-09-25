# Milestone 7C — Keyword Organization

**Implementation specification for Codex**
**Project:** SERP SaaS
**Depends on:** M7A Core Analytics and M7B Ranking Explorer
**Excluded:** Payment Gateway, Developer API, API Docs

## 1. Objective

Enable customers to organize hundreds or thousands of tracked Keywords within each Project using **Groups**, **Tags**, and **safe bulk operations**, then explore ranking performance for those subsets without duplicating ranking logic or consuming additional SERP credits.

Deliver:

1. Project-scoped Keyword Groups (one optional Group per Keyword).
2. Project-scoped Keyword Tags (multiple Tags per Keyword).
3. Keyword table organization, filters, badges and bulk editing.
4. Bulk archive, restore and existing supported status actions, implemented transactionally.
5. Group/Tag filtering in M7B Ranking Explorer.
6. Lightweight Group/Tag ranking summaries using existing M7A comparison and checked-depth semantics.
7. Responsive UX, tenant isolation, migration, tests, browser QA and performance verification.

**Do not implement M7B.1 performance optimization implicitly in this milestone.** First inspect whether the separate M7B.1 work has been completed. If not, record the status; M7C must avoid making the approximately two-second M7B benchmark worse. Any change to the existing Explorer query should be measured against its own baseline.

---

## 2. Existing Product Boundaries

Preserve the established stack and conventions:

- Next.js App Router, TypeScript, TanStack Query and the M6.5 design system.
- FastAPI, Pydantic 2, async SQLAlchemy 2, PostgreSQL, Alembic.
- User-only tenancy: no Organizations, Teams, Workspaces or Memberships.
- Project defines SERP environment/device; Keyword remains a search-query entity, not a website.
- Tracked Sites and Domain Aliases are user-scoped and independent of Groups/Tags.
- RankChecks, Ranking History, M7A Analytics and M7B Explorer already exist.
- Billing/usage, rank-check queue, scheduler, provider routing and entitlement enforcement must remain authoritative and unchanged except for necessary integration with keyword archive/restore semantics.

Before coding, inspect actual repository models, endpoints, pagination conventions, archive semantics, analytics query layer, migration head and existing shared UI primitives. Adapt names and file paths to the repository; do not build a parallel architecture.

---

## 3. Domain Model and Scope

```text
User
├── Projects
│   ├── Keywords
│   │   ├── optional Keyword Group (0..1)
│   │   └── Keyword Tags (0..N)
│   ├── Keyword Groups
│   └── Keyword Tags
└── Tracked Sites
    └── Domain Aliases
```

**Group:** a mutually exclusive, optional category inside a Project (e.g., `Brand`, `Product`, `Blog`). A Keyword can have **at most one** Group in that Project.

**Tag:** a flexible label inside a Project (e.g., `High priority`, `Commercial`, `Seasonal`). A Keyword can have multiple Tags, and a Tag can belong to multiple Keywords in the same Project.

All Groups and Tags belong to **exactly one Project**. Their IDs cannot be attached to Keywords in other Projects even when the same user owns both Projects. No global user-level Group/Tag catalog in M7C.

---

## 4. Data Model

Use repository naming conventions; suggested tables:

```text
keyword_groups
- id UUID PK
- project_id UUID NOT NULL FK projects(id)
- name VARCHAR(80) NOT NULL
- normalized_name VARCHAR(80) NOT NULL
- created_at
- updated_at
- UNIQUE(project_id, normalized_name)

keyword_tags
- id UUID PK
- project_id UUID NOT NULL FK projects(id)
- name VARCHAR(40) NOT NULL
- normalized_name VARCHAR(40) NOT NULL
- optional predefined semantic color token (not arbitrary client CSS)
- created_at
- updated_at
- UNIQUE(project_id, normalized_name)

keyword_tag_assignments
- keyword_id UUID NOT NULL FK keywords(id)
- tag_id UUID NOT NULL FK keyword_tags(id)
- created_at
- PRIMARY KEY(keyword_id, tag_id)

keywords
- add nullable keyword_group_id UUID FK keyword_groups(id)
```

Enforce **same-project referential integrity** for Group and Tag assignments. Prefer database-backed composite constraints/keys where practical; at minimum enforce it transactionally in the service and cover cross-project races and direct-invalid-assignment tests. Check actual existing schema before choosing composite FKs or migrations; never assume suggested column names already exist.

Normalize uniqueness using `trim + Unicode-aware case folding` or a repository-supported equivalent. Preserve user-entered display capitalization. Reject blank names after normalization. Clearly document any Unicode/database collation limitations and test case/whitespace duplicates.

Indexes should support Project listing, Group membership and Tag joins. Avoid duplicate indexes already supplied by FK/unique constraints. No materialized analytics tables in M7C.

### Deletion policy

- **Delete Group:** only delete the grouping entity and set its member Keywords' Group to `NULL`; never delete Keywords or their ranking history.
- **Delete Tag:** remove its assignments and the Tag; never delete Keywords or rankings.
- Prevent cross-Project cascade side effects.
- Existing archived Keywords retain their Group/Tag assignments so restoring them restores their organization, unless current archive semantics explicitly require otherwise.

---

## 5. Group and Tag CRUD

Suggested Project-scoped APIs under `/api/v1/projects/{project_id}`:

```http
GET    /keyword-groups
POST   /keyword-groups
PATCH  /keyword-groups/{group_id}
DELETE /keyword-groups/{group_id}

GET    /keyword-tags
POST   /keyword-tags
PATCH  /keyword-tags/{tag_id}
DELETE /keyword-tags/{tag_id}
```

Return Group/Tag ID, name and Keyword count (at least active count; state its definition), with stable ordering by normalized name then ID. Follow existing API pagination conventions if catalogs can be large. Group/Tag creation and rename must check uniqueness case-insensitively within the Project. Do not silently merge same-name entities.

If deleting a Group or Tag with assignments, require explicit confirmation in the UI showing the affected Keyword count. Backend deletion remains atomic. Use existing error structure for `GROUP_NOT_FOUND`, `TAG_NOT_FOUND`, `DUPLICATE_GROUP`, `DUPLICATE_TAG`, `CROSS_PROJECT_ASSIGNMENT` or equivalent established names. Non-owned Projects and foreign IDs must receive tenant-safe responses.

---

## 6. Individual Keyword Organization

Extend existing Keyword create/edit/detail flows with:

```text
Group: optional single selection
Tags: zero or more selections
```

Do not change keyword text, query normalization, ranking matching or Project/device settings. Organization metadata can be edited without creating a RankCheck, restarting a schedule, reserving usage or altering history.

Recommended edit payload:

```json
{
  "group_id": "<uuid-or-null>",
  "tag_ids": ["<uuid>", "<uuid>"]
}
```

Support explicit replace-set semantics for `tag_ids`; document whether omitted fields mean unchanged. Validate all references in one transaction before any mutation. Do not accept `user_id` or organization identifiers from the client.

---

## 7. Bulk Operations

Support selecting multiple Keywords from the current Project and applying **one explicit operation at a time**:

- Assign Group, including `No Group`.
- Add selected Tags without removing other Tags.
- Remove selected Tags without changing unrelated Tags.
- Replace all Tags only when the UI explicitly labels the action as destructive/replacing.
- Archive selected Keywords.
- Restore selected Keywords, if the repository already supports restoration safely.

Do not invent irreversible hard-delete behavior; use current archive semantics. If current Keyword status transitions have additional allowed bulk operations, reuse their service methods instead of duplicating state transitions.

Suggested endpoint:

```http
POST /api/v1/projects/{project_id}/keywords/bulk-organize
```

Example:

```json
{
  "keyword_ids": ["<uuid-1>", "<uuid-2>"],
  "operation": "add_tags",
  "tag_ids": ["<tag-uuid>"]
}
```

**Required atomicity:** validation of all Keyword IDs, Group/Tag IDs, ownership, Project scope, state transitions and entitlements must succeed **before mutation**. If one selected record is invalid, reject the request and change none. Perform DB mutations in one transaction. Deduplicate IDs or reject duplicates deterministically. Establish a documented per-request limit (suggested 100–500) to bound locking and SQL cost. Return affected count and useful per-operation metadata.

Bulk archive must follow the existing scheduling/RankCheck safety model. Archived Keywords must not be enqueued for future scheduled checks. Do not unexpectedly cancel an already-running check unless the repository already specifies that behavior. Preserved historical ranking data must remain readable where existing archival semantics allow.

Bulk restore must enforce current Plan `max_keywords` before restoring, transactionally. Do not allow the request to partially restore over the limit. Group/Tag changes alone do not count as new Keywords and must not change quota usage.

### Bulk selection UX

- Checkbox per Keyword, select all **on current page** by default.
- Show `N selected` and clear selection affordance.
- Selection should remain stable when opening/closing inline history, but changing Project, search/filters or pagination should clear selection by default unless the UI explicitly supports cross-page selection.
- Never imply that selecting one page selects every result on all pages.
- Confirm destructive archive and replace-all-Tags actions.
- Use accessible mixed/indeterminate header checkbox where appropriate.
- Keep buttons disabled during submission; show success/error toast with accurate affected count.

---

## 8. Project Keywords UI

Integrate organization into the existing Project Keywords table/card view without moving Ranking History back to a fixed section at the bottom.

Suggested columns/sections:

```text
[Select] Keyword | Group | Tags | Tracked Rankings | Status | Actions
```

- Keyword name remains lightweight clickable text and expands **inline Ranking History directly below that Keyword row**.
- Group is a subtle badge or text label, not a filled CTA.
- Tags render as restrained chips; show first few and `+N` overflow where necessary.
- Preserve existing sorting and pagination behaviors.
- Add `Manage Groups` and `Manage Tags` entry points in the Project context, preferably a lightweight drawer/dialog or existing Project settings pattern.
- Do not let group/tag chips interfere with the Keyword click target or keyboard navigation.
- Reuse shared design tokens/components, not page-specific colors.

Desktop and mobile must remain usable at 375, 768, 1024 and 1440 px. Mobile bulk controls may use a compact action bar; prevent horizontal page overflow.

---

## 9. M7B Ranking Explorer Integration

Extend existing Explorer filters with:

```text
Group: All | No Group | {Project Groups}
Tags: All | Any selected Tags | All selected Tags
```

**Define exact semantics:**

- Group filter is single-select in M7C.
- Tag filter defaults to **ANY** selected Tag; optionally support an explicit `ALL` mode if the UI clearly exposes it and the backend efficiently supports it.
- Filtering uses server-side SQL and composes with the existing keyword search, movement, checked-depth position bucket, Tracked Site, status, date comparison, sorting and pagination.
- Group/Tag filters apply to Keyword organization. They must not change the selected ranking observation or comparison semantics.

Suggested query parameters:

```text
group_id=<uuid>|none
tag_ids=<uuid>,<uuid>
tag_match=any|all
```

Use existing query conventions where different. Validate all Group/Tag IDs belong to the same Project. Unknown/foreign identifiers must be handled safely without leaking other tenants' data. URL-driven filters must survive refresh and browser Back/Forward; show removable chips and Clear All.

Explorer counts must reflect the active combined filters. Preserve the M7B pagination contract and stable sorting. Reuse M7B's existing canonical comparison model; do not recalculate ranking movement differently for Groups/Tags.

**Performance guardrail:** M7B's verified local baseline at 1,000 Keywords and two active Tracked Sites was approximately 2.16 s for the default Explorer query. Benchmark before and after the M7C joins. Do not claim a performance improvement without measurement, and do not allow unnecessary N+1 queries.

---

## 10. Group / Tag Analytics

Add a lightweight, read-only organization performance view in Project context. This is **filtered reuse** of M7A/M7B analytics, not a new analytics engine.

User can select a Group or Tag and see:

```text
Active Keyword count
Top 3
4–10
Not found in checked depth
Improved / Declined / Unchanged
Entered / Left checked depth
```

Use the current M7A date comparison (7D/30D/90D) and the same success-only, Project/device, checked-depth-aware semantics. If only Top 10 was checked, never show unsupported Top 20/Top 100 or claim global unranked status. Distinguish `never_checked` and `no_previous_data` as M7A does.

Prefer extending existing M7A summary/distribution queries with validated optional `group_id` / `tag_ids`, **only if the existing service can share the same canonical comparison query**. Alternatively, add one narrow organization-summary endpoint that delegates to the existing analytics repository. Do not introduce per-Group or per-Tag background computation and do not call a SERP provider.

Do not build complex Tag overlap graphs, share-of-voice or trend attribution in M7C.

---

## 11. Analytics and Data Consistency

- Organization edits change which Keywords are returned by Group/Tag filters and summaries; they do not rewrite historical ranking observations.
- A Tag with overlapping assignments may count the same Keyword in multiple **independent Tag views**. Do not sum individual Tag totals and present that as a de-duplicated Project total.
- One Group per Keyword makes Group counts mutually exclusive; include `No Group` when reconciling Project totals.
- Follow current rules for active versus archived Keywords; expose historical access consistently with existing M7A/M7B semantics.
- Handle deleted Tags and Groups gracefully in bookmarked URL filters: return a safe validation/not-found state and let users clear the stale filter.
- Keep explicit checked-depth wording throughout.

---

## 12. Services, Repositories and Query Keys

Suggested service boundaries:

```text
KeywordGroupService
KeywordTagService
KeywordBulkOrganizationService
ExistingProjectAnalyticsService / repository
ExistingRankingExplorerService / repository
```

Avoid putting business rules in FastAPI routers or React components. Prefer set-based SQL for assignments and bulk changes.

Suggested TanStack Query keys:

```text
keywordGroups.list(projectId)
keywordTags.list(projectId)
keywords.list(projectId, filters)
rankingExplorer.list(projectId, existingParams, groupId, tagIds, tagMatch)
projectAnalytics.summary(projectId, device, range, organizationFilter)
```

Reuse existing keys/factories instead of introducing duplicate caches. Invalidate only affected Project Keyword lists, Group/Tag counts, Explorer and relevant filtered analytics after successful organization mutations. Do not invalidate unrelated Billing, Account, Admin or public Pricing queries.

---

## 13. Tenant, Security and Integrity Requirements

- Every mutation and read is scoped through `current_user.id` and the Project's owner.
- Validate same-Project membership of Keyword, Group and Tag, including bulk operations.
- Reject cross-user and cross-Project references; avoid exposing resource existence through distinguishable responses where repository conventions require tenant-safe 404s.
- Never trust client-supplied `user_id`, tenant identifiers, Keyword counts or affected-row counts.
- DB constraints should prevent duplicate Tag assignments and duplicate normalized catalog names.
- Do not expose internal SERP provider routing, costs or credits in organization APIs.
- All organization actions must be independent of Stripe/payment state except existing Keyword-count entitlement enforcement on restore/create.

---

## 14. API and Error Behavior

Follow existing pagination and error-envelope conventions. Suggested stable error codes if not already represented:

```text
KEYWORD_GROUP_NOT_FOUND
KEYWORD_TAG_NOT_FOUND
DUPLICATE_GROUP_NAME
DUPLICATE_TAG_NAME
INVALID_GROUP_ASSIGNMENT
INVALID_TAG_ASSIGNMENT
INVALID_BULK_OPERATION
BULK_SELECTION_LIMIT_EXCEEDED
KEYWORD_LIMIT_EXCEEDED
```

Explicitly distinguish business errors from transient database errors. Return no partial success for transactional bulk operations. Keep API responses typed and generated frontend types aligned with repository conventions.

---

## 15. Migration and Rollout

Create one Alembic migration after inspecting the actual current head (M7B report recorded `0009_plan_catalog_audit`; confirm again against the live repo). Include Group, Tag, assignment and optional Keyword Group FK plus useful indexes/constraints. Migration should be additive and **backwards-compatible** with existing Keywords, Projects, RankChecks, subscriptions and history. Existing Keywords start with no Group or Tags. No backfill is required.

Verify:

```text
upgrade → downgrade → upgrade
current == head
no unexpected schema drift
existing data and ranking history intact
```

If adding composite database constraints requires changes to existing keys, document and test migration behavior rather than silently weakening same-Project integrity.

---

## 16. Performance and Scale

Target the current paid Plan scale, including Projects with 1,000–5,000 active Keywords and many historical RankChecks.

- No per-Keyword tag lookup; list APIs should aggregate/attach Tags in bounded queries.
- No per-Group query to calculate counts.
- No fetching all Keywords into JavaScript to implement server-side filters.
- Bulk operations should use set-based validation and mutation with bounded transaction sizes.
- Tag filter queries and Group/Tag analytics should use the existing bounded ranking comparison design.
- Benchmark M7B default query **before and after** adding organization joins using equivalent fixtures.

Minimum performance fixture:

```text
1,000 active Keywords
2 active Tracked Sites
2+ successful observations per Keyword
10 Groups
20 Tags
mixed multi-Tag assignments
```

Measure: Project Keywords list, filtered Explorer (Group/Tag ANY/ALL), filtered summary and 100-Keyword bulk edit. Record SQL query counts, approximate local timings and `EXPLAIN` findings where material. Report limitations rather than asserting unmeasured production SLAs.

---

## 17. Frontend UX, Responsive and Accessibility

Reuse `PageHeader`, `Card`, `TextLink`, `Button`, `Badge`, `Input`, `Select`, `Skeleton`, `EmptyState`, `ErrorState` and existing modal/drawer/table patterns.

Required states:

- First use: `No groups yet` / `No tags yet`, with clear creation action.
- No organization filter matches: contextual empty state and Clear Filters.
- Loading/errors localized to the relevant table or control, with retry.
- Group/Tag rename/delete confirmations show the real entity name.
- Duplicated names produce actionable inline validation.
- Bulk actions clearly state count and operation before confirmation.
- Truncated Tag chips have accessible full names.
- Filters, multiselect and dialogs are keyboard accessible and visibly focused.
- Do not use color alone to distinguish Tags/status.
- Preserve the existing single-expanded-Keyword Ranking History behavior.

Verify viewport widths: 375, 768, 1024, 1280 and 1440 px. No clipped controls, unexpected overflow or page-wide reflow from many Tags.

---

## 18. Backend Automated Tests

Add focused tests for:

1. Group CRUD, trimming/normalization, case-insensitive duplicate rejection.
2. Tag CRUD, duplicate rejection, Tag assignment and removal.
3. One Group per Keyword, multiple Tags per Keyword.
4. Same-Project constraints and cross-user/cross-Project isolation.
5. Delete Group clears Keyword association without deleting history.
6. Delete Tag removes assignments without deleting Keywords/history.
7. Bulk assign/add/remove/replace, ID deduplication or validation and atomic rollback.
8. Bulk archive and restore follow existing state/schedule semantics.
9. Bulk restore rejects `max_keywords` limit atomically.
10. Group/Tag filters compose with M7B search, movement, depth/status/site/date/sort/cursor.
11. Group and overlapping Tag analytics reconcile to the correct unique scope.
12. Failed RankChecks do not influence analytics.
13. No fake positions or unsupported Top 20/Top 100 labels for depth 10.
14. No RankChecks, jobs, usage reservations or provider calls from organization operations.
15. Migration upgrade/downgrade, unique constraints and FK integrity.

Use deterministic PostgreSQL fixtures for SQL/tenant/integrity tests.

---

## 19. Frontend and Browser Tests

Frontend unit/integration coverage:

- Group/Tag create, edit, delete and duplicate-name feedback.
- Keyword Group/Tag editor; chip overflow.
- Multi-select and page selection behavior.
- Bulk assign, add/remove Tags, archive/restore, confirmation, errors and success counts.
- Filter chips and URL-driven Group/Tag filters in Explorer.
- Group/Tag analytics loading, empty, error and depth-aware presentation.
- No regression to inline Ranking History.

Real browser journeys:

```text
Create Group and Tags
Assign one Keyword
Assign multiple Tags
Bulk assign 10 Keywords
Bulk add/remove Tag
Filter Explorer by Group
Filter Explorer by Tag ANY (and ALL if implemented)
Combine Tag + movement + keyword search
Refresh / Back / Forward retains filters
Open inline Ranking History inside filtered Explorer
Archive selected Keywords
Restore within Plan limit
Attempt restore over Plan limit → no partial restore
Rename and delete Group/Tag
375 / 768 / 1024 / 1280 / 1440 px
```

Use fake provider and local task execution for seeded ranking journeys. Explicitly assert provider selection **before** any browser QA action that could trigger a manual check, preventing a repeat of the real-credit incident recorded in M7A.

---

## 20. Regression and Quality Gates

Run and record exact final results for:

```text
backend tests
frontend tests
Ruff lint and format
mypy strict
ESLint
Prettier
TypeScript typecheck
npm audit
production Next.js build
Docker stack health
Alembic current/head and schema drift
real browser QA
bounded-query and local performance benchmark
```

Regression scope: Authentication; Projects; Keyword CRUD and inline history; Tracked Sites; M7A analytics; M7B Explorer; manual RankCheck; Batch/Schedule; Billing and quota; Admin; Home/Pricing/Login/Register.

Do not claim PASS for unexecuted tests. Do not spend real SERP provider credits.

---

## 21. Out of Scope

**Do not implement**:

```text
Payment Gateway / Stripe / automatic top-up
Developer API / API Keys / API Docs
Keyword CSV import/export or PDF reports
Saved Explorer views
Cross-Project Groups or shared Tag catalogs
Nested Groups / hierarchical taxonomies
Rules-based auto-tagging / AI categorization
Keyword research, search volume or difficulty
Competitor analytics
Ranking alerts, email, Slack or Telegram notifications
AI SEO recommendations
New SERP provider calls for Group/Tag analytics
A separate analytics warehouse or cache layer
```

CSV/PDF reporting belongs to M7E; alerts to M7D; competitor analytics to M7F. Keep M7C focused on organization.

---

## 22. Definition of Done

### Backend

- [ ] Project-scoped Group and Tag CRUD with tenant-safe validation.
- [ ] One optional Group and multiple Tags per Keyword.
- [ ] Strong same-Project assignment integrity.
- [ ] Transactional bulk operations, including safe archive/restore.
- [ ] Existing Plan limits enforced on bulk restore.
- [ ] M7B combined Group/Tag filtering and correct pagination.
- [ ] Group/Tag analytics reuse canonical M7A comparison/depth semantics.
- [ ] No unnecessary SERP, queue, billing or usage side effects.
- [ ] Migration and integrity tests pass.

### Frontend

- [ ] Manage Groups/Tags UI in Project context.
- [ ] Keyword editor and table display organization correctly.
- [ ] Bulk selection and explicit action bar.
- [ ] Explorer Group/Tag filters are URL-driven.
- [ ] Organization summary is readable and depth-aware.
- [ ] Inline Keyword Ranking History is preserved.
- [ ] Responsive/accessibility checks pass.

### Verification

- [ ] Full backend/frontend checks pass.
- [ ] Browser journeys pass with fake provider and zero real credits.
- [ ] Existing M7A/M7B behavior remains correct.
- [ ] 1,000-Keyword performance fixture and before/after M7B comparison recorded.
- [ ] Exact limitations and unexecuted checks disclosed.

---

## 23. Final Codex Instructions

1. Inspect the repository **before coding**: actual schema, existing Keyword archive/restore, M7A/M7B comparison query, indexes and UI components.
2. Report concrete conflicts between this spec and repository behavior, especially whether safe Keyword restore exists, before choosing an implementation.
3. Build the smallest coherent feature set that satisfies the definitions above; reuse existing service/repository patterns.
4. Use one canonical Project/device ranking comparison model. Do not alter ranking semantics to simplify Group/Tag analytics.
5. Keep organization changes atomic, tenant-safe and quota-safe.
6. Implement migration, tests and browser verification with a fake provider.
7. Produce `docs/verification-milestone-7c.md` with files changed, migration ID, endpoints, Group/Tag schema, bulk semantics, exact test counts, browser evidence, performance before/after and known limitations.
8. **Do not implement unrelated M7B.1 performance work, payment processing, Developer API or API Docs in M7C.** If M7B.1 is incomplete or new joins materially worsen Explorer timings, identify the issue explicitly for a separate follow-up.
