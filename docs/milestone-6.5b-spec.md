# SERP SaaS — Milestone 6.5B Specification

## Public Home + Pricing

**Target milestone:** M6.5B  
**Status:** Specification  
**Prerequisite:** M6.5A Design System + Authenticated App UX/UI Redesign accepted.  
**Primary goal:** Build a polished public-facing marketing website using the M6.5A visual language, with a clear Home page and a production-ready Pricing page that accurately represents the current product, current M6A Plans, and current manual activation/payment model.

---

# 1. Objective

M6.5B introduces the public marketing layer of the SERP SaaS.

The milestone must provide:

```text
/
→ Home

/pricing
→ Public Pricing
```

The public website should explain:

```text
what the product does
who it is for
how it works
what features exist
how Desktop and Mobile tracking differ
what Plans are available
how customers start using the service
```

This milestone is public-facing UX and product communication.

It must not add new billing/payment/business semantics.

---

# 2. Primary Product Positioning

The product should be presented as:

```text
SERP rank tracking SaaS
```

Core customer value:

```text
Track Google keyword rankings
Monitor Desktop and Mobile separately
Run manual or scheduled checks
Keep ranking history
Track site/domain migrations through aliases
View usage and Plan limits
```

Do not market the underlying SERP providers as the product.

Avoid public emphasis on:

```text
Serper
SerpApi
Cloud Tasks
Cloud Run
provider fallback
internal budgets
worker infrastructure
```

---

# 3. Scope

M6.5B must implement:

- Public Home page.
- Public Pricing page.
- Public website shell/header/footer.
- Responsive public navigation.
- Mobile navigation.
- Hero section.
- Product value proposition.
- Feature sections.
- How-it-works section.
- Desktop vs Mobile explanation.
- Tracked Sites / domain alias explanation.
- Scheduling explanation.
- Usage/Billing explanation.
- API/developer teaser for future M6.5C/D without exposing unfinished functionality.
- Pricing sourced from authoritative backend Plan catalog.
- Desktop Pricing section.
- Mobile Pricing section.
- Free/Starter/Pro cards.
- Current entitlement limits.
- Manual bank-transfer/customer-contact CTA.
- Login/Register CTAs.
- SEO metadata.
- Open Graph metadata.
- canonical URLs.
- robots.txt.
- sitemap.xml.
- basic structured data where appropriate.
- responsive behavior.
- accessibility.
- production build verification.
- public browser verification.
- regression verification.
- final verification report.

---

# 4. Explicitly Out of Scope

Do NOT implement in M6.5B:

```text
public customer API
API Keys
developer authentication
full Docs portal
Swagger-style customer API reference
Stripe
PayPal
crypto payment gateway
automatic Checkout
automatic recurring billing
automatic invoice/tax flow
self-service paid Plan activation
M7 analytics
competitor analytics
blog/CMS
contact CRM integration
newsletter system
affiliate/referral program
multi-language website
```

---

# 5. Public Information Architecture

Recommended public routes:

```text
/
├── pricing
├── login
├── register
└── app/*
```

Future reserved routes:

```text
/docs        → M6.5D
/developers  → M6.5C/D if desired
```

Do not create broken/dead Docs or Developer pages in M6.5B.

---

# 6. Public Site Shell

Create a reusable public layout separate from the authenticated AppShell.

Recommended:

```text
Header
Main content
Footer
```

Do not reuse the customer sidebar shell on public pages.

---

# 7. Header

Public header should include:

```text
Logo / Product name
Home
Pricing
Login
Get Started
```

Optional future-safe placeholder:

```text
Docs
```

only if the route already exists.

Otherwise omit it.

---

# 8. Header Behavior

Desktop:

```text
logo left
navigation center/right
Login secondary
Get Started primary
```

Mobile:

```text
logo
menu button
drawer/sheet menu
```

The public navigation should be simpler than the authenticated application navigation.

---

# 9. Home Page Structure

