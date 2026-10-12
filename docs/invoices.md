# Customer invoices and transaction PDFs

The customer menu now includes **Invoices** at `/app/invoices`. Billing & Usage
and the SePay payment result page also link to invoices. Users can open a
transaction, filter by payment status, Desktop/Mobile and Sandbox/Production,
load older entries and download a PDF from the list or detail page.

Invoices use existing SePay `payment_orders`, including earlier checkouts. All
checkout states are visible; pending/failed/expired attempts are not presented
as completed payments. Sandbox transactions are explicitly labelled in the
list, details and PDF. Free subscriptions and manual plan activations without
a payment order do not produce an invoice.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /api/v1/billing/invoices` | Current user's orders, newest first; `limit` 1–100 (default 20), `cursor`, optional `status`, `product_line`, `environment`; returns `items`, `has_more`, `next_cursor` |
| `GET /api/v1/billing/invoices/{invoice_id}` | Current user's transaction details and purchased plan terms |
| `GET /api/v1/billing/invoices/{invoice_id}/pdf` | Authenticated PDF attachment, `invoice-PAY_….pdf` |

`invoice_id` is the existing payment order UUID. All endpoints enforce current
account ownership and the application's email verification policy. Other
accounts receive 404 for detail/PDF requests. Responses use
`Cache-Control: private, no-store`; PDFs also use `nosniff`. Frontend downloads
use the existing authenticated download client with token refresh, rather than
a public file URL. Query caches are scoped to the current user.

The amount, currency, plan name and allowances come from the purchase snapshot,
so subsequent catalog edits do not rewrite transaction history. Account email
identifies the currently signed-in account. Subscription periods are not
inferred from a mutable current subscription. The API exports explicitly
allowed fields, excluding provider payloads, card details, internal failure
codes, webhook keys and signing credentials.

Expired pending checkouts are displayed and filtered as expired based on
`expires_at`, without changing payment records. Viewing/exporting never
activates, extends or modifies subscriptions. History remains available when
the checkout gateway is disabled. PDF generation runs in a worker thread using
the existing ReportLab Unicode font; there is no artifact storage or retention
dependency. Normal transactions fit one A4 page, with wrapping and pagination
for long references. PDF times are labelled UTC; UI times use the browser locale.

## Verification — 2026-10-12

- Backend: 48 targeted invoice/payment/report tests passed; 145 unit tests passed.
- Ownership, authentication, verification, other-account PDF denial, immutable
  purchase snapshots, payload redaction, disabled gateway, read-only exports,
  equal-timestamp cursor pagination, filters and pending expiry are covered.
- PDF tests cover all eight payment states, Production/Sandbox, missing legacy
  terms, Vietnamese text, escaped markup and long transaction references.
- Frontend: all 318 tests passed, including 10 invoice tests; ESLint, Prettier,
  TypeScript and production build passed.
- Browser fixture QA: list/details at 375, 768, 1024 and 1440px, with no page
  errors or horizontal overflow; authenticated PDF download passed at each size.
- An independent PDF reader verified Vietnamese text, VND amount, provider
  references and confirmation wording for paid, awaiting-payment and voided
  sample documents. These are synthetic transactions, not merchant Sandbox E2E.

No database migration, new environment variables or merchant secret changes
are required. Backend and frontend must both be released for the new page.

Synthetic artifacts: [sample Sandbox PDF](verification-artifacts/invoices/sample-sandbox-invoice.pdf),
[mobile list](verification-artifacts/invoices/list-mobile.png),
[desktop details](verification-artifacts/invoices/detail-desktop.png),
[browser checks](verification-artifacts/invoices/browser-qa.json).

## Production acceptance

1. Log in and open **Invoices**. An account without payment orders sees an empty
   state; existing SePay orders should be visible immediately.
2. Open a real Sandbox checkout's invoice. Confirm its invoice number, plan,
   VND amount, environment and current server-confirmed status.
3. Download PDF from list/details and compare the transaction references and
   purchase terms with the invoice screen.
4. Test a pending/failed/cancelled order and confirm the export does not claim
   completed payment. Refresh after an authenticated provider confirmation.
5. Sign into another account and verify the first account's invoice and PDF
   URLs return 404. Confirm their list contains only their own transactions.
