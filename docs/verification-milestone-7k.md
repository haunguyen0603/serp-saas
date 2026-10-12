# Milestone 7K — SePay implementation verification

Verified locally on 2026-10-11 (Asia/Ho_Chi_Minh).

Implementation and local fixture verification are complete. **Merchant Sandbox E2E, public HTTPS IPN reachability, production deployment and real payment verification have not been performed.** SePay stays disabled by default until an operator supplies merchant configuration. No real credentials were requested or added to source, logs or artifacts.

## Architecture

- Thin `app/api/v1/payments.py` router delegates to `PaymentService`.
- `PaymentOrderRepository` and `PaymentEventRepository` handle ownership, locks, provider-reference conflicts and event insertion.
- `PaymentProvider` defines the provider boundary; `SePayPaymentProvider` builds hosted checkout fields, verifies IPN authentication and minimizes provider evidence. `SePayCheckoutSigner` is independently testable.
- `SubscriptionService.activate_from_payment` reuses the existing activation, replacement, extension, usage-period and audit paths. Manual admin payment validation remains intact.
- Database writes use the existing `get_db` transaction. An activation failure rolls back the event, order, subscription and audit writes and returns 500 so the provider can retry.

## Migration and historical evidence

`0016_sepay_payments`, following `0015_vnd_pricing`, creates:

| Table | Evidence and constraints |
| --- | --- |
| `payment_orders` | User, product line, catalog FK, commercial snapshot, VND integer amount, unique server-generated UUID invoice, environment, provider references/status, expiry and activation timestamps, subscription FK, reconciliation reason |
| `payment_events` | Unique event fingerprint, notification type, optional matched order, minimized payload, received/processed timestamps and processing result |

Indexes cover user/created time, status, matched events and unique provider order / transaction references within each environment. Both `transaction.id` and `transaction.transaction_id` have independent uniqueness protection. Nullable reference columns use PostgreSQL's normal distinct-null behavior. Check constraints enforce positive VND money, supported product lines and known states. User/payment history FKs preserve financial records instead of cascading deletion.

Commercial snapshots include all M6A `TERMS`: code, name, device, currency, price, project/keyword/check limits, scheduling entitlements, plus `billing_months=1`. Activation uses this snapshot rather than a later mutable catalog. A test changes price and limits after checkout and verifies the purchased terms still activate. Invalid snapshot shape is routed to review.

The global schema invariant test includes the two new tables and checks Alembic metadata matches ORM metadata. The migration suite now expects revision `0016_sepay_payments`. Disposable test schemas run upgrade to head, downgrade one revision, upgrade to head and inspect indexes; every schema is dropped after its test. No existing application database was migrated by this implementation session.

## Payment-order states

| State | M7K behavior |
| --- | --- |
| `pending` | Internal order creation before form signing |
| `checkout_created` | Signed hosted form returned, payment unconfirmed |
| `paid` | Authenticated, validated IPN activated/extended the subscription atomically |
| `expired` | Unconfirmed attempt passed its 45-minute internal expiry; expired lazily on status reads or subsequent checkout creation |
| `review_required` | Amount/currency/status/reference mismatch, unknown transition, invalid snapshot, late payment or void reconciliation |
| `failed`, `cancelled`, `voided` | Persistable states reserved for provider/operator reconciliation; browser routes do not write them |

Unknown invoices are recorded as unmatched events with `PAYMENT_ORDER_NOT_FOUND`; there is no internal order to update. Unknown notification types are recorded and acknowledged without activation. Late valid payments remain visible for operator reconciliation and never silently disappear.

Only `ORDER_PAID` and `TRANSACTION_VOID` are documented in the reviewed IPN contract. M7K does not invent authoritative failure/cancellation notifications. Visiting an error/cancel route displays an unconfirmed checkout outcome while preserving backend financial state.

## Endpoints and checkout

| Method and route | Access and behavior |
| --- | --- |
| `GET /api/v1/billing/payments/sepay/options` | Authenticated; reports gateway availability and server-calculated eligible plan IDs |
| `POST /api/v1/billing/payments/sepay/checkout` | Authenticated, explicitly verified email; accepts only `plan_id` and `product_line`; creates a unique order and returns checkout URL plus signed fields |
| `POST /api/v1/billing/payments/sepay/ipn` | No user JWT; constant-time `X-Secret-Key` verification against the backend IPN key |
| `GET /api/v1/billing/payments/{payment_order_id}` | Authenticated owner only; safe order state and subscription reference; another account receives 404 |

