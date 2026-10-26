# Milestone 7D — Ranking Alerts (In-App + Email)

**Product:** SERP SaaS\
**Status:** Implementation specification for Codex — not yet implemented or verified\
**Priority:** Post-M7K core product engagement\
**Language:** Authenticated application UI remains English

## 1. Objective

Notify an authenticated user about meaningful Google ranking changes **after a successfully completed rank check**. Provide an in-app alert inbox, per-project alert preferences, optional email delivery, read/unread state, and reliable deduplication. Preserve all existing ownership, billing, ranking semantics, and queue architecture.

This is a **ranking alert** milestone, not a general notification platform. Do not rebuild ranking execution, change SERP providers, alter check depth, add billing tiers, or redesign unrelated app pages.

## 2. Current product invariants

- Tenant boundary is **User**; no organizations, teams, shared workspaces, client portals, or roles beyond existing platform administration.
- `User -> Projects -> Keywords` and separate user-owned `Tracked Sites -> Domain Aliases`. A Project represents a search environment, not a website.
- Desktop/Mobile project environments and plans are separate. Do not merge their rankings or compare a Desktop observation to a Mobile observation.
- Current measurement depth defaults to **Top 10**. Do not imply a missing result is position 11, 50, 100, or an exact rank beyond measured depth.
- A **complete** check with no domain match is *not found within checked Top 10*; an incomplete/failed check is *unknown*, not an alert-worthy loss.
- Ranking execution uses FastAPI/Python, PostgreSQL, Cloud Tasks and Cloud Run workers. Reuse the existing task and recovery patterns. Do not require Redis/Memorystore for production.
- Existing auth: verified user sessions and server-derived `current_user.id`; never accept client-supplied user ownership.
- Existing email infrastructure and verification rules should be inspected and reused; production email sending must be separately validated.
- Billing and SePay payment/activation are **out of scope** and must not be affected.

## 3. Deliverables

1. Alerts created from validated, persisted ranking changes.
2. In-app **Ranking Alerts** page, unread badge and basic actions.
3. User-editable alert settings scoped to **Project** (and user-level email enablement if appropriate).
4. Optional email notification with queue-backed retry and send tracking.
5. Idempotent processing, email delivery deduplication, concurrency safety, and security boundaries.
6. Tests, browser QA, migration, deployment checklist and verification report.

## 4. Alert types (M7D)

| Code | Meaning | Condition |
|---|---|---|
| `entered_top10` | Site entered checked Top 10 | Previous **complete** check had no match within Top 10, current **complete** check has position 1–10 |
| `left_top10` | Site left checked Top 10 | Previous complete position 1–10, current **complete** check has no match within Top 10 |
| `rank_improved` | Rank improved materially | Both complete observations have numeric Top-10 positions and previous_position - current_position >= configured threshold |
| `rank_declined` | Rank declined materially | Both complete observations have numeric Top-10 positions and current_position - previous_position >= configured threshold |

**Default threshold proposal:** 3 positions; configurable as a positive integer, with reasonable validated bounds (e.g. 1–10). Confirm naming and current schema before implementing.

Do not alert on a first-ever observation without a valid previous completed baseline. Never infer transitions from missing data, provider errors, cancelled jobs, timeouts, partial SERPs, or rank-check runs that did not produce a complete observation. A missing/unknown prior baseline must not be treated as *not in Top 10*.

For a single keyword/tracked site/observation pair, prefer one most-specific event: entering/leaving Top 10 takes precedence over numeric movement if applicable. If result records can contain several tracked sites, analyze each site independently.

## 5. Exact comparison semantics

### 5.1 Baseline selection

Compare current observation to the **immediately previous eligible complete observation** of the same:

- user and project;
- keyword;
- tracked site/domain-matching identity;
- desktop/mobile and all defining Google search-environment dimensions (location, language, engine, etc.).

Prefer existing ranking-history / check-result identifiers over synthesizing identities from display labels. Inspect existing ORM schema and domain-alias matching before choosing keys.

