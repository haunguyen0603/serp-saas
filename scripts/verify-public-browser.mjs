// M6.5B: production public-site, SEO, responsive and keyboard verification.
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const modulePath = process.env.PLAYWRIGHT_MODULE;
if (!modulePath) throw new Error("Set PLAYWRIGHT_MODULE to playwright-core/index.mjs");
const { chromium } = await import(pathToFileURL(modulePath).href);
const base = process.env.FRONTEND_URL ?? "http://localhost:3000";
const screenshots = process.env.SCREENSHOT_DIR ?? "docs/screenshots/milestone-6.5b";
await mkdir(screenshots, { recursive: true });

const expectedPlans = {
  desktop_free: [0, 1, 50, 100, false, "none"],
  desktop_starter: [1900, 5, 500, 5000, true, "weekly"],
  desktop_pro: [12900, 20, 5000, 50000, true, "daily"],
  mobile_free: [0, 1, 20, 50, false, "none"],
  mobile_starter: [3900, 3, 200, 1000, true, "weekly"],
  mobile_pro: [24900, 10, 1000, 10000, true, "daily"],
};

function contrastRatio(foreground, background) {
  const parse = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number);
  const luminance = (value) => {
    const channels = parse(value).map((channel) => {
      const normalized = channel / 255;
      return normalized <= 0.03928
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };
  const a = luminance(foreground);
  const b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

async function assertAuthPresentation(page) {
  const main = page.locator("main");
  assert.equal(await main.getByText("SERP SaaS", { exact: true }).count(), 0);
  const fields = main.locator('input[type="email"], input[type="password"]');
  assert((await fields.count()) >= 2);
  const styles = await fields.evaluateAll((inputs) =>
    inputs.map((input) => {
      const style = getComputedStyle(input);
      return {
        background: style.backgroundColor,
        borderColor: style.borderColor,
        borderStyle: style.borderStyle,
        borderWidth: style.borderWidth,
        color: style.color,
      };
    }),
  );
  for (const style of styles) {
    assert.equal(style.background, "rgb(255, 255, 255)");
    assert.equal(style.borderStyle, "solid");
    assert.notEqual(style.borderWidth, "0px");
    assert.notEqual(style.borderColor, "rgba(0, 0, 0, 0)");
    assert.notEqual(style.color, "rgb(255, 255, 255)");
  }
}

const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROME_EXECUTABLE
    ? { executablePath: process.env.CHROME_EXECUTABLE }
    : {}),
});

