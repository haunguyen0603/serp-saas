// Optional external Playwright/axe tools; only a local production standalone server is permitted.
import assert from "node:assert/strict";
import { request } from "node:http";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { publicLocalePairs, publicLocale } from "../src/lib/public-locales.ts";
import { getPublishedPosts } from "../src/features/blog/content.ts";

const importTool = (name) =>
  import(
    process.env.QA_TOOLS_DIRECTORY
      ? pathToFileURL(
          resolve(
            process.env.QA_TOOLS_DIRECTORY,
            name,
            name === "@axe-core/playwright" ? "dist/index.mjs" : "index.mjs",
          ),
        ).href
      : name
  );
const { chromium } = await importTool("playwright");
const { default: AxeBuilder } = await importTool("@axe-core/playwright");
const base = process.env.QA_BASE_URL ?? "http://127.0.0.1:3013";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const origin = "https://serpsaas.com";
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7i1",
);
await mkdir(directory, { recursive: true });
const fixturePlans = ["desktop", "mobile"].flatMap((device, di) =>
  ["free", "starter", "pro"].map((tier, ti) => ({
    id: `${device}-${tier}-qa`,
    code: `${device}_${tier}`,
    name: `${device === "desktop" ? "Desktop" : "Mobile"} ${tier[0].toUpperCase()}${tier.slice(1)}`,
    device_scope: device,
    price_monthly_minor_units: ti ? 2950 + ti * 1000 + di * 100 : 0,
    currency: "USD",
    max_projects: 1 + ti,
    max_keywords: 10 + ti * 123,
    monthly_keyword_checks: 25 + ti * 999,
    scheduled_checks_enabled: ti > 0,
    max_scheduled_frequency: ti === 0 ? "none" : ti === 1 ? "weekly" : "daily",
  })),
);
const results = [],
  noJavaScript = [],
  http = [],
  navigation = [],
  metadata = [],
  pricingParity = [],
  pricingErrors = [];
// Recheck only the final pricing stage against the same unchanged standalone build.
// A normal invocation always runs the complete responsive matrix from scratch.
const recheckPricing = process.env.QA_RECHECK_PRICING === "1";
if (recheckPricing) {
  const saved = JSON.parse(
    await readFile(resolve(directory, "browser-qa.json"), "utf8"),
  );
  for (const [name, target, count] of [
    ["results", results, 96],
    ["noJavaScript", noJavaScript, 96],
    ["navigation", navigation, 96],
    ["metadata", metadata, 24],
    ["pricingParity", pricingParity, 4],
  ]) {
    assert.equal(saved[name]?.length, count, `Completed ${name} required`);
    target.push(...saved[name]);
  }
}
const snapshot = async () =>
  writeFile(
    resolve(directory, "browser-qa.json"),
    JSON.stringify(
      {
        apiMode:
          "intercepted synthetic plans and anonymous session; no real backend/account/provider requests",
        results,
        noJavaScript,
        http,
        navigation,
        metadata,
        pricingParity,
        pricingErrors,
      },
      null,
      2,
    ) + "\n",
  );
const localGet = (path, headers = {}) =>
  new Promise((resolveResponse, reject) => {
    const incoming = request(new URL(path, base), { headers }, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        body += chunk;
      });
      response.on("end", () =>
        resolveResponse({
          status: response.statusCode,
          headers: response.headers,
          body,
        }),
      );
    });
    incoming.on("error", reject);
    incoming.end();
  });
