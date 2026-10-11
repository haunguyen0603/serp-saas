# Milestone 7I — Vietnamese SEO Localization + Language Switcher

## 1. Objective

Add a Vietnamese SEO localization layer to the public SERP SaaS website and add a visible **Change Language** control on Home.

Initial Vietnamese routes:

```text
/vi
/vi/cong-cu-kiem-tra-thu-hang-tu-khoa
/vi/theo-doi-thu-hang-tu-khoa-hang-ngay
/vi/seo-rank-tracking-cho-agency
/vi/blog
/vi/blog/cach-theo-doi-thu-hang-google
/vi/blog/cach-kiem-tra-thu-hang-tu-khoa
```

Goals:

- increase relevance and impressions for users in Vietnam;
- preserve existing English SEO performance;
- add explicit EN/VI switching on public Home;
- implement correct hreflang/canonical behavior;
- keep Vietnamese content crawlable and indexable;
- avoid forced GeoIP/browser-language redirects.

Do not change authenticated app behavior, billing, ranking execution, provider routing, database schema, or Cloud Run architecture.

## 2. Locale strategy

Use path-based localization:

```text
English:
https://serpsaas.com/

Vietnamese:
https://serpsaas.com/vi
```

Do not use a Vietnamese subdomain, query-string locale, or separate domain in this milestone.

## 3. Change Language on Home

Add a visible language selector to the public Home page.

Recommended options:

```text
English
Tiếng Việt
```

or:

```text
EN | VI
```

Requirements:

- available on desktop and mobile;
- keyboard accessible;
- visible focus state;
- accessible label such as `Change language`;
- implemented with crawlable links;
- no authentication required;
- no API dependency;
- no effect on authenticated application locale.

Recommended location: public header near Login/Register. On mobile, use the existing mobile drawer if needed.

## 4. Language switch behavior

English Home:

```text
https://serpsaas.com/
```

Selecting Vietnamese:

```text
https://serpsaas.com/vi
```

Vietnamese Home:

```text
https://serpsaas.com/vi
```

Selecting English:

```text
https://serpsaas.com/
```

When reused on localized public pages, switch to the equivalent route where one exists.

Examples:

```text
/google-serp-rank-tracker
↔ /vi/cong-cu-kiem-tra-thu-hang-tu-khoa

/daily-serp-tracker
↔ /vi/theo-doi-thu-hang-tu-khoa-hang-ngay

/serp-tracking-for-agencies
↔ /vi/seo-rank-tracking-cho-agency

/blog/how-to-track-google-rankings
↔ /vi/blog/cach-theo-doi-thu-hang-google
```

If no equivalent route exists, fall back to the corresponding locale Home.

Use an explicit locale mapping. Do not derive translated slugs algorithmically.

## 5. No forced redirects

Do not automatically redirect based on:

```text
IP country
GeoIP
Accept-Language
Googlebot location
```

Do not force users in Vietnam from `/` to `/vi`.

The language selector is an explicit user choice.

Optional preference persistence via cookie/localStorage is allowed, but must not block crawling or force server-side redirects.

## 6. Vietnamese Home

Create:

```text
/vi
```

Recommended positioning:

```text
Theo dõi thứ hạng từ khóa Google dễ dàng
```

Possible supporting copy:

```text
Theo dõi vị trí từ khóa, phân tích biến động thứ hạng,
so sánh đối thủ và tạo báo cáo SEO trên một nền tảng đơn giản.
```

Use natural Vietnamese, not literal machine translation.

## 7. Vietnamese commercial landing pages

### A. `/vi/cong-cu-kiem-tra-thu-hang-tu-khoa`

Primary intent:

```text
kiểm tra thứ hạng từ khóa
công cụ kiểm tra thứ hạng từ khóa
check ranking từ khóa
theo dõi thứ hạng từ khóa
```

Recommended title:

```text
Công cụ kiểm tra thứ hạng từ khóa Google | SERP SaaS
```

Recommended H1:

```text
Theo dõi thứ hạng từ khóa trên Google
```

Suggested sections:

```text
H2 Theo dõi vị trí từ khóa theo thời gian
H2 Phân tích biến động thứ hạng
H2 Theo dõi đối thủ trên cùng SERP
H2 Nhóm và lọc từ khóa
H2 Xem lịch sử thứ hạng
H2 Xuất báo cáo SEO
H2 Bắt đầu theo dõi thứ hạng
```

Do not imply Top 100 if production checked depth is Top 10.

### B. `/vi/theo-doi-thu-hang-tu-khoa-hang-ngay`

Primary intent:

```text
theo dõi thứ hạng từ khóa hàng ngày
kiểm tra thứ hạng từ khóa hàng ngày
daily rank tracker
```

Recommended title:

```text
Theo dõi thứ hạng từ khóa hàng ngày | SERP SaaS
```

Recommended H1:

```text
Theo dõi thứ hạng từ khóa hàng ngày
```

Important:

```text
Lịch kiểm tra hàng ngày hoặc hàng tuần tùy theo gói dịch vụ.
```

Do not imply real-time or that all plans include daily checks.

### C. `/vi/seo-rank-tracking-cho-agency`

Primary intent:

```text
công cụ seo cho agency
theo dõi từ khóa cho agency
rank tracker cho agency
```

Recommended title:

```text
Theo dõi thứ hạng từ khóa cho SEO Agency | SERP SaaS
```

Recommended H1:

```text
Theo dõi thứ hạng từ khóa cho SEO Agency
```

Safe wording:

```text
Quản lý nhiều dự án khách hàng trong cùng một tài khoản.
```

Do not imply organizations, teams, client portals, or role-based access.

## 8. Vietnamese Blog

Create:

```text
/vi/blog
```

Recommended heading:

```text
Kiến thức SEO & Theo dõi thứ hạng
```

Initial articles:

```text
/vi/blog/cach-theo-doi-thu-hang-google
/vi/blog/cach-kiem-tra-thu-hang-tu-khoa
```

Only Vietnamese articles should appear on `/vi/blog`.

The two articles must have distinct intent and not substantially duplicate one another.

## 9. hreflang

Every equivalent locale pair must emit reciprocal alternates.

Example:

```html
<link rel="alternate" hreflang="en" href="https://serpsaas.com/google-serp-rank-tracker" />
<link rel="alternate" hreflang="vi" href="https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa" />
<link rel="alternate" hreflang="x-default" href="https://serpsaas.com/google-serp-rank-tracker" />
```

Vietnamese page must emit the same pair reciprocally.

Use one consistent locale code strategy; prefer:

```text
vi
```

for this milestone.

## 10. Canonical rules

Every locale page must self-canonicalize.

English example:

```text
https://serpsaas.com/google-serp-rank-tracker
```

Vietnamese example:

```text
https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa
```

Do not canonical Vietnamese content to English.

Never use http, www, app, api, run.app, or localhost as canonical origin.

## 11. HTML language attribute

English public pages:

```html
<html lang="en">
```

Vietnamese public pages:

```html
<html lang="vi">
```

Verify rendered HTML.

## 12. Sitemap

Extend the existing sitemap with:

```text
https://serpsaas.com/vi
https://serpsaas.com/vi/blog
https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa
https://serpsaas.com/vi/theo-doi-thu-hang-tu-khoa-hang-ngay
https://serpsaas.com/vi/seo-rank-tracking-cho-agency
https://serpsaas.com/vi/blog/cach-theo-doi-thu-hang-google
https://serpsaas.com/vi/blog/cach-kiem-tra-thu-hang-tu-khoa
```

Do not create a separate sitemap unless technically necessary.

## 13. robots.txt

Vietnamese routes must be crawlable.

Do not add:

```text
Disallow: /vi
```

Keep:

```text
Sitemap: https://serpsaas.com/sitemap.xml
```

Existing app/admin/auth exclusions remain unchanged.

## 14. Internal linking

Vietnamese Home should link to:

```text
/vi/cong-cu-kiem-tra-thu-hang-tu-khoa
/vi/theo-doi-thu-hang-tu-khoa-hang-ngay
/vi/seo-rank-tracking-cho-agency
/vi/blog
```

Vietnamese Blog should link contextually to Vietnamese commercial pages.

Avoid linking Vietnamese content to English equivalents when a Vietnamese equivalent exists.

## 15. Public navigation localization

Vietnamese PublicShell should localize labels where appropriate:

```text
Home → Trang chủ
Pricing → Bảng giá
Blog → Blog
Login → Đăng nhập
Register → Đăng ký
```

If pricing remains English-only, Vietnamese navigation may still link to:

```text
/pricing
```

Do not hard-code prices in Vietnamese landing pages.

## 16. Language selector SEO requirements

Use crawlable anchors.

Good:

```html
<a href="/vi">Tiếng Việt</a>
```

Avoid JavaScript-only state changes.

Do not add `nofollow`.

## 17. Vietnamese content quality

Use natural Vietnamese SEO terminology, including common mixed-language terms where appropriate:

```text
thứ hạng từ khóa
check ranking
SERP
SEO agency
vị trí từ khóa
```

Avoid keyword stuffing and literal machine translation.

Do not mass-generate thin pages.

## 18. Vietnam-specific relevance

Where relevant, explain:

```text
Vietnam
Vietnamese search language
desktop/mobile
Google search environment
```

Do not invent capabilities the product does not support.

## 19. Metadata

Every Vietnamese page must have unique:

```text
title
meta description
canonical
Open Graph title
Open Graph description
Open Graph URL
Twitter metadata
```

## 20. Structured data

Use supported schema only:

```text
WebPage
BlogPosting
SoftwareApplication
BreadcrumbList
```

Localized structured-data text should be Vietnamese where applicable.

Do not invent ratings, reviews, customer counts, or FAQ rich results.

## 21. Content architecture

Prefer shared components/layout with locale-specific content.

For Blog, extend the existing content architecture cleanly, for example:

```text
frontend/content/blog/en/
frontend/content/blog/vi/
```

or an equivalent locale metadata model.

Do not break existing M7G/M7H Blog validation.

## 22. Locale mapping

Create an explicit mapping used by:

```text
language switcher
hreflang
alternate metadata
tests
```

Example:

```text
/ ↔ /vi
/google-serp-rank-tracker ↔ /vi/cong-cu-kiem-tra-thu-hang-tu-khoa
/daily-serp-tracker ↔ /vi/theo-doi-thu-hang-tu-khoa-hang-ngay
/serp-tracking-for-agencies ↔ /vi/seo-rank-tracking-cho-agency
/blog/how-to-track-google-rankings ↔ /vi/blog/cach-theo-doi-thu-hang-google
```

## 23. Home language-switch acceptance criteria

English Home must expose an EN/VI selector.

Selecting Vietnamese must navigate:

```text
https://serpsaas.com/
→
https://serpsaas.com/vi
```

Vietnamese Home must expose the same control.

Selecting English must navigate:

```text
https://serpsaas.com/vi
→
https://serpsaas.com/
```

Must work on mobile and desktop.

## 24. Indexability

All Vietnamese public routes must be:

```text
index, follow
```

They must not emit:

```text
X-Robots-Tag: noindex
```

on the canonical commercial host.

## 25. Canonical redirect compatibility

Preserve existing production behavior:

```text
http://serpsaas.com/*      → 301 → https://serpsaas.com/*
http://www.serpsaas.com/*  → 301 → https://serpsaas.com/*
https://www.serpsaas.com/* → 301 → https://serpsaas.com/*
```

Vietnamese paths must be preserved:

```text
http://www.serpsaas.com/vi
→ 301
→ https://serpsaas.com/vi
```

Do not modify the load balancer.

## 26. Accessibility

Language selector requirements:

- keyboard accessible;
- visible focus;
- accessible name;
- mobile target >= 44px where practical;
- if dropdown, ESC closes and state is announced.

Localized pages must preserve semantic headings, alt text, contrast, lists, tables, and links.

## 27. Performance

Do not add a heavy i18n framework unless necessary.

Prefer lightweight route/content mapping for two locales.

Do not import authenticated dashboard bundles into localized marketing pages.

## 28. Tests

Add tests for:

```text
/vi HTTP 200
Vietnamese landing routes HTTP 200
Vietnamese Blog routes HTTP 200
one H1
unique metadata
self canonical
html lang=vi
hreflang en/vi/x-default
reciprocal alternates
Home EN → VI
Home VI → EN
fallback behavior if no equivalent locale route exists
sitemap inclusion
robots crawlability
no accidental noindex
structured data
internal links
```

