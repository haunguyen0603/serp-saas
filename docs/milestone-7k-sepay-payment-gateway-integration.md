# Milestone 7K — SePay Payment Gateway Integration

## 1. Objective

Integrate SePay as the first real payment gateway for SERP SaaS and connect it to the authenticated `Change Plan` flow created in M7J.

Primary user flow:

```text
User logs in
→ opens Change Plan
→ chooses a non-current paid plan
→ SERP SaaS creates an internal payment order
→ backend creates signed SePay checkout data
→ user is sent to SePay checkout
→ user completes / fails / cancels payment
→ SePay sends IPN to SERP SaaS
→ backend verifies and reconciles payment
→ subscription is activated or extended idempotently
→ app displays final payment/subscription state
```

This milestone implements **one-time payment** only.

Do not implement recurring/autopay subscription charging because SePay currently documents recurring payment as not yet generally available.

Reference documentation:

- SePay quick start: `https://developer.sepay.vn/vi/cong-thanh-toan/bat-dau`
- Payment flow: `https://developer.sepay.vn/vi/cong-thanh-toan/luong-thanh-toan`
- IPN: `https://developer.sepay.vn/vi/cong-thanh-toan/IPN`
- Checkout form: `https://developer.sepay.vn/vi/cong-thanh-toan/API/don-hang/form-thanh-toan`
- Void transaction: `https://developer.sepay.vn/vi/cong-thanh-toan/API/giao-dich/huy-giao-dich`

## 2. Core architectural rule

Payment activation must be **server-authoritative**.

Never trust:

```text
frontend price
frontend currency
frontend plan limits
frontend success redirect
frontend query string
client-provided user_id
```

The backend must determine the authenticated user, selected plan, product line, price, currency, billing period and subscription mutation from trusted server-side state.

## 3. Payment model

M7K implements one-time plan purchase, not recurring automatic rebilling.

Recommended supported flow:

```text
Free → Paid
Paid → higher Paid plan
Paid → same Paid plan extension/renewal
```

Do not auto-downgrade an active paid user to a lower paid plan unless existing billing rules explicitly define that transition. If downgrade policy is not already defined, keep paid downgrade disabled in M7K and document it as follow-up.

## 4. Change Plan integration

M7J currently has non-transactional `Select` actions.

In M7K:

```text
Current Plan
→ remains disabled

Eligible paid target plan
→ Select / Upgrade
→ creates checkout

Unsupported downgrade
→ disabled or informational state
```

Do not expose a payment action for a plan if pricing/currency is not compatible with SePay requirements.

## 5. SePay environment configuration

Create backend-only configuration:

```text
SEPAY_ENABLED=true
SEPAY_ENV=sandbox
SEPAY_MERCHANT_ID=
SEPAY_SECRET_KEY=
SEPAY_IPN_SECRET_KEY=
SEPAY_CHECKOUT_URL=
SEPAY_VOID_URL=
SEPAY_SUCCESS_URL=
SEPAY_ERROR_URL=
SEPAY_CANCEL_URL=
```

Production examples from the supplied SePay docs:

```text
SEPAY_ENV=production
SEPAY_CHECKOUT_URL=https://pay.sepay.vn/v1/checkout/init
SEPAY_VOID_URL=https://pgapi.sepay.vn/v1/order/voidTransaction
```

Do not assume undocumented sandbox endpoint values. Configure exact Sandbox endpoints from the active merchant setup.

## 6. Secret handling

`SEPAY_SECRET_KEY` must never be exposed to frontend code.

Do not place it in:

```text
NEXT_PUBLIC_*
browser JS
HTML
API responses
logs
Git
Docker image layers
committed test fixtures
```

Production storage:

```text
Google Secret Manager
→ injected into Cloud Run backend
```

Sandbox may use local `.env` outside version control.

The user does not need to provide real secrets to Codex during implementation.

## 7. Currency constraint

The supplied SePay checkout documentation currently supports `VND` for checkout form currency.

