# SERP SaaS — Milestone 6A Specification

## Billing Domain + Manual Subscription Activation + Usage Limits

**Target milestone:** M6A  
**Status:** Specification  
**Prerequisite:** M1–M5 implemented, with M5 asynchronous Rank Check Batch/Job execution available.  
**Payment model for M6A:** Manual bank transfer only. No payment gateway integration yet.  
**Primary goal:** Introduce commercial Plans, device-scoped Subscriptions, Entitlements, Usage Metering, Usage Reservation/Enforcement, and an Admin UI for manually activating and changing customer Plans after bank-transfer confirmation.

---

# 1. Objective

Milestone 6A introduces the commercial control layer required before opening the SERP SaaS to customers.

The system must support two independent product lines:

```text
Desktop
├── Free
├── Starter
└── Pro

Mobile
├── Free
├── Starter
└── Pro
```

A customer may hold one active Desktop subscription and one active Mobile subscription at the same time.

Example:

```text
Customer A
├── Desktop Pro
└── Mobile Starter
```

The customer must not be able to hold two simultaneously active subscriptions for the same device scope.

---

# 2. Core Commercial Model

```text
User
├── Desktop Subscription
│    └── Desktop Plan
├── Mobile Subscription
│    └── Mobile Plan
├── Usage Periods
│    └── Usage Reservations / Usage Events
├── Projects
│    └── device = desktop | mobile
└── Rank Check Batches / Jobs
```

The existing `Project.device` determines which device-scoped subscription and usage quota apply.

---

# 3. Manual Payment Principle

M6A separates payment collection from entitlement activation:

```text
Customer performs bank transfer
        ↓
Admin confirms payment externally
        ↓
Admin activates or changes Plan
        ↓
Subscription becomes effective
        ↓
Entitlements apply
        ↓
Usage limits are enforced
```

No payment gateway is required.

---

# 4. In Scope

M6A must implement:

- Plans and Plan catalog.
- Separate Desktop and Mobile product lines.
- Six initial Plans: Free, Starter, Pro for each device.
- Plan price metadata.
- Plan entitlements.
- User Subscriptions scoped by device.
- Manual subscription activation after bank-transfer confirmation.
- Subscription period management.
- Subscription history.
- Platform Admin authorization.
- Admin customer list and customer billing detail UI.
- Admin actions to activate, upgrade, downgrade, extend, cancel, and inspect subscriptions.
- Usage periods.
- Monthly logical keyword-check quota.
- Atomic usage reservation.
- Usage commit/release.
- Project-count limits.
- Keyword-count limits.
- Schedule entitlement enforcement.
- Schedule-frequency enforcement.
- Device entitlement enforcement.
- Customer Billing & Usage page.
- Billing audit trail.
- Usage adjustments.
- M5 Batch/Job integration.
- Migrations, tests, browser verification, and final verification report.

---

# 5. Out of Scope

Do NOT implement in M6A:

```text
Stripe
Stripe Checkout
Stripe Billing
payment webhooks
crypto payment gateway
PayPal
automatic recurring billing
automatic bank reconciliation
bank-account API integration
tax/VAT engine
refund automation
coupons
promo codes
automatic overage billing
provider pricing synchronization
provider balance synchronization
customer-selectable SERP provider
annual billing automation
M7 analytics dashboard
```

---

# 6. Initial Plan Catalog

Use one `plans` table. Do not create separate Desktop and Mobile Plan tables.

## Desktop Plans

| Plan | Monthly Price | Max Projects | Max Keywords | Monthly Keyword Checks | Scheduled Checks | Max Frequency |
|---|---:|---:|---:|---:|---|---|
| Desktop Free | $0 | 1 | 50 | 100 | No | None |
| Desktop Starter | $19 | 5 | 500 | 5,000 | Yes | Weekly |
| Desktop Pro | $129 | 20 | 5,000 | 50,000 | Yes | Daily |

## Mobile Plans

| Plan | Monthly Price | Max Projects | Max Keywords | Monthly Keyword Checks | Scheduled Checks | Max Frequency |
|---|---:|---:|---:|---:|---|---|
| Mobile Free | $0 | 1 | 20 | 50 | No | None |
| Mobile Starter | $39 | 3 | 200 | 1,000 | Yes | Weekly |
| Mobile Pro | $249 | 10 | 1,000 | 10,000 | Yes | Daily |

These values are seed data. Enforcement logic must not hard-code them.

---

# 7. Plan Fields

Recommended `plans` fields:

