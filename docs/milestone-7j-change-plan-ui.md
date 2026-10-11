# Milestone 7J — Change Plan UI (Pre-Payment Upgrade Surface)

## Objective

Add an authenticated **Change Plan** page at:

```text
https://app.serpsaas.com/app/change-plan
```

for verified logged-in users.

Purpose:

- let users review available Desktop/Mobile plans inside the app;
- clearly show their current plan;
- prepare the upgrade UX for a future payment-gateway milestone;
- keep the `Select` action intentionally non-transactional until payment is integrated.

Do **not** implement checkout, payment collection, webhooks, invoices, automatic plan activation, refunds, coupons, taxes, or saved payment methods.

## 1. Navigation

Add `Change Plan` to the authenticated app sidebar/navigation.

Recommended placement:

```text
Overview
Projects
Tracked Sites
Ranking Explorer
Reports
Competitors
Change Plan
Settings
```

Follow the existing sidebar IA if ordering differs.

Do not add this item to the public website navigation.

## 2. Design

Use the attached pricing-card screenshot only as visual inspiration.

Desired structure:

```text
Change Plan
Compare available plans and choose the option that best matches your tracking needs.

[ Desktop ] [ Mobile ]

[ Plan Card ] [ Plan Card ] [ Plan Card ]
```

Each card should contain:

```text
plan icon
plan name
price / billing period
limits / entitlements
schedule availability
current-plan state
Select button
```

Design characteristics:

- clean SaaS pricing cards;
- equal-height cards;
- prominent plan name and price;
- divider between plan header and entitlement rows;
- compact rows;
- subtle borders/shadows;
- responsive mobile stacking;
- consistent with the existing authenticated app design system.

Do not copy unrelated branding/text from the reference image.

## 3. Source of Truth

Do not hard-code plan data.

Reuse the existing billing Plan catalog/backend API used by public Pricing:

```text
GET /api/v1/billing/plans
```

The authenticated Change Plan page and public Pricing page must share the same plan source.

No duplicate catalog configuration.

## 4. Desktop / Mobile Product Lines

SERP SaaS has separate Desktop and Mobile product lines.

Preserve that model.

Recommended UI:

```text
Tabs:
Desktop
Mobile
```

Only show plans belonging to the selected product line.

Do not merge Desktop and Mobile into one subscription.

## 5. Current Plan

Load the current user's subscription/entitlement state using existing billing APIs.

Display:

```text
current product line
current plan
subscription status
expiry date when available
```

The current plan card must be clearly marked:

```text
Current Plan
```

Its button should be disabled and labeled:

```text
Current Plan
```

or:

```text
Selected
```

## 6. Card Fields

Render actual backend values:

```text
Plan name
Price
Billing period
Max projects
Max keywords
Monthly checks
Schedule capability
Product line
```

Optional only if supported by catalog:

```text
description
recommended badge
feature summary
```

Do not invent entitlements.

## 7. Example Card

```text
┌───────────────────────────────┐
│            Starter            │
│          $19 / month          │
├───────────────────────────────┤
│ Projects                 5    │
│ Keywords               500    │
│ Checks / month        5,000   │
│ Schedule              Weekly  │
│                               │
│        [ Select ]             │
└───────────────────────────────┘
```

Current plan:

```text
┌───────────────────────────────┐
│             Free              │
│           $0 / month          │
│        CURRENT PLAN           │
├───────────────────────────────┤
│ ...                           │
│      [ Current Plan ]         │
└───────────────────────────────┘
```

## 8. Select Button — M7J Behavior

Payment gateway is not ready.

`Select` must **not**:

```text
change subscription
activate a plan
call billing mutation APIs
create checkout
create payment records
redirect to a fake payment page
```

Preferred behavior:

Clicking `Select` opens an informational modal:

```text
Plan upgrade coming soon

Online payment and automatic plan upgrades are being prepared.
Your current subscription has not been changed.

[ Close ]
```

No backend mutation.

Alternative: disabled Select buttons with helper text:

```text
Online plan changes are coming soon.
```

Preferred UX is the informational modal because it lets the user express upgrade intent without changing state.

## 9. Upgrade / Downgrade Labels

Optional UI labels:

```text
Upgrade
Current Plan
Downgrade
```

Only show them if plan ordering/entitlements allow the direction to be determined safely.

Do not execute upgrade/downgrade actions in this milestone.

## 10. Expiry / Free Fallback

Existing billing behavior remains unchanged.

Paid expiry continues to fall back to the matching Free entitlement according to existing billing logic.

If the backend exposes expiry, optionally show:

```text
Active until: Oct 31, 2026
```

Never infer expiry client-side.

## 11. Pricing Accuracy

Do not hard-code any price or numeric plan limit.

Use backend-provided values:

```text
price
currency
billing interval
limits
schedule entitlement
```

Reuse existing price-formatting logic from public Pricing where appropriate.

## 12. Loading / Error / Empty States

Loading:

```text
skeleton plan cards
```

Error:

```text
Unable to load plans.
[ Retry ]
```

Never show hard-coded fallback pricing.

Empty catalog:

```text
No plans are currently available.
```

If current-subscription lookup fails, do not guess which plan is current.

## 13. Responsive

Required widths:

