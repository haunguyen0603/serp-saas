import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { JSDOM } from "jsdom";

const baseline = process.argv.includes("--baseline");
const base = process.env.QA_BASE_URL ?? "http://127.0.0.1:3010";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const origin = "https://serpsaas.com";
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7l",
);
const baselinePath = resolve(
  process.env.QA_BASELINE_FILE ?? resolve(directory, "baseline.json"),
);
await mkdir(directory, { recursive: true });
const normalize = (text) => text.replace(/\s+/g, " ").trim();
const get = async (path) => {
  const response = await fetch(base + path, { redirect: "manual" });
  return { status: response.status, text: await response.text() };
};
const sitemap = await get("/sitemap.xml");
assert.equal(sitemap.status, 200);
const xml = new JSDOM(sitemap.text, { contentType: "text/xml" }).window
  .document;
const urls = [...xml.querySelectorAll("url > loc")].map((el) => el.textContent);
assert.equal(urls.length, 27);
assert.equal(new Set(urls).size, 27);
const pages = {};
for (const url of urls) {
  const path = new URL(url).pathname;
  const response = await get(path);
  assert.equal(response.status, 200, path);
  const document = new JSDOM(response.text).window.document;
  const attr = (selector, name) =>
    document.querySelector(selector)?.getAttribute(name) ?? null;
  const h1 = [...document.querySelectorAll("h1")].map((el) =>
    normalize(el.textContent),
  );
  assert.equal(h1.length, 1, path);
  const lang = attr("html", "lang");
  assert.equal(lang, path.startsWith("/vi") ? "vi" : "en");
  const canonical = attr('link[rel="canonical"]', "href");
  assert.equal(new URL(canonical).pathname, path);
  const alternates = [
    ...document.querySelectorAll('link[rel="alternate"][hreflang]'),
  ].map((el) => [el.hreflang, el.href]);
  const structured = [
    ...document.querySelectorAll('script[type="application/ld+json"]'),
  ].map((el) => JSON.parse(el.textContent));
  const links = [...document.querySelectorAll("a[href]")].map((el) => ({
    href: el.getAttribute("href"),
    text: normalize(el.textContent),
  }));
  pages[path] = {
    title: document.title,
    description: attr('meta[name="description"]', "content"),
    h1,
    lang,
    canonical,
    alternates,
    structured,
    robots: attr('meta[name="robots"]', "content"),
    links,
    cta: document.querySelector(".blog-cta")?.outerHTML ?? null,
    guide: document.querySelector(".landing-guides")?.textContent ?? null,
    prose: document.querySelector(".blog-prose")?.innerHTML ?? null,
    lead: document.querySelector(".public-lead")?.textContent ?? null,
    main: normalize(document.querySelector("main").textContent),
  };
}
for (const key of ["title", "description"]) {
  assert.equal(new Set(Object.values(pages).map((page) => page[key])).size, 27);
}
let paired = 0;
for (const [path, page] of Object.entries(pages)) {
  if (!page.alternates.length) continue;
  paired++;
  assert.equal(page.alternates.length, 3, path);
  for (const [locale, url] of page.alternates) {
    assert.deepEqual(pages[new URL(url).pathname].alternates, page.alternates);
    if (locale === "x-default")
      assert(!new URL(url).pathname.startsWith("/vi"));
  }
}
assert.equal(paired, 24);
assert.equal(
  Object.keys(pages).filter((path) => path.startsWith("/vi/blog/")).length,
  6,
);
assert.equal(
  Object.keys(pages).filter((path) => path.startsWith("/blog/")).length,
  3,
);
const targets = new Set();
for (const page of Object.values(pages)) {
  for (const link of page.links) {
    const url = new URL(link.href, origin);
    if (url.origin === origin) targets.add(url.pathname);
  }
}
for (const path of targets) assert.equal((await get(path)).status, 200, path);
const feed = await get("/feed.xml");
assert.equal(feed.status, 200);
assert.equal((feed.text.match(/<item>/g) ?? []).length, 3);
assert(!feed.text.includes("/vi/blog/"));
const robots = await get("/robots.txt");
assert.equal(robots.status, 200);
assert(robots.text.includes("Sitemap: https://serpsaas.com/sitemap.xml"));
assert(!robots.text.includes("Disallow: /vi"));
for (const path of [
  "/vi/blog/serp-la-gi",
  "/vi/blog/m7l-missing",
  "/blog/cong-cu-rank-tracker-la-gi",
  "/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay",
  "/blog/cach-theo-doi-thu-hang-doi-thu-seo",
]) {
  assert.equal((await get(path)).status, 404, path);
}
const snapshot = {
  pages,
  urls,
  feed: feed.text,
  robots: robots.text,
  internalTargets: [...targets],
};
await writeFile(
  resolve(directory, baseline ? "baseline.json" : "after.json"),
  JSON.stringify(snapshot, null, 2) + "\n",
);
if (baseline) {
  console.log(
    "Baseline saved: 27 routes, 12 reciprocal pairs, 3 unpaired VI posts, 9 posts, RSS/robots/404/internal links checked.",
  );
  process.exit(0);
}
const before = JSON.parse(await readFile(baselinePath, "utf8"));
assert.deepEqual(snapshot.urls, before.urls);
assert.equal(snapshot.feed, before.feed);
assert.equal(snapshot.robots, before.robots);
for (const [path, page] of Object.entries(pages)) {
  for (const key of [
    "title",
    "description",
    "lang",
    "canonical",
    "alternates",
    "robots",
  ])
    assert.deepEqual(page[key], before.pages[path][key], `${path}: ${key}`);
  if (path !== "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa")
    assert.deepEqual(page.h1, before.pages[path].h1);
  const priorSchema = JSON.parse(JSON.stringify(before.pages[path].structured));
  if (path === "/vi/blog/cong-cu-rank-tracker-la-gi")
    priorSchema[0]["@graph"][0].dateModified = "2026-10-29";
  // The existing breadcrumb uses the displayed heading; R1 changes that label too.
  if (path === "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa") {
    priorSchema[0]["@graph"][0].name =
      "Công cụ kiểm tra thứ hạng từ khóa Google";
    priorSchema[0]["@graph"][2].itemListElement.at(-1).name =
      "Công cụ kiểm tra thứ hạng từ khóa Google";
  }
  assert.deepEqual(page.structured, priorSchema, `${path}: JSON-LD`);
  for (const link of before.pages[path].links) {
    if (
      [
        "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
        "/vi/theo-doi-thu-hang-tu-khoa-hang-ngay",
        "/vi/seo-rank-tracking-cho-agency",
      ].includes(path) &&
      /Đọc (hướng dẫn|cách kiểm tra)/.test(link.text)
    )
      continue;
    assert(
      page.links.some(
        (next) => next.href === link.href && next.text === link.text,
      ),
      `${path}: retained ${link.href}`,
    );
  }
  if (path.startsWith("/vi/blog"))
    assert.equal(page.cta, before.pages[path].cta);
}
const guides = [
  [
    "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
    "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
    "Đọc cách kiểm tra thứ hạng từ khóa",
  ],
  [
    "/vi/theo-doi-thu-hang-tu-khoa-hang-ngay",
    "/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay",
    "Khi nào nên theo dõi thứ hạng hàng ngày?",
  ],
  [
    "/vi/seo-rank-tracking-cho-agency",
    "/vi/blog/serp-tracking-cho-agency",
    "Đọc quy trình báo cáo thứ hạng cho agency",
  ],
];
const enPaths = Object.keys(pages).filter(
  (path) => path === "/blog" || path.startsWith("/blog/"),
);
const productLabel = "Explore the Google rank tracker";
for (const path of enPaths) {
  const doc = new JSDOM(pages[path].cta).window.document;
  const links = [...doc.querySelectorAll("a")];
  assert.equal(
    links.filter(
      (el) =>
        el.textContent === productLabel &&
        new URL(el.href, origin).pathname === "/google-serp-rank-tracker",
    ).length,
    1,
  );
  assert(links.some((el) => el.textContent === "Explore rank-tracking Plans"));
}
for (const [path, target, label] of guides) {
  assert.equal(
    pages[path].links.filter(
      (el) =>
        new URL(el.href, origin).pathname === target &&
        el.text === label + " →",
    ).length,
    1,
  );
}
assert.deepEqual(pages[guides[0][0]].h1, [
  "Công cụ kiểm tra thứ hạng từ khóa Google",
]);
const article = new JSDOM(pages["/vi/blog/cong-cu-rank-tracker-la-gi"].prose)
  .window.document;