A failed/incomplete intermediate attempt must not create a false `left_top10` or reset the baseline. Avoid comparing two checks from different project configurations if the environment changed materially; define a safe no-alert/rebaseline rule and document it.

### 5.2 Ordering and late arrivals

Use canonical observation/check timestamps and stable IDs as tie-breakers. Do not assume task completion order equals observation order. Handle retries and late-arriving older checks without issuing false newer alerts; document whether historic backfill is intentionally suppressed. Do not let a late result replace the user's current baseline incorrectly.

### 5.3 Aliases / competitors

Use existing tracked-site aliases and site-identification logic. The alert concerns the user's **tracked primary sites**, not inferred competitors, unless the repository already has explicit user-intended tracked site associations. No new competitor alert type in M7D. Do not collapse arbitrary subdomains or mis-handle bidirectional `www` fallback.

### 5.4 Illustrative examples

| Previous complete observation | Current complete observation | Expected |
|---|---|---|
| Not found in checked Top 10 | #7 | `entered_top10` |
| #6 | Not found in checked Top 10 | `left_top10` |
| #9 | #4 | `rank_improved`, delta 5 |
| #2 | #6 | `rank_declined`, delta 4 |
| #6 | #4, threshold 3 | No alert |
| No valid prior baseline | #4 | No alert |
| #5 | Failed / incomplete | No alert |
| Failed / incomplete | #8 | Compare only to prior valid complete baseline, if safely identifiable |

## 6. Trigger point and reliability

Integrate detection **after** the rank result and check status are durably persisted and recognized as complete by the existing ranking execution service. Detection must not delay or fail the rank-check result itself due to email errors.

Recommended logical flow:

```text
Cloud Tasks rank worker
  -> RankCheckExecutionService
  -> persist complete rank check + normalized result/ranking
  -> durable alert evaluation job/event marker
  -> AlertEvaluationService (idempotent)
  -> ranking_alerts + delivery outbox
  -> in-app inbox
  -> email worker (optional, asynchronous)
```

Prefer an **outbox / durable pending evaluation** approach over a fire-and-forget call or fragile in-process background task. Follow current Cloud Tasks adapter and deterministic task naming. If enqueue fails, a reconciliation dispatcher should discover and retry pending evaluations. Avoid creating a queue task for each keyword when one check/batch can be efficiently processed.

**Failure principle:** a rank check may be successful even when alert evaluation/delivery is pending; surface recovery/metrics separately. Never call the SERP provider again merely to compute alerts.

## 7. Database design (adapt to existing schema)

Inspect existing migration head (including M7K payment migrations) and create the **next available Alembic revision**, without assuming revision numbers.

Proposed tables:

### `ranking_alert_preferences`

- `id` UUID PK
- `user_id` FK
- `project_id` FK
- `enabled` boolean (default true or explicitly documented)
- `notify_entered_top10`, `notify_left_top10`, `notify_improvement`, `notify_decline`
- `movement_threshold` integer default 3
- `email_enabled` boolean default false (opt-in recommended)
- `created_at`, `updated_at`
- Unique `(user_id, project_id)`; ownership validated server-side.

### `ranking_alerts`

- `id` UUID PK
- `user_id`, `project_id`, `keyword_id`, `tracked_site_id` (nullable only where justified)
- `alert_type`
- `previous_observation_id`, `current_observation_id` / actual relevant ranking/check IDs
- `previous_rank`, `current_rank` nullable, with explicit top-10-not-found classification
- `rank_delta` nullable
- `observed_at`, `created_at`, `read_at` nullable
- optional `email_delivery_status` exposed via delivery relation, not mutable mixed state
- Unique idempotency key derived from **current complete observation + keyword + tracked site + alert type** (and tenant/environment if IDs not globally unique).

### `ranking_alert_evaluations` (or equivalent durable task marker)