Frontend selection prevents duplicate clicks during checkout creation, posts JSON to the backend and submits hidden form fields with native HTML POST to the configured hosted endpoint. Free plans, unsupported currencies, unavailable checkout, unknown current subscriptions and disallowed transitions have disabled actions. Current Plan remains disabled. Checkout errors leave the current plan in place.

The hosted form contains `PURCHASE`, `VND`, backend amount/invoice, merchant, internal user UUID, callback URLs and signature. It omits `payment_method` to let merchant-enabled methods appear. Backend appends `payment_order_id` to every callback query, preserving unrelated query parameters.

## Signature fixtures

HMAC-SHA256 signs unencoded `field=value` pairs joined with commas, using only present fields in the documented order; raw digest bytes are Base64 encoded. Input dictionary insertion order does not affect the output. Alphabetical sorting produces a different signature and fails the tests.

The fixed fixture in `tests/test_sepay.py`, with an explicitly synthetic signing key and Unicode description, yields:

```text
/FM9RaKdUKoLxedrRQzzKAZ87z/fX0SeVogrlBHAido=
```

Four customer/method combinations verify optional field ordering and callback URL handling. Money fixtures cover integer and decimal strings, and reject fractional VND, floats, booleans, NaN, infinity, negative/zero and excessive values.

## IPN authentication, validation and idempotency

Missing/incorrect IPN keys return 401. IPN processing acknowledges recorded/processed events with HTTP 200. Authentication does not depend on cookies, JWT, CORS or browser CSRF, and global CORS is unchanged.

`ORDER_PAID` must match the internal invoice/environment and provide stable order/transaction references. Both order and transaction must have expected VND currency and exact integer-equivalent amount. Required statuses are order `CAPTURED`, transaction `APPROVED`, transaction type `PAYMENT`. No binary floating-point comparison is used. Unknown/reused/conflicting provider references never activate a second order.

The event fingerprint includes environment and minimized financial payload, excluding retry timestamp and personal/card fields. A unique event constraint and `INSERT ... ON CONFLICT DO NOTHING` acknowledge identical retries. Sorted transaction/order advisory locks serialize cross-order reference reuse. User advisory locking is acquired before locking the order row, matching billing's lock order. The order's `subscription_id` is a durable activation marker: a changed fingerprint referencing the same transaction cannot extend again. Orders that have been activated or marked for review cannot be reactivated by a later retry.

`TRANSACTION_VOID` persists its event and places the order under review, retaining the active subscription and original payment references. No void API call, refund action or automatic subscription reversal is exposed.

Only allowlisted financial provider fields are persisted. Full PAN, masked PAN, CVV, cardholder, expiry, customer data, user agent, IP and arbitrary custom data are discarded. `raw_payload` is intentionally a minimized evidence object, not an unredacted provider request.

## Subscription and VND commercial policy

- Free/expired → paid: activate for one calendar month from confirmed IPN processing time.
- Active paid → higher/equal-priced different plan: reuse manual immediate replacement, start a new calendar month, no proration or credit for unused time.
- Same paid plan: supported by the backend API; reuse `extend` to add one calendar month from current expiry. Existing entitlement snapshot and usage counters remain unchanged, matching manual extension semantics. The current-plan card stays disabled in M7K, so a separate renewal UI is deferred.
- Paid downgrade / paid → Free: unavailable in payment checkout; contact support/manual administration.
- Existing scheduled subscription: checkout unavailable; revalidated at confirmation to catch intervening admin changes. Conflicts enter review.
- Desktop/mobile subscriptions remain independent.
- Payment activation/replacement has `source=sepay`; renewals preserve the original subscription row/source and add explicit SePay audit evidence. Payment audits record invoice, subscription before/after, snapshot and expiry, and link back to the provider payment order.

Catalog prices already use whole VND after migration 0015. Checkout reads `Plan.price_monthly_minor_units` directly; no new exchange rate or conversion occurs. Historical USD subscription snapshots are preserved; comparison for transition policy uses the existing fixed migration comparison helper. Every payable catalog entry must itself be VND with a positive amount. Unsupported catalog currencies are rejected.

## Callback UX and browser verification