```text
id UUID PK
code
name
device_scope
price_monthly_minor_units
currency

max_projects
max_keywords
monthly_keyword_checks
scheduled_checks_enabled
max_scheduled_frequency

active
display_order

created_at
updated_at
```

Recommended codes:

```text
desktop_free
desktop_starter
desktop_pro

mobile_free
mobile_starter
mobile_pro
```

`device_scope`:

```text
desktop
mobile
```

Currency for M6A:

```text
USD
```

Prefer integer minor units for money.

---

# 8. Entitlement Semantics

`max_projects`

```text
Maximum active Projects for the Plan's device scope.
```

`max_keywords`

```text
Maximum total active Keywords across all active Projects
for the Plan's device scope.
```

`monthly_keyword_checks`

```text
Maximum logical Keyword Rank Checks per usage period.
```

`scheduled_checks_enabled`

```text
Whether scheduled Rank Checks are allowed.
```

`max_scheduled_frequency`

```text
Fastest allowed recurring schedule.
```

Initial values:

```text
none
weekly
daily
```

---

# 9. Logical Customer Usage vs Provider Usage

Customer quota counts logical keyword checks.

Example:

```text
1 customer Keyword check
→ Serper request fails
→ ProviderRouter falls back to SerpApi
→ SerpApi succeeds

Customer usage = 1 logical check
Provider usage = 2 upstream requests
```

M6A must never charge a customer extra because of provider retry or fallback.

---

# 10. Subscription Model

Recommended `subscriptions` table:

```text
id UUID PK

user_id UUID NOT NULL
plan_id UUID NOT NULL

device_scope

status
source

period_start
period_end

payment_method nullable
payment_reference nullable
payment_note nullable

activated_at nullable
activated_by_user_id nullable

cancelled_at nullable
cancelled_by_user_id nullable

created_at
updated_at
```

---

# 11. Subscription Source

M6A supports:

```text
manual
```

Design for future values:

```text
stripe
future_payment_provider
```

Payment provider logic must not leak into usage enforcement.

---

# 12. Manual Bank Transfer Metadata

Paid subscription:

```text
payment_method = manual_bank_transfer
```

Free Plan:

```text
payment_method = null
```

Optional internal reconciliation:

```text
payment_reference
payment_note
```

Do not store unnecessary sensitive banking credentials.

---

# 13. Subscription Status

Support:

```text
scheduled
active
expired
cancelled
```

Optional:

```text
pending
```

only if implementation benefits from it.

---

# 14. One Active Subscription Per Device

Enforce:

```text
1 active Desktop subscription per User
1 active Mobile subscription per User
```

Valid:

```text
Desktop Pro
+
Mobile Starter
```

Invalid:

```text
Desktop Starter
+
Desktop Pro
```

unless one is future-dated and not yet active.

---

# 15. Free Entitlement Behavior

Recommended:

Every User has effective:

```text
Desktop Free
Mobile Free
```

when no paid Plan is active for the corresponding device scope.

Implementation may use explicit Free subscriptions or equivalent deterministic fallback behavior.

Observable behavior must be predictable.

---

# 16. Manual Activation Flow

```text
Customer transfers money
        ↓
Admin verifies externally
        ↓
Admin opens customer
        ↓
Select device scope
        ↓
Select Plan
        ↓
Set subscription period
        ↓
Enter payment reference / note
        ↓
Activate
        ↓
Entitlements take effect
```

---

# 17. Subscription Period

A paid subscription has:

```text
period_start
period_end
```

It may represent:

```text
1 month
3 months
12 months
```

Subscription duration and usage reset cadence are separate concepts.

---

# 18. Subscription Commercial Snapshot

Historical subscriptions should preserve the commercial terms active at activation time.

Recommended snapshots:

```text
plan_code_snapshot
plan_name_snapshot
price_snapshot
currency_snapshot

max_projects_snapshot
max_keywords_snapshot
monthly_keyword_checks_snapshot
scheduled_checks_enabled_snapshot
max_scheduled_frequency_snapshot
```

Changing the Plan catalog later must not rewrite historical commercial terms.

---

# 19. Usage Period Model

Recommended `usage_periods` table:

```text
id UUID PK

user_id UUID NOT NULL
subscription_id UUID NOT NULL
plan_id UUID NOT NULL
device_scope

period_start
period_end

keyword_check_limit
reserved_keyword_checks
committed_keyword_checks

created_at
updated_at
```

---

# 20. Monthly Usage Reset

Recommended: subscription-anchored monthly periods.

Example:

```text
Subscription:
2026-09-12 → 2026-12-12

Usage:
2026-09-12 → 2026-10-12
2026-10-12 → 2026-11-12
2026-11-12 → 2026-12-12
```