async function isolate(context, mode = { failPlans: false }) {
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === new URL(base).origin) return route.continue();
    if (url.origin === origin)
      return route.fulfill({
        status: 302,
        headers: { location: base + url.pathname + url.search },
        body: "",
      });
    const cors = {
      "Access-Control-Allow-Origin": new URL(base).origin,
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (url.pathname === "/api/v1/auth/refresh")
      return route.fulfill({
        status: route.request().method() === "OPTIONS" ? 204 : 401,
        headers: cors,
        contentType: "application/json",
        body: '{"detail":"Anonymous QA"}',
      });
    if (url.pathname === "/api/v1/billing/plans")
      return route.fulfill({
        status:
          route.request().method() === "OPTIONS"
            ? 204
            : mode.failPlans
              ? 503
              : 200,
        headers: cors,
        contentType: "application/json",
        body: mode.failPlans
          ? '{"detail":"Synthetic catalog outage"}'
          : JSON.stringify(fixturePlans),
      });
    throw new Error(`Unexpected external request ${url.origin}${url.pathname}`);
  });
}
function pairFor(path) {
  return publicLocalePairs.find((pair) => pair.en === path || pair.vi === path);
}
const browser = await chromium.launch(
  process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {},
);
try {
  // Check all canonical/app host behavior first, preserving Host with node:http.
  for (const pair of publicLocalePairs)
    for (const path of [pair.en, pair.vi]) {
      const locale = publicLocale(path);
      const response = await localGet(path, {
        host: "serpsaas.com",
        "accept-language": locale === "vi" ? "en" : "vi-VN",
      });
      assert.equal(response.status, 200, path);
      assert(!response.headers["x-robots-tag"]?.includes("noindex"));
      assert(response.body.includes(`lang="${locale}"`));
      const canonical = response.body.match(/rel="canonical" href="([^"]+)"/);
      assert(canonical, path);
      assert.equal(new URL(canonical[1]).href, origin + path);
      for (const language of ["en", "vi", "x-default"]) {
        const alternate = response.body.match(
          new RegExp(`hreflang="${language}" href="([^"]+)"`, "i"),
        );
        assert(alternate, `${path}: ${language}`);
        assert.equal(
          new URL(alternate[1]).href,
          origin + pair[language === "x-default" ? "en" : language],
        );
      }
      for (const language of ["en", "vi"]) {
        const anchors = [...response.body.matchAll(/<a\b[^>]*>/g)].map(
          (match) => match[0],
        );
        assert(
          anchors.some(
            (anchor) =>
              new RegExp(`hreflang="${language}"`, "i").test(anchor) &&
              anchor.includes(`href="${origin}${pair[language]}"`),
          ),
          `${path}: crawlable ${language} anchor`,
        );
      }
      const redirected = await localGet(path + "?source=qa", {
        host: "app.serpsaas.com",
      });
      assert.equal(redirected.status, 307);
      assert.equal(
        redirected.headers.location,
        path === "/"
          ? "https://app.serpsaas.com/app?source=qa"
          : origin + path + "?source=qa",
      );
      http.push({
        path,
        status: 200,
        locale,
        noindex: false,
        appStatus: 307,
        appLocation: redirected.headers.location,
      });
    }
  const sitemap = await localGet("/sitemap.xml");
  assert.equal(sitemap.status, 200);
  const entries = [...sitemap.body.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
    (match) => match[1],
  );
  const unpairedVietnamesePosts = getPublishedPosts(undefined, "vi").filter(
    (post) => !pairFor(`/vi/blog/${post.slug}`),
  );
  const expectedEntries =
    publicLocalePairs.length * 2 + unpairedVietnamesePosts.length;
  assert.equal(entries.length, expectedEntries);
  assert.equal(new Set(entries).size, expectedEntries);
  for (const post of unpairedVietnamesePosts)
    assert(entries.includes(`${origin}/vi/blog/${post.slug}`));
  for (const pair of publicLocalePairs)
    for (const path of [pair.en, pair.vi])
      assert(entries.includes(origin + path));
  const robots = await localGet("/robots.txt");
  assert.equal(robots.status, 200);
  assert(!robots.body.includes("Disallow: /vi"));
  for (const path of [
    "/app",
    "/admin",
    "/settings",
    "/api",
    "/login",
    "/register",
  ])
    assert(robots.body.includes(`Disallow: ${path}`));
  assert(robots.body.includes(`Sitemap: ${origin}/sitemap.xml`));
  await writeFile(resolve(directory, "sitemap.xml"), sitemap.body);
  await writeFile(resolve(directory, "robots.txt"), robots.body);
  for (const flag of ["us", "vi"]) {
    const response = await localGet(`/flags/${flag}.svg`);
    assert.equal(response.status, 200);
    assert(response.headers["content-type"].includes("image/svg+xml"));
  }
  await snapshot();
  for (const width of recheckPricing ? [] : [375, 768, 1024, 1440]) {
    const prices = {};
    for (const path of publicLocalePairs.flatMap((pair) => [
      pair.en,
      pair.vi,
    ])) {
      const locale = publicLocale(path),
        pair = pairFor(path),
        target = locale === "en" ? "vi" : "en";
      const context = await browser.newContext({
        viewport: { width, height: 900 },
      });
      await isolate(context);
      const page = await context.newPage(),
        errors = [];
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
      assert.equal(
        (await page.goto(base + path, { waitUntil: "networkidle" })).status(),
        200,
      );
      assert.equal(await page.locator("h1").count(), 1);
      await page.locator("h1").waitFor({ state: "visible" });
      assert.equal(await page.locator("html").getAttribute("lang"), locale);
      assert.equal(
        new URL(
          await page.locator('link[rel="canonical"]').getAttribute("href"),
        ).href,
        origin + path,
      );
      for (const language of ["en", "vi", "x-default"])
        assert.equal(
          new URL(
            await page
              .locator(`link[rel="alternate"][hreflang="${language}"]`)
              .getAttribute("href"),
          ).href,
          origin + pair[language === "x-default" ? "en" : language],
        );
      if (width === 375) {
        const title = await page.title(),
          description = await page
            .locator('meta[name="description"]')
            .getAttribute("content");
        const structuredData = (
          await page
            .locator('script[type="application/ld+json"]')
            .allTextContents()
        ).map(JSON.parse);
        if (locale === "vi") {
          assert(structuredData.length);
          for (const graph of structuredData)
            for (const entity of graph["@graph"] ?? [graph])
              assert(
                [
                  "WebPage",
                  "SoftwareApplication",
                  "BreadcrumbList",
                  "BlogPosting",
                ].includes(entity["@type"]),
              );
          for (const key of ["og:title", "og:description", "og:url"])
            assert(
              await page
                .locator(`meta[property="${key}"]`)
                .getAttribute("content"),
            );
          for (const key of [
            "twitter:title",
            "twitter:description",
            "twitter:card",
          ])
            assert(
              await page.locator(`meta[name="${key}"]`).getAttribute("content"),
            );
          assert(
            (
              await page.locator('meta[name="robots"]').getAttribute("content")
            ).includes("index, follow"),
          );
        }
        metadata.push({ path, locale, title, description, structuredData });
      }
      if (path === "/pricing" || path === "/vi/bang-gia") {
        await page
          .locator(".pricing-card")
          .first()
          .waitFor({ state: "visible" });
        assert.equal(
          await page.locator(".pricing-card").count(),
          fixturePlans.length,
        );
        prices[locale] = await page
          .locator(".pricing-card")
          .evaluateAll((cards) =>
            cards.map((card) => ({
              id: card.dataset.planId,
              name: card.getAttribute("aria-label"),
              price: card.querySelector(".pricing-price strong").textContent,
              limits: [...card.querySelectorAll(".pricing-limits li strong")]
                .slice(0, 3)
                .map((element) => element.textContent),
              schedule: card
                .querySelector(".pricing-limits li:last-child")
                .textContent.trim(),
              href: card.querySelector("a").getAttribute("href"),
            })),
          );
        const schedules =
          locale === "vi"
            ? [
                "Không hỗ trợ kiểm tra theo lịch",
                "Lên lịch hàng tuần",
                "Lên lịch hàng ngày",
              ]
            : ["No scheduled checks", "Weekly scheduling", "Daily scheduling"];
        for (const card of prices[locale]) {
          const plan = fixturePlans.find((plan) => plan.id === card.id),
            tier = plan.code.split("_").at(-1);
          assert.equal(
            card.schedule,
            schedules[["free", "starter", "pro"].indexOf(tier)],
          );
        }
      }
      if (locale === "vi") {
        const anchors = await page
          .locator("main a[href], footer a[href], header .public-nav a[href]")
          .evaluateAll((elements) =>
            elements.map((element) => element.getAttribute("href")),
          );
        for (const href of anchors) {
          const url = new URL(href, base);
          if (url.origin === origin)
            assert(
              url.pathname === "/vi" || url.pathname.startsWith("/vi/"),
              `${path}: English public jump ${href}`,
            );
        }
      }
      if (width <= 1024) {
        const menu = page.getByRole("button", {
          name:
            locale === "vi" ? "Mở menu điều hướng" : "Open public navigation",
        });
        await menu.focus();
        await page.keyboard.press("Enter");
        await page.getByRole("dialog").waitFor({ state: "visible" });
        if (locale === "vi")
          assert.equal(
            await page
              .getByRole("dialog")
              .getByRole("link", { name: "Bảng giá", exact: true })
              .getAttribute("href"),
            origin + "/vi/bang-gia",
          );
        await page.keyboard.press("Escape");
        await page.getByRole("dialog").waitFor({ state: "hidden" });
        assert(
          await menu.evaluate((element) => element === document.activeElement),
        );
      }
      const select = page.locator("header .public-language-select"),
        trigger = select.locator("summary");
      await trigger.waitFor({ state: "visible" });
      assert.equal(
        await trigger.getAttribute("aria-label"),
        `Change language: ${locale === "vi" ? "Tiếng Việt" : "English"}`,
      );
      assert(
        (await trigger.innerText()).includes(
          locale === "vi" ? "Tiếng Việt" : "English",
        ),
      );
      assert.equal(
        await trigger.locator("img").getAttribute("src"),
        `/flags/${locale === "vi" ? "vi" : "us"}.svg`,
      );
      assert(
        await trigger.evaluate(
          (element) => element.firstElementChild.tagName === "IMG",
        ),
      );
      const bounds = await trigger.boundingBox();
      assert(bounds.height >= 44);
      await trigger.focus();
      assert(
        await trigger.evaluate(
          (element) => getComputedStyle(element).outlineStyle !== "none",
        ),
      );
      await page.keyboard.press("Space");
      assert(await select.evaluate((element) => element.open));
      await page.keyboard.press("Escape");
      assert(!(await select.evaluate((element) => element.open)));
      assert(
        await trigger.evaluate((element) => element === document.activeElement),
      );
      await page.keyboard.press("Enter");
      assert(await select.evaluate((element) => element.open));
      // Legal-page headings can sit behind the open popover; click a clear page margin.
      await page.mouse.click(8, 300);
      assert(!(await select.evaluate((element) => element.open)));
      await trigger.click();
      assert(await select.evaluate((element) => element.open));
      const options = select.locator("a");
      assert.equal(await options.count(), 2);
      for (const language of ["en", "vi"])
        assert.equal(
          await select.locator(`[hreflang="${language}"]`).getAttribute("href"),
          origin + pair[language],
        );
      assert.equal(
        await select
          .locator(`[hreflang="${locale}"]`)
          .getAttribute("aria-current"),
        "page",
      );
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `overflow ${path} ${width}`,
      );
      const accessibility = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      assert.deepEqual(
        accessibility.violations,
        [],
        `${path} ${width}: ${JSON.stringify(accessibility.violations)}`,
      );
      const filename =
        path === "/" ? "en-home" : path.slice(1).replaceAll("/", "-");
      await page.screenshot({
        path: resolve(directory, `${filename}-${width}.png`),
        fullPage: true,
      });
      await select.locator(`[hreflang="${target}"]`).focus();
      await page.keyboard.press("Enter");
      await page.waitForURL(base + pair[target]);
      await page.waitForLoadState("networkidle");
      assert.equal(await page.locator("html").getAttribute("lang"), target);
      assert.deepEqual(errors, []);
      navigation.push({
        path,
        destination: pair[target],
        width,
        keyboard: true,
      });
      results.push({
        path,
        width,
        status: 200,
        locale,
        overflow: false,
        axeViolations: 0,
        errors,
      });
      await context.close();
      const staticContext = await browser.newContext({
        javaScriptEnabled: false,
        viewport: { width, height: 900 },
      });
      await isolate(staticContext);
      const staticPage = await staticContext.newPage();
      assert.equal((await staticPage.goto(base + path)).status(), 200);
      assert.equal(
        await staticPage.locator("html").getAttribute("lang"),
        locale,
      );
      assert.equal(await staticPage.locator("h1").count(), 1);
      await staticPage.locator("h1").waitFor({ state: "visible" });
      const staticSelect = staticPage.locator("header .public-language-select");
      await staticSelect.locator("summary").click();
      await staticSelect
        .locator(`[hreflang="${target}"]`)
        .waitFor({ state: "visible" });
      assert(
        await staticPage.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      await staticSelect.locator(`[hreflang="${target}"]`).click();
      await staticPage.waitForURL(base + pair[target]);
      assert.equal(
        await staticPage.locator("html").getAttribute("lang"),
        target,
      );
      noJavaScript.push({
        path,
        width,
        readable: true,
        languageSwitch: pair[target],
        overflow: false,
      });
      await staticContext.close();
      await snapshot();
      console.log(`Pass ${path} @ ${width}`);
    }
    const normalize = (cards) =>
      cards.map((card) => {
        const normalized = { ...card };
        delete normalized.schedule;
        return normalized;
      });
    assert.deepEqual(normalize(prices.vi), normalize(prices.en));
    pricingParity.push({
      width,
      sameIDsPricesLimitsOrderAvailability: true,
      english: prices.en,
      vietnamese: prices.vi,
    });
    await snapshot();
  }
  for (const [path, label] of [
    ["/pricing", "Retry"],
    ["/vi/bang-gia", "Thử lại"],
  ]) {
    const mode = { failPlans: true },
      context = await browser.newContext({
        viewport: { width: 375, height: 900 },
      });
    await isolate(context, mode);
    const page = await context.newPage();
    await page.goto(base + path);
    await page
      .locator('.pricing-main .ui-alert[role="alert"]')
      .waitFor({ state: "visible" });
    assert.equal(await page.locator(".pricing-card").count(), 0);
    mode.failPlans = false;
    await page.getByRole("button", { name: label }).click();
    await page.locator(".pricing-card").first().waitFor({ state: "visible" });
    assert.equal(await page.locator(".pricing-card").count(), 6);
    pricingErrors.push({ path, noFallbackPrices: true, retryRecovered: true });
    await context.close();
  }
  const vietnamese = metadata.filter((entry) => entry.locale === "vi");
  assert.equal(new Set(vietnamese.map((entry) => entry.title)).size, 12);
  assert.equal(new Set(vietnamese.map((entry) => entry.description)).size, 12);
  assert.equal(getPublishedPosts(undefined, "vi").length, 7);
  await snapshot();
  console.log(
    JSON.stringify({
      browserCases: results.length,
      noJavaScriptCases: noJavaScript.length,
      keyboardSwitches: navigation.length,
      httpCases: http.length,
      pricingParityCases: pricingParity.length,
      pricingErrorCases: pricingErrors.length,
    }),
  );
} finally {
  await browser.close();
}
