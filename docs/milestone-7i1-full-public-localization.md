# Milestone 7I.1 — Full Public Website Localization + Flag Language Select

## Objective

Extend M7I from partial Vietnamese localization into **full public-site localization** and replace the current segmented `EN / VI` control with a compact **flag + language select/dropdown**.

The public marketing site must support English and Vietnamese consistently across all public pages. The authenticated app/dashboard remains English-only and is out of scope.

## 1. Language selector UX

Replace the current:

```text
EN   VI
```

with a single compact selector.

Recommended collapsed state:

```text
🇺🇸 English ▾
```

or:

```text
🇻🇳 Tiếng Việt ▾
```

Recommended menu:

```text
🇺🇸 English
🇻🇳 Tiếng Việt
```

Requirements:

- visible in public header;
- desktop + mobile;
- flag before language label;
- current language clearly indicated;
- keyboard accessible;
- visible focus;
- `aria-label="Change language"`;
- Enter/Space opens;
- Escape closes;
- click outside closes;
- target ~44px minimum on mobile;
- no authentication/API dependency.

Prefer local SVG flag assets instead of emoji for visual consistency:

```text
US flag → English
Vietnam flag → Tiếng Việt
```

Text label must always be present; do not use flag alone.

## 2. Locale strategy

Keep path-based localization:

```text
English:
https://serpsaas.com/...

Vietnamese:
https://serpsaas.com/vi/...
```

Do not introduce:

```text
?lang=
vi.serpsaas.com
GeoIP redirects
Accept-Language forced redirects
```

## 3. Full public-page localization

All current public English pages must have Vietnamese equivalents.

Required mapping:

```text
/ ↔ /vi

/pricing
↔ /vi/bang-gia

/about
↔ /vi/gioi-thieu

/privacy
↔ /vi/chinh-sach-bao-mat

/terms
↔ /vi/dieu-khoan-dich-vu

/google-serp-rank-tracker
↔ /vi/cong-cu-kiem-tra-thu-hang-tu-khoa

/daily-serp-tracker
↔ /vi/theo-doi-thu-hang-tu-khoa-hang-ngay

/serp-tracking-for-agencies
↔ /vi/seo-rank-tracking-cho-agency

/blog
↔ /vi/blog

/blog/how-to-track-google-rankings
↔ /vi/blog/cach-theo-doi-thu-hang-google

/blog/serp-tracking-for-agencies
↔ /vi/blog/serp-tracking-cho-agency

/blog/how-to-monitor-keyword-ranking
↔ /vi/blog/cach-kiem-tra-thu-hang-tu-khoa
```

This explicit map must be the single source for:

```text
language selector destinations
hreflang
x-default
alternate metadata
tests
fallback behavior
```

Do not derive translated slugs algorithmically.

## 4. Language switching behavior

Switching language must preserve page intent whenever an equivalent exists.

Examples:

```text
/pricing
→ Tiếng Việt
→ /vi/bang-gia
```

```text
/vi/chinh-sach-bao-mat
→ English
→ /privacy
```

```text
/blog/serp-tracking-for-agencies
→ Tiếng Việt
→ /vi/blog/serp-tracking-cho-agency
```

Fallback to locale Home only for a truly unmapped public route.

## 5. Vietnamese Pricing

Create:

```text
/vi/bang-gia
```

Reuse the exact same backend Plan catalog/source used by `/pricing`.

Do not hard-code price or limits.

Localize presentation labels only, e.g.:

```text
Pricing → Bảng giá
Projects → Dự án
Keywords → Từ khóa
Checks → Lượt kiểm tra
Daily → Hàng ngày
Weekly → Hàng tuần
Get Started → Bắt đầu
```

Plan names like `Free`, `Starter`, `Pro` may remain unchanged if treated as product names.

Verify EN and VI show identical commercial data:

```text
same Plan IDs
same prices
same entitlements
same ordering
same availability
```