If calendar-month periods are chosen instead, document and test the decision.

---

# 21. Usage Reservation

M5 queueing creates concurrency risk. Quota must be reserved before Batch/Job enqueue.

Example:

```text
remaining = 100

request A = 80
request B = 80
```

Only one may reserve successfully if both race.

Use transaction-safe reservation.

---

# 22. Usage Reservation Model

Recommended table:

```text
usage_reservations
```

Fields:

```text
id UUID PK
usage_period_id UUID NOT NULL
user_id UUID NOT NULL
device_scope
batch_id nullable
amount
status
created_at
committed_at nullable
released_at nullable
```

Status:

```text
reserved
committed
released
```

---

# 23. Reservation Formula

```text
remaining =
effective_limit
- committed
- reserved
```

New request requires:

```text
requested <= remaining
```

---

# 24. Reservation Flow

```text
Rank Check request
        ↓
Resolve Project.device
        ↓
Resolve effective Subscription
        ↓
Resolve entitlement snapshot
        ↓
Resolve current Usage Period
        ↓
Reserve requested logical checks atomically
        ↓
Create M5 Batch + Jobs
        ↓
Enqueue
```

Insufficient quota:

```text
USAGE_LIMIT_EXCEEDED
```

No provider work should be created.

---

# 25. Reservation Commit / Release

Recommended policy:

```text
Job never starts
→ release

Job starts logical RankCheck execution
→ commit
```

Provider no-match still counts.

Provider/internal retry does not double-charge.

Task redelivery does not double-charge.

---

# 26. Usage Idempotency

At-least-once M5 task delivery means usage accounting must also be idempotent.

The same Job must never commit usage twice.

Tie commit identity to stable Job/Reservation identity.

---

# 27. Usage Events

Recommended `usage_events` table:

```text
id
usage_period_id
user_id
device_scope

event_type
amount

job_id nullable
batch_id nullable
reservation_id nullable

created_at
```

Event types:

```text
commit
release
adjustment
```

---

# 28. Usage Adjustments

Admin can grant or correct usage in the current period.

Examples:

```text
+500 goodwill checks
-10 correction
```

Adjustments must be audited.

Do not edit aggregate counters silently.

---

# 29. Effective Limit

Conceptually:

```text
effective_limit =
plan_snapshot.monthly_keyword_checks
+ current_period_adjustments
```

---

# 30. Project Entitlement

On Project creation:

```text
resolve requested device scope
resolve active entitlement
count active Projects in same device scope
enforce max_projects
```

Error:

```text
PROJECT_LIMIT_EXCEEDED
```

---

# 31. Keyword Entitlement

Enforce `max_keywords` during:

```text
Project creation with initial Keywords
bulk Keyword add
Keyword reactivation
Project device change if supported
```

Count active Keywords across all active Projects of that device scope.

Error:

```text
KEYWORD_LIMIT_EXCEEDED
```

Bulk operations remain atomic.

---

# 32. Device Independence

Desktop resources use Desktop entitlements.

Mobile resources use Mobile entitlements.

Do not combine:

```text
Desktop Projects + Mobile Projects
```

into one count.

Do not combine Desktop and Mobile keyword quotas.

---

# 33. Schedule Entitlement

Before enabling schedule:

```text
scheduled_checks_enabled == true
```

Else:

```text
SCHEDULE_NOT_INCLUDED
```

Starter:

```text
weekly allowed
daily blocked
```

Pro:

```text
daily allowed
weekly allowed
```

Error:

```text
SCHEDULE_FREQUENCY_NOT_ALLOWED
```

---

# 34. Scheduled M5 Integration

Schedule dispatcher flow:

```text
due Project
    ↓
resolve device subscription
    ↓
validate schedule entitlement
    ↓
validate remaining monthly quota
    ↓
reserve usage
    ↓
create M5 Batch + Jobs
    ↓
enqueue
```

If insufficient quota:

```text
do not enqueue
```

Do not repeatedly retry every few minutes when monthly quota is exhausted.

---

# 35. Scheduled Partial Capacity

Example:

```text
Project active Keywords = 500
remaining quota = 200
```

Recommended:

```text
do not partially execute 200
```

Skip/reject the scheduled Batch atomically.

This preserves consistent rank-history cadence.

---

# 36. Downgrade Resource Behavior

Never delete customer data because of downgrade.

Example:

```text
Pro:
20 Projects
5000 Keywords

↓ downgrade

Starter:
5 Projects
500 Keywords
```

Existing resources remain readable.