```text
375
768
1024
1440
```

Desktop:

```text
3 cards in one row where space permits
```

Mobile:

```text
1 card per row
```

No horizontal overflow.

## 14. Accessibility

Requirements:

- one H1;
- semantic headings;
- real disabled state for current-plan button;
- visible focus;
- current-plan state not indicated by color alone;
- modal focus trap if modal used;
- Escape closes modal;
- focus returns to trigger;
- sufficient contrast;
- readable entitlement rows.

## 15. Auth / Tenant Safety

This page is user-scoped.

Never trust a client-provided:

```text
user_id
```

Use existing authenticated user/session context.

Do not expose another user's subscription data.

## 16. Backend Scope

Prefer no backend changes if current APIs already expose:

```text
plan catalog
current subscriptions
current entitlements
```

Inspect existing billing API first.

Only add a read-only endpoint if absolutely necessary.

Do not add:

```text
POST /change-plan
checkout session endpoints
payment APIs
subscription mutation APIs
```

in M7J.

## 17. Future Payment Readiness

Keep UI architecture provider-agnostic.

Recommended boundary:

```text
onPlanSelect(planId, productLine)
```

For M7J this only opens the coming-soon state.

A later payment milestone can replace the handler with:

```text
create checkout session
redirect to gateway
receive webhook
activate subscription
```

Do not couple plan cards to a specific provider yet.

## 18. Recommended Copy

```text
H1: Change Plan

Compare available plans and choose the option that best matches your tracking needs.
```

Placeholder note:

```text
Online plan changes are coming soon. Selecting a new plan does not change your subscription yet.
```

## 19. Tests

Add coverage for:

```text
authenticated route access
anonymous redirect to Login
unverified-user gating
Desktop catalog rendering
Mobile catalog rendering
current plan detection
current-plan disabled action
Select informational behavior
no mutation request on Select
catalog error + retry
empty catalog
backend price/limits rendering
no hard-coded fallback pricing
```

Critical assertion:

```text
Clicking Select produces ZERO billing/subscription mutation API requests.
```

## 20. Browser QA

Run production standalone QA for:

```text
/app/change-plan
```

At:

```text
375
768
1024
1440
```

Fixtures:

```text
Free Desktop current
Paid Desktop current
Free Mobile current
Paid Mobile current
catalog failure
empty catalog
```

Verify:

```text
no overflow
zero browser exceptions
zero hydration errors
axe A/AA
current-plan badge
Desktop/Mobile switching
Select placeholder
keyboard modal behavior
mobile card stacking
```

## 21. Regression

Verify existing app behavior remains unchanged:

```text
Overview
Projects
Ranking Explorer
Reports
Competitors
Settings
Admin protection
```

Do not modify public `/pricing`.

Do not change entitlement logic.

## 22. Security / Build Gate

Run:

```bash
npm test
npm run lint
npm run typecheck
npm run format:check
npm run build
npm audit --omit=dev
git diff --check
```

Preserve:

```text
0 critical runtime vulnerabilities
0 high runtime vulnerabilities
```

## 23. Production Verification

After authorized deployment:

1. log in as a normal verified user;
2. open:

```text
https://app.serpsaas.com/app/change-plan
```

3. compare Desktop/Mobile catalog with backend;
4. verify current-plan state;
5. click `Select` on a non-current plan;
6. verify informational placeholder only;
7. verify subscription remains unchanged;
8. refresh and confirm current plan is unchanged;
9. verify no payment/billing mutation network request occurred.

## 24. Definition of Done

- [ ] `Change Plan` added to authenticated navigation.
- [ ] `/app/change-plan` exists.
- [ ] Auth and verified-email gates work.
- [ ] Uses existing backend plan catalog.
- [ ] Desktop and Mobile product lines supported.
- [ ] Current plan visibly identified.
- [ ] Plan cards match design direction.
- [ ] Prices and limits are not hard-coded.
- [ ] Select does not mutate billing state.
- [ ] Coming-soon behavior is clear.
- [ ] Loading/error/retry/empty states work.
- [ ] Responsive QA passes.
- [ ] Accessibility passes.
- [ ] Existing app regression passes.
- [ ] Runtime security gate remains clean.

## 25. Out of Scope

Do not implement:

```text
payment gateway
checkout
credit/debit cards
bank transfer automation
payment webhooks
automatic activation
automatic downgrade
invoice generation
refunds
coupons
taxes
billing portal
saved payment method
```

These belong to a future payment milestone.

## 26. Final Instruction to Codex

Treat M7J as a **pre-payment plan-selection UI milestone**.

Before coding:

1. inspect existing billing-plan APIs;
2. inspect current subscription/entitlement APIs;
3. inspect authenticated sidebar/navigation;
4. inspect public Pricing components for reusable plan formatting;
5. reuse existing design-system components;
6. do not duplicate or hard-code catalog values.

The `Select` action must remain intentionally non-transactional.

Create:

```text
docs/verification-milestone-7j.md
```

Document:

```text
route
navigation
plan source
current-plan detection
Desktop/Mobile switching
card states
Select placeholder behavior
network mutation assertions
tests
browser QA
accessibility
runtime audit
build
production deployment status
```

Do not claim payment functionality or subscription mutation.