Therefore M7K must explicitly resolve the relationship between current SERP SaaS plan pricing and VND.

If production plans are currently stored in USD:

```text
DO NOT convert USD to VND in the browser.
DO NOT use implicit live FX.
```

Preferred policy: add trusted VND checkout prices to the billing catalog/commercial configuration, or otherwise define a deterministic server-side VND amount for every payable plan.

Do not start real payment until the backend has a deterministic VND amount for every payable plan.

## 8. Payment order persistence

Create an internal payment order before sending the user to SePay.

Recommended table:

```text
payment_orders
```

Suggested fields:

```text
id UUID PK
user_id FK users
provider
provider_environment
invoice_number UNIQUE
product_line
plan_id / plan_code
plan_name_snapshot
currency
amount_minor
status
provider_order_id nullable
provider_transaction_id nullable
payment_method nullable
provider_order_status nullable
provider_transaction_status nullable
provider_payload_snapshot nullable JSONB
failure_code nullable
failure_message nullable
created_at
updated_at
paid_at nullable
cancelled_at nullable
failed_at nullable
expires_at nullable
```

Recommended internal statuses:

```text
pending
checkout_created
paid
failed
cancelled
voided
expired
review_required
```

## 9. Commercial snapshot

Payment order must snapshot the commercial terms at checkout creation.

At minimum:

```text
plan code
plan name
device/product line
currency
amount
billing duration
entitlements if current billing architecture normally snapshots them
```

Do not rely on reading a mutable catalog later to decide what a historical payment purchased.

Keep this consistent with the existing M6A commercial snapshot model.

## 10. Invoice number

SePay requires `order_invoice_number` to be unique.

Generate server-side.

Example:

```text
PAY_<ULID>
```

Requirements:

- unique DB constraint;
- not user-controlled;
- not based only on timestamp;
- immutable after checkout creation;
- new invoice for a new payment attempt.

## 11. Checkout creation endpoint

Recommended authenticated endpoint:

```text
POST /api/v1/billing/payments/sepay/checkout
```

Request:

```json
{
  "plan_id": "...",
  "product_line": "desktop"
}
```

Do not accept trusted values for:

```text
amount
price
currency
user_id
entitlements
subscription expiry
```

Backend flow:

```text
1. authenticate user
2. require verified email
3. load target plan from catalog
4. validate active/purchasable plan
5. validate product line
6. validate transition policy
7. determine VND amount server-side
8. create payment_orders row
9. generate SePay checkout fields
10. sign fields using backend SECRET_KEY
11. return safe checkout form data
```

## 12. Checkout form fields

SePay documents these checkout fields:

```text
order_amount
merchant
currency
operation
order_description
order_invoice_number
customer_id
payment_method
success_url
error_url
cancel_url
```

For M7K:

```text
operation = PURCHASE
currency = VND
```

Recommended:

```text
customer_id = internal stable user/payment customer reference
```

Avoid putting raw sensitive account data into checkout fields.

If you want SePay to show merchant-enabled methods, omit `payment_method` rather than forcing a specific method.

## 13. Signature generation

Implement signature exactly according to SePay's documented field order:

```text
order_amount
merchant
currency
operation
order_description
order_invoice_number
customer_id
payment_method
success_url
error_url
cancel_url
```

Signature algorithm:

```text
HMAC-SHA256
→ raw binary digest
→ Base64 encoding
```

Signed string concept:

```text
field1=value1,field2=value2,...
```

Only include fields that are present, preserving the documented order.

Do not alphabetically sort fields.

Do not sign in frontend.

Create isolated testable code such as:

```text
SePayCheckoutSigner
```

## 14. Checkout response to frontend

Recommended backend response:

```json
{
  "payment_order_id": "...",
  "invoice_number": "...",
  "checkout_url": "...",
  "form": {
    "order_amount": "...",
    "merchant": "...",
    "currency": "VND",
    "operation": "PURCHASE",
    "order_description": "...",
    "order_invoice_number": "...",
    "success_url": "...",
    "error_url": "...",
    "cancel_url": "...",
    "signature": "..."
  }
}
```

