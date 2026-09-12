// Deterministic real-browser Milestone 4 rank-check and history journey.
import assert from "node:assert/strict";
import { randomBytes, randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";

const modulePath = process.env.PLAYWRIGHT_MODULE;
if (!modulePath) throw new Error("Set PLAYWRIGHT_MODULE");
const { chromium } = await import(pathToFileURL(modulePath).href);
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
  const responses = [];
  page.on("pageerror", (error) => exceptions.push(error.message));
  page.on("requestfailed", (request) => {
    const reason = request.failure()?.errorText;
    const path = new URL(request.url()).pathname;
    if (
      reason === "net::ERR_ABORTED" &&
      request.method() === "GET" &&
      path.startsWith("/app/")
    )
      return;
    failures.push({
      path,
      method: request.method(),
      reason,
    });
  });
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (path.startsWith("/api/v1/"))
      responses.push({ path, status: response.status() });
  });
  const base = process.env.FRONTEND_URL ?? "http://localhost:3000";
  const email = `milestone-4-${randomUUID()}@example.com`;
  const password = randomBytes(24).toString("base64url");

  await page.goto(`${base}/signup`);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password", { exact: true }).fill(password);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create Account" }).click();
  await page.waitForURL(`${base}/app`);

  await page
    .getByRole("link", { name: "Tracked Sites", exact: true })
    .first()
    .click();
  await page.getByRole("link", { name: "Add Tracked Site" }).click();
  await page.getByLabel("Site Name").fill("Browser Owned Site");
  await page.getByLabel("Primary Domain").fill("tracked.example");
  await page
    .getByLabel("Previous / Alias Domains")
    .fill("www.secondary.example");
  await page.getByRole("button", { name: "Create Site" }).click();
  await page.waitForURL(/\/app\/tracked-sites\/[0-9a-f-]+$/);

  await page
    .getByRole("link", { name: "Projects", exact: true })
    .first()
    .click();
  await page
    .getByRole("link", { name: "Create Project", exact: true })
    .first()
    .click();
  assert.equal(await page.getByLabel(/provider/i).count(), 0);
  await page.getByLabel("Project name").fill("Browser Rankings");
  await page.getByLabel("Country", { exact: true }).fill("vn");
  await page.getByLabel("Language", { exact: true }).fill("vi");
  await page.getByLabel("Keywords, one per line").fill("browser rank query");
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.waitForURL(/\/app\/projects\/[0-9a-f-]+$/);
  await page.getByText("browser rank query", { exact: true }).waitFor();

  await page.getByRole("button", { name: "Check Rankings" }).click();
  await page.getByRole("button", { name: "Checking Rankings…" }).waitFor();
  await page.getByText("Browser Owned Site #2", { exact: true }).waitFor();
  await page.getByRole("button", { name: "History" }).click();
  await page.getByRole("region", { name: "Ranking history" }).waitFor();
  await page.getByRole("button", { name: "View results" }).click();
  const detail = page.getByRole("region", { name: "Rank Check detail" });
  await detail.getByText("Top 10 Organic Results").waitFor();
  await detail.getByText("Tracked · Browser Owned Site").waitFor();
  await detail.getByText("competitor.example", { exact: true }).waitFor();
  await detail.getByText(/Data source: Test Provider/).waitFor();

  await page.reload();
  await page.getByText("Browser Owned Site #2", { exact: true }).waitFor();
  await page.getByRole("button", { name: "History" }).click();
  await page.getByRole("region", { name: "Ranking history" }).waitFor();

  assert.deepEqual(exceptions, []);
  assert.deepEqual(failures, []);
  assert(
    responses.every(
      (response) =>
        response.status < 400 ||
        (response.path.endsWith("/auth/refresh") && response.status === 401),
    ),
  );
  process.stdout.write(
    `${JSON.stringify({
      milestone_4_1_browser: "passed",
      provider: "fake",
      realProviderCredits: 0,
      checks: [
        "signup",
        "tracked_site_aliases",
        "project_keyword",
        "no_provider_selector",
        "manual_project_check",
        "loading_state",
        "latest_position",
        "history",
        "rank_check_detail",
        "top_n_results",
        "tracked_label",
        "provider_metadata",
        "reload_persistence",
      ],
      browserExceptions: 0,
      networkFailures: 0,
    })}\n`,
  );
} finally {
  await browser.close();
}