Also verify English pages retain `lang=en`, existing canonical URLs, and existing metadata.

## 29. Browser QA

Run against production standalone build at:

```text
375
768
1024
1440
```

Verify:

```text
English Home language switcher
Vietnamese Home language switcher
Vietnamese landing pages
Vietnamese Blog index
Vietnamese Blog articles
```

Check:

- no horizontal overflow;
- no hydration errors;
- no browser exceptions;
- axe accessibility;
- correct lang/canonical/hreflang;
- mobile language switcher;
- JavaScript-disabled readability.

## 30. Build and security gate

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

## 31. Production verification

After authorized deployment:

```bash
curl -I https://serpsaas.com/vi
curl -I https://serpsaas.com/vi/cong-cu-kiem-tra-thu-hang-tu-khoa
curl -I https://serpsaas.com/vi/theo-doi-thu-hang-tu-khoa-hang-ngay
curl -I https://serpsaas.com/vi/seo-rank-tracking-cho-agency
curl -I https://serpsaas.com/vi/blog
curl https://serpsaas.com/sitemap.xml
curl https://serpsaas.com/robots.txt
```

Inspect HTML for:

```text
lang="vi"
canonical
hreflang="en"
hreflang="vi"
hreflang="x-default"
```

## 32. Search Console follow-up

After deployment:

1. confirm Vietnamese URLs are in sitemap;
2. URL Inspection initial Vietnamese landing pages;
3. run Live Test;
4. Request Indexing once;
5. filter Performance by:

```text
Country = Vietnam
```

Track:

```text
Queries
Pages
Impressions
Average position
Clicks
CTR
```

## 33. Definition of Done

- [ ] `/vi` implemented.
- [ ] Change Language added to English Home.
- [ ] Change Language added to Vietnamese Home.
- [ ] EN ↔ VI switching works on desktop/mobile.
- [ ] Explicit locale mapping exists.
- [ ] 3 Vietnamese commercial landing pages implemented.
- [ ] `/vi/blog` implemented.
- [ ] 2 Vietnamese Blog articles implemented.
- [ ] `html lang="vi"` correct.
- [ ] English pages retain `lang="en"`.
- [ ] Reciprocal hreflang works.
- [ ] x-default included.
- [ ] Self-canonical per locale.
- [ ] Sitemap contains Vietnamese URLs.
- [ ] robots permits `/vi`.
- [ ] No accidental noindex.
- [ ] Vietnamese internal linking implemented.
- [ ] Product claims remain accurate.
- [ ] No Top 100 or real-time claims.
- [ ] Plan-dependent schedule language remains accurate.
- [ ] Agency page does not invent teams/client portals.
- [ ] Responsive/accessibility QA passes.
- [ ] Frontend regression passes.
- [ ] Runtime audit remains 0 high/critical.
- [ ] Existing English SEO pages do not regress.

## 34. Out of Scope

Do not implement:

```text
authenticated-app localization
Vietnamese dashboard
Vietnamese emails
Vietnamese payment flow
new pricing plans
new rank depth
team workspaces
organizations
client portal
forced GeoIP redirect
forced Accept-Language redirect
translation CMS
mass machine-translation pipeline
```

## 35. Final Instruction to Codex

Treat M7I as a focused Vietnamese SEO localization milestone.

Before coding:

1. inspect Home/PublicShell;
2. inspect M7H landing pages;
3. inspect Blog architecture;
4. inspect sitemap, robots, canonical, hreflang/metadata helpers;
5. preserve production apex/www 301 routing;
6. preserve existing English SEO output;
7. reuse the current design system.

Prioritize:

```text
natural Vietnamese copy
correct locale URLs
hreflang
self-canonicalization
crawlability
language switching
internal linking
low runtime complexity
```

Do not implement forced GeoIP/browser-language redirects.

Create:

```text
docs/verification-milestone-7i.md
```

Report:

```text
routes
locale mapping
language-switcher behavior
titles/descriptions
canonical URLs
hreflang
html lang
structured data
sitemap
robots
internal links
tests
browser QA
accessibility
runtime audit
build
production deployment status
Search Console status if actually verified
```

Do not claim production or Search Console verification unless actually performed.