Frontend builds and submits a POST form directly to the configured SePay checkout endpoint.

Never expose `SECRET_KEY`.

## 15. Checkout endpoint ambiguity

The supplied SePay docs currently show both:

```text
https://pgapi.sepay.vn/v1/checkout/init
```

and example/go-live usage of:

```text
https://pay.sepay.vn/v1/checkout/init
```

Therefore:

- do not hard-code by inference;
- configure `SEPAY_CHECKOUT_URL`;
- use the exact Sandbox endpoint from merchant integration setup during test;
- use the exact Production endpoint confirmed by SePay/merchant setup during go-live;
- document the endpoint used in verification without exposing credentials.

## 16. User callback URLs

Recommended routes:

```text
https://app.serpsaas.com/app/change-plan/payment/success
https://app.serpsaas.com/app/change-plan/payment/error
https://app.serpsaas.com/app/change-plan/payment/cancel
```

These are user-facing result pages only.

They are **not payment proof**.

## 17. Success page

Success redirect must not directly activate subscription.

Recommended UI:

```text
fetch internal payment status

if paid:
  show Payment successful
  show active plan

if pending:
  show Payment received, confirming...
  bounded polling/refetch

if failed/cancelled/review_required:
  show actual backend state
```

Do not state payment success solely because SePay redirected to `success_url`.

## 18. Error page

Fetch internal payment state and display a non-success result.

Offer:

```text
Return to Change Plan
```

Do not mutate subscription and do not automatically retry payment.

## 19. Cancel page

Do not overwrite a backend `paid` order merely because the browser visited cancel page.

Recommended copy:

```text
Payment cancelled
Your subscription has not changed.
[ Return to Change Plan ]
```

The payment-order state remains server-authoritative.

## 20. IPN endpoint

Create a public backend endpoint:

```text
POST /api/v1/billing/payments/sepay/ipn
```

Requirements:

- publicly reachable over HTTPS;
- no user JWT/session required;
- provider authentication required;
- fast response;
- return HTTP 200 after successful processing/acknowledgement.

## 21. IPN authentication

The supplied SePay docs support:

```text
X-Secret-Key
```

when merchant IPN auth type is configured as:

```text
SECRET_KEY
```

M7K should use this mode.

Compare incoming `X-Secret-Key` against:

```text
SEPAY_IPN_SECRET_KEY
```

using constant-time comparison where practical.

Invalid/missing key:

```text
401 Unauthorized
```

Never log the secret.

## 22. IPN supported events

At minimum handle:

```text
ORDER_PAID
TRANSACTION_VOID
```

### ORDER_PAID

Main subscription activation event.

### TRANSACTION_VOID

Record/reconcile financial state.

Do not automatically roll back an already consumed subscription unless business semantics are explicitly defined.

## 23. ORDER_PAID validation

Before activating a subscription, validate the event against the internal payment order.

Minimum checks:

```text
notification_type == ORDER_PAID
invoice number matches
internal order exists
order_status == CAPTURED
transaction_status == APPROVED
transaction_type == PAYMENT
order_currency == expected currency
transaction_currency == expected currency
order_amount == expected amount
transaction_amount == expected amount
```

Do not accept amount mismatch.

## 24. Money handling

Use exact decimal/integer values, never binary floating point.

Recommended internal representation:

```text
amount_minor = integer VND amount
```

Normalize SePay strings such as:

```text
"100000.00"
"100000"
```

to exact values before comparison.

## 25. IPN idempotency

IPN processing must be idempotent.

Use provider identifiers where available:

```text
transaction.id
transaction.transaction_id
order.id
invoice_number
```

Recommended table:

```text
payment_events
```

Suggested fields:

```text
id
provider
event_key UNIQUE
notification_type
payment_order_id
raw_payload JSONB
received_at
processed_at
processing_result
```