Recommended order:

```text
1. Hero
2. Product credibility / concise benefit strip
3. How it works
4. Core features
5. Desktop vs Mobile tracking
6. Tracked Sites + Domain Aliases
7. Scheduling
8. Usage / Plans preview
9. Developer/API teaser
10. Final CTA
11. Footer
```

Do not overload Home with every technical capability.

---

# 10. Hero Section

The Hero should communicate the product within a few seconds.

Suggested conceptual copy:

```text
Track your Google rankings with clarity.

Monitor keywords across Desktop and Mobile,
schedule recurring checks, and keep reliable ranking history.
```

Primary CTA:

```text
Start Free
```

Secondary CTA:

```text
View Pricing
```

Do not claim capabilities that are not implemented.

---

# 11. Hero Visual

Use a polished product UI preview inspired by M6.5A.

Possible visual:

```text
Overview dashboard
+
ranking table
+
usage card
```

The visual should feel like the real product.

Avoid generic abstract stock illustrations.

---

# 12. Product Benefit Strip

Recommended benefit points:

```text
Desktop & Mobile tracking
Scheduled checks
Ranking history
Domain alias tracking
Usage-based Plans
```

Use concise icon/text blocks.

---

# 13. How It Works

Recommended 4-step flow:

```text
1. Add your Tracked Site
2. Create a Project
3. Add Keywords
4. Run or schedule rank checks
```

This should match the actual authenticated product workflow.

---

# 14. Core Features

Feature cards may include:

```text
Keyword Rank Tracking
Desktop SERP Tracking
Mobile SERP Tracking
Scheduled Rank Checks
Ranking History
Tracked Sites
Domain Aliases
Batch Progress
Usage & Billing
```

Keep descriptions customer-focused.

---

# 15. Desktop vs Mobile Section

Explain clearly that Desktop and Mobile are separate product scopes.

Example:

```text
Desktop and Mobile rankings can differ.
Track them independently with separate Projects, usage limits and Plans.
```

Do not mention the provider-cost reason publicly.

---

# 16. Tracked Sites + Domain Aliases

Explain the value:

```text
Keep one logical SEO asset even when domains change.

Add historical/current domain aliases so ranking results remain associated
with the same tracked site after migrations or redirects.
```

Avoid excessive 301 implementation detail.

---

# 17. Scheduling Section

Explain:

```text
Manual checks
Weekly schedules
Daily schedules
```

Availability depends on Plan.

Do not imply all Plans support all frequencies.

---

# 18. Usage Section

Explain that Plans include:

```text
Project limits
Keyword limits
Monthly rank-check limits
Schedule entitlement
```

This prepares users for Pricing.

---

# 19. Developer/API Teaser

M6.5B may contain a future-facing teaser such as:

```text
Built for teams and integrations.

A customer API and developer documentation are coming next.
```

Only use wording that makes it explicit if the feature is not yet available.

Do not create fake API examples or fake API-key UI before M6.5C/D.

---

# 20. Pricing Page

The Pricing page must reflect M6A Plan catalog accurately.

Recommended structure:

```text
Pricing Hero

Desktop Rank Tracking
├── Free
├── Starter
└── Pro

Mobile Rank Tracking
├── Free
├── Starter
└── Pro

FAQ / Plan explanation
CTA
```

---

# 21. Pricing Data Source

Pricing must use the authoritative Plan API:

```text
GET /api/v1/billing/plans
```

or equivalent existing backend source.

Do not duplicate hard-coded prices and entitlements in the frontend.

---

# 22. Desktop Plans

Current catalog:

| Plan | Monthly Price | Max Projects | Max Keywords | Monthly Checks | Scheduling |
|---|---:|---:|---:|---:|---|
| Free | $0 | 1 | 50 | 100 | None |
| Starter | $19 | 5 | 500 | 5,000 | Weekly |
| Pro | $129 | 20 | 5,000 | 50,000 | Daily |

