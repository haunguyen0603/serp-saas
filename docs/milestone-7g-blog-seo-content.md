# Milestone 7G — Blog & SEO Content

## 1. Objective

Add a public SEO-focused Blog to SERP SaaS.

Initial routes:

```text
/blog
/blog/how-to-track-google-rankings
/blog/serp-tracking-for-agencies
/blog/how-to-monitor-keyword-ranking
```

The Blog should help acquire organic traffic around rank tracking and SERP monitoring while staying lightweight, crawlable, fast, and easy to maintain.

This milestone must not change authenticated application behavior, provider routing, ranking execution, billing, subscriptions, reports, or production infrastructure.

---

## 2. Recommended Architecture

Use file-based Markdown/MDX stored in the frontend repository.

Recommended structure:

```text
frontend/
  content/
    blog/
      how-to-track-google-rankings.mdx
      serp-tracking-for-agencies.mdx
      how-to-monitor-keyword-ranking.mdx

  src/
    app/
      blog/
        page.tsx
        [slug]/
          page.tsx
```

Reasons:

- static/server rendering works well for SEO;
- no database dependency;
- no admin CMS/security surface;
- content is version controlled;
- simple review/deployment;
- minimal operational complexity.

Do not introduce a database-backed CMS in M7G unless the repository already has a reusable content-management layer.

---

## 3. Content Metadata

Each article should have validated frontmatter similar to:

```yaml
title: "How to Track Google Rankings"
slug: "how-to-track-google-rankings"
description: "Learn how to monitor Google keyword rankings and interpret ranking changes."
publishedAt: "2026-10-07"
updatedAt: "2026-10-07"
author: "SERP SaaS"
category: "Rank Tracking"
tags:
  - SERP tracking
  - Google rankings
  - SEO
featured: true
draft: false
```

Optional:

```yaml
image: "/images/blog/how-to-track-google-rankings.png"
```

Duplicate slugs or invalid required metadata must fail the build.

Draft posts must not appear in production lists, sitemap, RSS, or static generation.

---

## 4. Blog Index

Route:

```text
/blog
```

Use the existing public shell/header/footer.

Recommended page heading:

```text
SERP Tracking & SEO Insights
```

Recommended introduction:

```text
Practical guides on Google rank tracking, SERP monitoring,
keyword performance, reporting, and competitor analysis.
```

Each article card/list item should show:

- title;
- description;
- category;
- published/updated date;
- estimated reading time;
- article link.

Do not add unnecessary pagination with only three initial articles.

---

## 5. Article Page

Route:

```text
/blog/[slug]
```

Required layout:

```text
Breadcrumb
Category
H1
Lead/description
Published / updated date
Reading time

Article content

Related articles
Contextual product CTA
```

Recommended article reading width:

```text
680–800px
```

Typography should support H2/H3/H4, lists, tables, blockquotes, links, code, callouts, and images.

Unknown or draft slugs must return 404 in production.

---

## 6. SEO Metadata

Every published article must have unique:

```text
title
meta description
canonical
Open Graph title
Open Graph description
Open Graph URL
Twitter metadata
```

Canonical example:

```text
https://serpsaas.com/blog/how-to-track-google-rankings
```

Never emit localhost, Cloud Run service URLs, `app.serpsaas.com`, or `api.serpsaas.com` as public canonicals.

Use the existing production site-origin configuration for:

```text
https://serpsaas.com
```

---

## 7. Structured Data

Add `Article` or `BlogPosting` JSON-LD to article pages.

Include when available:

```text
headline
description
datePublished
dateModified
author
publisher
mainEntityOfPage
image
```

Do not add fake reviews, ratings, FAQ rich-result markup, or unsupported claims.

Add visible breadcrumbs:

```text
Home
→ Blog
→ Article
```

`BreadcrumbList` JSON-LD may be added using the same canonical URLs.

---

## 8. Sitemap Integration

Extend the existing production sitemap to include:

```text
https://serpsaas.com/blog
https://serpsaas.com/blog/how-to-track-google-rankings
https://serpsaas.com/blog/serp-tracking-for-agencies
https://serpsaas.com/blog/how-to-monitor-keyword-ranking
```

Include only published content.