## 6. Vietnamese About

Create:

```text
/vi/gioi-thieu
```

Translate/localize naturally from the existing About page.

Do not invent:

```text
customer counts
company size
funding
awards
office locations
years in business
```

unless explicitly supported by the English source.

## 7. Vietnamese Privacy Policy

Create:

```text
/vi/chinh-sach-bao-mat
```

Translate faithfully from the existing English Privacy Policy.

Do not silently change:

```text
data categories
retention
security
third-party services
user rights
contact info
effective dates
jurisdiction wording
```

Legal meaning takes precedence over marketing tone.

Do not invent a “Vietnamese version prevails” or “English version prevails” clause unless explicitly approved.

## 8. Vietnamese Terms of Service

Create:

```text
/vi/dieu-khoan-dich-vu
```

Translate faithfully from English Terms.

Preserve:

```text
service scope
acceptable use
account obligations
billing/subscription terms
termination
warranties/disclaimers
liability structure
governing law
effective date
```

Do not change legal obligations through localization.

## 9. Vietnamese Agency Blog article

Add:

```text
/vi/blog/serp-tracking-cho-agency
```

This is the informational equivalent of:

```text
/blog/serp-tracking-for-agencies
```

Keep it distinct from the commercial landing page:

```text
/vi/seo-rank-tracking-cho-agency
```

Blog = educational workflow.
Landing page = product capabilities + conversion.

## 10. Public navigation localization

English:

```text
Home
Pricing
Blog
About us
Privacy Policy
Terms of Service
[Language Select]
Log in
Get Started
```

Vietnamese:

```text
Trang chủ
Bảng giá
Blog
Giới thiệu
Chính sách bảo mật
Điều khoản dịch vụ
[Chọn ngôn ngữ]
Đăng nhập
Bắt đầu
```

The dropdown replaces the current segmented `EN / VI` UI.

## 11. Footer localization

Vietnamese public footer must also use Vietnamese labels and Vietnamese public routes where equivalents exist.

Example:

```text
Sản phẩm
- Công cụ kiểm tra thứ hạng từ khóa
- Theo dõi thứ hạng hàng ngày
- Dành cho SEO Agency

Tài nguyên
- Blog
- Bảng giá

Pháp lý
- Chính sách bảo mật
- Điều khoản dịch vụ
```

## 12. Auth links

Login/Register/Get Started can continue pointing to:

```text
https://app.serpsaas.com/...
```

Vietnamese labels may be localized, but do not imply the authenticated dashboard itself is Vietnamese.

## 13. Canonical

Every locale page self-canonicalizes.

Examples:

```text
https://serpsaas.com/pricing
https://serpsaas.com/vi/bang-gia
```

```text
https://serpsaas.com/privacy
https://serpsaas.com/vi/chinh-sach-bao-mat
```

Never canonical Vietnamese pages to English.

## 14. hreflang

All mapped pairs must emit reciprocal:

```text
hreflang="en"
hreflang="vi"
hreflang="x-default"
```

`x-default` should point to the English/default URL.

Example:

```html
<link rel="alternate" hreflang="en" href="https://serpsaas.com/pricing" />
<link rel="alternate" hreflang="vi" href="https://serpsaas.com/vi/bang-gia" />
<link rel="alternate" hreflang="x-default" href="https://serpsaas.com/pricing" />
```

## 15. HTML language

English pages:

```html
<html lang="en">
```

Vietnamese pages:

```html
<html lang="vi">
```

Verify server-rendered HTML.

## 16. Sitemap

Add the new Vietnamese routes:

```text
https://serpsaas.com/vi/bang-gia
https://serpsaas.com/vi/gioi-thieu
https://serpsaas.com/vi/chinh-sach-bao-mat
https://serpsaas.com/vi/dieu-khoan-dich-vu
https://serpsaas.com/vi/blog/serp-tracking-cho-agency
```

Keep all current M7I URLs.

