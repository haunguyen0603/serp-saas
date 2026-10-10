# Milestone 7H — SEO Landing Pages

## 1. Objective

Add three public commercial SEO landing pages to SERP SaaS:

```text
/google-serp-rank-tracker
/daily-serp-tracker
/serp-tracking-for-agencies
```

Goals:

- capture non-brand commercial search intent already appearing in Google Search Console;
- reduce over-reliance on the homepage for impressions;
- give Google clearer intent-specific landing pages;
- improve organic acquisition and conversion;
- strengthen topical coverage around SERP rank tracking.

Do not change authenticated application behavior, billing, ranking execution, provider routing, reports, competitor analytics, database schema, or Cloud Run infrastructure.

## 2. Search intent mapping

### `/google-serp-rank-tracker`

Target themes:

```text
google serp rank tracker
google rank tracker
serp position tracker
keyword rank tracker
```

Purpose: broad commercial/product landing page for people looking for a Google SERP rank-tracking tool.

### `/daily-serp-tracker`

Target themes:

```text
daily serp tracker
google serp daily tracking
daily rank tracker
daily keyword tracking
```

Purpose: commercial page focused on scheduled recurring rank monitoring.

### `/serp-tracking-for-agencies`

Target themes:

```text
serp tracking for agencies
rank tracker for agencies
seo rank tracking for agencies
agency keyword rank tracker
```

Purpose: commercial page for SEO freelancers/agencies managing multiple client projects.

Do not claim search volume, ranking difficulty, or expected traffic unless separately researched and verified.

## 3. Architecture

Use normal Next.js App Router pages:

```text
frontend/src/app/
  google-serp-rank-tracker/
    page.tsx
  daily-serp-tracker/
    page.tsx
  serp-tracking-for-agencies/
    page.tsx
```

Reuse existing:

```text
PublicShell
public typography/layout
button/link components
metadata helpers
canonical helpers
JSON-LD conventions
```

Prefer static/server rendering.

Do not introduce a CMS, database content, client-side page builder, or new marketing framework.

## 4. Commercial landing pages vs Blog

These pages are not Blog articles.

Blog content should remain informational.

Landing pages should focus on:

```text
problem
product capability
workflow
benefits
use case
product limitations
CTA
```

Do not move them under `/blog`.

## 5. Google SERP Rank Tracker page

Route:

```text
/google-serp-rank-tracker
```

Recommended metadata:

```text
Title:
Google SERP Rank Tracker for Keyword Position Monitoring | SERP SaaS

Description:
Track Google keyword positions, compare ranking changes, monitor competitors, and review ranking history with SERP SaaS.
```

Recommended H1:

```text
Google SERP Rank Tracker
```

Recommended hero:

```text
Track keyword positions in Google, compare ranking changes over time,
and monitor the sites that matter to your SEO workflow.
```

Suggested structure:

```text
H1 Google SERP Rank Tracker

Hero + CTA

H2 Track keyword positions in one place
- Projects
- Keywords
- Tracked Sites
- Ranking history

H2 Compare ranking movement over time
- improved
- declined
- unchanged
- entered checked depth
- left checked depth

H2 Monitor competitors alongside your site
- same-check competitor comparisons
- opportunities
- trends

H2 Organize keyword sets
- Groups
- Tags
- filters
- Ranking Explorer

H2 Export and share ranking data
- CSV
- PDF
- scheduled reports where supported

H2 Understand what SERP SaaS measures
- checked-depth semantics
- desktop/mobile distinction
- search environment

H2 Start tracking Google rankings
- CTA
```

Do not imply full Top 100 tracking if the current production checked depth is Top 10.

Use checked-depth-aware language.

## 6. Daily SERP Tracker page

Route:

```text
/daily-serp-tracker
```

Recommended metadata:

```text
Title:
Daily SERP Tracker for Google Keyword Rankings | SERP SaaS

Description:
Monitor Google keyword ranking changes on a recurring schedule, review movement over time, and investigate meaningful SERP changes with SERP SaaS.
```

Recommended H1:

```text
Daily SERP Tracker
```

Recommended hero:

```text
Monitor recurring Google ranking changes without manually checking every keyword each day.
```

Suggested structure:

```text
H1 Daily SERP Tracker

Hero + CTA

H2 Why daily SERP tracking matters
H2 Schedule recurring ranking checks
H2 See what changed
H2 Investigate ranking drops
H2 Keep reporting consistent
H2 Daily tracking without unnecessary complexity
H2 Start monitoring ranking changes
```

Important product rule:

Daily scheduling is plan-dependent.

Do not claim:

```text
Every account gets daily checks.
```

Use:

```text
Daily or weekly scheduling is available according to plan entitlement.
```

Do not describe the product as real-time or continuous monitoring.

## 7. SERP Tracking for Agencies page

Route:

```text
/serp-tracking-for-agencies
```

Recommended metadata:

```text
Title:
SERP Tracking for SEO Agencies | Client Rank Tracking | SERP SaaS

Description:
Organize client keyword tracking, compare competitors, monitor ranking movement, and create reports with SERP SaaS.
```

Recommended H1:

```text
SERP Tracking for SEO Agencies
```

Recommended hero:

```text
Organize client ranking projects, monitor keyword movement, compare competitors, and create repeatable SEO reports.
```

Suggested structure:

```text
H1 SERP Tracking for SEO Agencies

Hero + CTA

H2 Keep client environments separated
H2 Organize client keyword sets
H2 Track client and competitor visibility
H2 Build repeatable client reports
H2 Review movement without scanning every keyword
H2 Scale tracking with clear plan limits
H2 A simpler workflow for small SEO teams
H2 Start a client tracking project
```

Important tenant rule:

Current product ownership is user-based.

Do not imply:

```text
organizations
team workspaces
memberships
client portals
role-based agency access
```

Safe wording:

```text
manage multiple client projects from one account
```

## 8. Avoid page duplication

Each page must satisfy a distinct search intent:

```text
/google-serp-rank-tracker
→ broad product/category intent

/daily-serp-tracker
→ recurring monitoring intent

/serp-tracking-for-agencies
→ agency workflow/use-case intent
```

Do not duplicate large blocks of copy and simply replace keywords.

## 9. Internal linking

Create a crawlable content graph.

Homepage should link naturally to the new pages.

Relevant Blog links:

```text
/blog/how-to-track-google-rankings
→ /google-serp-rank-tracker

/blog/how-to-monitor-keyword-ranking
→ /daily-serp-tracker

/blog/serp-tracking-for-agencies
→ /serp-tracking-for-agencies
```

Landing pages should also link back to related Blog guides.

Use normal `<a href>` / Next Link semantics.

Avoid excessive exact-match anchor text.

## 10. Homepage changes

Do not rewrite the entire homepage.

Add only enough content to expose the new pages.

Possible section:

```text
Built for different rank-tracking workflows

Google SERP Rank Tracker
Daily SERP Tracking
SERP Tracking for Agencies
```

Keep homepage as the broad brand/product page.

## 11. Navigation and footer

Do not overload the top navigation.

Recommended primary nav can remain:

```text
Home
Pricing
Blog
```

Expose landing pages through homepage sections, footer, and contextual Blog links.

If the footer structure supports it, add:

```text
Product
- Google SERP Rank Tracker
- Daily SERP Tracker
- SERP Tracking for Agencies
```

## 12. Canonical URLs

Canonical URLs must be:

```text
https://serpsaas.com/google-serp-rank-tracker
https://serpsaas.com/daily-serp-tracker
https://serpsaas.com/serp-tracking-for-agencies
```

Never emit:

```text
http://
www.serpsaas.com
app.serpsaas.com
api.serpsaas.com
*.run.app
localhost
```

## 13. Preserve canonical redirect infrastructure

Current production canonical behavior must remain:

```text
http://serpsaas.com/*      → 301 → https://serpsaas.com/*
http://www.serpsaas.com/*  → 301 → https://serpsaas.com/*
https://www.serpsaas.com/* → 301 → https://serpsaas.com/*
```

Do not modify the current load-balancer architecture.

## 14. Sitemap

Add:

```text
https://serpsaas.com/google-serp-rank-tracker
https://serpsaas.com/daily-serp-tracker
https://serpsaas.com/serp-tracking-for-agencies
```

to the existing sitemap.

Do not create a second sitemap.

Do not remove Blog/public URLs.

