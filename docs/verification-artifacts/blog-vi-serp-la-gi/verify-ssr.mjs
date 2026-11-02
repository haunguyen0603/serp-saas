import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
const require = createRequire(
  new URL("../../../frontend/package.json", import.meta.url),
);
const { JSDOM } = require("jsdom");
const base = process.env.QA_BASE_URL ?? "http://127.0.0.1:3014";
assert(["127.0.0.1", "localhost"].includes(new URL(base).hostname));
const get = async (path) => {
  const response = await fetch(base + path);
  assert.equal(response.status, 200, path);
  return response.text();
};
const baseline = JSON.parse(
  await readFile(
    new URL(
      "../milestone-7l-final/linux-20261101/seo/after.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const sitemap = await get("/sitemap.xml");
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
  (match) => match[1],
);
assert.equal(urls.length, 28);
assert.equal(new Set(urls).size, 28);
const pages = {};
const preserved = [];
for (const url of urls) {
  const path = new URL(url).pathname;
  const document = new JSDOM(await get(path)).window.document;
  const attr = (selector, name) =>
    document.querySelector(selector)?.getAttribute(name) ?? null;
  const page = {
    title: document.title,
    description: attr('meta[name="description"]', "content"),
    h1: [...document.querySelectorAll("h1")].map((el) =>
      el.textContent.replace(/\s+/g, " ").trim(),
    ),
    lang: attr("html", "lang"),
    canonical: attr('link[rel="canonical"]', "href"),
    alternates: [
      ...document.querySelectorAll('link[rel="alternate"][hreflang]'),
    ].map((el) => [el.hreflang, el.href]),
    structured: [
      ...document.querySelectorAll('script[type="application/ld+json"]'),
    ].map((el) => JSON.parse(el.textContent)),
    robots: attr('meta[name="robots"]', "content"),
    prose: document.querySelector(".blog-prose")?.innerHTML ?? null,
  };
  assert.equal(page.h1.length, 1, path);
  assert.equal(page.lang, path.startsWith("/vi") ? "vi" : "en");
  assert.equal(new URL(page.canonical).pathname, path);
  if (baseline.pages[path]) {
    for (const key of Object.keys(page))
      assert.deepEqual(page[key], baseline.pages[path][key], `${path}: ${key}`);
    preserved.push(path);
  }
  pages[path] = page;
}
assert.equal(preserved.length, 27);
for (const key of ["title", "description"])
  assert.equal(new Set(Object.values(pages).map((page) => page[key])).size, 28);
await writeFile(
  new URL("ssr-inventory.json", import.meta.url),
  JSON.stringify(
    {
      pages,
      existingPagesPreserved: preserved,
      sitemapCount: 28,
      titleAndDescriptionUniqueCount: 28,
      comparison:
        "All 27 existing pages retain title, description, H1, lang, canonical, alternates, structured data, robots and article prose from the previously verified 2026-11-01 local baseline.",
    },
    null,
    2,
  ) + "\n",
);
console.log(
  "SSR passed: 28 URLs, 28 unique titles/descriptions, 27 existing pages preserved.",
);
