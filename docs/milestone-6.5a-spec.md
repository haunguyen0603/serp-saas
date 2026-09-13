# SERP SaaS — Milestone 6.5A Specification

## Design System + Customer App UX/UI Redesign

**Target milestone:** M6.5A  
**Status:** Specification  
**Prerequisite:** M6A Billing + Manual Subscription + Usage Limits completed or functionally stable.  
**Primary goal:** Establish a reusable design system and redesign the authenticated customer application so the product feels consistent, modern, clear, responsive, and production-ready without changing core business behavior.

---

# 1. Objective

M6.5A is a product-experience milestone.

It must improve:

- visual consistency
- navigation
- information hierarchy
- data readability
- responsive behavior
- empty/loading/error states
- accessibility
- customer task flows

It must NOT change the underlying business semantics of Projects, Keywords, Tracked Sites, Rankings, Rank Check Batches, Schedules, Billing, Usage, Subscriptions, Provider routing, or Worker execution.

The redesign should be a presentation and UX refactor, not a business-logic rewrite.

---

# 2. Scope

M6.5A must implement:

- Design tokens.
- Typography system.
- Spacing system.
- Radius/shadow system.
- Semantic color system.
- Reusable Button, Input, Select, Textarea, Checkbox, Radio, Switch.
- Card, Table, Badge, Tabs, Dialog, Drawer, Dropdown, Tooltip, Toast.
- Skeleton/loading patterns.
- Empty-state patterns.
- Error-state patterns.
- Confirmation patterns for destructive actions.
- Application shell.
- Sidebar navigation.
- Top bar/contextual header.
- Breadcrumbs where useful.
- Authenticated customer Overview screen.
- Project list redesign.
- Project detail redesign.
- Keyword management redesign.
- Tracked Sites redesign.
- Rankings UI redesign.
- Batch history redesign.
- Schedule UI redesign.
- Billing & Usage redesign.
- Account/settings cleanup.
- Responsive desktop/tablet/mobile layouts.
- Accessibility pass.
- Interaction consistency.
- Visual polish.
- Optional dark mode if implementation cost remains contained.
- Browser regression verification.
- Responsive browser verification.
- Documentation and final verification report.

---

# 3. Explicitly Out of Scope

Do NOT implement in M6.5A:

```text
public marketing Home page
public Pricing page
public Docs portal
customer API keys
public customer API
Stripe
crypto payments
new Billing logic
new Plan rules
new provider logic
new ranking algorithm
new analytics engine
new reporting engine
competitor analysis
new notifications
new backend workflow
M6.5B/C/D functionality
```

---

# 4. UX Principles

Follow these principles:

1. Clear before clever.
2. Data-heavy screens must remain easy to scan.
3. Primary actions must be obvious.
4. Secondary actions must not compete visually.
5. Destructive actions require clear confirmation.
6. Empty states explain the next useful action.
7. Loading states preserve layout.
8. Error states explain what the user can do next.
9. Mobile layouts must be truly usable, not just compressed desktop.
10. Customer UI must not expose infrastructure concepts.

Do not show normal customers:

```text
SerpApi
Serper
Cloud Tasks
Cloud Run
GCP service accounts
queue names
provider budgets
worker internals
```

unless a technical detail screen intentionally exposes safe metadata.

---

# 5. Design System Foundation

Create a reusable design-system layer consistent with the current frontend architecture.

Recommended conceptual categories:

```text
tokens
components
patterns
layouts
```

---

# 6. Design Tokens

Define semantic tokens instead of repeated raw styles.

Recommended color semantics:

```text
background
surface
surface-muted
border
border-strong

text-primary
text-secondary
text-muted

brand
brand-hover

success
warning
danger
info
```

Avoid scattered hard-coded color choices in feature components.

---

# 7. Typography

Define consistent variants:

```text
display
heading-1
heading-2
heading-3
body
body-sm
caption
label
mono
```

Use consistent line-height and weight.

---

# 8. Spacing

Use a consistent rhythm, for example:

```text
4
8
12
16
24
32
48
64
```

Avoid arbitrary spacing per screen.

---

# 9. Radius and Shadows

Use a small consistent set:

```text
radius-sm
radius-md
radius-lg

shadow-sm
shadow-md
```