- check/result identity, status `pending|processing|completed|retryable_failed`, attempts, lease timestamps, last error, uniqueness.
- Can be replaced by existing reliable job/outbox infrastructure if it provides equivalent recovery guarantees.

### `ranking_alert_deliveries` / outbox

- `id`, `alert_id`, `channel='email'`, `status`, `attempts`, `next_attempt_at`, `sent_at`, `last_error`, unique `(alert_id, channel)`.
- Add provider message id where available and prevent duplicate concurrent sends.
- **Exactly-once external email delivery cannot be guaranteed** without provider idempotency. Document the at-least-once boundary and minimize duplicates with leases/durable state and provider-specific idempotency if available.

Add indexes for user inbox `(user_id, created_at desc)`, unread lookups, project, and pending evaluation/delivery work. Do not cascade-delete audit-critical records without reviewing retention requirements.

## 8. Settings behavior

Per-project preferences are the source of truth. Changing the threshold or alert types affects **future evaluations**, not past persisted alerts; no automatic retroactive recomputation. Choose and document evaluation-time snapshot behavior for preferences if checks and setting changes race.

Email only when:

- user email is verified;
- email notifications are explicitly enabled;
- the alert type is enabled;
- user/account/project remains eligible under documented rules;
- the SMTP provider is configured and permitted for sending.

User can disable alerts per project without disabling rank tracking. Notification preferences must not be writable by any other user. Document behavior on project/keyword/tracked-site deletion and when historical alerts reference deleted objects.

## 9. Backend API (proposed)

Use existing `/api/v1` naming, pagination, error envelope, authorization and service/repository conventions. Adjust endpoint names to repository patterns while preserving functionality.

```text
GET   /api/v1/ranking-alerts?project_id=&unread_only=&limit=&cursor=
GET   /api/v1/ranking-alerts/unread-count
PATCH /api/v1/ranking-alerts/{alert_id}/read
POST  /api/v1/ranking-alerts/mark-all-read
GET   /api/v1/projects/{project_id}/ranking-alert-preferences
PUT   /api/v1/projects/{project_id}/ranking-alert-preferences
```

Requirements:

- All requests authenticate and derive `current_user.id`; verified-email gate consistent with existing app.
- Pagination server-side, deterministic ordering (`created_at DESC, id DESC`); cap page size.
- Optional project/unread filters fully tenant-scoped.
- `read_at` is server timestamp; marking already read is idempotent.
- Unknown or foreign IDs return 404 without leaking existence.
- No arbitrary `user_id`, `email`, or target address accepted from client.
- Avoid N+1 listing queries; preserve acceptable performance under thousands of alerts.

## 10. In-app UX

### Navigation and inbox

Add **Ranking Alerts** to the authenticated app navigation, ideally alongside Rankings/Analytics or under a notification bell. Recommended route:

```text
/app/ranking-alerts
```

A notification bell/unread badge in AppShell is optional but strongly recommended if consistent with the existing design system. A user should always have an obvious path to the inbox. Avoid polling every few seconds; use TanStack Query with restrained refetch (focus/interval) and invalidate after mutations.

Each alert row displays:

- keyword text;
- project and device context;
- tracked site;
- change classification (`Entered Top 10`, `Left Top 10`, `Improved`, `Declined`);
- previous and current observed position, using explicit **Not found in Top 10** for a complete missing observation;
- observed time in clear timezone/local convention;
- read/unread indicator;
- link to existing project/Ranking Explorer history, preserving access checks.

Do not display fabricated rank positions outside Top 10. For deleted/archived objects, show safe fallback snapshot text without broken links.

Support filters (`All`, `Unread`, project), paginated list, mark read and mark all read, loading/empty/error/retry states.

### Preferences UI

Place alert preferences in the project's existing settings/details UI where sensible, not in a new global admin panel. Provide clear toggles for alert types, threshold, enable/disable and email opt-in. Explain that alerts depend on completed checks, not realtime Google monitoring.

