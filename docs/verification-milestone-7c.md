# Milestone 7C verification — Keyword Organization

Verified on 2026-09-23 (Asia/Ho_Chi_Minh).

## Outcome

M7C is implemented across the PostgreSQL schema, tenant-safe service layer, APIs,
Project Keywords UI, Ranking Explorer and filtered analytics. Organization reads
reuse persisted successful RankChecks and never call a SERP provider.

M7B.1 was inspected and is not present as a separate optimization. M7C therefore
only adds bounded organization predicates to the existing canonical Explorer CTE.
The measured default Explorer query did not regress against the M7B report's
approximately 2.16 second baseline, but this milestone does not claim an M7B.1
optimization.

## Schema and migration

- Migration: `0010_keyword_organization`
- Parent: `0009_plan_catalog_audit`
- `keyword_groups`: Project FK, normalized Project-unique name and stable indexes.
- `keyword_tags`: Project FK, normalized Project-unique name and stable indexes.
- `keyword_tag_assignments`: composite primary key and composite same-Project FKs
  to Keyword and Tag, with Project/Tag and Project/Keyword indexes.
- `keywords.keyword_group_id`: nullable, with a composite same-Project FK and
  membership index.
- Group deletion clears membership. Tag deletion cascades assignments. Neither
  operation deletes Keywords, RankChecks or Rankings.

Migration verification against the local PostgreSQL instance:

1. Upgrade `0009 -> 0010`: PASS.
2. Downgrade `0010 -> 0009`: PASS.
3. Upgrade `0009 -> 0010`: PASS.
4. Alembic metadata comparison in the backend suite: PASS.

## API surface

- `GET|POST /api/v1/projects/{project_id}/keyword-groups`
- `PATCH|DELETE /api/v1/projects/{project_id}/keyword-groups/{group_id}`
- `GET|POST /api/v1/projects/{project_id}/keyword-tags`
- `PATCH|DELETE /api/v1/projects/{project_id}/keyword-tags/{tag_id}`
- `POST /api/v1/projects/{project_id}/keywords/bulk-organize`
- Existing Keyword create/update responses now include `group` and `tags`.
- Existing Keyword list accepts `group_id`, CSV `tag_ids`, and `tag_match=any|all`.
- Existing Ranking Explorer accepts the same organization filters; all filters
  remain URL-driven in the frontend.
- `GET /api/v1/projects/{project_id}/analytics/organization-summary` accepts
  exactly one validated `group_id` or `tag_id` and delegates to M7A semantics.

Omitted `group_id`/`tag_ids` on Keyword update means unchanged. Explicit
`group_id: null` clears the Group. Explicit `tag_ids: []` replaces all Tags with
an empty set.

## Bulk behavior

- Operations: assign/no Group, add Tags, remove Tags, replace Tags, archive and
  restore.
- Maximum 200 unique Keyword IDs and 100 Tag IDs per request.
- All Keyword and organization IDs are validated and locked before mutation.
- Set-based writes execute inside one transaction; failures return no partial
  result.
- Restore locks the subscription, calculates inactive selected Keywords once,
  and enforces the existing device Plan `max_keywords` before changing state.
- Archive uses the existing `active=false` state. Schedulers continue selecting
  only active Keywords; already-running checks are not cancelled.
- Group/Tag edits do not reserve usage, run checks or alter ranking history.

## UI

- Project Keywords includes Group and Tag filters, badges/chips, chip overflow,
  responsive data labels, and individual create/edit organization controls.
- Current loaded rows can be selected with an accessible mixed-state header
  checkbox. Selection is cleared when search/state/organization filters change.
- The bulk action bar exposes all six operations and confirms archive and
  replace-all-Tags actions.
- The management dialog supports create, rename and deletion confirmation with
  active Keyword counts for Groups and Tags.
