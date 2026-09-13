// Run with an external Playwright installation; no production browser dependency.
import assert from "node:assert/strict";
import { randomUUID, randomBytes } from "node:crypto";
import { pathToFileURL } from "node:url";

const modulePath = process.env.PLAYWRIGHT_MODULE;
if (!modulePath) throw new Error("Set PLAYWRIGHT_MODULE to the installed playwright/index.mjs path");
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROME_EXECUTABLE ? { executablePath: process.env.CHROME_EXECUTABLE } : {}),
});
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  const exceptions = [];
  const failures = [];
  const responses = [];
  page.on("pageerror", error => exceptions.push(error.message));
  page.on("requestfailed", request => failures.push({ path: new URL(request.url()).pathname, reason: request.failure()?.errorText }));
  page.on("response", response => {
    if (new URL(response.url()).pathname.startsWith("/api/v1/")) {
      responses.push({ path: new URL(response.url()).pathname, status: response.status() });
    }
  });
  const base = process.env.FRONTEND_URL ?? "http://localhost:3000";
  const email = `browser-${randomUUID()}@example.com`;
  const password = randomBytes(24).toString("base64url");
  await page.goto(`${base}/signup`);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password", { exact: true }).fill(password);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create Account" }).click();
  await page.waitForURL(`${base}/app`);
  await page.getByText(email, { exact: true }).waitFor();
  const cookie = (await context.cookies()).find(value => value.name === "serp_refresh_token");
  assert(cookie?.httpOnly && cookie.sameSite === "Lax", "Refresh cookie flags are incorrect");
  assert.equal(await page.evaluate(() => document.cookie.includes("serp_refresh_token")), false);
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  await page.reload();
  await page.getByText(email, { exact: true }).waitFor();
  assert.equal(new URL(page.url()).pathname, "/app");
  await page.goto(`${base}/app/settings`);
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.waitForURL(`${base}/login`);
  await page.waitForLoadState("networkidle");
  assert(!(await context.cookies()).some(value => value.name === "serp_refresh_token"));
  await page.goto(`${base}/app`);
  await page.waitForURL(`${base}/login`);
  assert.equal(await page.getByText(email, { exact: true }).count(), 0);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.waitForURL(`${base}/app`);
  await page.getByText(email, { exact: true }).waitFor();
  await page.goto(`${base}/app/settings`);
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.waitForURL(`${base}/login`);
  await page.waitForLoadState("networkidle");
  for (const path of ["/", "/health"]) {
    await page.goto(`${base}${path}`);
    for (const service of ["API", "Database", "Redis"]) {
      await page.getByLabel(`${service}: connected`, { exact: true }).waitFor();
    }
  }
  assert.deepEqual(exceptions, []);
  assert.deepEqual(failures, []);
  assert(responses.some(value => value.path.endsWith("/register") && value.status === 201));
  assert(responses.some(value => value.path.endsWith("/refresh") && value.status === 200));
  assert(responses.every(value => value.status < 400 || (value.path.endsWith("/refresh") && value.status === 401)), "Unexpected API failure");
  process.stdout.write(JSON.stringify({ browser_authentication: "passed", checks: ["signup", "protected_account", "reload_restoration", "logout", "anonymous_redirect", "login", "cookie_flags", "no_token_storage", "milestone_1_health_pages"], browserExceptions: 0, networkFailures: 0 }) + "\n");
} finally {
  await browser.close();
}
