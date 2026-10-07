// Optional QA tools can live outside the repository:
// npm install --prefix /path/to/temp-tools playwright @axe-core/playwright
// QA_TOOLS_DIRECTORY=/path/to/temp-tools/node_modules node scripts/verify-blog-browser.mjs
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const toolsDirectory = process.env.QA_TOOLS_DIRECTORY;
const importTool = (packageName) =>
  import(
    toolsDirectory
      ? pathToFileURL(
          resolve(
            toolsDirectory,
            packageName,
            packageName === "@axe-core/playwright"
              ? "dist/index.mjs"
              : "index.mjs",
          ),
        ).href
      : packageName
  );
const { chromium } = await importTool("playwright");
const { default: AxeBuilder } = await importTool("@axe-core/playwright");
const base = process.env.QA_BASE_URL ?? "http://localhost:3010";
assert(
  ["localhost", "127.0.0.1"].includes(new URL(base).hostname),
  "QA must target a local server, not production.",
);
const artifactDirectory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7g",
);
await mkdir(artifactDirectory, { recursive: true });
const routes = [
  "/blog",
  "/blog/how-to-track-google-rankings",
  "/blog/serp-tracking-for-agencies",
  "/blog/how-to-monitor-keyword-ranking",
];
const browser = await chromium.launch({
  ...(process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {}),
});
const results = [];
try {
  for (const width of [375, 768, 1024, 1440]) {
    for (const path of routes) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
      });
      // The inherited AuthProvider may restore a local session. Never contact a live API in blog QA.
      await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin === new URL(base).origin) return route.continue();
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
          `Unexpected external browser request: ${url.origin}${url.pathname}`,
        );
      });
      const page = await context.newPage();
      await page.addInitScript(() => {
        window.__blogLayoutShifts = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries())
            if (!entry.hadRecentInput) window.__blogLayoutShifts += entry.value;
        }).observe({ type: "layout-shift", buffered: true });
      });
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (
          message.type() === "error" &&
          /hydration|hydrated|server rendered|Minified React error #(418|423|425)/i.test(
            message.text(),
          )
        )
          errors.push(`Hydration console error: ${message.text()}`);
      });
      const response = await page.goto(`${base}${path}`, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      const reference = await page
        .locator(path === "/blog" ? ".blog-card-featured" : ".blog-related")
        .boundingBox();
      const cta = await page.locator(".blog-cta").boundingBox();
      assert(
        Math.abs(reference.x - cta.x) < 1,
        "Blog CTA left edge must align with the featured card or related guides",
      );
      assert(
        Math.abs(reference.width - cta.width) < 1,
        "Blog CTA must match the featured card or related guides width",
      );
      assert.equal(await page.locator("h1").count(), 1);
      assert.equal(
        await page.locator('link[rel="canonical"]').getAttribute("href"),
        `https://serpsaas.com${path}`,
      );
      assert.equal(
        await page.locator('meta[property="og:url"]').getAttribute("content"),
        `https://serpsaas.com${path}`,
      );
      assert.equal(
        await page.locator('meta[name="twitter:card"]').getAttribute("content"),
        "summary",
      );
      assert(
        await page.locator('meta[name="description"]').getAttribute("content"),
      );
      assert.equal(
        await page.locator(".blog-card").count(),
        path === "/blog" ? 3 : 2,
      );
      assert.equal(
        await page
          .getByRole("contentinfo")
          .getByRole("link", { name: "Blog", exact: true })
          .getAttribute("href"),
        "https://serpsaas.com/blog",
      );
      assert.equal(
        await page
          .getByRole("link", { name: "Explore rank-tracking Plans" })
          .getAttribute("href"),
        "https://serpsaas.com/pricing",
      );
      if (path !== "/blog") {
        const structured = JSON.parse(
          await page
            .locator('script[type="application/ld+json"]')
            .textContent(),
        );
        assert.equal(structured["@graph"][0]["@type"], "BlogPosting");
        assert.equal(
          structured["@graph"][0].mainEntityOfPage["@id"],
          `https://serpsaas.com${path}`,
        );
        assert.equal(await page.locator("table th").count(), 3);
      }
      const dimensions = await page.evaluate(() => ({
        viewport: window.innerWidth,
        scroll: document.documentElement.scrollWidth,
        readingWidth:
          document.querySelector(".blog-article")?.getBoundingClientRect()
            .width ?? null,
        layoutShift: window.__blogLayoutShifts,
        responseTimeMs:
          performance.getEntriesByType("navigation")[0].responseStart -
          performance.getEntriesByType("navigation")[0].requestStart,
      }));
      assert.equal(
        dimensions.scroll,
        width,
        `Horizontal overflow: ${path} at ${width}`,
      );
      if (dimensions.readingWidth !== null) {
        assert(dimensions.readingWidth <= 800);
        if (width >= 1024) assert(dimensions.readingWidth >= 680);
      }
      const accessibility = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      assert.deepEqual(
        accessibility.violations.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          nodes: violation.nodes.map((node) => node.target),
        })),
        [],
        `Accessibility: ${path} at ${width}`,
      );
      await page.keyboard.press("Tab");
      assert.equal(
        await page
          .locator(".public-skip")
          .evaluate((element) => element === document.activeElement),
        true,
      );
      assert.notEqual(
        await page
          .locator(".public-skip")
          .evaluate((element) => getComputedStyle(element).outlineStyle),
        "none",
      );
      if (width < 1100) {
        await page
          .getByRole("button", { name: "Open public navigation" })
          .click();
        const menu = page.getByRole("dialog");
        assert.equal(
          await menu
            .getByRole("link", { name: "Blog", exact: true })
            .getAttribute("aria-current"),
          "page",
        );
        await page.keyboard.press("Escape");
        assert.equal(await menu.count(), 0);
      } else {
        assert.equal(
          await page
            .getByRole("banner")
            .getByRole("link", { name: "Blog", exact: true })
            .getAttribute("aria-current"),
          "page",
        );
      }
      assert.deepEqual(errors, []);
      assert(
        dimensions.layoutShift < 0.1,
        `Unexpected layout shift: ${path} at ${width}`,
      );
      await page.locator(".public-skip").evaluate((element) => element.blur());
      const name = path === "/blog" ? "blog" : path.split("/").at(-1);
      await page.screenshot({
        path: resolve(artifactDirectory, `${name}-${width}.png`),
        fullPage: false,
      });
      results.push({
        path,
        width,
        status: response.status(),
        ...dimensions,
        accessibilityViolations: 0,
        pageErrors: errors,
      });
      await context.close();
    }
  }
  const page = await browser.newPage({ javaScriptEnabled: false });
  for (const path of routes) {
    const response = await page.goto(`${base}${path}`);
    assert.equal(response.status(), 200);
    assert.equal(await page.locator("h1").count(), 1);
    if (path !== "/blog")
      assert.equal((await page.locator(".blog-prose h2").count()) > 0, true);
  }
  for (const path of [
    "/",
    "/pricing",
    "/login",
    "/register",
    "/app",
    "/app/projects",
  ]) {
    assert.equal((await page.request.get(`${base}${path}`)).status(), 200);
  }
  for (const path of ["/blog/unknown-slug", "/blog/private-draft"]) {
    const response = await page.goto(`${base}${path}`);
    assert.equal(response.status(), 404);
  }
  const sitemap = await (await page.request.get(`${base}/sitemap.xml`)).text();
  for (const path of routes)
    assert(sitemap.includes(`https://serpsaas.com${path}`));
  assert(!sitemap.includes("private-draft"));
  const robots = await (await page.request.get(`${base}/robots.txt`)).text();
  assert(robots.includes("Allow: /blog"));
  assert(!robots.includes("Disallow: /blog"));
  const feed = await page.request.get(`${base}/feed.xml`);
  assert.equal(feed.status(), 200);
  assert(feed.headers()["content-type"].includes("application/rss+xml"));
  assert.equal(((await feed.text()).match(/<item>/g) ?? []).length, 3);
  const appRedirect = await page.request.get(
    `${base}/blog/how-to-track-google-rankings`,
    { headers: { Host: "app.serpsaas.com" }, maxRedirects: 0 },
  );
  assert.equal(appRedirect.status(), 307);
  assert.equal(
    appRedirect.headers().location,
    "https://serpsaas.com/blog/how-to-track-google-rankings",
  );
  await writeFile(
    resolve(artifactDirectory, "browser-qa.json"),
    `${JSON.stringify({ results, unknownSlugsStatus: 404, rssItems: 3, sitemapBlogUrls: 4, appDomainBlogRedirect: 307 }, null, 2)}\n`,
  );
  console.log(
    `Blog browser QA passed: ${results.length} route/viewport cases, zero accessibility violations or page exceptions.`,
  );
} finally {
  await browser.close();
}
