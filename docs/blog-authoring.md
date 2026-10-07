# Blog authoring

The public blog is built from repository-controlled Markdown in `frontend/content/blog/`. There is no CMS, database, runtime MDX execution, or category/tag landing page. Deploy the frontend again after a content change.

## Add or update a guide

Create a lowercase kebab-case `.md` filename that exactly matches its slug. Use this frontmatter:

```yaml
---
title: "A unique, descriptive guide title"
slug: a-unique-guide
description: "A unique summary of what readers will learn."
publishedAt: "2026-10-07"
updatedAt: "2026-10-07"
author: "SERP SaaS"
category: "Rank Tracking"
tags: ["Rank Tracking", "SEO"]
featured: false
draft: true
---
```

Write the body using H2–H4; the article template supplies the only H1. GFM tables, ordered/unordered lists, blockquotes (including labeled callouts), fenced code and normal Markdown links are supported. Raw HTML is ignored. Code and table containers are keyboard-focusable when scrolling is needed.

Link to other guides using `/blog/<slug>` and to Plans using `/pricing`. External links open in the same tab. Do not add unsupported product promises, fake ranking examples presented as live data, reviews, or FAQ rich-result markup. Cite primary documentation where helpful. Keep fundamental and operational guides distinct.

Images are optional; the initial guides intentionally contain none. For a hero image, place an optimized raster asset under `frontend/public/images/blog/` and add all four fields:

```yaml
image: "/images/blog/a-unique-guide.webp"
imageAlt: "A useful description of the image's information"
imageWidth: 1200
imageHeight: 630
```

The hero uses Next.js Image with explicit dimensions. Do not hotlink third-party images or expose customer data. Prefer the hero metadata mechanism to Markdown body images so dimensions and optimization are retained.

## Validation and publication

Use Node 22.22+ from `frontend/`:

```bash
npm ci
npm run prebuild
npm run build
```

`prebuild` also runs automatically before `npm run build`. It validates all files, including drafts: required fields/types, real ISO dates, update chronology, slug/filename, unique slug/title/description, tags, article headings and image metadata. Invalid content fails the build with an error. Reading time is calculated at roughly 220 words/minute; listings are newest-first with featured guides promoted, related guides are selected deterministically by category/tags.

Keep `draft: true` until review is complete, then set it to `false`. Drafts never enter the public listing, static article params, sitemap or RSS; direct requests return 404. Dates are editorial metadata: preserve the original publication date and update `updatedAt` after a substantive revision.

Public SEO outputs always use `https://serpsaas.com`, including local and run.app previews. Navigation/auth origins still use the existing `NEXT_PUBLIC_SITE_URL` / `NEXT_PUBLIC_APP_URL` configuration. App-domain Blog and feed requests redirect to the commercial domain, while existing app robots/noindex behavior is retained.

## Optional browser verification

The optional script uses Playwright and axe, not production dependencies. Install them in a temporary tools directory, start a local production build on port 3010, then run from `frontend/`:

```bash
npm install --prefix /absolute/path/to/temp-tools playwright @axe-core/playwright
QA_TOOLS_DIRECTORY=/absolute/path/to/temp-tools/node_modules \
QA_CHROME_PATH=/absolute/path/to/chrome \
node scripts/verify-blog-browser.mjs
```

If using Playwright's installed Chromium, omit `QA_CHROME_PATH`. `QA_BASE_URL` defaults to `http://localhost:3010` and is restricted to localhost/127.0.0.1. The script covers the four initial routes at 375/768/1024/1440 px, WCAG axe checks, keyboard focus/menu behavior, metadata, JSON-LD, overflow, local layout shift, 404s, sitemap, robots, RSS and app-domain redirect. It writes screenshots and JSON under `docs/verification-artifacts/milestone-7g/` and stubs only the inherited unauthenticated local refresh; it never calls a live API/provider.

Production URL checks and Search Console inspection must be performed separately after authorized deployment. See [M7G verification](verification-milestone-7g.md).