New creation/reactivation is blocked until usage returns below limits.

---

# 37. Downgrade Schedule Behavior

If:

```text
Pro daily
→ Starter weekly
```

an incompatible daily schedule must be disabled safely.

Record audit event.

---

# 38. Subscription Expiry

When a paid device subscription expires:

```text
fallback to Free for that device scope
```

Example:

```text
Desktop Pro expires
→ Desktop Free effective
```

Paid history remains intact.

---

# 39. Upgrade / Downgrade Timing

M6A must support immediate Admin activation.

Recommended downgrade default:

```text
effective at current period end
```

Recommended upgrade options:

```text
immediate
next period
```

If only one mode is implemented initially, immediate activation is mandatory.

No automatic proration.

---

# 40. Immediate Upgrade Usage

Recommended:

```text
immediate upgrade
→ close old effective period
→ activate new Plan
→ start new usage period
→ fresh quota
```

No automated financial proration.

Admin handles payment differences externally.

---

# 41. Same-Plan Extension

Extending same Plan:

```text
extend period_end
```

Do not prematurely reset current monthly usage period.

---

# 42. Platform Admin

M6A introduces minimal platform-level Admin authorization.

Recommended:

```text
is_platform_admin
```

or equivalent.

Do NOT introduce:

```text
Organization
Workspace
Team
customer roles
```

Tenant model remains User-only.

---

# 43. Admin Security

Normal users must never access Admin billing APIs.

Admin checks must be backend-authoritative.

Frontend route hiding is not sufficient.

---

# 44. Admin Customer List

Add:

```text
/admin/customers
```

Display:

```text
email
Desktop Plan
Desktop status
Desktop usage
Mobile Plan
Mobile status
Mobile usage
account status
```

Support:

```text
email search
cursor pagination
```

---

# 45. Admin Customer Detail

Example:

```text
Customer: user@example.com

Desktop
Plan: Starter
Status: Active
Period: 12 Sep → 12 Oct
Usage: 3,200 / 5,000
Projects: 3 / 5
Keywords: 410 / 500

Mobile
Plan: Free
Status: Active
Usage: 12 / 50
Projects: 1 / 1
Keywords: 8 / 20
```

Actions:

```text
Activate Plan
Change Plan
Extend
Cancel
View Subscription History
View Usage
Adjust Usage
```

---

# 46. Admin Activation Form

Fields:

```text
Plan
period_start
period_end
payment_method
payment_reference
internal_note
```

Paid Plan:

```text
payment_method = manual_bank_transfer
```

Free Plan:

```text
no payment required
```

Device scope is derived from selected Plan.

---

# 47. Admin Changes Are Device-Specific

Changing Desktop Plan must not alter Mobile Plan.

Changing Mobile Plan must not alter Desktop Plan.

---

# 48. Subscription History

Never overwrite commercial history.

Track:

```text
Free → Starter → Pro → Starter
```

with:

```text
effective period
Plan snapshots
payment method
payment reference
Admin actor
timestamps
```

---

# 49. Billing Audit Log

Recommended table:

```text
billing_audit_events
```

Fields:

```text
id
actor_user_id
target_user_id
event_type
device_scope
subscription_id nullable
plan_id nullable
safe_metadata JSON
created_at
```

---

# 50. Audit Events

Examples:

```text
subscription_activated
subscription_extended
subscription_upgraded
subscription_downgraded
subscription_cancelled
subscription_expired
schedule_disabled_due_to_plan
usage_adjusted
```

---

# 51. Customer Billing & Usage UI

Add:

```text
/settings/billing
```

Show separately:

```text
Desktop
Mobile
```

For each:

```text
Plan
price
status
period
Projects used / limit
Keywords used / limit
monthly checks used / limit
reserved checks if useful
remaining checks
next reset
schedule entitlement
```

---

# 52. Pricing UI

Optional but recommended:

```text
/pricing
```

Group Plans:

```text
Desktop Rank Tracking
Free | Starter | Pro

Mobile Rank Tracking
Free | Starter | Pro
```

No automated checkout.

CTA may be:

```text
Contact / Bank Transfer
```

---

# 53. No Self-Service Paid Activation

End users must NOT be able to:

```text
activate Plan
mark payment complete
change payment reference
grant usage
```

Only platform Admin can activate paid subscriptions in M6A.

---

# 54. Usage Limit Error

Suggested response:

```json
{
  "code": "USAGE_LIMIT_EXCEEDED",
  "limit": 5000,
  "used": 4800,
  "reserved": 100,
  "remaining": 100,
  "requested": 250
}
```