No duplicate entries.

## 17. robots.txt

All localized public routes remain crawlable.

Do not block `/vi`.

Keep private/app/auth restrictions unchanged.

## 18. LanguageSelect implementation

Prefer a shared component:

```text
LanguageSelect
```

driven by explicit locale mapping.

Suggested option data:

```ts
{
  locale: "en",
  label: "English",
  shortLabel: "EN",
  flag: "...",
  href: "..."
}
```

```ts
{
  locale: "vi",
  label: "Tiếng Việt",
  shortLabel: "VI",
  flag: "...",
  href: "..."
}
```

Use existing dropdown/popover primitives if available.

Do not add a large UI dependency for this one control.

## 19. Flag assets

Use local SVG assets.

Requirements:

- local/static;
- no third-party request;
- no tracking;
- consistent size;
- decorative flag can be `aria-hidden="true"` because text names the language.

## 20. URL is source of truth

Direct URL access must win over any saved preference.

Examples:

```text
/privacy
→ English Privacy
```

```text
/vi/chinh-sach-bao-mat
→ Vietnamese Privacy
```

Optional cookie/localStorage preference may be stored only after explicit selection, but must not override a directly requested locale path.

## 21. No automatic locale redirect

Do not redirect based on:

```text
Vietnam IP
browser language
Googlebot location
Accept-Language
```

Both locales must remain independently crawlable.

## 22. Structured data

Use supported existing schema only:

```text
WebPage
SoftwareApplication
BreadcrumbList
BlogPosting
```

Localized schema text should match the selected language where applicable.

Do not invent ratings/reviews/offers.

## 23. Metadata examples

Vietnamese Pricing:

```text
Title:
Bảng giá SERP SaaS | Gói theo dõi thứ hạng từ khóa
```

Vietnamese About:

```text
Title:
Giới thiệu SERP SaaS | Công cụ theo dõi thứ hạng Google
```

Privacy:

```text
Chính sách bảo mật | SERP SaaS
```

Terms:

```text
Điều khoản dịch vụ | SERP SaaS
```

## 24. Internal linking

Vietnamese public pages should link to Vietnamese equivalents whenever available.

Examples:

```text
/vi → /vi/bang-gia
/vi/gioi-thieu → /vi/cong-cu-kiem-tra-thu-hang-tu-khoa
/vi/blog/serp-tracking-cho-agency → /vi/seo-rank-tracking-cho-agency
/vi/chinh-sach-bao-mat → /vi/dieu-khoan-dich-vu
```

Avoid unnecessary jumps back to English public pages.

## 25. Translation quality

Use natural Vietnamese suitable for Vietnamese SaaS/SEO users.

Prefer:

```text
theo dõi thứ hạng từ khóa
lượt kiểm tra
dự án
báo cáo
đối thủ
```

For legal pages, semantic fidelity is more important than SEO wording.

## 26. Tests

Add tests for:

```text
LanguageSelect current state
flag before language text
dropdown open/close
keyboard behavior
mobile behavior
all explicit mappings
Pricing EN ↔ VI
About EN ↔ VI
Privacy EN ↔ VI
Terms EN ↔ VI
Agency Blog EN ↔ VI
hreflang reciprocity
self canonical
html lang
sitemap inclusion
robots crawlability
no accidental noindex
pricing data equality
```

## 27. Browser QA

Run standalone production QA at:

```text
375
768
1024
1440
```

At minimum test:

```text
/
/vi
/pricing
/vi/bang-gia
/about
/vi/gioi-thieu
/privacy
/vi/chinh-sach-bao-mat
/terms
/vi/dieu-khoan-dich-vu
/blog/serp-tracking-for-agencies
/vi/blog/serp-tracking-cho-agency
```

Verify:

```text
correct flag
current language
dropdown interaction
keyboard interaction
mobile interaction
destination URL
localized header/footer
no overflow
no hydration errors
no browser exceptions
axe A/AA
canonical/hreflang/lang
```