### Sample copy

```text
Ranking Alerts
Get notified when tracked Google rankings change significantly after a completed check.

Entered Top 10: example keyword — Not found in Top 10 → #8
Improved: example keyword — #9 → #4 (+5 positions)
Left Top 10: example keyword — #6 → Not found in Top 10
```

## 11. Email notifications

Use existing real SMTP integration/configuration; fake transport for deterministic unit/browser tests. Do not expose SMTP credentials or send user-controlled HTML as raw markup. Send email to **the verified account's email only**. Avoid arbitrary recipient inputs, agency bulk sends or custom lists.

Recommended message: subject `SERP SaaS ranking alert: <keyword>` and compact body with project, device, site, observed change, timestamp and deep link. Escape HTML and include readable plaintext. No unsupported product claims.

Delivery design:

- store durable outbox entry transactionally with alert creation;
- send asynchronously in Cloud Tasks worker or existing email delivery worker;
- bounded exponential retries; permanent failure state visible to operators;
- no long synchronous SMTP operation in ranking worker/API;
- stop or suppress pending emails when user disables email as specified; document race semantics;
- respect rate/cost limits: aggregate multiple alerts from one check into a digest if necessary **without losing in-app detail**. If sending per-alert in v1, impose per-user caps and document policy.

Consider default email **off** until users explicitly opt in, to avoid surprise emails/cost.

## 12. Abuse, privacy and observability

- Limit query sizes, pagination and preferences values.
- Never leak cross-tenant keyword/site/subscription data.
- No provider API keys, raw SERP payload, user tokens or SMTP secrets in alerts/logs.
- Do not send alerts for checks belonging to disabled/deleted projects or ineligible user accounts as defined by existing lifecycle.
- Structured logs: evaluation id, check id, user/project ids, counts by type, retry count, delivery status; redact keyword/PII where possible.
- Metrics: evaluations queued/completed/failed, alert count, unread count (aggregate), emails sent/failed/retried, backlog age and duplicate suppression.
- Reuse existing retention/privacy policy; document any new alert/evidence retention assumptions rather than silently inventing them.

## 13. Testing: backend

Test against isolated PostgreSQL schemas with real constraints and SQLAlchemy/Alembic, following existing project test infrastructure.

**Detection:** enter/leave Top 10; threshold ±3; no alert below threshold; first-baseline suppression; failed/incomplete/cancelled checks; provider failure; aliases/www; distinct sites; Desktop vs Mobile; location/language/environment isolation; same-keyword multiple observations; late/out-of-order checks; unchanged positions; repeated processing; keyword/project deletion.

**Concurrency:** duplicate Cloud Tasks, overlapping worker claims, duplicate alert unique keys, retry after crash, enqueue failure + reconciliation, transactional rollback, database locks and lease expiry.

**API/tenant:** list/filter/pagination, unread count, read/mark-all, preferences CRUD, invalid threshold, anonymous/unverified gating, foreign project/alert 404, account switch cache boundaries.

**Email:** verification required, email opt-in/off, transient SMTP retry, permanent fail, no duplicate outbox rows, HTML escaping, verified recipient only, throttle/digest policy, fake transport.

**Migration:** upgrade head / downgrade revision / upgrade, uniqueness, indexes, ORM parity. Confirm latest Alembic head dynamically.

## 14. Frontend and browser QA

Run authenticated production standalone QA at **375, 768, 1024 and 1440px**. Test verified/anonymous/unverified users, project with alerts, empty inbox, unread filter, pagination, mark read/all read, project preference toggles, threshold input, SMTP-disabled state, loading/error/retry, deep links, dark/light design if applicable and long Vietnamese keyword strings.

No horizontal overflow, page errors/hydration warnings, or WCAG 2.1 A/AA axe violations in tested cases. Keyboard labels, focus management and status announcements must work. Run existing app/auth/billing/SePay regressions; **no real payment or SERP provider calls** in automated browser tests.