Do not expose:

```text
Serper credits
SerpApi credits
provider cost
Cloud Tasks cost
```

---

# 55. Stable Error Codes

Add at least:

```text
PLAN_NOT_FOUND
NO_ACTIVE_SUBSCRIPTION
SUBSCRIPTION_EXPIRED
SUBSCRIPTION_CONFLICT
INVALID_SUBSCRIPTION_PERIOD

PROJECT_LIMIT_EXCEEDED
KEYWORD_LIMIT_EXCEEDED
USAGE_LIMIT_EXCEEDED

SCHEDULE_NOT_INCLUDED
SCHEDULE_FREQUENCY_NOT_ALLOWED
PLAN_DEVICE_MISMATCH

ADMIN_REQUIRED
```

---

# 56. M5 Integration

Rank-check flow becomes:

```text
Authenticate
    ↓
Ownership
    ↓
Project/Keyword validation
    ↓
Resolve device entitlement
    ↓
Reserve logical usage
    ↓
Create M5 Batch/Jobs
    ↓
Enqueue
    ↓
Worker
    ↓
ProviderRouter
    ↓
Rank persistence
```

---

# 57. Reservation Compensation

If Batch creation or enqueue permanently fails after reservation:

```text
release unused reservation
```

Do not leak quota because of infrastructure failure.

---

# 58. Batch Cancellation

For cancelled Batch:

```text
not-started Jobs
→ release unused reservation

started Jobs
→ committed usage remains
```

Partial batches require proportional reconciliation.

---

# 59. Provider Budgets Stay Separate

Customer quota:

```text
monthly_keyword_checks
```

Infrastructure safety:

```text
SERPER_REQUEST_BUDGET
SERPAPI_REQUEST_BUDGET
```

Do not merge these models.

---

# 60. Plan Prices Are Explicit Data

M6A does not dynamically calculate selling price from provider cost.

Provider costs may inform future business decisions, but Plan prices stay explicit.

---

# 61. Future M6B Compatibility

Future:

```text
Stripe / other payment gateway
        ↓
SubscriptionService
        ↓
same Plan / Subscription / Entitlement / Usage model
```

Payment integration becomes another source of subscription state, not a replacement architecture.

---

# 62. Customer Billing API

Suggested:

```text
GET /api/v1/billing/plans
GET /api/v1/billing/me
GET /api/v1/billing/me/usage
```

No paid-activation mutation endpoint for normal users.

---

# 63. Admin Billing API

Suggested:

```text
GET  /api/v1/admin/customers
GET  /api/v1/admin/customers/{user_id}/billing

GET  /api/v1/admin/customers/{user_id}/subscriptions
POST /api/v1/admin/customers/{user_id}/subscriptions

POST /api/v1/admin/customers/{user_id}/subscriptions/{subscription_id}/extend
POST /api/v1/admin/customers/{user_id}/subscriptions/{subscription_id}/cancel

GET  /api/v1/admin/customers/{user_id}/usage
POST /api/v1/admin/customers/{user_id}/usage-adjustments
```

Adapt routes to current repository conventions.

---

# 64. Activation Request Example

```json
{
  "plan_code": "desktop_starter",
  "period_start": "2026-09-12T00:00:00Z",
  "period_end": "2026-10-12T00:00:00Z",
  "payment_method": "manual_bank_transfer",
  "payment_reference": "BANK-20260912-001",
  "note": "Payment verified"
}
```

Do not accept a conflicting separately supplied device scope.

---

# 65. Reconciliation

Create reusable service:

```text
reconcile_subscriptions(now)
```

Responsibilities:

```text
expire ended subscriptions
activate scheduled subscriptions
ensure Free fallback
create/advance usage periods
disable incompatible schedules after downgrade/expiry
```

Can run:

```text
lazily during entitlement resolution
+
periodically through existing M5 maintenance/scheduler mechanism
```

No new always-on service.

---

# 66. Migration

Create the next migration after M5.

Expected conceptually:

```text
0008_billing_usage_limits
```

Use actual repository head.

Create at minimum:

```text
plans
subscriptions
usage_periods
usage_reservations
usage_events
billing_audit_events
```

plus platform-Admin authorization field/table.

Do not edit previous migrations.

---

# 67. Existing Users

After migration, all existing Users must have effective:

```text
Desktop Free
Mobile Free
```

Do not leave existing users without entitlement.

---

# 68. Existing Projects

Existing Projects already have a device.

Classify them under the corresponding effective Free entitlement.

If user already exceeds Free resource limits:

```text
preserve data
mark over-limit
block expansion
```