The public page must render current backend values rather than trusting these numbers as hard-coded UI constants.

---

# 23. Mobile Plans

Current catalog:

| Plan | Monthly Price | Max Projects | Max Keywords | Monthly Checks | Scheduling |
|---|---:|---:|---:|---:|---|
| Free | $0 | 1 | 20 | 50 | None |
| Starter | $39 | 3 | 200 | 1,000 | Weekly |
| Pro | $249 | 10 | 1,000 | 10,000 | Daily |

Again, values must come from the backend catalog.

---

# 24. Pricing Presentation

Desktop and Mobile must be visually distinct but part of the same design language.

Recommended:

```text
Desktop
[ Free ] [ Starter ] [ Pro ]

Mobile
[ Free ] [ Starter ] [ Pro ]
```

Do not combine them into one misleading comparison table.

---

# 25. Plan Card Content

Each card should show:

```text
Plan name
Price/month
Projects
Keywords
Monthly checks
Schedule availability
CTA
```

Optional:

```text
short target-customer description
```

Example:

```text
Starter
For freelancers and small SEO teams
```

---

# 26. Pricing CTA Behavior

Free:

```text
Start Free
→ /register
```

Paid Plans:

```text
Request Activation
```

or:

```text
Contact to Upgrade
```

Do not use:

```text
Buy Now
Checkout
Subscribe Now
```

until automatic payment exists.

---

# 27. Manual Payment Disclosure

Pricing should clearly state:

```text
Paid Plans are currently activated manually after payment confirmation.
```

Keep wording concise and transparent.

Do not imply automated processing.

---

# 28. Logged-In Pricing Behavior

If an authenticated customer visits `/pricing`:

- Page remains public-readable.
- CTA may direct to `/app/billing` or current billing settings.
- Do not auto-upgrade.
- Do not expose Admin actions.

---

# 29. Logged-Out Pricing Behavior

Free CTA:

```text
Register
```

Paid CTA:

```text
Register / Contact
```

Use current product flow.

---

# 30. Pricing FAQ

Recommended FAQ topics:

```text
What is a keyword check?
Why are Desktop and Mobile Plans separate?
When does monthly usage reset?
Can I use both Desktop and Mobile?
What happens when I reach my limit?
Can I upgrade later?
How are paid Plans activated?
```

Answers must align with M6A behavior.

---

# 31. FAQ Semantics

Explain:

```text
one logical keyword check = one customer usage unit
```

Do not discuss provider retries/fallback unless necessary.

---

# 32. Free Plan Messaging

Free should be positioned as:

```text
Try the product
Validate the workflow
Track a small set of keywords
```

Do not market Free as unlimited.

---

# 33. Starter Messaging

Suggested audience:

```text
freelancers
small websites
small SEO teams
```

---

# 34. Pro Messaging

Suggested audience:

```text
larger SEO teams
agencies
higher-volume tracking
```

Do not claim enterprise functionality that does not exist.

---

# 35. SEO Requirements

Public pages should be indexable.

Implement:

```text
title
meta description
canonical
Open Graph
Twitter/X metadata if project convention supports it
```

---

# 36. Suggested Home Metadata

Example:

```text
Title:
Google Rank Tracker for Desktop & Mobile | <Product Name>

Description:
Track Google keyword rankings across Desktop and Mobile, schedule rank checks,
monitor ranking history, and manage SEO sites in one place.
```

Use actual product name.

---

# 37. Suggested Pricing Metadata

Example:

```text
Title:
Pricing | <Product Name>

Description:
Compare Desktop and Mobile rank-tracking Plans, keyword limits,
monthly checks and scheduling options.
```

---

# 38. Sitemap

Generate sitemap entries for public pages only:

```text
/
/pricing
/login
/register
```

Do not expose private app/admin routes as public SEO destinations.

---

# 39. robots.txt

Allow public marketing pages.

Disallow/private-prevent indexing where appropriate:

```text
/app
/admin
/settings
```