Repeated identical `ORDER_PAID` must:

```text
return 200
not extend subscription twice
not duplicate billing history
```

## 26. Atomic transaction

Process successful payment atomically:

```text
BEGIN
lock payment order

if already paid/processed:
    return idempotent success

validate event
mark payment order paid
store provider IDs/status
activate/extend subscription
write subscription history/audit

COMMIT
```

If activation fails:

```text
ROLLBACK
```

Do not leave financial/subscription state partially committed.

## 27. Subscription service reuse

Reuse the existing billing/subscription service.

Do not duplicate subscription business logic in the payment router.

Recommended:

```text
PaymentService
→ SubscriptionService.activate_from_payment(...)
```

The billing layer remains responsible for activation, extension, expiry and history semantics.

## 28. Same-plan renewal

If the same paid plan can be purchased again, define behavior explicitly.

Recommended if consistent with current M6A rules:

```text
active subscription → extend from current expiry
expired/free → start from confirmed paid time
```

Do not invent renewal semantics if current billing rules differ.

## 29. Upgrade policy

For active paid → higher plan, inspect current manual admin `Change/Activate/Extend` rules and reuse them.

Do not invent proration.

If there is no existing policy, require explicit product decision before implementation.

## 30. Downgrade policy

Safe M7K default:

```text
Free → Paid: allowed
Paid → higher Paid: allowed if policy defined
Paid → same Paid renewal: allowed if policy defined
Paid → lower Paid: unavailable / contact support
Paid → Free: no payment checkout
```

## 31. Payment status endpoint

Add authenticated read endpoint:

```text
GET /api/v1/billing/payments/{payment_order_id}
```

User may only access their own payment order.

Example response:

```json
{
  "id": "...",
  "invoice_number": "...",
  "status": "paid",
  "product_line": "desktop",
  "plan_code": "desktop_pro",
  "amount": 2490000,
  "currency": "VND",
  "created_at": "...",
  "paid_at": "..."
}
```

Do not return secret/provider-sensitive fields unnecessarily.

## 32. Database migration

Create migration for payment persistence.

Likely:

```text
payment_orders
payment_events
```

Potential constraints:

```text
UNIQUE(invoice_number)
UNIQUE(provider, provider_transaction_id) WHERE not null
FK user_id
```

Indexes:

```text
user_id, created_at
status
invoice_number
provider_transaction_id
```

## 33. Provider abstraction

Avoid coupling subscription domain logic directly to SePay.

Recommended interface:

```text
PaymentProvider
├── create_checkout(...)
├── verify_ipn(...)
└── normalize_event(...)
```

Implementation:

```text
SePayPaymentProvider
```

Do not overbuild a generic multi-gateway platform yet.

## 34. Backend service structure

Recommended components:

```text
PaymentOrderRepository
PaymentEventRepository
PaymentService
SePayCheckoutSigner
SePayPaymentProvider
SubscriptionService (existing/reused)
```

Keep FastAPI routers thin.

## 35. Pending-order control

Prevent uncontrolled stale payment attempts.

A simple first version may:

```text
create one unique payment order per explicit click
expire old pending attempts after a configured window
```

Do not reuse invoice numbers.

## 36. Payment order expiry

Define internal pending-order expiry, e.g. 30–60 minutes.

This is an internal UX/state concept, not proof that SePay cannot later send a legitimate paid event.

If a valid payment arrives late, do not silently discard it. Either safely reconcile it or mark `review_required`.

## 37. Reconciliation state

Use a safe state such as:

```text
review_required
```

for inconsistencies such as:

```text
amount mismatch
unknown invoice
late paid event with invalid snapshot
provider conflict
void after activation
```

Do not activate subscription automatically when validation is inconsistent.

## 38. Logging

Structured logs may include:

```text
payment_order_id
invoice_number
provider
notification_type
provider_transaction_id
status transition
```

Never log:

```text
SEPAY_SECRET_KEY
SEPAY_IPN_SECRET_KEY
raw Authorization
full card number
CVV
```

## 39. Card data minimization

SERP SaaS should rely on SePay-hosted checkout and should not handle raw card details.

If storing provider payload snapshots, redact unnecessary card fields and never persist full PAN/CVV.

## 40. Frontend checkout flow

On eligible plan Select:

```text
button loading
→ POST checkout endpoint
→ receive signed form data
→ construct hidden POST form
→ submit to SePay
```

Disable duplicate clicks while checkout creation is pending.

If checkout creation fails, leave subscription unchanged.

## 41. Result routes

Recommended routes:

```text
/app/change-plan/payment/success
/app/change-plan/payment/error
/app/change-plan/payment/cancel
```

The separate backend IPN route must remain provider-callable without user login.

## 42. Polling after success redirect

Because redirect and IPN can arrive in either order:

```text
GET payment status
```

If still pending, poll with bounded retries, e.g. every 2–3 seconds for up to ~30–60 seconds.

Stop on:

```text
paid
failed
cancelled
review_required
timeout
```

Do not poll indefinitely.

## 43. Change Plan refresh

After status becomes `paid`, invalidate/refetch:

```text
billing/me
usage/entitlements
relevant subscription queries
```

The new plan should appear current without logout/login.

## 44. Free plan

Free plan must never create SePay checkout.

If downgrade-to-Free behavior exists, use existing cancellation/end-of-term logic, not payment.

## 45. Payment methods

The supplied SePay docs list examples such as:

```text
CARD
BANK_TRANSFER
NAPAS_BANK_TRANSFER
```

For first release, prefer not forcing `payment_method` unless merchant configuration requires it. Let SePay show merchant-enabled methods.

## 46. Void transaction

The supplied SePay docs state void is only available when:

```text
payment_method = CARD
order_status = CAPTURED
before settlement
```

Endpoint:

```text
POST https://pgapi.sepay.vn/v1/order/voidTransaction
```

with `order_invoice_number` and Basic Auth.

### M7K scope

Do **not** expose void/refund functionality to normal users in M7K.

Recommended:

```text
persist TRANSACTION_VOID IPN
support reconciliation
follow up with M7K.1 for operator/admin void tooling
```

Do not call void automatically.

## 47. Refund semantics

Do not label void as a general refund.

Do not implement refund UI until separate SePay refund documentation and business policy are reviewed.

## 48. Sandbox first

M7K must be verified in Sandbox before Production.

Sandbox scenarios:

```text
successful payment
failed payment
cancelled payment
invalid IPN secret
duplicate IPN
amount mismatch fixture
unknown invoice fixture
success redirect before IPN
IPN before success redirect
```

Use sandbox credentials only.

## 49. Production secret setup

After implementation passes locally/Sandbox, operator manually configures:

```text
SEPAY_MERCHANT_ID
SEPAY_SECRET_KEY
SEPAY_IPN_SECRET_KEY
SEPAY_ENV=production
SEPAY_CHECKOUT_URL
SEPAY_VOID_URL
callback URLs
IPN URL
```

through Google Secret Manager / Cloud Run configuration.

Codex must not request real secrets in source or artifacts.

## 50. Production IPN URL

Recommended:

```text
https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn
```

Verify:

```text
POST
public HTTPS
no login redirect
no Cloud Run auth blocking this endpoint
```

while preserving application-level IPN secret authentication.

## 51. CORS / CSRF

IPN is server-to-server and does not rely on browser CORS.

Do not weaken global CORS.

Do not apply browser session/CSRF requirements to the IPN endpoint. Authenticate it via the SePay provider mechanism instead.

## 52. Manual subscription compatibility

Existing manual subscription activation must remain supported.

Payment-created subscription history should identify source:

```text
sepay
```

Manual admin activation remains:

```text
manual
```

Do not remove manual activation.

## 53. Audit trail

It must be possible to reconstruct:

```text
who paid
what plan
what product line
how much
which invoice
which provider transaction
when IPN arrived
when subscription changed
subscription state before/after
```

Do not overwrite historical payment records.

## 54. Domain errors

Recommended errors:

```text
PAYMENT_PLAN_NOT_FOUND
PAYMENT_PLAN_NOT_PURCHASABLE
PAYMENT_CURRENCY_UNSUPPORTED
PAYMENT_AMOUNT_INVALID
PAYMENT_TRANSITION_NOT_ALLOWED
PAYMENT_CHECKOUT_UNAVAILABLE
PAYMENT_ORDER_NOT_FOUND
PAYMENT_PROVIDER_AUTH_FAILED
PAYMENT_PROVIDER_EVENT_INVALID
PAYMENT_AMOUNT_MISMATCH
PAYMENT_CURRENCY_MISMATCH
```

Use existing API error conventions.

## 55. Tests — signature

Unit test deterministic signature generation with fixed fixtures.

Cover:

```text
required fields
optional customer_id
optional payment_method
missing optional fields
field ordering
unicode description
callback URLs
Base64 output
```

A test must fail if fields are alphabetically sorted instead of the documented order.

## 56. Tests — checkout

Cover:

```text
auth required
verified email required
valid paid plan
Free plan rejected
inactive plan rejected
wrong product line
frontend amount ignored/rejected
server amount used
unique invoice
commercial snapshot
secret never returned
```

## 57. Tests — IPN

Cover:

```text
missing secret → 401
invalid secret → 401
valid ORDER_PAID
wrong invoice
wrong amount
wrong currency
wrong order_status
wrong transaction_status
duplicate event
duplicate transaction ID
unknown notification type
TRANSACTION_VOID persistence
```

Critical assertion:

```text
duplicate valid ORDER_PAID activates/extends subscription exactly once
```

## 58. Tests — subscription

Cover:

```text
Free → paid activation
same-plan renewal if supported
paid → upgrade
unsupported downgrade
expired paid → paid
payment failure leaves subscription unchanged
cancel leaves subscription unchanged
```

Do not add proration unless it already exists by product policy.

## 59. Tests — frontend

Cover:

```text
Select starts checkout
loading prevents double-submit
checkout error leaves plan unchanged
signed fields POST to configured SePay URL
success paid
success pending + polling
success timeout
error page
cancel page
Change Plan refetch after paid
```

## 60. Browser QA

At:

```text
375
768
1024
1440
```

Verify Change Plan, checkout creation, result pages and current-plan refresh using safe fixtures/interception.

Automated QA must not make a real production payment.

## 61. Security/build gate

Run the normal backend/frontend gates, including:

```text
backend tests
frontend tests
lint
typecheck
format
production builds
npm audit --omit=dev
git diff --check
```

Preserve frontend runtime security:

```text
0 critical
0 high
```

## 62. Migration verification

Against a disposable database:

```text
Alembic upgrade head
Alembic downgrade one revision
Alembic upgrade head
```

Verify constraints/indexes.

## 63. Sandbox E2E

After sandbox credentials are configured:

```text
1. create checkout from Change Plan
2. redirect to SePay Sandbox
3. complete sandbox payment
4. receive IPN
5. payment order becomes paid
6. subscription activates exactly once
7. browser result page shows paid
8. Change Plan shows new current plan
9. repeated IPN does not change expiry again
```

Also verify cancel and failure scenarios.

## 64. Production go-live gate

Do not switch to Production until:

```text
Sandbox success passes
duplicate IPN passes
amount mismatch passes
callback pages pass
subscription state verified
real HTTPS IPN reachable
secrets stored in Secret Manager
production Merchant ID ready
production Secret Key ready
production IPN secret configured
production callback URLs configured
```

## 65. Production verification

Use a controlled real transaction only after explicit authorization.

Verify:

```text
checkout endpoint/URL
merchant
VND amount
IPN 200 acknowledgement
payment order paid
subscription activated once
provider transaction reference stored
result page
Change Plan current state
logs contain no secret
```