Use article `updatedAt` or `publishedAt` as `lastModified`.

Do not include drafts.

Keep the current single sitemap unless article volume later justifies sitemap splitting.

---

## 9. robots.txt

Blog must remain crawlable.

Do not add:

```text
Disallow: /blog
```

Keep authenticated/private path restrictions unchanged.

Keep:

```text
Sitemap: https://serpsaas.com/sitemap.xml
```

---

## 10. Public Navigation

Add:

```text
Blog
```

to the public header/footer where appropriate.

Recommended public header:

```text
Home
Pricing
Blog
```

Do not add Blog to the authenticated app sidebar unless there is a clear UX reason.

---

## 11. Initial SEO Content Cluster

### Article 1

Route:

```text
/blog/how-to-track-google-rankings
```

Primary intent:

```text
how to track Google rankings
```

Suggested outline:

```text
H1 How to Track Google Rankings

H2 What Google rank tracking means
H2 Why rankings change
H2 Manual ranking checks vs rank-tracking software
H2 Step-by-step ranking tracking workflow
H2 How often should you check rankings?
H2 Desktop vs mobile rankings
H2 Country/language differences
H2 How to interpret ranking movement
H2 Common rank-tracking mistakes
H2 How SERP SaaS helps
H2 Conclusion
```

### Article 2

Route:

```text
/blog/serp-tracking-for-agencies
```

Primary intent:

```text
SERP tracking for agencies
SEO rank tracking for agencies
```

Suggested outline:

```text
H1 SERP Tracking for SEO Agencies

H2 Why agencies need dedicated rank tracking
H2 Managing multiple client projects
H2 Keyword organization
H2 Scheduled checks
H2 Client reporting
H2 Competitor tracking
H2 What agencies should look for in a rank tracker
H2 A practical agency workflow with SERP SaaS
```

### Article 3

Route:

```text
/blog/how-to-monitor-keyword-ranking
```

Primary intent:

```text
how to monitor keyword ranking
keyword rank monitoring
```

Suggested outline:

```text
H1 How to Monitor Keyword Rankings

H2 Choose the keywords worth monitoring
H2 Define the search environment
H2 Establish a baseline
H2 Track changes over time
H2 Understand entered/left checked depth
H2 Organize keywords with Groups and Tags
H2 Compare ranking periods
H2 Monitor competitors
H2 Build recurring reports
H2 What to do when rankings drop
```

Avoid substantial duplication between Article 1 and Article 3.

Article 1 should emphasize rank-tracking fundamentals.
Article 3 should emphasize ongoing monitoring and operational workflow.

---

## 12. Content Quality Rules

Articles must be useful to humans first.

Required:

- answer search intent clearly;
- use descriptive H2/H3 headings;
- explain terminology;
- include actionable examples/workflows;
- avoid filler;
- avoid keyword stuffing;
- avoid unsupported claims;
- only describe SERP SaaS features that actually exist;
- use checked-depth-aware wording where ranking depth matters;
- disclose limitations accurately.

Do not mass-publish thin AI-generated pages.

Start with a small, high-quality topic cluster.

---

## 13. Internal Linking

Articles should naturally link to:

```text
/
 /pricing
other relevant /blog/... articles
```

Contextual CTA example:

```text
Track your own Google rankings with SERP SaaS.
```

Possible destination:

```text
/pricing
```

or:

```text
/register
```

Avoid repetitive keyword-stuffed anchors.

---

## 14. Related Articles

Show 2–3 related articles.

Initial relationships:

```text
How to Track Google Rankings
→ How to Monitor Keyword Rankings
→ SERP Tracking for Agencies

How to Monitor Keyword Rankings
→ How to Track Google Rankings
→ SERP Tracking for Agencies
```

Use tags/categories or a simple deterministic rule.

Do not build recommendation infrastructure.

---

## 15. Categories and Tags

M7G needs metadata only.

Example categories:

```text
Rank Tracking
Agency SEO
SERP Analytics
```

Do not create indexable category/tag pages until there is enough content to make them useful.

Avoid thin taxonomy pages.

---

## 16. Images

Images are optional but recommended.

If used:

- use the existing frontend static asset system;
- provide descriptive alt text;
- set dimensions;
- optimize images;
- use Next.js image optimization when appropriate;
- never expose secrets/customer data in screenshots;
- avoid hotlinking unstable third-party assets.

---

## 17. RSS

Recommended route:

```text
/feed.xml
```

Include only published posts with:

```text
title
canonical URL
description
published date
```

RSS may be deferred if it creates unnecessary complexity for the first release.

---

## 18. Performance

Blog pages should be lightweight.

Prefer static or server-rendered content.

Do not load authenticated-app bundles or heavy chart libraries unnecessarily.

Verify:

```text
no horizontal overflow
minimal layout shift
optimized images
fast initial response
```

---

## 19. Accessibility

Required:

- one clear H1;
- correct heading hierarchy;
- descriptive links;
- visible focus;
- image alt text;
- sufficient contrast;
- proper table headers;
- keyboard-accessible navigation;
- no essential hover-only content.

---

## 20. Security

Blog source is repository-controlled trusted content.

Do not allow arbitrary untrusted runtime code through MDX.

Do not expose credentials/secrets in frontmatter or assets.

Use appropriate `rel` attributes on external links opened in new tabs.

---

## 21. Tests

Add tests for:

- `/blog` rendering;
- published post listing;
- draft exclusion;
- article route;
- unknown slug -> 404;
- article metadata;
- canonical URL;
- JSON-LD;
- sitemap inclusion;
- sitemap draft exclusion;
- related articles;
- PublicShell Blog navigation;
- MDX content rendering.

---

## 22. Browser QA

Verify:

```text
/blog
/blog/how-to-track-google-rankings
/blog/serp-tracking-for-agencies
/blog/how-to-monitor-keyword-ranking
```

At:

```text
375
768
1024
1440
```

Check:

- responsive typography;
- reading width;
- heading spacing;
- links;
- images;
- CTA;
- header/footer;
- no horizontal overflow;
- no browser exceptions.

---

## 23. Production SEO Verification

After deployment run:

```bash
curl -I https://serpsaas.com/blog
curl -I https://serpsaas.com/blog/how-to-track-google-rankings
curl https://serpsaas.com/sitemap.xml
curl https://serpsaas.com/robots.txt
```

Expected:

```text
HTTP 200
publicly crawlable
correct HTTPS canonical
Blog routes present in sitemap
```

Use Google Search Console URL Inspection for `/blog` and the three initial articles.

---

## 24. Definition of Done

- [ ] `/blog` exists.
- [ ] `/blog/[slug]` exists.
- [ ] Three initial articles are published.
- [ ] Content uses maintainable Markdown/MDX.
- [ ] Draft handling exists.
- [ ] Unique metadata per article.
- [ ] Correct canonical URLs.
- [ ] Open Graph/Twitter metadata.
- [ ] Article/BlogPosting JSON-LD.
- [ ] Blog included in public navigation.
- [ ] Blog URLs included in sitemap.
- [ ] robots.txt permits Blog crawling.
- [ ] Related article links exist.
- [ ] Contextual product CTA/internal links exist.
- [ ] Responsive QA passes.
- [ ] Accessibility checks pass.
- [ ] Production build passes.
- [ ] Existing public/authenticated routes do not regress.

---

## 25. Out of Scope

Do not implement in M7G:

```text
database-backed CMS
admin Blog editor
comments
user-generated posts
Blog search
saved content
newsletter platform
programmatic SEO
automatic AI publishing
category pagination
Payment Gateway
Developer API
API Docs
```

---

## 26. Final Instruction to Codex

Implement the Blog as a lightweight public SEO surface using existing Next.js and PublicShell conventions.

Before coding:

1. inspect current metadata/canonical implementation;
2. inspect sitemap and robots routes;
3. inspect PublicShell/header/footer;
4. inspect existing JSON-LD conventions;
5. inspect production site-origin configuration;
6. reuse existing public design-system styles where practical.

Prioritize:

```text
crawlability
content quality
semantic HTML
performance
internal linking
maintainability
```

Do not change authenticated application behavior.

Do not create thin SEO pages merely to increase URL count.

Create a final verification artifact documenting routes, content metadata, sitemap output, tests, responsive/browser QA, and production verification.
