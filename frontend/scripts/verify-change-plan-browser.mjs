// Local production standalone QA. Every API response is synthetic; mutations abort.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
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
const base = process.env.QA_BASE_URL ?? "http://127.0.0.1:3014";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const origin = new URL(base).origin;
const directory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7j",
);
await mkdir(directory, { recursive: true });
const plans = ["desktop", "mobile"].flatMap((device, di) =>
  ["free", "starter", "pro"].map((tier, ti) => ({
    id: `${device}-${tier}-qa`,
    code: `${device}_${tier}`,
    name: `${device === "desktop" ? "Desktop" : "Mobile"} ${tier[0].toUpperCase()}${tier.slice(1)}`,
    device_scope: device,
    price_monthly_minor_units: ti ? 2875 + ti * 1000 + di * 100 : 0,
    currency: di ? "EUR" : "USD",
    max_projects: 3 + ti,
    max_keywords: 43 + ti * 123,
    monthly_keyword_checks: 1234 + ti * 999,
    scheduled_checks_enabled: ti > 0,
    max_scheduled_frequency: ti === 0 ? "none" : ti === 1 ? "weekly" : "daily",
  })),
);
const user = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "plan-qa@example.test",
  status: "active",
  email_verified: true,
  is_platform_admin: false,
  terms_accepted_at: "2026-10-01T00:00:00Z",
  last_login_at: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};
const results = [],
  gates = [];
const browser = await chromium.launch(
  process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {},
);
const checkAxe = async (page) => {
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  assert.deepEqual(
    report.violations.map(({ id, nodes }) => ({
      id,
      nodes: nodes.map((n) => n.target),
    })),
    [],
  );
};
const noOverflow = async (page) =>
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "Horizontal overflow",
  );