try {
  const context = await browser.newContext();
  const page = await context.newPage();
  const exceptions = [];
  const failures = [];
  const harmless = [];
  const apiResponses = [];
  page.on("pageerror", (error) => exceptions.push(error.message));
  page.on("requestfailed", (request) => {
    const event = {
      path: new URL(request.url()).pathname,
      method: request.method(),
      reason: request.failure()?.errorText,
    };
    if (event.method === "GET" && event.reason === "net::ERR_ABORTED") harmless.push(event);
    else failures.push(event);
  });
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (path.startsWith("/api/v1/")) apiResponses.push({ path, status: response.status() });
  });

  await page.goto(`${base}/`);
  await page.getByRole("heading", { level: 1, name: "Track your Google rankings with clarity." }).waitFor();
  assert.equal(await page.locator(".public-header").count(), 1);
  assert.equal(await page.locator(".app-sidebar").count(), 0);
  for (const text of [
    "From site setup to a ranking history in four steps.",
    "Desktop and Mobile rankings can differ.",
    "Keep one SEO asset through domain changes.",
    "Check manually, weekly or daily.",
    "Built with teams and integrations in mind.",
    "Start building a clearer ranking history.",
  ]) assert.equal(await page.getByText(text, { exact: true }).count(), 1, `Missing Home content: ${text}`);
  assert((await page.getByText("seo-demo.com", { exact: true }).count()) >= 2);
  assert((await page.locator("main").textContent()).includes("not available yet"));
  assert.equal(await page.getByRole("link", { name: "Start Free", exact: true }).first().getAttribute("href"), "/register");
  assert.equal(await page.getByRole("link", { name: "View Pricing", exact: true }).first().getAttribute("href"), "/pricing");
  assert.equal(await page.getByRole("link", { name: "Log in", exact: true }).first().getAttribute("href"), "/login");
  const productFooter = page.getByRole("navigation", { name: "Product links" });
  const accountFooter = page.getByRole("navigation", { name: "Account links" });
  assert.equal(await productFooter.getByRole("link", { name: "Home" }).getAttribute("href"), "/");
  assert.equal(await productFooter.getByRole("link", { name: "Pricing" }).getAttribute("href"), "/pricing");
  assert.equal(await accountFooter.getByRole("link", { name: "Log in" }).getAttribute("href"), "/login");
  assert.equal(await accountFooter.getByRole("link", { name: "Create account" }).getAttribute("href"), "/register");
  const jsonLd = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent());
  assert.deepEqual(
    [jsonLd["@type"], jsonLd.name, jsonLd.applicationCategory, jsonLd.operatingSystem],
    ["SoftwareApplication", "SERP SaaS", "BusinessApplication", "Web"],
  );
  assert(!("offers" in jsonLd) && !("aggregateRating" in jsonLd));

  const homeSeo = await page.evaluate(() => ({
    title: document.title,
    description: document.querySelector('meta[name="description"]')?.content,
    canonical: document.querySelector('link[rel="canonical"]')?.href,
    ogTitle: document.querySelector('meta[property="og:title"]')?.content,
    ogDescription: document.querySelector('meta[property="og:description"]')?.content,
    ogUrl: document.querySelector('meta[property="og:url"]')?.content,
  }));
  assert.equal(homeSeo.title, "Google Rank Tracker for Desktop & Mobile | SERP SaaS");
  assert(homeSeo.description?.includes("Desktop and Mobile"));
  assert.equal(homeSeo.canonical, `${base}/`);
  assert.equal(homeSeo.ogTitle, homeSeo.title);
  assert.equal(homeSeo.ogUrl, base);

  await page.getByRole("link", { name: "Start Free", exact: true }).first().click();
  await page.waitForURL(`${base}/register`);
  await page.getByRole("heading", { level: 1, name: "Create your account" }).waitFor();
  await assertAuthPresentation(page);
  await page.goto(`${base}/`);
  await page.getByRole("link", { name: "Log in", exact: true }).first().click();
  await page.waitForURL(`${base}/login`);
  await page.getByRole("heading", { level: 1, name: "Log in" }).waitFor();
  await assertAuthPresentation(page);
  await page.goto(`${base}/`);
  const plansResponse = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/billing/plans"),
  );
  await page.getByRole("link", { name: "View Pricing", exact: true }).first().click();
  await page.waitForURL(`${base}/pricing`);
  const response = await plansResponse;
  assert.equal(response.status(), 200);
  const plans = await response.json();
  assert.equal(plans.length, 6);
  assert.deepEqual(
    Object.fromEntries(
      plans.map((plan) => [
        plan.code,
        [
          plan.price_monthly_minor_units,
          plan.max_projects,
          plan.max_keywords,
          plan.monthly_keyword_checks,
          plan.scheduled_checks_enabled,
          plan.max_scheduled_frequency,
        ],
      ]),
    ),
    expectedPlans,
  );
  await page.getByRole("region", { name: "Mobile Pro" }).waitFor();
  assert.equal(await page.getByRole("region", { name: /^(Desktop|Mobile) (Free|Starter|Pro)$/ }).count(), 6);
  for (const plan of plans) {
    const card = page.getByRole("region", { name: plan.name });
    const text = await card.textContent();
    const decimals = new Intl.NumberFormat("en-US", { style: "currency", currency: plan.currency }).resolvedOptions().maximumFractionDigits;
    const scale = 10 ** decimals;
    const price = new Intl.NumberFormat(plan.currency === "VND" ? "vi-VN" : "en-US", {
      style: "currency", currency: plan.currency,
      minimumFractionDigits: plan.price_monthly_minor_units % scale ? decimals : 0,
      maximumFractionDigits: decimals,
    }).format(plan.price_monthly_minor_units / scale);
    assert(text.includes(price), `${plan.code}: rendered price differs from API`);
    assert(text.includes(plan.max_keywords.toLocaleString("en-US")), `${plan.code}: keyword limit missing`);
    assert(text.includes(plan.monthly_keyword_checks.toLocaleString("en-US")), `${plan.code}: usage limit missing`);
  }
  assert.equal(await page.getByRole("link", { name: "Start Free", exact: true }).count(), 3);
  assert.equal(await page.getByRole("link", { name: "Request Activation", exact: true }).count(), 4);
  assert.equal(await page.getByRole("link", { name: "Request Activation", exact: true }).first().getAttribute("href"), "/register");
  const pricingText = await page.locator("main").textContent();
  for (const forbidden of ["Buy Now", "Checkout", "Subscribe", "Stripe", "PayPal", "crypto"])
    assert(!pricingText.toLowerCase().includes(forbidden.toLowerCase()), `Forbidden payment wording: ${forbidden}`);
  assert.equal(await page.locator(".manual-payment-note, .pricing-manual").count(), 0);

  const pricingSeo = await page.evaluate(() => ({
    title: document.title,
    description: document.querySelector('meta[name="description"]')?.content,
    canonical: document.querySelector('link[rel="canonical"]')?.href,
    ogTitle: document.querySelector('meta[property="og:title"]')?.content,
    ogUrl: document.querySelector('meta[property="og:url"]')?.content,
  }));
  assert(pricingSeo.title.startsWith("Pricing"));
  assert(pricingSeo.description?.includes("Desktop and Mobile"));
  assert.equal(pricingSeo.canonical, `${base}/pricing`);
  assert.equal(pricingSeo.ogTitle, pricingSeo.title);
  assert.equal(pricingSeo.ogUrl, `${base}/pricing`);
  await page.getByRole("link", { name: "Request Activation", exact: true }).first().click();
  await page.waitForURL(`${base}/register`);
  await page.getByRole("heading", { level: 1, name: "Create your account" }).waitFor();

  const robots = await fetch(`${base}/robots.txt`);
  const robotsText = await robots.text();
  assert(robots.ok && robotsText.includes("Disallow: /app") && robotsText.includes("Disallow: /admin"));
  assert(robotsText.includes(`Sitemap: ${base}/sitemap.xml`));
  const sitemap = await fetch(`${base}/sitemap.xml`);
  const sitemapText = await sitemap.text();
  assert(sitemap.ok);
  for (const path of ["/", "/pricing", "/login", "/register"])
    assert(sitemapText.includes(`<loc>${base}${path}</loc>`));
  for (const path of ["/app", "/admin", "/settings"])
    assert(!sitemapText.includes(`<loc>${base}${path}`));

  const widths = [375, 768, 1024, 1280, 1440];
  let responsiveViews = 0;
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ["/", "/pricing"]) {
      await page.goto(`${base}${route}`);
      await page.locator("main h1").waitFor();
      if (route === "/pricing") await page.getByRole("region", { name: "Mobile Pro" }).waitFor();
      assert(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        `${route} overflows at ${width}px`,
      );
      assert(
        await page.locator("main a").evaluateAll((links) =>
          links.every((link) => {
            const box = link.getBoundingClientRect();
            return box.width > 0 && box.left >= 0 && box.right <= innerWidth + 1;
          }),
        ),
        `${route} has a clipped or hidden CTA at ${width}px`,
      );
      if (route === "/" && width === 375) {
        const primaryCta = await page
          .getByRole("link", { name: "Start Free", exact: true })
          .first()
          .boundingBox();
        assert(
          primaryCta && primaryCta.y + primaryCta.height <= 900,
          "Mobile Hero CTA is not above the fold",
        );
      }
      await page.screenshot({
        path: `${screenshots}/${route === "/" ? "home" : "pricing"}-${width}.png`,
        fullPage: true,
      });
      responsiveViews += 1;
    }
    if (width <= 760) {
      await page.getByRole("button", { name: "Open public navigation" }).click();
      const drawer = page.getByRole("dialog");
      await drawer.waitFor();
      assert.equal(await drawer.getByRole("link", { name: "Pricing", exact: true }).getAttribute("aria-current"), "page");
      for (let index = 0; index < 12; index += 1) {
        await page.keyboard.press("Tab");
        assert(await drawer.evaluate((element) => element.contains(document.activeElement)), "Focus escaped public drawer");
      }
      if (width === 375) await page.screenshot({ path: `${screenshots}/navigation-375.png` });
      await page.keyboard.press("Escape");
      assert.equal(await drawer.count(), 0);
      assert(await page.getByRole("button", { name: "Open public navigation" }).evaluate((element) => element === document.activeElement));
      assert.notEqual(await page.evaluate(() => getComputedStyle(document.body).overflow), "hidden");
    } else {
      assert.equal(await page.getByRole("button", { name: "Open public navigation" }).isVisible(), false);
    }
    if (process.env.SCREENSHOT_DIR && [375, 768, 1024, 1440].includes(width)) {
      for (const route of ["/login", "/register"]) {
        await page.goto(`${base}${route}`);
        await page.locator("main h1").waitFor();
        await assertAuthPresentation(page);
        assert(
          await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
          `${route} overflows at ${width}px`,
        );
        await page.screenshot({
          path: `${screenshots}/${route.slice(1)}-${width}.png`,
          fullPage: true,
        });
      }
    }
  }

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${base}/`);
  const focusLink = page.getByRole("link", { name: "View Pricing", exact: true }).first();
  await focusLink.focus();
  const focusStyle = await focusLink.evaluate((element) => getComputedStyle(element).outlineStyle);
  assert.notEqual(focusStyle, "none");
  const headingLevels = await page.locator("main h1, main h2, main h3").evaluateAll((headings) =>
    headings.map((heading) => Number(heading.tagName.slice(1))),
  );
  assert.equal(headingLevels[0], 1);
  assert(headingLevels.every((level, index) => index === 0 || level <= headingLevels[index - 1] + 1));
  const colors = await page.locator(".public-hero-copy .public-lead").evaluate((element) => {
    const style = getComputedStyle(element);
    let ancestor = element.parentElement;
    let background = "rgba(0, 0, 0, 0)";
    while (ancestor && background === "rgba(0, 0, 0, 0)") {
      background = getComputedStyle(ancestor).backgroundColor;
      ancestor = ancestor.parentElement;
    }
    return [style.color, background];
  });
  assert(contrastRatio(colors[0], colors[1]) >= 4.5, "Hero body-text contrast is below 4.5:1");

  const authContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const authPage = await authContext.newPage();
  await authPage.goto(`${base}/register`);
  assert.equal(await authPage.locator(".app-sidebar").count(), 0);
  const email = `public-${randomUUID()}@example.com`;
  const password = "M65B-browser-safe-password-123!";
  await authPage.getByLabel("Email", { exact: true }).fill(email);
  await authPage.getByLabel("Password", { exact: true }).fill(password);
  await authPage.getByLabel("Confirm Password", { exact: true }).fill(password);
  await authPage.getByRole("checkbox").check();
  await authPage.getByRole("button", { name: "Create Account", exact: true }).click();
  await authPage.waitForURL(`${base}/app`);
  await authPage.goto(`${base}/pricing`);
  await authPage.getByRole("region", { name: "Mobile Pro" }).waitFor();
  await authPage.getByRole("link", { name: "Open App", exact: true }).first().waitFor();
  assert.equal(await authPage.getByRole("link", { name: "Request Activation", exact: true }).first().getAttribute("href"), "/settings/billing");
  assert.equal(await authPage.getByRole("link", { name: "Open App", exact: true }).first().getAttribute("href"), "/app");
  await authContext.close();

  const customerApiPaths = apiResponses
    .map((item) => item.path)
    .filter((path) => /projects|tracked-sites|rankings|billing\/me/.test(path));
  assert.deepEqual(customerApiPaths, [], "Logged-out public pages requested customer data");
  assert.deepEqual(exceptions, []);
  assert.deepEqual(failures, []);
  process.stdout.write(
    `${JSON.stringify({
      public_browser: "passed",
      widths,
      responsiveViews,
      plans: plans.length,
      checks: [
        "home_content",
        "public_shell",
        "authoritative_plan_catalog",
        "logged_out_and_authenticated_ctas",
        "manual_activation_wording",
        "metadata",
        "structured_data",
        "robots",
        "sitemap",
        "no_customer_data_leak",
        "no_horizontal_overflow",
        "mobile_drawer_focus",
        "visible_focus",
        "heading_hierarchy",
        "contrast",
      ],
      browserExceptions: exceptions,
      networkFailures: failures,
      harmlessEvents: harmless,
      screenshots,
    })}\n`,
  );
} finally {
  await browser.close();
}