Exact rules should fit Next.js routing.

---

# 40. Structured Data

Optional but recommended:

```text
SoftwareApplication
```

or:

```text
Product/Offer
```

only if the data accurately represents current public Plans.

Do not add review/rating schema without real review data.

---

# 41. Public Footer

Recommended sections:

```text
Product
- Home
- Pricing

Account
- Login
- Register

Future
- Docs (only when available)

Legal
- Terms
- Privacy
```

If Terms/Privacy routes do not exist, do not create dead links.

---

# 42. Legal Link Handling

If Terms/Privacy are not implemented yet:

- omit from Footer, or
- add only if existing legal pages exist.

Do not create empty placeholder legal pages in this milestone unless explicitly required.

---

# 43. Design Language

Reuse M6.5A visual direction:

```text
clean SaaS
light-first
strong typography
dark/navy accents where appropriate
white surfaces
subtle border/shadow
blue/brand primary actions
responsive cards
compact data previews
```

Public site should feel related to the authenticated app.

---

# 44. Design-System Reuse

Reuse M6.5A primitives where appropriate:

```text
Button
Card
Badge
Tabs if useful
Drawer
Alert
Skeleton
```

Public shell may have dedicated layout components, but should not reinvent basic UI primitives.

---

# 45. Home Hero Responsiveness

Desktop:

```text
two-column hero
copy + product preview
```

Mobile:

```text
stacked hero
CTA visible above fold
product preview scaled below
```

---

# 46. Pricing Responsiveness

Desktop:

```text
three cards per product line
```

Tablet:

```text
two-column or adaptive grid
```

Mobile:

```text
single-column stacked cards
```

No horizontal card scrolling required for core comprehension.

---

# 47. Accessibility

At minimum:

```text
semantic landmarks
proper heading hierarchy
keyboard-accessible navigation
visible focus styles
accessible mobile menu
buttons/links correctly distinguished
sufficient contrast
pricing cards readable without color dependency
```

---

# 48. Performance

Public pages should be lightweight.

Avoid shipping authenticated app bundles unnecessarily.

Use server/static rendering where practical.

Avoid large client-only hydration for static marketing content.

---

# 49. Rendering Strategy

Recommended:

```text
Home
→ static/server-rendered

Pricing
→ server-rendered or revalidated from Plan catalog
```

Pricing data must remain fresh enough to reflect catalog changes.

---

# 50. Pricing Data Failure UX

If Plan catalog cannot load:

```text
show a graceful error state
```

Do not silently show stale hard-coded prices.

If safe cached/revalidated data exists, use framework-appropriate fallback.

---

# 51. No Marketing Claims Beyond Product Reality

Do not claim:

```text
real-time rankings
unlimited keywords
unlimited projects
global unlimited mobile tracking
AI recommendations
competitor intelligence
automated billing
API availability
```

unless those features actually exist.

---

# 52. CTA Accuracy

Allowed:

```text
Start Free
Create Account
View Pricing
Request Activation
Contact to Upgrade
Login
```

Avoid:

```text
Subscribe instantly
Buy now
Activate automatically
```

---

# 53. Product Screenshots / Visuals

Use real/stable product-style visuals derived from current UI.

Do not expose:

```text
real customer email
real bank reference
provider secrets
internal Admin notes
```

Use synthetic/demo data.

---

# 54. Marketing Demo Data

Any public mock UI should use safe synthetic values:

```text
example.com
seo-demo.com
best running shoes
project names like "US Desktop"
```

No real customer data.

---

# 55. Public Pricing and M6A Billing Consistency

Pricing must match:

```text
Plan code
device scope
price
Projects
Keywords
monthly checks
schedule entitlement
```

from backend.

Add test coverage ensuring frontend grouping maps backend plan data correctly.

---

# 56. Analytics Instrumentation

Do NOT add third-party marketing analytics in M6.5B unless explicitly requested.

No Google Analytics, Meta Pixel, Hotjar, etc. by default.

