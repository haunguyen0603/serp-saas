// Optional external Playwright/axe tools, using the same QA environment as the other blog scripts.
import assert from "node:assert/strict";
import { request } from "node:http";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const importTool = (name) =>
  import(
    pathToFileURL(
      resolve(
        process.env.QA_TOOLS_DIRECTORY,
        name,
        name === "@axe-core/playwright" ? "dist/index.mjs" : "index.mjs",
      ),
    ).href
  );
const { chromium } = await importTool("playwright");
const { default: AxeBuilder } = await importTool("@axe-core/playwright");
const base = process.env.QA_BASE_URL ?? "http://127.0.0.1:3010";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const origin = "https://serpsaas.com";
const path = "/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay";
const title = "Có nên theo dõi thứ hạng từ khóa Google hàng ngày?";
const description =
  "Khi nào nên kiểm tra thứ hạng từ khóa hàng ngày, khi nào theo dõi hàng tuần là đủ? Tìm hiểu cách đọc biến động ranking và chọn lịch kiểm tra SEO.";
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/blog-vi-daily-tracking",
);
await mkdir(directory, { recursive: true });
const localGet = (route, headers = {}) =>
  new Promise((accept, reject) => {
    const incoming = request(new URL(route, base), { headers }, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => (body += chunk));
      response.on("end", () =>
        accept({
          status: response.statusCode,
          headers: response.headers,
          body,
        }),
      );
    });
    incoming.on("error", reject);
    incoming.end();
  });