- The same dialog provides depth-aware Group/Tag performance for 7D/30D/90D.
- Ranking Explorer provides All/No Group, multi-Tag ANY/ALL controls, removable
  URL filter chips and Clear All behavior.

## Automated verification

- Backend: **228 passed** in 160.50 seconds.
- Frontend: **103 passed** across 20 files in 7.58 seconds.
- Backend Ruff check and format check: PASS.
- Backend mypy: PASS, 122 source files.
- Frontend TypeScript typecheck: PASS.
- Frontend ESLint: PASS.
- Next.js production build: PASS, including `/app/projects/[projectId]` and
  `/app/projects/[projectId]/rankings`.
- Docker backend, worker and frontend health checks: healthy.

The frontend suite still prints pre-existing React Query warnings where older
ranking test mocks intentionally return `undefined` for unrelated background
queries. They do not fail tests; M7C-specific component and Explorer tests pass.

## Local journey evidence

Before QA, resolved Compose configuration was explicitly checked:

- `SERP_PROVIDER=fake`
- `TASK_QUEUE_PROVIDER=local`
- zero manual RankCheck actions were issued
- zero real provider credits were used

An authenticated local production-stack journey created a test Project and Site,
created/renamed a Group, created two Tags, assigned two Tags individually, bulk
added a Tag, filtered Keywords, filtered Explorer and loaded organization
analytics. Observed results:

- individual Group: `Brand`
- renamed Group: `Brand Core`
- individual Tags: 2
- bulk affected Keywords: 1 (the other assignment was already present)
- combined Group + ALL-Tags result: 1 Keyword
- Tag-filtered Explorer result: 2 rows
- Group analytics active Keyword count: 1

The runtime available to this verification had no Playwright/Chromium executable,
so an interactive screenshot pass at 375/768/1024/1280/1440 was not executed.
Responsive behavior is covered by production CSS/build and component tests, but
the viewport screenshot journey remains a manual follow-up and is not reported as
PASS.

## Performance guardrail

One local integration run used 1,000 active Keywords, two active Tracked Sites,
10 Groups, 20 Tags with mixed assignments, two successful
observations per Keyword, and a 100-Keyword bulk edit. Approximate timings:

| Query/action | Time (ms) |
| --- | ---: |
| Explorer default | 1,583.24 |
| Explorer movement | 1,551.16 |
| Explorer position | 1,987.62 |
| Explorer search | 27.15 |
| Explorer change sort | 1,597.07 |
| Explorer Group | 298.84 |
| Explorer Tags ANY | 283.73 |
| Explorer Tags ALL | 96.27 |
| Explorer next page | 1,547.65 |
| Organized Keyword list (limit 200) | 21.93 |
| Organization summary | 13.79 |
| Bulk add Tag to 100 Keywords | 11.26 |

This is a single local run, not a production SLA. The default measurement is
below the recorded M7B baseline, so no regression was observed. No performance
improvement is claimed because hardware/load and run variance were not controlled.

## Main files changed

- `backend/alembic/versions/0010_keyword_organization.py`
- `backend/app/models/keyword_organization.py`
- `backend/app/repositories/keyword_organization.py`
- `backend/app/services/keyword_organization.py`
- `backend/app/api/v1/keyword_organization.py`
- Existing Keyword, analytics and Ranking Explorer model/repository/service/API
  files.
- `backend/tests/test_keyword_organization.py` plus analytics, Explorer,
  migration and invariant regressions.
- `frontend/src/features/projects/keyword-organization-manager.tsx`
- Existing Project Keyword, Ranking Explorer and analytics API/type files.
- Relevant frontend component tests and design-system responsive styles.

## Known limitations

- M7B.1 remains separate and incomplete.
- Tag selection uses the native multi-select control; it is accessible and
  functional but not a searchable combobox.
- Selection covers currently loaded Keyword rows. The UI explicitly says
  “loaded rows” and never implies all matching results across cursors.
- Interactive multi-viewport browser screenshots remain unexecuted as noted
  above.