Do not delete anything.

---

# 69. Existing M5 Schedules

If existing user has schedules but Free Plan does not allow scheduling:

```text
disable incompatible schedules
```

and record safe audit/reason metadata.

Do not allow free scheduled provider spend to continue accidentally.

---

# 70. Existing Ranking History

M6A must not rewrite or delete:

```text
RankChecks
RankCheckResults
Rankings
provider attempts
provider usage
Batch/Job history
```

---

# 71. Concurrency Safety

Test and protect:

```text
two Admin activations same device
two simultaneous Rank Check requests
manual + scheduled check race
usage reservation race
```

Use PostgreSQL row locking / atomic updates as appropriate.

---

# 72. Repository / Service Boundaries

Recommended structure:

```text
models/
  plan.py
  subscription.py
  usage_period.py
  usage_reservation.py
  usage_event.py
  billing_audit_event.py

repositories/
  plan.py
  subscription.py
  usage.py
  billing_audit.py

services/billing/
  entitlements.py
  subscriptions.py
  usage.py
  reconciliation.py
```

Adapt to current codebase conventions.

Do not put SQLAlchemy queries in route handlers.

---

# 73. Frontend Structure

Suggested:

```text
features/billing/
features/admin/customers/
features/admin/billing/
```

Keep Admin billing actions separate from normal Project UI.

---

# 74. Backend Tests — Plans

Test:

```text
six Plans seeded
unique stable codes
correct device scope
correct price
correct entitlements
inactive Plan cannot be newly activated
```

---

# 75. Backend Tests — Subscription

Test:

```text
Desktop + Mobile simultaneous active subscriptions
second active subscription same device rejected
manual activation
extension
immediate upgrade
scheduled downgrade
expiration
Free fallback
history retained
payment reference safely retained
Admin authorization
```

---

# 76. Backend Tests — Resource Entitlements

Test:

```text
Desktop max_projects
Mobile max_projects
independent counts
Desktop max_keywords
Mobile max_keywords
bulk Keyword atomic rejection
reactivation enforcement
Project device change enforcement
downgrade preserves existing data
```

---

# 77. Backend Tests — Usage

Test:

```text
reservation success
insufficient quota
concurrent reservation race
commit
release
duplicate commit idempotency
Batch cancellation release
partial Batch reconciliation
provider fallback still counts one logical check
usage reset
usage adjustment
```

---

# 78. Backend Tests — Schedule

Test:

```text
Free schedule blocked
Starter weekly allowed
Starter daily blocked
Pro daily allowed
downgrade disables invalid schedule
scheduled dispatcher checks quota
insufficient scheduled quota creates no Batch
```

---

# 79. M5 Integration Tests

Test:

```text
quota reserved before Batch enqueue
no quota means no Batch/provider work
enqueue failure compensates reservation
worker start commits usage
task replay does not double-charge
cancelled non-started Job releases quota
```

---

# 80. Frontend Customer Tests

Test:

```text
Billing & Usage page
Desktop Plan
Mobile Plan
prices
usage counters
reset dates
schedule entitlement
limit errors
no Admin mutation actions
```

---

# 81. Frontend Admin Tests

Test:

```text
customer list
search/pagination
customer Billing detail
activate Desktop Plan
activate Mobile Plan
extend
upgrade
downgrade
cancel
history
usage adjustment
payment reference
normal user denied
```

---

# 82. Browser Verification — Customer

Deterministic local journey:

```text
register/login
effective Free Plans
create allowed Desktop Project
hit Project/Keyword limits
perform Rank Check
verify logical usage increments
verify Billing & Usage page
verify Desktop/Mobile quotas remain separate
```

Use fake provider and local task queue.

---

# 83. Browser Verification — Admin

```text
login as platform Admin
open customer list
open customer detail
activate Desktop Starter
enter bank-transfer reference
verify entitlement
activate Mobile Starter independently
extend/change one device Plan
verify other device unchanged
review history
review usage
```

---

# 84. Zero-Cost Verification

Normal M6A verification must consume:

```text
0 payment-provider calls
0 real Cloud Tasks operations
0 real Serper credits
0 real SerpApi credits
```

---

# 85. Security Verification

Verify:

```text
normal user cannot access Admin API
normal user cannot activate own paid Plan
normal user cannot forge payment state
normal user cannot modify usage
cross-user billing read blocked
cross-user subscription mutation blocked
task payload cannot bypass entitlement
Admin notes hidden from customer
payment reference handled safely
secrets not logged
```

---

# 86. Recommended Indexes

Plans:

```text
UNIQUE(code)
(device_scope, active, display_order)
```

Subscriptions:

```text
(user_id, device_scope, status)
(user_id, period_end)
```

Usage:

```text
(subscription_id, period_start)
(user_id, device_scope, period_start)
```

Reservations:

```text
(usage_period_id, status)
(batch_id)
```

Audit:

```text
(target_user_id, created_at DESC)
```

---

# 87. Definition of Done — Plans

```text
[ ] six initial Plans seeded
[ ] Desktop and Mobile product lines are separate
[ ] prices stored as data
[ ] entitlements stored as data
[ ] no Plan numbers hard-coded into enforcement
```

---

# 88. Definition of Done — Subscription

```text
[ ] manual subscription source
[ ] manual bank-transfer metadata
[ ] one active subscription per user/device
[ ] Desktop + Mobile can coexist
[ ] activation
[ ] extension
[ ] upgrade
[ ] downgrade
[ ] cancellation
[ ] expiration
[ ] Free fallback
[ ] commercial snapshots/history
```

---

# 89. Definition of Done — Admin

```text
[ ] platform Admin authorization
[ ] customer list
[ ] customer Billing detail
[ ] activate/change Desktop Plan
[ ] activate/change Mobile Plan independently
[ ] bank-transfer reference
[ ] extend/cancel
[ ] subscription history
[ ] usage view
[ ] audited usage adjustment
[ ] normal users cannot access
```

---

# 90. Definition of Done — Usage

```text
[ ] monthly logical Keyword checks enforced
[ ] Desktop/Mobile usage separate
[ ] atomic reservation
[ ] commit/release
[ ] replay idempotency
[ ] remaining includes reservations
[ ] Batch cancellation reconciliation
[ ] provider retry/fallback does not double-charge
[ ] adjustments audited
```

---

# 91. Definition of Done — Resource Entitlements

```text
[ ] max_projects enforced per device
[ ] max_keywords enforced per device
[ ] bulk operations atomic
[ ] schedule enabled enforced
[ ] schedule frequency enforced
[ ] Project device change cannot bypass limits
[ ] downgrade never deletes customer data
[ ] over-limit user cannot expand resources
```

---

# 92. Definition of Done — M5 Integration

```text
[ ] entitlement check occurs before enqueue
[ ] usage reserved before enqueue
[ ] insufficient quota creates no provider work
[ ] scheduled checks enforce Plan + quota
[ ] task replay does not double-charge
[ ] enqueue failure releases unused reservation
[ ] existing Batch/Job progress remains intact
```

---

# 93. Definition of Done — Customer UI

```text
[ ] Billing & Usage page
[ ] Desktop Plan
[ ] Mobile Plan
[ ] price
[ ] status
[ ] period
[ ] Project usage
[ ] Keyword usage
[ ] monthly checks
[ ] next reset
[ ] schedule entitlement
[ ] no Admin mutation actions
```

---

# 94. Definition of Done — Quality

```text
[ ] backend full suite passes
[ ] frontend full suite passes
[ ] billing tests pass
[ ] usage concurrency tests pass
[ ] subscription transition tests pass
[ ] M5 integration tests pass
[ ] customer browser flow passes
[ ] Admin browser flow passes
[ ] Ruff passes
[ ] Ruff format passes
[ ] mypy strict passes
[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes
[ ] npm audit acceptable
[ ] production builds pass
[ ] migration tests pass
[ ] alembic check passes
[ ] Docker services healthy
```

---

# 95. Definition of Done — Regression

```text
[ ] M1 regression
[ ] M2 regression
[ ] M3/M3.1 regression
[ ] M4 regression
[ ] M4.1 regression
[ ] M5 regression
[ ] ProviderRouter unchanged
[ ] DomainMatcher unchanged
[ ] ranking history unchanged
[ ] worker idempotency unchanged
[ ] schedules continue working for entitled Plans
```

---

# 96. Verification Report

Create:

```text
docs/verification-milestone-6a.md
```

Include:

```text
implementation summary
Desktop/Mobile Plan architecture
seeded Plans and prices
subscription model
manual bank-transfer workflow
subscription snapshots/history
usage-period semantics
reservation/commit/release
resource enforcement
schedule enforcement
M5 integration
Admin authorization/UI
customer Billing UI
migration
existing-user migration
existing Project/Schedule compatibility
files changed
exact commands
exact test counts
browser verification
security verification
production builds
schema drift
Docker health
M1–M5 regression
known limitations
full DoD checklist
```

Do not claim a check passed unless actually executed.

---

# 97. Expected Known Limitations