Routes:

```text
/app/change-plan/payment/success
/app/change-plan/payment/error
/app/change-plan/payment/cancel
```

All read the owner-only payment endpoint. Success redirects do not activate subscriptions. Pending success pages poll every 2.5 seconds for at most 45 seconds, stop on terminal state/fetch error and show an unconfirmed timeout message. Paid status invalidates billing, usage, entitlements, payment eligibility, overview and project queries. Cancel/error routes honor an already paid backend result.

`verify-sepay-browser.mjs` ran against the local frontend production build on `http://127.0.0.1:13001`. All API requests and hosted checkout were intercepted with synthetic fixtures. Hosted fixture URL: `https://checkout.example.test/init`; this is not a SePay Sandbox endpoint.

QA passed at 375, 768, 1024 and 1440 px for Change Plan Free/paid, success, error, cancel, reconciliation and timeout. It verified signed POST form submission, redirect before confirmation, confirmation before redirect, current-plan refresh, paid state on cancel and bounded polling. No horizontal overflow, clipped controls or JavaScript page errors occurred. The generated [browser report](verification-artifacts/milestone-7k/browser-report.json) and 28 screenshots are under `docs/verification-artifacts/milestone-7k/`.

## Test/build/security gates

| Gate | Result |
| --- | --- |
| Backend full test suite | 347 passed (full final suite) |
| Backend Ruff lint/format | Passed |
| Backend mypy | Passed (152 source files) |
| Frontend Vitest | 308 passed across 34 files |
| Frontend ESLint/typecheck/Prettier | Passed |
| Next.js production build | Passed; all three callback routes included |
| Backend production Docker build | Passed (`serp-saas-backend-m7k:local`, latest source) |
| `npm audit --omit=dev` | 0 vulnerabilities, including 0 high / 0 critical |
| Migration roundtrip and ORM parity | Passed: disposable upgrade/downgrade/upgrade and ORM parity |
| Browser QA | Passed using intercepted fixtures |
| `git diff --check` | Passed |

The final full backend run passed 347 tests. The focused payment/migration/schema run also passed 42 tests. Schema assertions now include the added payment tables and revision.

Backend tests cover authentication, forced verification, Free/inactive/wrong-scope/unsupported-currency plans, rejected client money/user fields, unique invoices, snapshots, secret omission, payment ownership, required IPN statuses, missing/invalid secret, unknown invoice/type, duplicate events, concurrent duplicate renewal, repeated transaction references, concurrent cross-user reference reuse, void persistence, activation rollback, late payment, corrupt snapshots, scheduling conflicts, expired/manual compatibility, upgrade/downgrade and migration roundtrip.

Frontend tests cover checkout submission, duplicate-click protection, checkout errors, disabled transitions, owner-scoped queries, paid/pending/timeout states, polling termination, error/cancel/review pages, missing reference, fetch errors and query invalidation. Existing frontend regression suites also passed.

Backend checks use the existing local Docker Python environment; the host virtualenv points to a removed interpreter. Frontend checks use the available Node 22.22.0 binary rather than the older default Node. Tests use isolated PostgreSQL schemas; no merchant service is called.

## Sandbox/operator configuration and deployment status

Disabling new checkout leaves authenticated IPN intake available for outstanding orders when the same environment/IPN key is retained.

Implementation defaults: `SEPAY_ENABLED=false`, `SEPAY_ENV=sandbox`, pending expiry 45 minutes. All checkout/callback URLs default to empty and must be explicitly supplied before enabling. Enabled configuration requires merchant, signing/IPN keys and HTTPS checkout/callback URLs. `SEPAY_VOID_URL` is reserved configuration; M7K never calls it.

The actual merchant Sandbox checkout endpoint **has not been configured or verified**. Obtain it from the active merchant setup; do not substitute an inferred Sandbox hostname. Configure:

```text
SEPAY_ENABLED=true
SEPAY_ENV=sandbox
SEPAY_MERCHANT_ID=<merchant configuration>
SEPAY_SECRET_KEY=<backend-only secret injection>
SEPAY_IPN_SECRET_KEY=<backend-only secret injection>
SEPAY_CHECKOUT_URL=<merchant-confirmed sandbox URL>
SEPAY_SUCCESS_URL=https://<sandbox-app>/app/change-plan/payment/success
SEPAY_ERROR_URL=https://<sandbox-app>/app/change-plan/payment/error
SEPAY_CANCEL_URL=https://<sandbox-app>/app/change-plan/payment/cancel
SEPAY_PENDING_MINUTES=45
```