## 28. JavaScript-disabled SEO fallback

Localized URL discovery must not depend entirely on client JavaScript.

The server-rendered markup must expose crawlable alternate locale URLs, through actual links and/or appropriate fallback markup.

## 29. Security/build gate

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

## 30. Production verification

After authorized deployment:

```bash
curl -I https://serpsaas.com/vi/bang-gia
curl -I https://serpsaas.com/vi/gioi-thieu
curl -I https://serpsaas.com/vi/chinh-sach-bao-mat
curl -I https://serpsaas.com/vi/dieu-khoan-dich-vu
curl -I https://serpsaas.com/vi/blog/serp-tracking-cho-agency
```

Verify:

```text
HTTP 200
indexable
self canonical
reciprocal hreflang
lang=vi
```

Check www/http path preservation, e.g.:

```bash
curl -I http://www.serpsaas.com/vi/bang-gia
curl -I https://www.serpsaas.com/vi/bang-gia
```

Expected:

```text
301 → https://serpsaas.com/vi/bang-gia
```

## 31. Search Console follow-up

After deploy, request indexing once for newly created Vietnamese URLs.

Monitor:

```text
Performance
→ Country = Vietnam
```

Track:

```text
Queries
Pages
Impressions
Clicks
CTR
Average position
```

## 32. Definition of Done

- [ ] Current segmented EN/VI control removed.
- [ ] Flag + language dropdown implemented.
- [ ] English and Vietnamese labels shown.
- [ ] Desktop/mobile behavior works.
- [ ] Keyboard/accessibility passes.
- [ ] Crawlable locale links remain server-rendered.
- [ ] `/vi/bang-gia` implemented.
- [ ] `/vi/gioi-thieu` implemented.
- [ ] `/vi/chinh-sach-bao-mat` implemented.
- [ ] `/vi/dieu-khoan-dich-vu` implemented.
- [ ] `/vi/blog/serp-tracking-cho-agency` implemented.
- [ ] Entire public nav localized.
- [ ] Entire public footer localized.
- [ ] Pricing shares the same plan catalog.
- [ ] Legal translations preserve source meaning.
- [ ] Full explicit locale mapping exists.
- [ ] Reciprocal hreflang works.
- [ ] x-default correct.
- [ ] Self canonical per locale.
- [ ] html lang correct.
- [ ] Sitemap updated.
- [ ] robots correct.
- [ ] No accidental noindex.
- [ ] Existing English SEO pages do not regress.
- [ ] Authenticated app remains unchanged.
- [ ] Responsive/accessibility QA passes.
- [ ] Runtime audit remains 0 high/critical.

## 33. Out of Scope

Do not localize:

```text
authenticated dashboard/app
email verification templates
report emails
admin UI
API/developer docs
backend validation messages
Cloud Run infrastructure
database
```

Do not add languages beyond English and Vietnamese.

## 34. Final Instruction to Codex

Treat this milestone as completion of public-site EN/VI localization.

Before coding:

1. inspect current M7I locale map and language control;
2. inspect Pricing data loading;
3. inspect About, Privacy and Terms source content;
4. inspect English agency Blog article;
5. inspect sitemap, robots, metadata, hreflang and canonical helpers;
6. preserve all M7I/M7H SEO behavior;
7. preserve current production canonical redirects.

Replace the segmented `EN / VI` UI with a compact flag + language dropdown without reducing crawlability.

The selected language must apply consistently across the **entire public website**.

Create:

```text
docs/verification-milestone-7i1.md
```

Document:

```text
language-select UX
flag assets
locale mapping
localized routes
pricing source consistency
legal translation approach
nav/footer localization
canonical
hreflang
html lang
sitemap
robots
tests
browser QA
accessibility
runtime audit
build
production status
Search Console status if actually verified
```

Do not claim production or Search Console verification unless actually performed.