---

# 57. Public API Boundary

M6.5B must not expose or document `/api/v1` as a customer integration API.

M6.5C will create the stable public API boundary.

---

# 58. Authenticated App Boundary

The public site may link to:

```text
/app
```

after login.

Do not merge public and authenticated navigation states.

---

# 59. Browser Verification — Home

Verify:

```text
Home loads logged out
header navigation
hero CTA
pricing CTA
feature sections
responsive menu
login/register routes
footer
no authenticated data leak
```

---

# 60. Browser Verification — Pricing

Verify:

```text
six Plans render
Desktop grouped correctly
Mobile grouped correctly
prices correct
entitlements correct
Free CTA correct
paid CTA reflects manual activation
mobile card layout
logged-in CTA behavior
```

---

# 61. Responsive Verification

At minimum:

```text
375px
768px
1024px
1280px
1440px
```

Check:

```text
header
mobile menu
hero
feature cards
pricing grids
FAQ
footer
CTA buttons
no critical overflow
```

---

# 62. SEO Verification

Check generated output for:

```text
title
description
canonical
Open Graph
robots
sitemap
```

Confirm private authenticated/admin routes are not promoted in sitemap.

---

# 63. Frontend Tests

Add tests for:

```text
Home sections
public navigation
mobile menu
Pricing grouping
Pricing values from API
CTA behavior
pricing load failure
logged-in vs logged-out CTA behavior if implemented
```

---

# 64. Backend Tests

No backend business change should be needed.

If Plan catalog endpoint changes for public rendering, add focused tests.

Do not weaken authentication/business rules.

---

# 65. Regression

Must preserve:

```text
M6.5A authenticated AppShell
Overview
Projects
Keywords
Tracked Sites
Rankings
Batch/Job
Schedule
Billing & Usage
Admin
M6A Plan behavior
```

---

# 66. Build Verification

Run:

```text
frontend tests
ESLint
Prettier
TypeScript strict
npm audit
Next.js production build
Docker health
```

If backend touched:

```text
backend tests
Ruff
mypy
```

---

# 67. Documentation

Create:

```text
docs/public-site-architecture.md
```

Document:

```text
public shell
route ownership
Home sections
Pricing data source
SEO strategy
responsive rules
CTA rules
public/authenticated boundary
future M6.5C/D hooks
```

---

# 68. Verification Report

Create:

```text
docs/verification-milestone-6.5b.md
```

Include:

```text
implementation summary
public shell
Home structure
Pricing architecture
Plan data source
CTA behavior
SEO metadata
robots/sitemap
responsive verification
accessibility
browser verification
exact commands
test counts
production build
Docker health
regression status
known limitations
full DoD
```

Do not claim checks that were not executed.

---

# 69. Definition of Done — Public Shell

```text
[ ] public header
[ ] public mobile navigation
[ ] public footer
[ ] login CTA
[ ] register/start CTA
[ ] public shell visually matches M6.5A language
```

---

# 70. Definition of Done — Home

```text
[ ] Hero
[ ] product value proposition
[ ] How It Works
[ ] core features
[ ] Desktop vs Mobile explanation
[ ] Tracked Sites / alias section
[ ] scheduling section
[ ] usage/Plans preview
[ ] API/developer teaser is truthful
[ ] final CTA
[ ] responsive
```

---

# 71. Definition of Done — Pricing

```text
[ ] six Plans render
[ ] Desktop and Mobile are separate sections
[ ] prices sourced from authoritative backend data
[ ] Project limits shown
[ ] Keyword limits shown
[ ] monthly checks shown
[ ] scheduling shown
[ ] Free CTA correct
[ ] paid CTA reflects manual activation
[ ] no fake checkout
[ ] FAQ aligns with M6A
```

---

# 72. Definition of Done — SEO

```text
[ ] Home metadata
[ ] Pricing metadata
[ ] canonical URLs
[ ] Open Graph
[ ] robots.txt
[ ] sitemap.xml
[ ] no private routes advertised in sitemap
```