assert.equal(
  article.querySelectorAll('a[href$="/vi/blog/cach-kiem-tra-thu-hang-tu-khoa"]')
    .length,
  1,
);
assert.equal(
  article.querySelectorAll('a[href$="/vi/cong-cu-kiem-tra-thu-hang-tu-khoa"]')
    .length,
  1,
);
const scope =
  "Checks cover Google's Top 10. Desktop and Mobile tracking are managed separately; available schedules depend on your plan.";
const caption =
  "Illustrative interface preview. Sample domains, rankings and usage numbers are not live customer results or current plan limits.";
assert(pages["/"].main.includes(scope));
assert(pages["/"].main.includes(caption));
console.log(
  "SSR regression passed: all metadata, locale mappings, counts, retained links, R1–R5 and expected date/breadcrumb changes.",
);
if (process.argv.includes("--ssr-only")) process.exit(0);

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
const browser = await chromium.launch({
  executablePath: process.env.QA_CHROME_PATH,
});
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
      for (const path of [
        "/",
        ...guides.map(([path]) => path),
        ...enPaths,
        "/vi/blog",
        "/vi/blog/cong-cu-rank-tracker-la-gi",
        "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
      ]) {
        assert.equal(
          (await page.goto(base + path, { waitUntil: "networkidle" })).status(),
          200,
        );
        assert.equal(await page.locator("h1").count(), 1);
        assert.equal(
          await page.evaluate(() => document.documentElement.scrollWidth),
          width,
          path,
        );
        if (path === "/") {
          await page.getByText(scope, { exact: true }).scrollIntoViewIfNeeded();
          assert(await page.getByText(scope, { exact: true }).isVisible());
          await page
            .getByText(caption, { exact: true })
            .scrollIntoViewIfNeeded();
          assert(await page.getByText(caption, { exact: true }).isVisible());
        }
        let navigationLink;
        if (enPaths.includes(path))
          navigationLink = page
            .locator(".blog-cta")
            .getByRole("link", { name: productLabel, exact: true });
        const guide = guides.find(([source]) => source === path);
        if (guide) navigationLink = page.locator(".landing-guides > a");
        if (path === "/vi/blog/cong-cu-rank-tracker-la-gi")
          navigationLink = page.locator(
            '.blog-prose a[href$="/vi/blog/cach-kiem-tra-thu-hang-tu-khoa"]',
          );
        let focus = null;
        if (navigationLink) {
          await navigationLink.scrollIntoViewIfNeeded();
          await navigationLink.focus();
          await page.keyboard.press("Shift+Tab");
          await page.keyboard.press("Tab");
          focus = await navigationLink.evaluate((el) => ({
            active: el === document.activeElement,
            style: getComputedStyle(el).outlineStyle,
            width: getComputedStyle(el).outlineWidth,
          }));
          assert(
            focus.active && focus.style !== "none" && focus.width !== "0px",
            `${path}: keyboard focus`,
          );
          const target = new URL(
            await navigationLink.getAttribute("href"),
            origin,
          ).pathname;
          await page.keyboard.press("Enter");
          await page.waitForURL(base + target);
          await page.goto(base + path, { waitUntil: "networkidle" });
        }
        if (javaScriptEnabled) {
          const axe = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
            .analyze();
          assert.deepEqual(axe.violations, [], `${path}: axe`);
          if (path === "/" || guide || path === "/blog") {
            if (guide)
              await page.locator(".landing-guides").scrollIntoViewIfNeeded();
            if (path === "/blog")
              await page.locator(".blog-cta").scrollIntoViewIfNeeded();
            await page.screenshot({
              path: resolve(
                directory,
                `${path === "/" ? "home" : path.slice(1).replaceAll("/", "-")}-${width}.png`,
              ),
            });
          }
        }
        assert.deepEqual(errors, []);
        results.push({
          path,
          width,
          javaScriptEnabled,
          overflow: false,
          focus,
          axe: javaScriptEnabled ? "zero violations" : "not run: JS disabled",
          errors: [...errors],
        });
      }
      await context.close();
    }
  }
  await writeFile(
    resolve(directory, "browser-qa.json"),
    JSON.stringify({ results, browserVersion: browser.version() }, null, 2) +
      "\n",
  );
  console.log(
    `Browser QA passed: ${results.length} route/viewport/JS cases, keyboard navigation and WCAG 2/2.1 A/AA axe with no exclusions.`,
  );
} finally {
  await browser.close();
}