---

# 10. Core Components

Create or standardize:

```text
Button
IconButton
Input
Textarea
Select
Combobox
Checkbox
Radio
Switch
FormField
FormError

Card
StatCard
Badge
StatusBadge

Table
DataTable
CursorPagination

Tabs
DropdownMenu
Tooltip
Popover

Dialog
ConfirmDialog
Drawer

Toast
Alert

Skeleton
Spinner
EmptyState
ErrorState
```

---

# 11. Button Hierarchy

Support:

```text
primary
secondary
ghost
danger
```

Sizes:

```text
sm
md
lg
```

Rules:

- One dominant primary action per major screen section.
- Danger actions never look like normal primary actions.
- Disabled/loading states are visually obvious.

---

# 12. Form UX

Forms must include:

- visible labels
- help text where needed
- inline validation
- clear errors
- required-state indication
- disabled/loading states

Do not use placeholder text as the only label.

---

# 13. Status System

Standardize status badges for:

```text
Active
Paused
Archived
Queued
Running
Completed
Completed with errors
Failed
Cancelled
Free
Starter
Pro
```

The same semantic state must look the same across features.

---

# 14. Loading Patterns

Use skeletons for content-heavy screens.

Examples:

```text
Project rows
Ranking table
Billing usage cards
Batch history
```

Avoid full-page centered spinners when layout is known.

---

# 15. Empty States

Each empty state should answer:

```text
What is missing?
Why does it matter?
What should the user do next?
```

Examples:

```text
No Projects yet → Create your first Project
No Tracked Sites → Add a site to match ranking results
No ranking history → Run your first rank check
No schedule → Add a schedule
```

---

# 16. Error States

Provide reusable patterns for:

```text
inline form errors
page-level errors
table/data load errors
action failure toasts
```

Map backend error codes to useful customer-facing messages.

Never expose raw exceptions.

---

# 17. Authenticated App Shell

Recommended structure:

```text
┌──────────────────────────────────────────────┐
│ Top bar                                      │
├───────────────┬──────────────────────────────┤
│ Sidebar       │ Main content                 │
│               │                              │
│ Overview      │                              │
│ Projects      │                              │
│ Rankings      │                              │
│ Tracked Sites │                              │
│ Billing       │                              │
│ Account       │                              │
└───────────────┴──────────────────────────────┘
```

---

# 18. Customer Navigation

Recommended:

```text
Overview

Rank Tracking
├── Projects
├── Rankings
└── Tracked Sites

Usage & Billing
└── Billing & Usage

Account
└── Settings
```

Do not show unfinished Developer/API navigation yet.

---

# 19. Top Bar

May include:

```text
page title/context
breadcrumb
account menu
theme toggle if implemented
```

Avoid duplicating the sidebar.

---

# 20. Overview Screen

Add authenticated Overview at `/app` or current equivalent.

Use existing product data only:

```text
active Projects
active Keywords
Desktop usage summary
Mobile usage summary
recent Rank Check Batches
subscription summary
```

Optional first-time checklist:

```text
[ ] Add Tracked Site
[ ] Create Project
[ ] Add Keywords
[ ] Run first rank check
```

Do not introduce M7 analytics.

---

# 21. Project List Redesign

Display:

```text
Project name
device
country
language
location
Keyword count
latest check status/date
schedule status
```

Primary action:

```text
New Project
```

Secondary row actions should live in a compact actions menu.

---

# 22. Project Detail

Recommended layout:

```text
Project Header
├── name
├── search environment
├── status
├── Check Rankings
└── actions menu

Sections/Tabs
├── Keywords
├── Rankings
├── Batch History
└── Schedule
```

---

# 23. Project Search Environment

Show clearly:

```text
Google
Desktop / Mobile
Country
Language
Location
```

Use compact chips or structured metadata.

Do not expose provider selection.

---

# 24. Keyword Manager

Improve:

```text
bulk add
search/filter
active/paused state
Check now
latest position
latest status
```

Bulk add should clearly show limits and validation errors.

---

# 25. Keyword Actions

Standardize:

```text
Check now
Pause / Resume
Delete
```

Destructive actions require confirmation.

---

# 26. Rankings UI

Optimize for scanability.

Recommended columns:

```text
Keyword
Tracked Site
Position
Checked at
Status
```

Only include previous-position delta if current APIs already support it.

Do not add new analytics calculations in M6.5A.

---

# 27. Ranking States

Clearly distinguish:

```text
Ranked
Not found
Never checked
Failed
Queued
Running
```

Use text plus semantic badge/icon, not color alone.

---

# 28. Rank Check Detail

Group information:

```text
Summary
Search Environment
Matched Sites
Top Organic Results
Safe provider metadata if intentionally shown
Attempt metadata
Timestamps
```

Provider metadata remains informational only.

---

# 29. Tracked Sites

Site list:

```text
Site name
Primary domain
Alias count
Status
```

Site detail:

```text
Primary domain
Aliases
Active/inactive status
Add alias
Promote primary
Deactivate/remove where allowed
```

Explain the 301/domain-alias use case clearly.

---

# 30. Domain Labels

Use explicit labels:

```text
Primary
Alias
Inactive
```

Do not rely on icon-only distinction.

---

# 31. Batch History

Display:

```text
Requested at
Trigger
Status
Progress
Succeeded
Failed
Duration
```

---

# 32. Batch Progress

Show both text and progress bar:

```text
312 / 500 completed
62%
```

---

# 33. Batch Job Detail

If current API supports it, show:

```text
Keyword
Status
Attempts
Last safe error
Completed at
```

---

# 34. Schedule UX

Simple editor:

```text
Enabled
Daily / Weekly
Weekday if weekly
Local time
Timezone
Next run
```

Never expose raw cron.

---

# 35. Schedule States

Use:

```text
Active
Paused
Not configured
Disabled by Plan
```

If disabled by M6A Plan rules, explain why.

---

# 36. Billing & Usage Redesign

Keep Desktop and Mobile clearly separate.

For each:

```text
Plan name
Price
Subscription period
Projects used / limit
Keywords used / limit
Checks used / limit
Schedule entitlement
Next reset
```

---

# 37. Usage Visualization

Use simple progress bars plus exact numbers.

Example:

```text
3,200 / 5,000 checks
64%
```

Do not make users infer exact usage from charts.

---

# 38. Manual Upgrade Messaging

Because M6A uses manual activation:

```text
Upgrade available via bank transfer / contact
```

Do not create fake checkout UX.

---

# 39. Admin UI Consistency

Existing M6A Admin screens should reuse the same design system.

Do not expand Admin business scope.

---

# 40. Account / Settings

Standardize:

```text
profile
email
billing link
logout
```

Do not expose session/token internals.

---

# 41. Responsive Targets

Verify at minimum:

```text
1440px
1280px
1024px
768px
375px
```

---

# 42. Mobile Navigation

Use:

```text
collapsible sidebar
or
drawer navigation
```

Do not keep a wide fixed sidebar on small screens.

---

# 43. Mobile Data Views

For dense tables, use:

```text
stacked rows
cards
priority columns with expandable details
```

Avoid unreadably small table layouts.

---

# 44. Accessibility

At minimum:

```text
keyboard navigation
visible focus states
form labels
ARIA labels for icon-only controls
dialog focus trapping
escape-to-close where appropriate
semantic heading hierarchy
acceptable contrast
status not conveyed by color alone
```

---

# 45. Dark Mode

Optional.

If implemented, support:

```text
light
dark
system
```

Do not ship incomplete dark mode.

A polished light mode is more important than a broken theme toggle.

---

# 46. Content Style

UI copy should be:

```text
short
specific
task-oriented
consistent
```

Example:

Bad:

```text
SERP_NO_PROVIDER_AVAILABLE
```

Customer-facing:

```text
Ranking service is temporarily unavailable.
```

---

# 47. Confirmation UX

Require confirmation for:

```text
Project deletion
Keyword deletion
destructive Tracked Site/domain changes
Batch cancellation
destructive Admin actions already present
```

State consequences clearly.

---

# 48. Toast Usage

Appropriate for transient success:

```text
Project created
Schedule updated
Rank check queued
Alias added
```

Critical persistent errors should also remain visible in-page.

---

# 49. Routing

Recommended authenticated route direction:

```text
/app
/app/projects
/app/projects/{id}
/app/tracked-sites
/app/rankings
/app/billing
/app/settings
```

