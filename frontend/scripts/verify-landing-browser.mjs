// Optional tools live outside the project; see verify-blog-browser.mjs.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const toolsDirectory = process.env.QA_TOOLS_DIRECTORY;
const importTool = (name) =>
  import(
    toolsDirectory
      ? pathToFileURL(
          resolve(
            toolsDirectory,
            name,
            name === "@axe-core/playwright" ? "dist/index.mjs" : "index.mjs",
          ),
        ).href
      : name
  );
const { chromium } = await importTool("playwright");
const { default: AxeBuilder } = await importTool("@axe-core/playwright");
const base = process.env.QA_BASE_URL ?? "http://localhost:3011";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7h",
);
await mkdir(directory, { recursive: true });
const pages = [
  {
    path: "/google-serp-rank-tracker",
    heading: "Google SERP Rank Tracker",
    title:
      "Google SERP Rank Tracker for Keyword Position Monitoring | SERP SaaS",
    description:
      "Track Google keyword positions, compare ranking changes, monitor competitors, and review ranking history with SERP SaaS.",
    guide: "/blog/how-to-track-google-rankings",
  },
  {
    path: "/daily-serp-tracker",
    heading: "Daily SERP Tracker",
    title: "Daily SERP Tracker for Google Keyword Rankings | SERP SaaS",
    description:
      "Monitor Google keyword ranking changes on a recurring schedule, review movement over time, and investigate meaningful SERP changes with SERP SaaS.",
    guide: "/blog/how-to-monitor-keyword-ranking",
  },
  {
    path: "/serp-tracking-for-agencies",
    heading: "SERP Tracking for SEO Agencies",
    title: "SERP Tracking for SEO Agencies | Client Rank Tracking | SERP SaaS",
    description:
      "Organize client keyword tracking, compare competitors, monitor ranking movement, and create reports with SERP SaaS.",
    guide: "/blog/serp-tracking-for-agencies",
  },
];
const browser = await chromium.launch({
  ...(process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {}),
});
const results = [];
const noJavaScript = [];
const http = [];
try {
  for (const width of [375, 768, 1024, 1440]) {
    for (const spec of pages) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
      });
      await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin === new URL(base).origin) return route.continue();
        // Local session restoration cannot reach a real account/backend.
        if (url.pathname === "/api/v1/auth/refresh")
          return route.fulfill({
            status: route.request().method() === "OPTIONS" ? 204 : 401,
            contentType: "application/json",
            headers: {
              "Access-Control-Allow-Origin": base,
              "Access-Control-Allow-Credentials": "true",
              "Access-Control-Allow-Methods": "POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type",
            },
            body: '{"detail":"Unauthenticated QA session"}',
          });
        throw new Error(
          `Unexpected external request: ${url.origin}${url.pathname}`,
        );
      });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (
          message.type() === "error" &&
          /hydration|hydrated|server rendered|Minified React error #(418|423|425)/i.test(
            message.text(),
          )
        )
          errors.push(message.text());
      });
      await page.addInitScript(() => {
        window.__landingLayoutShift = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries())
            if (!entry.hadRecentInput)
              window.__landingLayoutShift += entry.value;
        }).observe({ type: "layout-shift", buffered: true });
      });
      const response = await page.goto(`${base}${spec.path}`, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      assert(!response.headers()["x-robots-tag"]?.includes("noindex"));
      assert.equal(await page.locator("h1").count(), 1);
      assert.equal(await page.locator("h1").textContent(), spec.heading);
      assert(await page.locator("h1").isVisible());
      assert.equal(await page.title(), spec.title);
      const url = `https://serpsaas.com${spec.path}`;
      assert.equal(
        await page.locator('meta[name="description"]').getAttribute("content"),
        spec.description,
      );
      assert.equal(
        await page.locator('link[rel="canonical"]').getAttribute("href"),
        url,
      );
      assert.equal(
        await page.locator('meta[property="og:url"]').getAttribute("content"),
        url,
      );
      assert.equal(
        await page.locator('meta[property="og:title"]').getAttribute("content"),
        spec.title,
      );
      assert.equal(
        await page
          .locator('meta[property="og:description"]')
          .getAttribute("content"),
        spec.description,
      );
      for (const [name, value] of [
        ["card", "summary"],
        ["title", spec.title],
        ["description", spec.description],
      ])
        assert.equal(
          await page
            .locator(`meta[name="twitter:${name}"]`)
            .getAttribute("content"),
          value,
        );
      const robots = await page
        .locator('meta[name="robots"]')
        .getAttribute("content");
      assert(
        robots.includes("index") &&
          robots.includes("follow") &&
          !robots.includes("noindex"),
      );
      const graph = JSON.parse(
        await page.locator('script[type="application/ld+json"]').textContent(),
      )["@graph"];
      assert.deepEqual(
        graph.map((item) => item["@type"]),
        ["WebPage", "SoftwareApplication", "BreadcrumbList"],
      );
      assert.equal(graph[0].url, url);
      assert.equal(graph[2].itemListElement[1].item, url);
      assert(!JSON.stringify(graph).match(/AggregateRating|FAQPage|Review/));
      const main = page.getByRole("main");
      assert.equal(
        await main
          .locator('a[href="https://app.serpsaas.com/register"]')
          .count(),
        3,
      );
      assert.equal(
        await main
          .getByRole("link", { name: "View pricing", exact: true })
          .count(),
        3,
      );
      assert.equal(
        await main
          .locator(`a[href="https://serpsaas.com${spec.guide}"]`)
          .count(),
        1,
      );
      for (const link of await page
        .locator(".landing-hero .public-cta-row a")
        .all()) {
        const box = await link.boundingBox();
        assert(box.width > 100 && box.height >= 44);
      }
      for (const other of pages)
        assert.equal(
          await page
            .getByRole("contentinfo")
            .locator(`a[href="https://serpsaas.com${other.path}"]`)
            .count(),
          1,
        );
      const dimensions = await page.evaluate(() => ({
        viewport: window.innerWidth,
        scroll: document.documentElement.scrollWidth,
        readingWidths: [...document.querySelectorAll(".landing-section")].map(
          (el) => el.getBoundingClientRect().width,
        ),
        layoutShift: window.__landingLayoutShift,
      }));
      assert.equal(
        dimensions.scroll,
        width,
        `Overflow: ${spec.path} at ${width}`,
      );
      assert(
        dimensions.readingWidths.every((readingWidth) => readingWidth <= 800),
      );
      assert(dimensions.layoutShift < 0.1);
      const accessibility = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      assert.deepEqual(
        accessibility.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
        [],
        `${spec.path} at ${width}`,
      );
      await page.keyboard.press("Tab");
      assert(
        await page
          .locator(".public-skip")
          .evaluate((el) => el === document.activeElement),
      );
      assert.notEqual(
        await page
          .locator(".public-skip")
          .evaluate((el) => getComputedStyle(el).outlineStyle),
        "none",
      );
      if (width < 1100) {
        const trigger = page.getByRole("button", {
          name: "Open public navigation",
        });
        await trigger.focus();
        await page.keyboard.press("Enter");
        const menu = page.getByRole("dialog");
        assert(await menu.isVisible());
        assert.equal(
          await menu
            .getByRole("link", { name: "Pricing", exact: true })
            .getAttribute("href"),
          "https://serpsaas.com/pricing",
        );
        await page.keyboard.press("Escape");
        assert.equal(await menu.count(), 0);
        assert(await trigger.evaluate((el) => el === document.activeElement));
      }
      assert.deepEqual(errors, []);
      await page.locator(".public-skip").evaluate((el) => el.blur());
      await page.screenshot({
        path: resolve(directory, `${spec.path.slice(1)}-${width}.png`),
        fullPage: true,
      });
      results.push({
        path: spec.path,
        width,
        status: response.status(),
        ...dimensions,
        accessibilityViolations: 0,
        errors,
      });
      await context.close();

      const noJsContext = await browser.newContext({
        javaScriptEnabled: false,
        viewport: { width, height: 900 },
      });
      const noJsPage = await noJsContext.newPage();
      assert.equal((await noJsPage.goto(`${base}${spec.path}`)).status(), 200);
      assert(await noJsPage.locator("h1").isVisible());
      assert((await noJsPage.locator(".landing-section h2").count()) >= 6);
      assert.equal(
        await noJsPage
          .getByRole("main")
          .locator('a[href="https://app.serpsaas.com/register"]')
          .count(),
        3,
      );
      assert.equal(
        await noJsPage.evaluate(() => document.documentElement.scrollWidth),
        width,
      );
      noJavaScript.push({ path: spec.path, width, readable: true });
      await noJsContext.close();
    }
  }
  const page = await browser.newPage({ javaScriptEnabled: false });
  assert.equal((await page.goto(`${base}/`)).status(), 200);
  for (const spec of pages) {
    assert(
      (await page
        .getByRole("main")
        .locator(`a[href="https://serpsaas.com${spec.path}"]`)
        .count()) >= 1,
    );
    const canonical = await page.request.get(`${base}${spec.path}`, {
      headers: { Host: "serpsaas.com" },
      maxRedirects: 0,
    });
    assert.equal(canonical.status(), 200);
    assert(!canonical.headers()["x-robots-tag"]?.includes("noindex"));
    const redirected = await page.request.get(`${base}${spec.path}?source=qa`, {
      headers: { Host: "app.serpsaas.com" },
      maxRedirects: 0,
    });
    assert.equal(redirected.status(), 307);
    assert.equal(
      redirected.headers().location,
      `https://serpsaas.com${spec.path}?source=qa`,
    );
    http.push({
      path: spec.path,
      canonicalHostStatus: 200,
      noindex: false,
      appHostStatus: 307,
      location: redirected.headers().location,
    });
  }
  for (const spec of pages) {
    assert.equal((await page.goto(`${base}${spec.guide}`)).status(), 200);
    assert.equal(
      await page
        .locator(`.blog-prose a[href="https://serpsaas.com${spec.path}"]`)
        .count(),
      1,
    );
  }
  const sitemapResponse = await page.request.get(`${base}/sitemap.xml`);
  assert.equal(sitemapResponse.status(), 200);
  const sitemap = await sitemapResponse.text();
  const robotsResponse = await page.request.get(`${base}/robots.txt`);
  assert.equal(robotsResponse.status(), 200);
  const robots = await robotsResponse.text();
  for (const spec of pages) {
    assert(sitemap.includes(`https://serpsaas.com${spec.path}`));
    assert(sitemap.includes(`https://serpsaas.com${spec.guide}`));
    assert(robots.includes(`Allow: ${spec.path}`));
    const disallowed = [...robots.matchAll(/^Disallow: (.+)$/gm)].map((match) =>
      match[1].trim(),
    );
    assert(disallowed.every((path) => !spec.path.startsWith(path)));
  }
  assert(robots.includes("Sitemap: https://serpsaas.com/sitemap.xml"));
  assert(!sitemap.match(/app\.serpsaas|\/login<|\/register<|\/app</));
  await writeFile(resolve(directory, "sitemap.xml"), sitemap);
  await writeFile(resolve(directory, "robots.txt"), robots);
  await writeFile(
    resolve(directory, "browser-qa.json"),
    `${JSON.stringify({ results, noJavaScript, http, sitemapUrls: (sitemap.match(/<loc>/g) ?? []).length, internalLinkChecks: "homepage, footer, three contextual Blog links, related guides and product workflows passed" }, null, 2)}\n`,
  );
  console.log(
    `Landing QA passed: ${results.length} viewport cases, ${noJavaScript.length} JS-disabled cases, zero axe violations or browser exceptions.`,
  );
} finally {
  await browser.close();
}
