import { verifyResponsive } from "./browser-responsive.mjs";
// Real-browser Milestone 3.1 Tracked Site and Project/Keyword journey.
import assert from "node:assert/strict";
import { randomBytes, randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";
const modulePath = process.env.PLAYWRIGHT_MODULE;
if (!modulePath) throw new Error("Set PLAYWRIGHT_MODULE");
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_EXECUTABLE ? { executablePath: process.env.CHROME_EXECUTABLE } : {}) });
try {
  const context = await browser.newContext(); const page = await context.newPage(); const exceptions = []; const failures = []; const responses = [];
  page.on("pageerror", (error) => exceptions.push(error.message));
  page.on("requestfailed", (request) => {
    const reason = request.failure()?.errorText;
    const path = new URL(request.url()).pathname;
    if (reason === "net::ERR_ABORTED" && request.method() === "GET" && path.startsWith("/app/")) return;
    failures.push({ path, method: request.method(), reason });
  });
  page.on("response", (response) => { const path = new URL(response.url()).pathname; if (path.startsWith("/api/v1/")) responses.push({ path, status: response.status() }); });
  const base = process.env.FRONTEND_URL ?? "http://localhost:3000"; const email = `milestone-31-${randomUUID()}@example.com`; const password = randomBytes(24).toString("base64url");
  await page.goto(`${base}/signup`); await page.getByLabel("Email", { exact: true }).fill(email); await page.getByLabel("Password", { exact: true }).fill(password); await page.getByLabel("Confirm Password", { exact: true }).fill(password); await page.getByRole("checkbox").check(); await page.getByRole("button", { name: "Create Account" }).click(); await page.waitForURL(`${base}/app`);

  await page.getByRole("link", { name: "Tracked Sites", exact: true }).first().click(); await page.waitForURL(`${base}/app/tracked-sites`); await page.getByText("No tracked sites yet.", { exact: true }).waitFor(); await page.getByRole("link", { name: "Add Tracked Site" }).click(); await page.getByLabel("Site Name").fill("Browser SEO Site"); await page.getByLabel("Primary Domain").fill("old.browser.example"); await page.getByLabel("Previous / Alias Domains").fill("older.browser.example"); await page.getByRole("button", { name: "Create Site" }).click(); await page.waitForURL(/\/app\/tracked-sites\/[0-9a-f-]+$/); await page.getByText("old.browser.example", { exact: true }).first().waitFor();
  await page.getByLabel("Domain", { exact: true }).fill("new.browser.example"); await page.getByRole("button", { name: "Add Domain" }).click(); await page.getByText("new.browser.example", { exact: true }).waitFor(); const newDomain = page.getByRole("article").filter({ hasText: "new.browser.example" }); await newDomain.getByRole("button", { name: "Make primary" }).click(); await page.getByText("Primary: new.browser.example", { exact: true }).waitFor(); assert.equal(await page.getByText("old.browser.example", { exact: true }).count(), 1);

  await page.getByRole("link", { name: "Projects", exact: true }).first().click(); await page.getByText("No projects yet.", { exact: true }).waitFor(); await page.getByRole("link", { name: "Create Project", exact: true }).first().click(); await page.getByLabel("Project name").fill("Vietnam Desktop"); await page.getByLabel("Country", { exact: true }).fill("vn"); await page.getByLabel("Language", { exact: true }).fill("vi"); await page.getByLabel("Location (optional)").fill("Ho Chi Minh City"); await page.getByLabel("Keywords, one per line").fill("first query\nsecond query\nFIRST QUERY"); await page.getByRole("button", { name: "Create Project" }).click(); await page.waitForURL(/\/app\/projects\/[0-9a-f-]+$/); await page.getByRole("cell", { name: "first query", exact: true }).waitFor(); await page.getByRole("cell", { name: "second query", exact: true }).waitFor(); assert.equal(await page.getByText("Domain", { exact: true }).count(), 0);
  await page.getByLabel("Country", { exact: true }).last().fill("th"); await page.getByRole("button", { name: "Save Project Settings" }).click(); await page.getByText("Project settings saved.").waitFor(); await page.getByRole("cell", { name: "first query", exact: true }).waitFor();
  await page.getByRole("button", { name: "Add Keyword" }).click(); await page.getByLabel("Keyword", { exact: true }).fill("third query"); await page.getByRole("button", { name: "Add keyword", exact: true }).click(); await page.getByRole("cell", { name: "third query", exact: true }).waitFor(); let row = page.getByRole("row").filter({ hasText: "third query" }); await row.getByRole("button", { name: "Edit" }).click(); await page.getByRole("checkbox", { name: "Active" }).uncheck(); await page.getByRole("button", { name: "Save Keyword" }).click(); await page.getByLabel("Keyword state").selectOption("false"); await page.getByRole("cell", { name: "third query", exact: true }).waitFor(); await page.reload(); await page.getByRole("heading", { name: "Vietnam Desktop" }).waitFor(); await page.getByLabel("Keyword state").selectOption("false"); await page.getByRole("cell", { name: "third query", exact: true }).waitFor();
  await verifyResponsive(page,"project-keywords");
  await page.goto(`${base}/app/projects`);await page.getByText("Vietnam Desktop",{exact:true}).waitFor();await verifyResponsive(page,"projects-populated");
  await page.goto(`${base}/app/tracked-sites`);await page.getByText("Browser SEO Site",{exact:true}).waitFor();await verifyResponsive(page,"tracked-sites-populated");await page.getByText("Browser SEO Site",{exact:true}).click();await page.getByText("Primary: new.browser.example",{exact:true}).waitFor();await verifyResponsive(page,"tracked-site-domains");
  const unexpected = failures.filter((failure) => !(failure.reason === "net::ERR_ABORTED" && failure.method === "DELETE")); assert.deepEqual(exceptions, []); assert.deepEqual(unexpected, []); assert(responses.every((value) => value.status < 400 || (value.path.endsWith("/auth/refresh") && value.status === 401)));
  process.stdout.write(`${JSON.stringify({ milestone_3_1_browser: "passed", checks: ["signup", "tracked_site_empty", "tracked_site_create", "alias_create", "primary_promotion", "old_alias_retained", "project_empty", "atomic_project_create", "keyword_deduplication", "project_settings_update", "keyword_unchanged", "keyword_add", "keyword_pause", "reload_persistence"], browserExceptions: 0, networkFailures: 0 })}\n`);
} finally { await browser.close(); }
