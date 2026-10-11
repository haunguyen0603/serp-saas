// Public Pricing uses the real local API. Protected views use synthetic sessions
// and the same real catalog; no account, subscription or payment is changed.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const { chromium } = await import(
  process.env.QA_TOOLS_DIRECTORY
    ? pathToFileURL(
        resolve(process.env.QA_TOOLS_DIRECTORY, "playwright/index.mjs"),
      ).href
    : "playwright"
);
const base = process.env.QA_BASE_URL ?? "http://localhost:3000";
const api = process.env.QA_API_URL ?? "http://localhost:8000";
for (const url of [base, api])
  assert(["localhost", "127.0.0.1"].includes(new URL(url).hostname));
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/vnd-pricing",
);
await mkdir(directory, { recursive: true });
const response = await fetch(`${api}/api/v1/billing/plans`);
assert.equal(response.status, 200);
const plans = await response.json();
const expected = {
  desktop_free: 0,
  desktop_starter: 495330,
  desktop_pro: 3363030,
  mobile_free: 0,
  mobile_starter: 1016730,
  mobile_pro: 5187930,
};
assert.equal(plans.length, 6);
for (const plan of plans) {
  assert.equal(plan.currency, "VND");
  assert.equal(plan.price_monthly_minor_units, expected[plan.code]);
}
const user = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "vnd-qa@example.test",
  status: "active",
  email_verified: true,
  is_platform_admin: true,
  terms_accepted_at: "2026-10-01T00:00:00Z",
  last_login_at: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};
const summary = {
  user_id: user.id,
  email: user.email,
  account_status: "active",
  devices: ["desktop", "mobile"].map((device) => {
    const plan = { ...plans.find((p) => p.code === `${device}_starter`) };
    if (device === "desktop")
      Object.assign(plan, { currency: "USD", price_monthly_minor_units: 1900 });
    return {
      device_scope: device,
      subscription_id: `${device}-qa`,
      plan,
      status: "active",
      period_start: "2026-10-01T00:00:00Z",
      period_end: "2026-11-01T00:00:00Z",
      projects_used: 0,
      keywords_used: 0,
      over_limit: false,
      usage: {
        id: device,
        period_start: "2026-10-01T00:00:00Z",
        period_end: "2026-11-01T00:00:00Z",
        limit: plan.monthly_keyword_checks,
        used: 0,
        reserved: 0,
        remaining: plan.monthly_keyword_checks,
        adjustment: 0,
      },
    };
  }),
};
const browser = await chromium.launch(
  process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {},
);
const checks = [],
  errors = [];
const normalized = (text) => text.replaceAll("\u00a0", " ");
const noOverflow = async (page) =>
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    `Horizontal overflow at ${page.url()}`,
  );