```text
manual payment collection
manual bank-transfer verification
no Stripe
no crypto payment gateway
no automatic recurring billing
no invoice/tax engine
no refund/proration automation
no coupons
no overage billing
no annual pricing automation
no enterprise custom entitlement overrides
no automatic provider-cost-based pricing
no self-service paid activation
```

---

# 98. Roadmap

```text
M1    Foundation                                  ✅
M2    Authentication                              ✅
M3    Projects + Keywords                         ✅
M3.1  Tracked Sites + Domain Aliases              ✅
M4    SERP Provider + Ranking Engine               ✅
M4.1  Multi-provider Routing                       ✅
M5    Cloud Tasks + Cloud Run Worker               current/finalizing
M6A   Billing + Manual Subscription + Usage Limits ← next
M6B   Payment Gateway Integration                  future
M7    Ranking Dashboard + Analytics                future
M8    Production Cloud Deployment                  future
```

---

# 99. Final Architecture

```text
Platform Admin
      │
      │ confirms manual bank transfer
      ▼
Admin Billing UI
      │
      ▼
SubscriptionService
      │
      ├───────────────┐
      ▼               ▼
Desktop Plan      Mobile Plan
      │               │
      └───────┬───────┘
              ▼
      EntitlementService
              │
              ▼
         UsageService
              │
      reserve logical checks
              │
              ▼
        M5 Batch / Jobs
              │
              ▼
         Cloud Tasks
              │
              ▼
       Cloud Run Worker
              │
              ▼
        ProviderRouter
        ┌─────┴─────┐
        ▼           ▼
     Serper      SerpApi
              │
              ▼
      Ranking persistence
```

---

# 100. Final Instruction to Codex

Implement this M6A specification against the CURRENT M5 repository.

The repository and current migrations are the source of truth.

Before changing code, inspect:

```text
all M1–M5 specs
all available verification reports
README
current User/auth model
Project.device behavior
Project/Keyword repositories
M5 Batch/Job implementation
M5 schedule implementation
worker idempotency
ProviderRouter and provider budgets
current migrations
frontend routing/navigation
existing tests
```

Critical rules:

```text
1. No payment gateway in M6A.

2. Paid subscriptions are activated manually by platform Admin
   after external bank-transfer confirmation.

3. Desktop and Mobile are separate product lines.

4. Six initial Plans:
   Desktop Free / Starter / Pro
   Mobile Free / Starter / Pro.

5. One active Desktop subscription and one active Mobile subscription
   may coexist for a customer.

6. Never allow two simultaneous active subscriptions for the same device scope.

7. Project.device determines which subscription and quota apply.

8. Customer usage counts logical Keyword Rank Checks, not provider HTTP requests.

9. Provider retries/fallback must never double-charge usage.

10. Usage must be atomically reserved before M5 Batch/Job enqueue.

11. M5 task replay must never double-charge usage.

12. Cancelled/non-executed work releases unused reservation.

13. max_projects and max_keywords are enforced independently by device.

14. Schedule entitlements and schedule frequency must be enforced.

15. Downgrades must never delete customer Projects, Keywords, or ranking history.

16. Over-limit existing resources remain readable; new expansion is blocked.

17. Incompatible schedules are disabled safely after downgrade/expiry.

18. Admin authorization must be server-side.

19. End users cannot self-activate paid Plans or forge payment state.

20. Plan prices and entitlement values are data, not hard-coded branches.

21. Historical Subscription commercial terms must be preserved.

22. Existing users must receive effective Desktop Free and Mobile Free entitlements.

23. Existing M5 asynchronous execution semantics must remain intact.

24. Do not implement Stripe, crypto payment, PayPal, billing webhooks,
    coupons, overage charging, or M7 analytics.
```

Before completion:

```text
run full backend suite
run full frontend suite

run Plan/subscription tests
run usage reservation concurrency tests
run resource entitlement tests
run schedule entitlement tests
run Admin authorization/security tests
run M5 integration/idempotency tests

run migration tests
run alembic check

run existing M1–M5 smoke tests
run Billing/Usage smoke
run Admin billing smoke

run customer Billing browser journey
run Admin subscription browser journey

run lint
run formatting
run strict typing
run npm audit

build backend production image
verify worker production build/command
build frontend production bundle

verify Docker health
verify all regressions
```

Create:

```text
docs/verification-milestone-6a.md
```

Do not claim a check passed unless actually executed.

Normal M6A verification must consume:

```text
0 real payment-provider operations
0 real Cloud Tasks operations unless explicitly opted in
0 real Serper/SerpApi credits
```