Route migration is optional if it creates unnecessary regression risk.

---

# 50. Shared Component Ownership

Feature screens should use shared components.

Do not create separate button/table/badge implementations in each feature.

---

# 51. Tailwind Rules

Tailwind remains appropriate.

Avoid repeated large class strings across features.

Prefer reusable semantic components.

---

# 52. Icons

Use one icon family consistently.

Icon-only buttons need accessible labels/tooltips.

---

# 53. First-Time Experience

After registration/login, guide users toward:

```text
1. Add Tracked Site
2. Create Project
3. Add Keywords
4. Run Rankings
```

A lightweight checklist is sufficient.

No full onboarding wizard required.

---

# 54. Performance UX

Use:

```text
stable skeleton dimensions
targeted TanStack Query invalidation
query caching
optimistic UI only where safe
```

Avoid refetching the entire app after every mutation.

---

# 55. TanStack Query

Preserve existing data architecture.

Standardize:

```text
query keys
loading handling
error handling
mutation invalidation
```

Do not replace TanStack Query in this milestone.

---

# 56. Small Overview API Exception

If the Overview page would otherwise require excessive client requests, a narrow authenticated summary endpoint may be added.

Example:

```text
GET /api/v1/overview
```

Allowed data:

```text
Project counts
Keyword counts
current Billing/Usage summary
recent batches
```

Do not turn it into analytics.

---

# 57. Backend Change Rule

M6.5A should be frontend-heavy.

Backend changes are allowed only for presentation ergonomics or a narrow Overview aggregation.

Do not alter business rules to simplify UI.

---

# 58. Design Documentation

Create:

```text
docs/design-system.md
docs/ux-app-architecture.md
```

Document:

```text
tokens
components
navigation
responsive rules
status mapping
form rules
empty/error/loading patterns
accessibility conventions
```

---

# 59. Frontend Tests

Add or update tests for:

```text
shared components
navigation
mobile navigation
empty states
error states
status rendering
Billing & Usage rendering
Batch progress
dialogs
confirmation flows
```

---

# 60. Regression Tests

Existing behavior must remain correct:

```text
authentication
Projects
Keywords
Tracked Sites
Rankings
Batch history
Schedules
Billing
Usage limits
Admin access
```

---

# 61. Browser Verification

Full customer journey:

```text
login
Overview
create Project
manage Keywords
manage Tracked Sites
queue rank check
observe Batch progress
view Rankings
manage Schedule
view Billing & Usage
Account
logout
```

---

# 62. Responsive Browser Verification

Run at least:

```text
desktop
tablet
mobile
```

Verify:

```text
no critical overflow
navigation works
dialogs fit
primary actions remain visible
data-heavy screens remain readable
```

---

# 63. Visual Verification

If practical, capture stable screenshots for:

```text
Overview
Projects
Project detail
Tracked Sites
Rankings
Billing
mobile navigation
```

Do not block the milestone solely on introducing pixel-perfect screenshot infrastructure if none exists.

---

# 64. Definition of Done — Design System

```text
[ ] semantic color tokens
[ ] typography system
[ ] spacing system
[ ] radius/shadow system
[ ] shared form controls
[ ] Card/Table/Badge/Tabs/Dialog/Drawer
[ ] Toast/Alert
[ ] Skeleton
[ ] EmptyState
[ ] ErrorState
[ ] consistent status system
```

---

# 65. Definition of Done — App Shell

```text
[ ] authenticated app shell
[ ] sidebar navigation
[ ] responsive mobile navigation
[ ] top bar/context header
[ ] active navigation state
[ ] consistent page width/spacing
```

---

# 66. Definition of Done — Overview

```text
[ ] Overview screen exists
[ ] existing product summary data displayed
[ ] current usage summary
[ ] recent Batch summary
[ ] first-time checklist
[ ] no M7 analytics added
```

---

# 67. Definition of Done — Core Screens

```text
[ ] Projects redesigned
[ ] Project detail redesigned
[ ] Keywords redesigned
[ ] Tracked Sites redesigned
[ ] Rankings redesigned
[ ] Rank Check detail redesigned
[ ] Batch history/progress redesigned
[ ] Schedule UX redesigned
[ ] Billing & Usage redesigned
[ ] Account/settings aligned
[ ] M6A Admin screens use shared system
```