try {
  for (const width of [375, 768, 1024, 1440]) {
    for (const fixture of [
      "free-desktop",
      "paid-desktop",
      "free-mobile",
      "paid-mobile",
      "catalog-failure",
      "empty",
      "subscription-failure",
      "anonymous",
      "unverified",
    ]) {
      const context = await browser.newContext({
        viewport: { width, height: 1000 },
      });
      const requests = [],
        errors = [];
      let catalogFailure = fixture === "catalog-failure";
      let subscriptionFailure = fixture === "subscription-failure";
      const sessionUser = { ...user, email_verified: fixture !== "unverified" };
      const summary = {
        user_id: user.id,
        email: user.email,
        account_status: "active",
        devices: ["desktop", "mobile"].map((device) => {
          const tier = fixture === `paid-${device}` ? "starter" : "free";
          const plan = { ...plans.find((p) => p.code === `${device}_${tier}`) };
          delete plan.id;
          return {
            device_scope: device,
            subscription_id: `${device}-sub`,
            plan,
            status: "active",
            period_start: "2026-10-01T00:00:00Z",
            period_end: tier === "free" ? null : "2026-11-01T00:00:00Z",
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
      await context.route("**/*", async (route) => {
        const request = route.request(),
          url = new URL(request.url());
        if (!url.pathname.startsWith("/api/v1/")) {
          if (url.origin === origin) return route.continue();
          errors.push(`External request ${url.origin}${url.pathname}`);
          return route.abort();
        }
        const headers = {
          "Access-Control-Allow-Origin": origin,
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
        };
        if (request.method() === "OPTIONS")
          return route.fulfill({ status: 204, headers });
        requests.push({ method: request.method(), path: url.pathname });
        let body,
          status = 200;
        if (url.pathname === "/api/v1/auth/refresh") {
          status = fixture === "anonymous" ? 401 : 200;
          body =
            status === 401
              ? { detail: "Anonymous" }
              : {
                  access_token: "synthetic-qa-token",
                  token_type: "bearer",
                  expires_in: 3600,
                  email_verification_required: true,
                  user: sessionUser,
                };
        } else if (request.method() !== "GET") {
          errors.push(`Mutation ${request.method()} ${url.pathname}`);
          return route.abort();
        } else if (url.pathname === "/api/v1/billing/plans") {
          status = catalogFailure ? 503 : 200;
          body = fixture === "empty" ? [] : plans;
        } else if (url.pathname === "/api/v1/billing/me") {
          status = subscriptionFailure ? 503 : 200;
          body = summary;
        } else if (url.pathname === "/api/v1/auth/email-verification")
          body = {
            verified: false,
            delivery_status: "sent",
            retry_after_seconds: 0,
            expires_at: null,
          };
        else {
          errors.push(`Unexpected API ${url.pathname}`);
          return route.abort();
        }
        return route.fulfill({
          status,
          headers,
          contentType: "application/json",
          body: JSON.stringify(body),
        });
      });
      const page = await context.newPage();
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (
          message.type() === "error" &&
          /hydration|Minified React error/i.test(message.text())
        )
          errors.push(message.text());
      });
      const response = await page.goto(`${base}/app/change-plan`, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      if (["anonymous", "unverified"].includes(fixture)) {
        await page.waitForURL(
          `${base}/${fixture === "anonymous" ? "login" : "verify-email"}`,
        );
        assert(!requests.some((r) => r.path.startsWith("/api/v1/billing/")));
        assert.deepEqual(errors, []);
        gates.push({
          width,
          fixture,
          finalPath: new URL(page.url()).pathname,
          billingRequests: 0,
          errors,
        });
        await context.close();
        continue;
      }
      await page
        .getByRole("heading", { level: 1, name: "Change Plan", exact: true })
        .waitFor();
      assert.equal(await page.locator("h1").count(), 1);
      if (catalogFailure) {
        const alert = page
          .getByRole("alert")
          .filter({ hasText: "Unable to load plans." });
        await alert.waitFor();
        assert.equal(await page.locator("[data-plan-code]").count(), 0);
        await checkAxe(page);
        await noOverflow(page);
        catalogFailure = false;
        await alert.getByRole("button", { name: "Retry", exact: true }).click();
      }
      if (subscriptionFailure) {
        const alert = page
          .getByRole("alert")
          .filter({ hasText: "Unable to load your current subscription." });
        await alert.waitFor();
        assert.equal(
          await page
            .getByRole("button", { name: "Current Plan", exact: true })
            .count(),
          0,
        );
        await checkAxe(page);
        await noOverflow(page);
        subscriptionFailure = false;
        await alert.getByRole("button", { name: "Retry", exact: true }).click();
      }
      if (width > 800) {
        const link = page
          .getByRole("navigation", { name: "Customer navigation" })
          .getByRole("link", { name: "Change Plan", exact: true });
        assert.equal(await link.getAttribute("aria-current"), "page");
      } else {
        await page.getByRole("button", { name: "Open navigation" }).click();
        const drawer = page.getByRole("dialog", {
          name: "SERP SaaS",
          exact: true,
        });
        assert.equal(
          await drawer
            .getByRole("link", { name: "Change Plan", exact: true })
            .getAttribute("aria-current"),
          "page",
        );
        await page.keyboard.press("Escape");
      }
      const scopeChecks = [];
      for (const device of ["desktop", "mobile"]) {
        const label = device === "desktop" ? "Desktop" : "Mobile";
        await page.getByRole("tab", { name: label, exact: true }).click();
        if (fixture === "empty") {
          await page
            .getByRole("heading", {
              name: "No plans are currently available.",
              exact: true,
            })
            .waitFor();
          assert.equal(await page.locator("[data-plan-code]").count(), 0);
        } else {
          await page.locator(`[data-plan-code="${device}_pro"]`).waitFor();
          const current = summary.devices.find(
            (d) => d.device_scope === device,
          );
          const currentCard = page.locator(
            `[data-plan-code="${current.plan.code}"]`,
          );
          assert(
            await currentCard
              .getByRole("button", { name: "Current Plan", exact: true })
              .isDisabled(),
          );
          await currentCard
            .locator(".ui-badge")
            .filter({ hasText: "Current Plan" })
            .waitFor();
          assert.equal(await page.locator("[data-plan-code]").count(), 3);
          for (const plan of plans.filter((p) => p.device_scope === device)) {
            const card = page.locator(`[data-plan-code="${plan.code}"]`);
            assert.equal(await card.locator("h3").textContent(), plan.name);
            assert.equal(
              await card.locator(".change-plan-price strong").textContent(),
              new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: plan.currency,
                minimumFractionDigits:
                  plan.price_monthly_minor_units % 100 ? 2 : 0,
                maximumFractionDigits: 2,
              }).format(plan.price_monthly_minor_units / 100),
            );
            assert.deepEqual(await card.locator("dd").allTextContents(), [
              plan.max_projects.toLocaleString("en-US"),
              plan.max_keywords.toLocaleString("en-US"),
              plan.monthly_keyword_checks.toLocaleString("en-US"),
              plan.scheduled_checks_enabled
                ? `Up to ${plan.max_scheduled_frequency}`
                : "Not included",
              label,
            ]);
          }
          const boxes = await page
            .locator("[data-plan-code]")
            .evaluateAll((cards) =>
              cards.map((c) => {
                const r = c.getBoundingClientRect();
                return { x: r.x, y: r.y, height: r.height };
              }),
            );
          if (width === 375)
            assert(
              boxes.every((b) => b.x === boxes[0].x) && boxes[1].y > boxes[0].y,
            );
          if (width === 1440)
            assert(
              boxes.every(
                (b) => b.y === boxes[0].y && b.height === boxes[0].height,
              ),
            );
          if (current.period_end)
            assert(
              (
                await page.locator(".change-plan-summary").textContent()
              ).includes("Nov 1, 2026 (UTC)"),
            );
          else
            assert.equal(
              await page.locator(".change-plan-summary time").count(),
              0,
            );
          await page.screenshot({
            path: resolve(directory, `${fixture}-${device}-${width}.png`),
            fullPage: true,
          });
          const trigger = page
            .locator(`[data-plan-code="${device}_pro"]`)
            .getByRole("button", { name: "Select", exact: true });
          await trigger.focus();
          const before = requests.length;
          await page.keyboard.press("Enter");
          const modal = page.getByRole("dialog", {
            name: "Plan upgrade coming soon",
          });
          await modal.waitFor();
          assert(
            (await modal.textContent()).includes(
              "Your current subscription has not been changed.",
            ),
          );
          await modal
            .getByRole("button", { name: "Close", exact: true })
            .focus();
          await page.keyboard.press("Tab");
          assert(
            await modal
              .getByRole("button", { name: "Close dialog", exact: true })
              .evaluate((el) => el === document.activeElement),
          );
          await page.keyboard.press("Shift+Tab");
          assert(
            await modal
              .getByRole("button", { name: "Close", exact: true })
              .evaluate((el) => el === document.activeElement),
          );
          await checkAxe(page);
          await noOverflow(page);
          await page.keyboard.press("Escape");
          await modal.waitFor({ state: "hidden" });
          assert(await trigger.evaluate((el) => el === document.activeElement));
          await trigger.click();
          await modal
            .getByRole("button", { name: "Close", exact: true })
            .click();
          assert(await trigger.evaluate((el) => el === document.activeElement));
          assert.equal(
            requests.length,
            before,
            "Select must cause zero additional API requests",
          );
          assert(
            await currentCard
              .getByRole("button", { name: "Current Plan", exact: true })
              .isDisabled(),
          );
        }
        await checkAxe(page);
        await noOverflow(page);
        scopeChecks.push({
          device,
          cards: fixture === "empty" ? 0 : 3,
          axeViolations: 0,
          overflow: false,
          selectApiRequests: 0,
        });
      }
      await page.getByRole("tab", { name: "Mobile", exact: true }).focus();
      await page.keyboard.press("ArrowLeft");
      assert.equal(
        await page
          .getByRole("tab", { name: "Desktop", exact: true })
          .getAttribute("aria-selected"),
        "true",
      );
      if (fixture !== "empty") {
        await page.reload({ waitUntil: "networkidle" });
        const code = summary.devices[0].plan.code;
        assert(
          await page
            .locator(`[data-plan-code="${code}"]`)
            .getByRole("button", { name: "Current Plan", exact: true })
            .isDisabled(),
        );
      }
      assert(
        !requests.some(
          (r) => r.path.includes("/billing/") && r.method !== "GET",
        ),
      );
      assert.deepEqual(errors, []);
      results.push({
        width,
        fixture,
        scopeChecks,
        requests,
        billingMutations: 0,
        errors,
      });
      await context.close();
      console.log(`Passed ${fixture} at ${width}px`);
    }
  }
  await writeFile(
    resolve(directory, "browser-qa.json"),
    JSON.stringify(
      {
        apiMode:
          "Synthetic intercepted API; local production standalone; no real accounts or backend changes",
        results,
        gates,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `Change Plan QA passed: ${results.length} responsive cases, ${gates.length} auth cases; zero mutations, axe violations, overflow or browser errors.`,
  );
} finally {
  await browser.close();
}