try {
  for (const width of [375, 768, 1024, 1440]) {
    for (const path of [
      "/pricing",
      "/vi/bang-gia",
      "/app/change-plan",
      "/settings/billing",
      "/admin/plans",
    ]) {
      const context = await browser.newContext({
        viewport: { width, height: 1000 },
      });
      const protectedView = !["/pricing", "/vi/bang-gia"].includes(path);
      if (protectedView)
        await context.route("**/api/v1/**", async (route) => {
          const request = route.request(),
            url = new URL(request.url());
          const headers = {
            "Access-Control-Allow-Origin": new URL(base).origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          };
          if (request.method() === "OPTIONS")
            return route.fulfill({ status: 204, headers });
          let body;
          if (url.pathname === "/api/v1/auth/refresh")
            body = {
              access_token: "synthetic-vnd-qa-token",
              token_type: "bearer",
              expires_in: 3600,
              email_verification_required: true,
              user,
            };
          else if (request.method() !== "GET") {
            errors.push(
              `Unexpected mutation ${request.method()} ${url.pathname}`,
            );
            return route.abort();
          } else if (url.pathname === "/api/v1/billing/plans") body = plans;
          else if (url.pathname === "/api/v1/billing/me") body = summary;
          else if (url.pathname === "/api/v1/admin/plans")
            body = plans.map((plan) => ({
              ...plan,
              updated_at: "2026-10-11T00:00:00Z",
            }));
          else if (url.pathname === "/api/v1/admin/plans/history") body = [];
          else {
            errors.push(`Unexpected API ${url.pathname}`);
            return route.abort();
          }
          return route.fulfill({
            status: 200,
            headers,
            contentType: "application/json",
            body: JSON.stringify(body),
          });
        });
      const page = await context.newPage();
      page.on("pageerror", (error) => errors.push(error.message));
      assert.equal(
        (
          await page.goto(`${base}${path}`, { waitUntil: "networkidle" })
        ).status(),
        200,
      );
      if (path === "/pricing" || path === "/vi/bang-gia") {
        await page
          .getByRole("region", { name: "Mobile Pro", exact: true })
          .waitFor();
        for (const [code, price] of [
          ["desktop_starter", "495.330 ₫"],
          ["desktop_pro", "3.363.030 ₫"],
          ["mobile_starter", "1.016.730 ₫"],
          ["mobile_pro", "5.187.930 ₫"],
        ]) {
          const card = page.locator(
            `[data-plan-id="${plans.find((p) => p.code === code).id}"]`,
          );
          assert(
            normalized(
              await card.locator(".pricing-price strong").textContent(),
            ).includes(price),
          );
          assert(
            await card
              .locator(".pricing-price")
              .evaluate(
                (element) => element.scrollWidth <= element.clientWidth,
              ),
            `${code}: price overflows its card at ${width}px`,
          );
        }
        for (const device of ["Desktop", "Mobile"]) {
          const cards = ["Free", "Starter", "Pro"].map((tier) =>
            page.getByRole("region", {
              name: `${device} ${tier}`,
              exact: true,
            }),
          );
          const y = await Promise.all(
            cards.map(
              async (card) => (await card.locator("a").last().boundingBox()).y,
            ),
          );
          if (width >= 1024)
            assert(
              Math.max(...y) - Math.min(...y) <= 1,
              "Pricing CTA alignment",
            );
        }
      } else if (path === "/app/change-plan") {
        await page
          .getByRole("region", { name: "Desktop Pro", exact: true })
          .waitFor();
        assert(
          normalized(
            await page
              .getByRole("region", { name: "Desktop Pro", exact: true })
              .textContent(),
          ).includes("3.363.030 ₫"),
        );
        await page.getByRole("tab", { name: "Mobile", exact: true }).click();
        assert(
          normalized(
            await page
              .getByRole("region", { name: "Mobile Pro", exact: true })
              .textContent(),
          ).includes("5.187.930 ₫"),
        );
      } else if (path === "/settings/billing") {
        await page.getByText(/\$19.00/).waitFor();
        assert(
          normalized(await page.locator("main").textContent()).includes(
            "1.016.730 ₫",
          ),
        );
      } else {
        await page.getByRole("form", { name: "Edit Mobile Pro" }).waitFor();
        assert.equal(
          await page
            .getByRole("form", { name: "Edit Mobile Pro" })
            .getByLabel("Monthly price (VND)")
            .inputValue(),
          "5187930",
        );
        assert.equal(
          await page
            .getByRole("form", { name: "Edit Desktop Starter" })
            .getByLabel("Monthly price (VND)")
            .inputValue(),
          "495330",
        );
      }
      await noOverflow(page);
      if ([375, 1440].includes(width))
        await page.screenshot({
          path: resolve(
            directory,
            `${path.replaceAll("/", "-").slice(1)}-${width}.png`,
          ),
          fullPage: true,
        });
      checks.push({
        path,
        width,
        passed: true,
        api: protectedView
          ? "synthetic session; real catalog fixture"
          : "real local API",
      });
      await context.close();
    }
  }
  assert.deepEqual(errors, []);
  await writeFile(
    resolve(directory, "browser.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(
    JSON.stringify({
      passed: true,
      cases: checks.length,
      widths: [375, 768, 1024, 1440],
      errors: errors.length,
    }),
  );
} finally {
  await browser.close();
}
