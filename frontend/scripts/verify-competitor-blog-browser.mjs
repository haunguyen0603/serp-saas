// Optional external Playwright/axe tools, using the same QA environment as the other blog scripts.
import assert from "node:assert/strict";
import { request } from "node:http";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { format } from "prettier";

const brief = await readFile(
  "../docs/seo-blog-vi-theo-doi-doi-thu-codex.md",
  "utf8",
);
const source = brief
  .split("# Article body (Vietnamese)")[1]
  .split(/\r?\n---\r?\n/)[0]
  .trim();
const clarification =
  "Bạn chỉ phân tích dữ liệu trong các project thuộc tài khoản của mình; Desktop và Mobile được tổ chức thành các project riêng để giữ bối cảnh đo lường nhất quán.";
const expected = source.replace(
  "Trong mô hình hiện tại, mỗi project",
  `${clarification}\n\nTrong mô hình hiện tại, mỗi project`,
);
const actual = (
  await readFile(
    "content/blog/vi/cach-theo-doi-thu-hang-doi-thu-seo.md",
    "utf8",
  )
).replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "");
assert.equal(
  await format(actual, { parser: "markdown" }),
  await format(expected, { parser: "markdown" }),
);

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
const path = "/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo";
const title = "Cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP";
const description =
  "Hướng dẫn xác định đối thủ SEO từ kết quả Google, so sánh thứ hạng theo nhóm từ khóa và tìm cơ hội nội dung bằng dữ liệu SERP.";
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/blog-vi-seo-competitors",
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
      assert.equal(graph[0].datePublished, "2026-10-21");
      assert.equal(graph[0].dateModified, "2026-10-21");
      assert.equal(graph[1]["@type"], "BreadcrumbList");
      assert.equal(graph[1].itemListElement.at(-1).item, origin + path);
      assert.equal(await page.locator(".blog-prose table").count(), 4);
      assert.equal(await page.locator(".blog-prose th").count(), 12);
      assert.equal(
        await page
          .locator('.blog-table-scroll[tabindex="0"][role="region"]')
          .count(),
        4,
      );
      const prose = await page.locator(".blog-prose").textContent();
      for (const text of [
        "Top 10",
        "không có nghĩa là website đứng ngoài Top 100",
        "Desktop",
        "Mobile",
        "tối đa năm đối thủ",
        "dữ liệu SERP đã được lưu từ những lần kiểm tra",
        "project thuộc tài khoản của mình",
        "Desktop và Mobile được tổ chức thành các project riêng",
        "số liệu chỉ để minh họa",
        "dữ liệu minh họa",
        "Không nên coi average position",
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
      for (const [label, href] of [
        ["Rank Tracker là gì?", "/vi/blog/cong-cu-rank-tracker-la-gi"],
        ["SERP SaaS dành cho SEO Agency", "/vi/seo-rank-tracking-cho-agency"],
      ])
        assert.equal(
          await page
            .locator(".blog-prose")
            .getByRole("link", { name: label, exact: true })
            .getAttribute("href"),
          origin + href,
        );
      // Reach each table with Tab, including when JavaScript is disabled.
      for (const table of await page.locator(".blog-table-scroll").all()) {
        let reached = false;
        for (let attempt = 0; attempt < 50; attempt++) {
          await page.keyboard.press("Tab");
          if (
            await table.evaluate(
              (element) => element === document.activeElement,
            )
          ) {
            reached = true;
            break;
          }
        }
        assert(reached, "Table reachable with Tab");
        if (width === 375) {
          await page.keyboard.press("ArrowRight");
          // Poll from Node: requestAnimationFrame polling does not run in a no-JS context.
          let scrolled = false;
          for (let attempt = 0; attempt < 20; attempt++) {
            if (await table.evaluate((element) => element.scrollLeft > 0)) {
              scrolled = true;
              break;
            }
            await page.waitForTimeout(50);
          }
          assert(
            scrolled,
            `Keyboard table scrolling, JavaScript=${javaScriptEnabled}`,
          );
        }
      }
      await page.screenshot({
        path: resolve(
          directory,
          `article-tables-${width}${javaScriptEnabled ? "" : "-no-js"}.png`,
        ),
      });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: resolve(
          directory,
          `article-${width}${javaScriptEnabled ? "" : "-no-js"}.png`,
        ),
      });
      if (javaScriptEnabled) {
        assert.deepEqual(
          (
            await new AxeBuilder({ page })
              .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
              .analyze()
          ).violations,
          [],
        );
        await page.screenshot({
          path: resolve(directory, `article-full-${width}.png`),
          fullPage: true,
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
        keyboardTables: 4,
        axeViolations: javaScriptEnabled ? 0 : null,
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
  const sitemapCount = (sitemap.body.match(/<loc>/g) ?? []).length;
  assert.equal(sitemapCount, 28);
  await writeFile(resolve(directory, "sitemap.xml"), sitemap.body);
  const definition = await localGet("/vi/blog/cong-cu-rank-tracker-la-gi");
  assert.equal(definition.status, 200);
  assert(definition.body.includes(`href="${origin + path}"`));
  const feed = await localGet("/feed.xml");
  assert.equal(feed.status, 200);
  assert.equal((feed.body.match(/<item>/g) ?? []).length, 3);
  assert(!feed.body.includes("cach-theo-doi-thu-hang-doi-thu-seo"));
  assert.equal(
    (await localGet("/blog/cach-theo-doi-thu-hang-doi-thu-seo")).status,
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
        sitemapCount,
        editorialFidelity:
          "Supplied body preserved; one project-boundary clarification added",
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
    `Competitor analysis blog QA passed: ${results.length} viewport/JavaScript cases, metadata, tables, axe, language switch, links, sitemap, RSS and redirects.`,
  );
} finally {
  await browser.close();
}
