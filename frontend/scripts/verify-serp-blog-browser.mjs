// Optional external Playwright/axe tools, using the same QA environment as the other blog scripts.
import assert from "node:assert/strict";
import { request } from "node:http";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { format } from "prettier";
import { JSDOM } from "jsdom";

const brief = await readFile("../docs/seo-blog-vi-serp-la-gi-codex.md", "utf8");
const expected = brief
  .split("Khi tìm một từ khóa trên Google,")[1]
  .split("## 3. Final Codex verification checklist")[0]
  .replace(/\r?\n---\s*$/, "");
const expectedBody = "Khi tìm một từ khóa trên Google," + expected.trimEnd();
const actual = (
  await readFile("content/blog/vi/serp-la-gi.md", "utf8")
).replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "");
assert.equal(
  await format(actual, { parser: "markdown" }),
  await format(expectedBody, { parser: "markdown" }),
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
const path = "/vi/blog/serp-la-gi";
const title =
  "SERP là gì? Các thành phần của trang kết quả tìm kiếm Google và vai trò trong SEO";
const description =
  "SERP là gì? Tìm hiểu kết quả tìm kiếm tự nhiên, quảng cáo, Featured Snippet, Local Pack và cách phân tích SERP để tối ưu SEO.";
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/blog-vi-serp-la-gi",
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
      const failedResponses = [];
      page.on("response", (response) => {
        if (
          response.status() >= 400 &&
          !response.url().includes("/api/v1/auth/refresh")
        )
          failedResponses.push({
            url: response.url(),
            status: response.status(),
          });
      });
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
      assert.equal(
        await page.title(),
        "SERP là gì? Các thành phần SERP Google và vai trò SEO | SERP SaaS",
      );
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
      assert.equal(graph[0].datePublished, "2026-11-02");
      assert.equal(graph[0].dateModified, "2026-11-02");
      assert.equal(graph[1]["@type"], "BreadcrumbList");
      assert.equal(graph[1].itemListElement.at(-1).item, origin + path);
      assert.equal(await page.locator(".blog-prose table").count(), 2);
      assert.equal(await page.locator(".blog-prose th").count(), 6);
      assert.equal(
        await page
          .locator('.blog-table-scroll[tabindex="0"][role="region"]')
          .count(),
        2,
      );
      const prose = await page.locator(".blog-prose").textContent();
      for (const text of [
        "Search Engine Results Page",
        "Top 10",
        "Desktop",
        "Mobile",
        "dự án Desktop và Mobile riêng biệt",
        "đã hoàn tất",
        "phụ thuộc vào gói dịch vụ",
        "không thể suy ra vị trí chính xác",
        "không phải kết quả SERP thực tế",
        "average position",
        "quảng cáo, Local Pack, câu trả lời AI hay vị trí ngoài Top 10",
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
        [
          "hướng dẫn kiểm tra thứ hạng từ khóa",
          "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
        ],
        [
          "cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP",
          "/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo",
        ],
        [
          "công cụ kiểm tra thứ hạng từ khóa Google của SERP SaaS",
          "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
        ],
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
      assert.deepEqual(failedResponses, []);
      results.push({
        width,
        javaScriptEnabled,
        status: 200,
        overflow: false,
        languageFallback: "/",
        roundTrip: "/vi",
        listingCards: 7,
        keyboardTables: 2,
        axeViolations: javaScriptEnabled ? 0 : null,
        pageErrors: errors,
        failedResponses,
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
  const document = new JSDOM(article.body).window.document;
  assert.equal(document.documentElement.lang, "vi");
  assert.equal(document.querySelectorAll("h1").length, 1);
  assert.equal(document.querySelector("h1").textContent, title);
  assert.equal(document.querySelectorAll(".blog-prose table").length, 2);
  assert.equal(document.querySelectorAll(".blog-prose th").length, 6);
  assert(
    document
      .querySelector(".blog-prose")
      .textContent.includes("Search Engine Results Page"),
  );
  await writeFile(resolve(directory, "article-ssr.html"), article.body);
  await writeFile(
    resolve(directory, "source-render.json"),
    JSON.stringify(
      {
        sourceFidelity: true,
        headings: [
          ...document.querySelectorAll(".blog-prose h2, .blog-prose h3"),
        ].map((el) => el.textContent),
        tables: [...document.querySelectorAll(".blog-prose table")].map(
          (table) =>
            [...table.rows].map((row) =>
              [...row.cells].map((cell) => cell.textContent),
            ),
        ),
        links: [...document.querySelectorAll(".blog-prose a")].map((el) => ({
          text: el.textContent,
          href: el.href,
        })),
      },
      null,
      2,
    ) + "\n",
  );
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
  const definition = await localGet("/vi/blog/cach-kiem-tra-thu-hang-tu-khoa");
  assert.equal(definition.status, 200);
  assert(definition.body.includes(`href="${origin + path}"`));
  const feed = await localGet("/feed.xml");
  assert.equal(feed.status, 200);
  assert.equal((feed.body.match(/<item>/g) ?? []).length, 3);
  assert(!feed.body.includes("serp-la-gi"));
  assert.equal((await localGet("/blog/serp-la-gi")).status, 404);
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
          "Supplied body preserved; Markdown table formatting only",
        relatedDiscoveryFromCheckingGuide: true,
        englishRssItems: 3,
        forcedLanguageRedirect: false,
        appHostRedirect: 307,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `SERP definition blog QA passed: ${results.length} viewport/JavaScript cases, metadata, tables, axe, language switch, links, sitemap, RSS and redirects.`,
  );
} finally {
  await browser.close();
}