Keep local credentials only in ignored `.env`; `.env.example` has no keys. Docker Compose forwards backend-only configuration. `.dockerignore` excludes local env files from image layers. For Cloud Run, create signing/IPN secrets in Google Secret Manager and attach secret version references to backend environment variables; do not use build arguments or public frontend variables. Run Alembic via the existing migration process before enabling payment.

Configure merchant IPN auth type `SECRET_KEY` and an externally accessible HTTPS IPN URL. Intended production URL: `https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn`. This session has not verified public reachability or changed Cloud Run IAM. Cloud Run ingress must permit the provider call, with application-level IPN key authentication retained.

Before go-live, an operator must run actual merchant Sandbox success/failure/cancel journeys, validate both redirect/IPN orderings, replay IPN without a second extension, inject mismatches and unknown invoices, inspect payment/subscription/audit records and confirm the public HTTPS callback works. Only then configure confirmed production endpoints and merchant secrets. Production examples in the supplied docs are `https://pay.sepay.vn/v1/checkout/init` and `https://pgapi.sepay.vn/v1/order/voidTransaction`; the implementation has no inferred environment endpoints.

Production deployment: **not performed**. Real-payment verification: **not performed**. No real transaction is authorized by this implementation request. Production deployment and any controlled real transaction require explicit authorization after Sandbox verification.

## Documentation reviewed and limitations

Directly reviewed [checkout form/signature](https://developer.sepay.vn/vi/cong-thanh-toan/API/don-hang/form-thanh-toan), [IPN](https://developer.sepay.vn/vi/cong-thanh-toan/IPN), [payment flow](https://developer.sepay.vn/vi/cong-thanh-toan/luong-thanh-toan) and [card void](https://developer.sepay.vn/vi/cong-thanh-toan/API/giao-dich/huy-giao-dich) documentation. The supplied [quick start](https://developer.sepay.vn/vi/cong-thanh-toan/bat-dau) repeatedly timed out in the browsing tool; no behavior or endpoint was inferred from its unavailable contents.

Sandbox and public HTTPS verification remain operator gates. Reconciliation/operator payment history, renewal UI, recurring charging, saved cards, refunds/void tooling, proration, tax, coupons and other gateways are outside M7K. Unconfirmed expiry is lazy rather than a new background job. Failure/cancel redirects cannot provide financial proof. Payload minimization preserves reconciliation evidence without card/customer details; it deliberately cannot reconstruct unredacted provider requests.


## 2026-10-12 — Authorized production-hosted Sandbox rollout

The user authorized deploying M7K onto the existing production infrastructure while keeping the gateway in Sandbox, and chose Cloud Shell for Google Cloud configuration. This supersedes the earlier deployment authorization status; it does not authorize real payment processing. See [Sandbox deployment runbook](deployment-milestone-7k-sandbox.md).

Production Sandbox checkout is limited to platform admins or configured `SEPAY_SANDBOX_ALLOWED_USER_IDS`. Other production users cannot activate subscriptions using simulated payments. Backend test configuration now explicitly excludes local merchant credentials. A missing local IPN key was generated in ignored `.env` without printing it; actual Cloud Run binding still requires the authenticated Cloud Shell helper.


The authorized rollout completed for application code: both backend and frontend Cloud Build checks succeeded for commit `b45cd2f`. Public production verification passed 13 HTTPS checks and the fixture browser journeys at all four responsive widths. Actual Secret Manager bindings remain pending the user's authenticated Cloud Shell helper execution, followed by SePay merchant IPN configuration and a real merchant Sandbox journey. These checks did not make a real payment or mutate a production subscription. The [rollout report](deployment-milestone-7k-sandbox.md) records the builds and remaining setup.

## 2026-10-12 — Sandbox acceptance and real Production authorization

The user confirmed Sandbox testing succeeded and explicitly requested switching
the payment gateway to Production. They also confirmed Production merchant
credentials are available. This supersedes the Sandbox-only rollout scope above.
Actual Cloud Run gateway configuration is handled through the user's chosen
Cloud Shell workflow; see [Production gateway rollout](deployment-sepay-production.md).