## 15. CI/security/build gates

Run project equivalents of:

```bash
# Backend
pytest
ruff check .
ruff format --check .
mypy app
# Alembic upgrade/downgrade/upgrade against disposable database

# Frontend
npm test
npm run lint
npm run typecheck
npm run format:check
npm run build
npm audit --omit=dev
git diff --check
```

Preserve runtime audit with 0 high/critical findings. If environment constraints prevent a check, report it as unverified; do not claim PASS without evidence.

## 16. Staging and production rollout

1. Apply migration via existing **release migration job**, not concurrent app startup.
2. Deploy backend/worker compatible with new tables and queue handlers.
3. Deploy frontend.
4. Initially keep outbound email disabled/opt-in while validating in-app alerts.
5. Run controlled complete rank checks with a fake provider in staging, then approved real provider checks when safe.
6. Confirm transitions, no duplicates, tenant isolation, unread/count/read functionality, outbox replay and failure recovery.
7. Configure SMTP in Secret Manager, SPF/DKIM/DMARC, sender verification and delivery tests before enabling real email.
8. Monitor backlog/error rates after rollout; provide an operational disable switch for detection and/or email dispatch.

Never claim production deployment or email deliverability until actual verified.

## 17. Out of scope

- SMS/Telegram/Slack/push notifications; custom webhooks.
- SERP feature alerts, competitor alerts, Top 100 claims or exact position beyond measured Top 10.
- Real-time instant Google changes: events are derived from scheduled/manual completed checks.
- Team/org/member subscriptions or client portal.
- SePay checkout, billing changes, renewal/downgrade policy changes.
- Rebuilding reports or analytics.
- Machine-learning anomaly detection and unapproved per-keyword billing quotas.

## 18. Definition of Done

- [ ] In-app alerts created only from eligible complete rank observations.
- [ ] Four alert types implemented with correct Top-10 semantics.
- [ ] No first-check/failed/incomplete false positives.
- [ ] Environment, device, site and tenant boundaries respected.
- [ ] Late/retried/concurrent checks cannot generate false/duplicate alerts.
- [ ] Durable evaluation + recovery and persistent unique alert events.
- [ ] Preferences per project, with safe defaults and validation.
- [ ] User-scoped list/unread/read/all-read APIs.
- [ ] In-app inbox and accessible navigation/badge.
- [ ] Email only to verified account when opted-in.
- [ ] Durable email outbox, retry/deduplication and documented delivery semantics.
- [ ] Existing ranking, Cloud Tasks, billing, SePay and app behavior unchanged.
- [ ] Migration, backend/frontend tests, responsive browser QA and security gates pass.
- [ ] Verification report explains tested vs unverified environments.

## 19. Required verification artifact

Create:

```text
docs/verification-milestone-7d.md
```

Include: files and migration revisions changed; exact rank-comparison semantics and sample matrix; architecture/task lifecycle; idempotency keys/locks/recovery; preference defaults; API contract and tenant checks; email outbox/retries/opt-in; test/build outputs; browser/accessibility results; known limitations; staging/production deployment and real-email delivery status.

## 20. Final instruction to Codex

**Read existing code before coding.** Inspect the latest `rank_checks`, `rank_check_results`, `rankings`, tracked-site/alias matching, Cloud Tasks worker/scheduler, tenant authorization, billing entitlement check hooks, email transport, AppShell/sidebar, existing alert/notification code, and Alembic head. Treat old milestone specs as historical requirements when current code differs; reconcile with implementation rather than overriding correct behavior.

Choose the smallest reliable architecture respecting existing service/repository boundaries. Implement complete ranking alerts with recoverable processing and honest Top-10 semantics, without inventing external provider behavior, weakening tenant isolation, or changing SePay/subscriptions.

Ask for secrets only through environment/Secret Manager setup, never via chat, source files, logs or verification reports. Do not deploy production or enable real outbound email without authorization.