---

# 73. Definition of Done — Responsive

```text
[ ] 375px passed
[ ] 768px passed
[ ] 1024px passed
[ ] 1280px passed
[ ] 1440px passed
[ ] no critical overflow
[ ] mobile navigation usable
[ ] Pricing cards readable
[ ] CTAs visible
```

---

# 74. Definition of Done — Accessibility

```text
[ ] semantic landmarks
[ ] coherent headings
[ ] keyboard public navigation
[ ] focus visible
[ ] mobile menu accessible
[ ] buttons/links semantically correct
[ ] contrast acceptable
```

---

# 75. Definition of Done — Quality

```text
[ ] frontend tests pass
[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes
[ ] npm audit acceptable
[ ] production build passes
[ ] browser Home journey passes
[ ] browser Pricing journey passes
[ ] responsive verification passes
[ ] Docker services healthy
[ ] authenticated app regression passes
```

---

# 76. Expected Known Limitations

After M6.5B, intentionally deferred:

```text
public Docs
customer API
API Keys
payment gateway
automatic checkout
automatic recurring billing
advanced analytics
blog/CMS
multi-language marketing site
dark public theme
```

---

# 77. Roadmap

```text
M1     Foundation
M2     Authentication
M3     Projects + Keywords
M3.1   Tracked Sites + Domain Aliases
M4     Ranking Engine
M4.1   Multi-provider Routing
M5     Async Jobs + Cloud Tasks
M6A    Billing + Manual Subscription + Usage Limits
M6.5A  Design System + App UX/UI Redesign
M6.5B  Public Home + Pricing
M6.5C  Developer API + API Keys
M6.5D  Developer Docs
M6B    Payment Integration
M7     Ranking Dashboard + Analytics
M8     Production Deployment
```

---

# 78. Final Instruction to Codex

Implement M6.5B against the CURRENT accepted M6.5A repository.

Before modifying code, inspect:

```text
M6.5A design system
public/auth route layout
existing /pricing implementation from M6A
billing Plan API
AppShell/public boundary
current metadata handling
Next.js sitemap/robots support
existing browser scripts
frontend test conventions
```

Critical rules:

```text
1. Reuse M6.5A visual language and shared primitives.

2. Build a dedicated public shell; do not use the authenticated sidebar layout.

3. Home must accurately describe the implemented product.

4. Pricing must render authoritative backend Plan data.

5. Desktop and Mobile must remain separate product lines.

6. Do not hard-code Plan prices/limits into business rendering logic.

7. Free CTA may register/start immediately.

8. Paid CTA must reflect manual activation/bank-transfer workflow.

9. Do not implement fake Checkout.

10. Do not implement Stripe, crypto, PayPal or automatic payment.

11. Do not expose provider/cloud infrastructure.

12. Do not document internal /api/v1 as a customer integration API.

13. Do not implement API Keys or public customer API.

14. Do not add M7 analytics.

15. Public pages must be responsive and accessible.

16. Public pages must have correct SEO metadata.

17. Do not claim features that are not implemented.

18. Preserve all M1–M6.5A authenticated behavior.
```

Before completion:

```text
run frontend full suite
run backend suite if backend touched

run ESLint
run Prettier
run TypeScript strict
run npm audit

run production Next.js build
verify sitemap
verify robots
verify metadata/canonical/Open Graph

run Home browser journey
run Pricing browser journey

run responsive checks:
375
768
1024
1280
1440

run authenticated regression:
login
Overview
Projects
Tracked Sites
Rankings
Billing
Admin

verify Docker services healthy
```

Create:

```text
docs/public-site-architecture.md
docs/verification-milestone-6.5b.md
```

Do not mark M6.5B complete unless the Pricing page is driven by the authoritative Plan catalog and the Home page accurately reflects the actual product without exposing unfinished or internal capabilities.