---

# 68. Definition of Done — Responsive UX

```text
[ ] desktop usable
[ ] laptop usable
[ ] tablet usable
[ ] mobile usable
[ ] no critical horizontal overflow
[ ] mobile navigation works
[ ] dense data remains readable
```

---

# 69. Definition of Done — Accessibility

```text
[ ] visible focus states
[ ] keyboard navigation
[ ] semantic labels
[ ] dialog focus management
[ ] accessible icon-only actions
[ ] status not color-only
[ ] contrast acceptable
[ ] heading hierarchy coherent
```

---

# 70. Definition of Done — Behavior Preservation

```text
[ ] auth unchanged
[ ] Project/Keyword behavior unchanged
[ ] Tracked Site behavior unchanged
[ ] ranking behavior unchanged
[ ] Batch/Job behavior unchanged
[ ] schedule behavior unchanged
[ ] Billing/Usage limits unchanged
[ ] Admin authorization unchanged
[ ] provider/cloud infrastructure remains hidden from normal UX
```

---

# 71. Definition of Done — Quality

```text
[ ] frontend full suite passes
[ ] backend regression suite passes if backend touched
[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes
[ ] npm audit acceptable
[ ] frontend production build passes
[ ] browser verification passes
[ ] responsive browser verification passes
[ ] Docker services healthy
```

---

# 72. Verification Report

Create:

```text
docs/verification-milestone-6.5a.md
```

Include:

```text
implementation summary
design system architecture
tokens
shared components
app shell
navigation
Overview
screen-by-screen redesign
responsive behavior
accessibility
files created/modified
backend changes if any
exact commands
exact test counts
browser verification
responsive verification
production build
regressions
known limitations
full Definition of Done
```

Do not claim a check passed unless actually executed.

---

# 73. Expected Known Limitations

After M6.5A, these remain intentionally absent:

```text
public marketing Home
public Pricing
public Docs
public customer API
API key management
payment gateway
advanced analytics
```

---

# 74. Roadmap

```text
M6A   Billing + Manual Subscription + Usage Limits
M6.5A Design System + App UX/UI Redesign
M6.5B Public Home + Pricing
M6.5C Developer API + API Keys
M6.5D Developer Docs
M6B   Payment Integration
M7    Ranking Dashboard + Analytics
M8    Production Deployment
```

---

# 75. Final Instruction to Codex

Implement this M6.5A specification against the CURRENT repository after M6A.

Before modifying code, inspect:

```text
current frontend architecture
authenticated routes
Tailwind configuration
TanStack Query usage
forms
tables
dialogs
toasts
M5 Batch/Job UI
M6A Billing/Admin UI
browser verification scripts
frontend test conventions
```

Critical rules:

```text
1. This is a UX/UI redesign, not a business rewrite.

2. Preserve all M1–M6A backend/business semantics.

3. Build reusable design-system primitives before feature-by-feature styling.

4. Avoid repeated ad-hoc Tailwind patterns.

5. Do not expose provider/cloud infrastructure in normal customer UX.

6. Preserve Desktop/Mobile Billing separation from M6A.

7. Do not implement public Home, public Pricing, Docs, API keys,
   public API, Stripe, crypto payments, or M7 analytics.

8. Responsive mobile behavior is mandatory.

9. Accessibility is mandatory.

10. Do not remove functionality for visual simplicity.

11. Existing automated tests and browser journeys must remain green.

12. Add focused tests for new shared components and redesigned critical flows.

13. A small Overview summary endpoint is permitted only if required to avoid
    excessive frontend requests.

14. Do not claim browser/visual verification passed unless actually executed.
```

Before completion:

```text
run frontend full suite
run backend regression if backend changed

run ESLint
run Prettier
run TypeScript strict
run npm audit

run frontend production build

run full authenticated customer browser journey
run desktop viewport verification
run tablet viewport verification
run mobile viewport verification

verify Docker services healthy
verify relevant M1–M6A regressions
```

Create:

```text
docs/verification-milestone-6.5a.md
```

M6.5A is not complete if the design system exists only as unused shared components. It must actually be adopted across the primary customer-facing application screens.