Do not include private/authenticated routes.

## 15. robots.txt

All three pages must be crawlable.

Keep:

```text
Sitemap: https://serpsaas.com/sitemap.xml
```

Do not add any matching Disallow rules.

## 16. Structured data

Use only supported structured data.

Recommended:

```text
WebPage
SoftwareApplication
BreadcrumbList
```

Reuse existing site-wide SoftwareApplication data where appropriate.

Do not invent reviews, ratings, FAQ rich-result markup, or unsupported claims.

## 17. Product claim accuracy

Safe product areas include:

```text
keyword tracking
tracked sites/aliases
ranking history
Ranking Explorer
Groups and Tags
competitor analytics
CSV/PDF reports
scheduled checks according to plan
scheduled reports according to current capability
desktop/mobile where currently supported
```

Do not invent:

```text
Top 100 tracking
real-time rankings
unlimited plans
AI recommendations
backlink analysis
site audit
keyword volume
keyword difficulty
team workspaces
client portal
white-label reports
Slack alerts
Developer API
```

## 18. Checked-depth semantics

Avoid wording like:

```text
Know exactly where every keyword ranks in Google.
```

Prefer:

```text
Track whether your site appears within the configured SERP checked depth and compare ranking movement over time.
```

Keep current Top 10 semantics accurate where relevant.

## 19. Pricing references

Do not hard-code plan prices or limits into these pages unless sourced from the existing plan catalog/API.

Prefer:

```text
View pricing
```

linking to:

```text
/pricing
```

## 20. CTAs

Each page should contain:

```text
Hero CTA
Mid-page CTA
Final CTA
```

Recommended destinations:

```text
/register
/pricing
```

Possible text:

```text
Start tracking rankings
View pricing
Create your first project
```

Do not use misleading CTAs such as `Start free daily tracking` if the Free plan does not include daily scheduling.

## 21. Visual content

Use real product screenshots only when they are safe and useful.

Possible screenshots:

```text
Ranking summary
Ranking Explorer
Ranking history
Competitor analytics
Report preview
```

Do not use customer/private data.

If no clean screenshots exist, ship without them rather than creating fake proof.

## 22. UX and responsiveness

Use the existing public design language.

Recommended widths:

```text
overall content: 1100–1200px
long prose: 680–800px
```

QA at:

```text
375
768
1024
1440
```

Requirements:

- no horizontal overflow;
- usable CTAs;
- responsive sections;
- readable screenshots;
- working mobile navigation;
- no fixed desktop-only layout.

## 23. Accessibility

Required:

- one H1;
- correct heading hierarchy;
- keyboard navigation;
- visible focus;
- descriptive links;
- image alt text;
- sufficient contrast;
- semantic tables/lists.

Run existing axe checks.

## 24. Performance

Keep pages mostly static.

Do not import authenticated dashboard bundles, heavy chart libraries, or TanStack Query unless required.

Do not fetch ranking APIs to render public marketing pages.

Prefer:

```text
static/server rendered
minimal JavaScript
optimized images
no major layout shift
```

## 25. Blog cannibalization

Existing:

```text
/blog/serp-tracking-for-agencies
```

and new:

```text
/serp-tracking-for-agencies
```

must not be duplicates.

Differentiate:

```text
Blog article:
educational
workflow explanation
informational intent

Landing page:
SERP SaaS capabilities
agency use case
conversion intent
CTA
```

Link them to each other.

## 26. Indexability

All three canonical commercial URLs should be:

```text
index, follow
```

They must not inherit app-domain noindex behavior.

Do not emit:

```text
X-Robots-Tag: noindex
```

on the canonical commercial host.

## 27. Tests

Add coverage for:

```text
all 3 routes render
HTTP 200
one H1
unique titles
unique descriptions
correct canonicals
Open Graph URLs
Twitter metadata
structured data
sitemap inclusion
robots crawlability
no accidental noindex
homepage internal links
Blog-to-landing links
landing-to-Blog links
CTA destinations
```

Also verify no two landing pages share identical title/description.

## 28. Browser QA

Run against production/standalone build, not only `next dev`.

At:

```text
375
768
1024
1440
```

Validate:

```text
HTTP 200
zero browser exceptions
zero hydration errors
no horizontal overflow
axe WCAG A/AA
correct canonical
visible H1
CTA links
internal links
mobile navigation
JavaScript-disabled readability
```

## 29. Build and security gate

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

Preserve M7G.1 runtime security status:

```text
0 critical runtime vulnerabilities
0 high runtime vulnerabilities
```

## 30. Production verification

After authorized deployment:

```bash
curl -I https://serpsaas.com/google-serp-rank-tracker
curl -I https://serpsaas.com/daily-serp-tracker
curl -I https://serpsaas.com/serp-tracking-for-agencies

curl https://serpsaas.com/sitemap.xml
curl https://serpsaas.com/robots.txt
```

Check redirect variants:

```bash
curl -I http://serpsaas.com/google-serp-rank-tracker
curl -I http://www.serpsaas.com/google-serp-rank-tracker
curl -I https://www.serpsaas.com/google-serp-rank-tracker
```

Expected canonical destination:

```text
https://serpsaas.com/google-serp-rank-tracker
```

with 301 for non-canonical variants.

Apply equivalent checks to the other two routes.

## 31. Search Console follow-up

After deployment:

1. confirm all three URLs appear in the sitemap;
2. inspect each URL in Search Console;
3. run Live Test;
4. Request Indexing once;
5. do not repeatedly submit the same URL;
6. monitor Queries and Pages over the following weeks.

Key objective:

```text
Impressions should begin spreading from homepage-only traffic
toward intent-specific landing pages.
```

## 32. Success metrics

Track:

```text
landing pages indexed
landing pages receiving impressions
number of non-brand queries
impressions per page
average position trend
clicks
CTR
```

Do not require an artificial traffic guarantee.

## 33. Definition of Done

- [ ] `/google-serp-rank-tracker` implemented.
- [ ] `/daily-serp-tracker` implemented.
- [ ] `/serp-tracking-for-agencies` implemented.
- [ ] Unique search intent per page.
- [ ] Unique title/meta description.
- [ ] Correct production canonical.
- [ ] OG/Twitter metadata.
- [ ] Supported structured data.
- [ ] No accidental noindex.
- [ ] Sitemap includes all three pages.
- [ ] robots.txt permits crawling.
- [ ] Homepage links to landing pages.
- [ ] Relevant Blog articles link to landing pages.
- [ ] Landing pages link to relevant Blog articles.
- [ ] CTA links work.
- [ ] Product claims remain accurate.
- [ ] Checked-depth semantics remain accurate.
- [ ] Plan-dependent daily scheduling wording remains accurate.
- [ ] Agency page does not invent team/workspace/client-portal functionality.
- [ ] Blog/landing-page copy is not substantially duplicated.
- [ ] Responsive QA passes.
- [ ] Accessibility QA passes.
- [ ] Frontend regression tests pass.
- [ ] Runtime audit remains 0 high/critical.
- [ ] Production build passes.
- [ ] Existing authenticated app behavior is unchanged.

## 34. Out of Scope

Do not implement:

```text
new billing plans
new scheduling capabilities
new ranking depth
team workspaces
organizations
client accounts
white-label reporting
payment gateway
Developer API
API Docs
programmatic SEO generation
dozens of landing pages
automatic AI publishing
CMS
A/B testing platform
new analytics infrastructure
```

## 35. Final Instruction to Codex

Treat M7H as a focused SEO + conversion milestone.

Before coding:

1. inspect the existing homepage, pricing, Blog, PublicShell, sitemap, robots, metadata, canonical and JSON-LD implementation;
2. inspect current product capabilities so all marketing claims remain accurate;
3. reuse existing design-system components;
4. preserve `https://serpsaas.com` as the canonical commercial origin;
5. preserve production apex/www 301 canonical redirects;
6. preserve M7G.1 runtime dependency remediation.

Do not create thin keyword pages.

Each page must independently satisfy a distinct search intent and provide enough useful product explanation to deserve indexing.

Create:

```text
docs/verification-milestone-7h.md
```

The verification report should include:

```text
routes
titles/descriptions
canonical URLs
structured data
sitemap output
internal-link map
tests
browser QA
accessibility
build
runtime audit
production deployment status
Search Console status if actually verified
```

Do not claim production or Search Console verification unless it was actually performed.