Never expose credentials in verification artifacts.

## 66. Observability

Where existing infrastructure allows, add structured events such as:

```text
payment_checkout_created
payment_checkout_failed
payment_ipn_received
payment_ipn_authenticated
payment_ipn_rejected
payment_paid
payment_duplicate_event
payment_reconciliation_required
subscription_activated_from_payment
```

Do not add a new observability platform solely for M7K.

## 67. Out of scope

Do not implement:

```text
automatic recurring billing
saved cards
customer card vault
general refund system
user-facing void
admin void button
chargeback workflow
coupons
promo codes
tax engine
VAT invoice generation
multiple payment gateways
wallet/balance
proration
team billing
organization billing
```

## 68. Recommended follow-up

Potential M7K.1:

```text
Payment Operations & Reconciliation
```

Possible scope:

```text
admin payment history
manual reconciliation
card void
refund workflow after reviewing SePay refund docs
payment retry/resend tooling
support dashboard
financial export
```

## 69. Definition of Done

- [ ] Payment order persistence exists.
- [ ] Unique invoice number enforced.
- [ ] Commercial snapshot persisted.
- [ ] SePay config is backend-only.
- [ ] No secret exposed to frontend/logs.
- [ ] Checkout creation endpoint implemented.
- [ ] Price/currency determined server-side.
- [ ] VND pricing policy explicitly implemented.
- [ ] SePay signature follows documented field order.
- [ ] Frontend submits signed form to configured SePay checkout.
- [ ] Success/error/cancel pages implemented.
- [ ] Success redirect does not activate subscription.
- [ ] Public HTTPS IPN endpoint implemented.
- [ ] IPN secret authentication implemented.
- [ ] ORDER_PAID checks amount/currency/status.
- [ ] IPN processing is idempotent.
- [ ] Duplicate event cannot extend twice.
- [ ] Existing subscription service reused.
- [ ] Manual subscription flow remains intact.
- [ ] Current plan refreshes after payment.
- [ ] Free plan never creates checkout.
- [ ] Unsupported downgrade protected.
- [ ] TRANSACTION_VOID safely recorded/reconciled.
- [ ] No user-facing void/refund in M7K.
- [ ] Backend/frontend tests pass.
- [ ] Migration verification passes.
- [ ] Runtime security gates pass.
- [ ] Sandbox E2E succeeds before Production.
- [ ] Production secrets are not committed.
- [ ] Production deployment occurs only after explicit authorization.

## 70. Final instruction to Codex

Treat M7K as a financial-state and subscription-integrity milestone.

Before coding:

1. inspect M6A billing/subscription models and services;
2. inspect M7J Change Plan implementation;
3. inspect current plan-catalog currency/pricing;
4. determine exactly how VND checkout amount will be sourced;
5. inspect manual Activate/Extend/Change subscription logic and reuse it;
6. inspect existing transaction/audit patterns;
7. review the supplied SePay documentation directly.

Do not invent undocumented SePay behavior.

Where documentation/examples differ, make the value environment-configurable and document the verified value used in Sandbox/Production.

Never activate a subscription from browser redirect alone.

The authoritative transition is:

```text
authenticated checkout creation
+
validated authenticated SePay IPN
+
idempotent backend subscription mutation
```

Create:

```text
docs/verification-milestone-7k.md
```

The report must include:

```text
architecture
database migration
payment-order states
commercial snapshot
checkout endpoint
signature fixture results
configured SePay environment (without secrets)
callback routes
IPN authentication
IPN validation rules
idempotency strategy
subscription activation semantics
renewal/upgrade/downgrade policy
VND pricing policy
tests
migration checks
browser QA
sandbox E2E results
runtime/security gates
production deployment status
real-payment verification status
known limitations
```

Never print, commit, screenshot or include the real Merchant Secret Key / IPN Secret Key in verification artifacts.