const browser = await chromium.launch(
  process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {},
);
const results = [];
try {
  for (const width of [375, 768, 1024, 1440]) {
    for (const javaScriptEnabled of [true, false]) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        javaScriptEnabled,
      });
      await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin === new URL(base).origin) return route.continue();
        if (url.origin === origin)
          return route.fulfill({
            status: 302,
            headers: { location: base + url.pathname + url.search },
            body: "",
          });
        if (url.pathname === "/api/v1/auth/refresh")
          return route.fulfill({
            status: route.request().method() === "OPTIONS" ? 204 : 401,
            headers: {
              "Access-Control-Allow-Origin": new URL(base).origin,
              "Access-Control-Allow-Credentials": "true",
              "Access-Control-Allow-Methods": "POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type",
            },
            contentType: "application/json",
            body: '{"detail":"Anonymous local QA"}',
          });
        throw new Error(`Unexpected external request: ${url.href}`);
      });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (
          message.type() === "error" &&
          /hydration|hydrated|Minified React/i.test(message.text())
        )
          errors.push(message.text());
      });
      const response = await page.goto(base + path, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      assert.equal(await page.locator("html").getAttribute("lang"), "vi");
      assert.equal(await page.title(), `${title} | SERP SaaS`);
      assert.equal(await page.locator("h1").count(), 1);
      assert.equal(await page.locator("h1").textContent(), title);
      assert.equal(
        await page.locator('meta[name="description"]').getAttribute("content"),
        description,
      );
      assert.equal(
        await page.locator('link[rel="canonical"]').getAttribute("href"),
        origin + path,
      );
      assert.equal(
        await page.locator('meta[property="og:url"]').getAttribute("content"),
        origin + path,
      );
      assert.equal(
        await page.locator('meta[name="robots"]').getAttribute("content"),
        "index, follow",
      );
      assert.equal(
        await page.locator('link[rel="alternate"][hreflang]').count(),
        0,
      );
      assert.equal(
        await page.locator('link[type="application/rss+xml"]').count(),
        0,
      );
      const graph = JSON.parse(
        await page.locator('script[type="application/ld+json"]').textContent(),
      )["@graph"];
      assert.equal(graph[0]["@type"], "BlogPosting");
      assert.equal(graph[0].inLanguage, "vi");
      assert.equal(graph[0].mainEntityOfPage["@id"], origin + path);
      assert.equal(graph[0].datePublished, "2026-10-19");
      assert.equal(graph[0].dateModified, "2026-10-19");
      assert.equal(graph[1]["@type"], "BreadcrumbList");
      assert.equal(graph[1].itemListElement.at(-1).item, origin + path);
      assert.equal(await page.locator(".blog-prose table").count(), 2);
      assert.equal(await page.locator(".blog-prose th").count(), 5);
      assert.equal(
        await page
          .locator('.blog-table-scroll[tabindex="0"][role="region"]')
          .count(),
        2,
      );
      const prose = await page.locator(".blog-prose").textContent();
      for (const text of [
        "Top 10",
        "không cho biết vị trí chính xác ngoài Top 10",
        "Desktop",
        "Mobile",
        "phụ thuộc vào quyền lợi của từng gói dịch vụ",
        "không phải dữ liệu từ một chiến dịch thực tế",
      ])
        assert(prose.includes(text), text);
      assert.equal(
        await page.locator('.blog-related a[href*="/vi/blog/"]').count(),
        6,
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width,
      );
      if (javaScriptEnabled) {
        assert.deepEqual(
          (
            await new AxeBuilder({ page })
              .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
              .analyze()
          ).violations,
          [],
        );
        for (const table of await page.locator(".blog-table-scroll").all()) {
          await table.focus();
          assert(
            await table.evaluate(
              (element) => element === document.activeElement,
            ),
          );
          if (width === 375) {
            await page.keyboard.press("ArrowRight");
            await page.waitForFunction(
              () => document.activeElement.scrollLeft > 0,
            );
          }
        }
        await page.screenshot({
          path: resolve(directory, `article-tables-${width}.png`),
        });
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({
          path: resolve(directory, `article-${width}.png`),
        });
      }
      const selector = page.locator("header .public-language-select");
      await selector.locator("summary").click();
      assert.equal(
        await selector.locator('[hreflang="en"]').getAttribute("href"),
        origin + "/",
      );
      assert.equal(
        await selector.locator('[hreflang="vi"]').getAttribute("href"),
        origin + "/vi",
      );
      await selector.locator('[hreflang="en"]').click();
      await page.waitForURL(base + "/");
      assert.equal(await page.locator("html").getAttribute("lang"), "en");
      await page.locator("header .public-language-select summary").click();
      await page
        .locator('header .public-language-select [hreflang="vi"]')
        .click();
      await page.waitForURL(base + "/vi");
      assert.equal(await page.locator("html").getAttribute("lang"), "vi");
      await page.goto(base + "/vi/blog", { waitUntil: "networkidle" });
      assert.equal(await page.locator(".blog-card").count(), 7);
      assert.equal(
        await page
          .getByRole("link", { name: title, exact: true })
          .getAttribute("href"),
        origin + path,
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width,
      );
      assert.deepEqual(errors, []);
      results.push({
        width,
        javaScriptEnabled,
        status: 200,
        overflow: false,
        languageFallback: "/",
        roundTrip: "/vi",
        listingCards: 7,
        pageErrors: errors,
      });
      await context.close();
    }
  }
  const article = await localGet(path, {
    host: "serpsaas.com",
    "accept-language": "en",
    cookie: "locale=en",
  });
  assert.equal(article.status, 200);
  assert.equal(article.headers.location, undefined);
  assert.equal(article.headers["x-robots-tag"], undefined);
  const redirected = await localGet(path + "?source=qa", {
    host: "app.serpsaas.com",
  });
  assert.equal(redirected.status, 307);
  assert.equal(redirected.headers.location, origin + path + "?source=qa");
  const internalLinks = [
    ...new Set(
      [
        ...article.body.matchAll(/href="(https:\/\/serpsaas\.com\/vi[^"#]*)"/g),
      ].map((match) => new URL(match[1]).pathname),
    ),
  ];
  for (const link of internalLinks)
    assert.equal((await localGet(link)).status, 200, link);
  const sitemap = await localGet("/sitemap.xml");
  assert.equal(sitemap.status, 200);
  assert.equal(sitemap.body.split(`<loc>${origin + path}</loc>`).length - 1, 1);
  assert(!sitemap.body.includes(`${origin}/blog/${path.split("/").at(-1)}`));
  await writeFile(resolve(directory, "sitemap.xml"), sitemap.body);
  const definition = await localGet("/vi/blog/cong-cu-rank-tracker-la-gi");
  assert.equal(definition.status, 200);
  assert(definition.body.includes(`href="${origin + path}"`));
  const feed = await localGet("/feed.xml");
  assert.equal(feed.status, 200);
  assert.equal((feed.body.match(/<item>/g) ?? []).length, 3);
  assert(!feed.body.includes("co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay"));
  assert.equal(
    (await localGet("/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay")).status,
    404,
  );
  const robots = await localGet("/robots.txt");
  assert.equal(robots.status, 200);
  assert(!robots.body.includes("Disallow: /vi"));
  await writeFile(
    resolve(directory, "browser-qa.json"),
    JSON.stringify(
      {
        results,
        internalLinks,
        sitemapOccurrences: 1,
        relatedDiscoveryFromDefinition: true,
        englishRssItems: 3,
        forcedLanguageRedirect: false,
        appHostRedirect: 307,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `Daily tracking blog QA passed: ${results.length} viewport/JavaScript cases, metadata, tables, axe, language switch, links, sitemap, RSS and redirects.`,
  );
} finally {
  await browser.close();
}
