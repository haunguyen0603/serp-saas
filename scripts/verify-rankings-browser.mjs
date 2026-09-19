import { verifyResponsive } from "./browser-responsive.mjs";
// Deterministic real-browser Milestone 4 rank-check and history journey.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
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
  const batchGets = [];
  page.on("request", (request) => {
    if (request.method() === "GET" && request.url().includes("/rank-check-batches")) batchGets.push(request.url());
  });
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

  const acceptedResponse = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/rank-check-batches"));
  await page.getByRole("button", { name: "Check Rankings" }).click();
  const accepted = await acceptedResponse;
  assert.equal(accepted.status(), 202);
  const batchId = (await accepted.json()).batch_id;
  await page.getByText("Ranking checks queued.", { exact: true }).waitFor();
  await page.getByText("tracked.example #2", { exact: true }).first().waitFor();
  await page.getByRole("progressbar", { name: "Batch progress" }).evaluate((element) => {
    if (element.value !== 100) throw new Error("Batch is not terminal");
  });
  await page.getByText("Keyword check details", { exact: true }).click();
  await page.getByText(/browser rank query: succeeded/).waitFor();
  assert(batchGets.filter((url) => new URL(url).pathname.endsWith(`/rank-check-batches/${batchId}`)).length >= 2, "Expected progress polling before completion");
  await page.waitForTimeout(2200);
  const settledCount = batchGets.length;
  await page.waitForTimeout(2500);
  assert.equal(batchGets.length, settledCount, "Batch polling continued after terminal state");
  const keywordTrigger = page.getByRole("button", { name: "browser rank query" });
  assert.equal(await keywordTrigger.getAttribute("aria-expanded"), "false");
  assert.equal(await page.getByRole("region", { name: "Ranking history" }).count(), 0);
  await keywordTrigger.scrollIntoViewIfNeeded();
  const scrollBeforeHistory = await page.evaluate(() => scrollY);
  await keywordTrigger.click();
  assert.equal(await keywordTrigger.getAttribute("aria-expanded"), "true");
  assert.equal(await page.evaluate(() => scrollY), scrollBeforeHistory);
  let history = page.getByRole("region", { name: "Ranking history" });
  await history.waitFor();
  assert.equal(await page.getByRole("button", { name: "History" }).count(), 0);
  await history.getByText("Ranking history · browser rank query", { exact: true }).waitFor();
  await verifyResponsive(page,"keyword-inline-history");
  await keywordTrigger.focus();
  await keywordTrigger.press("Enter");
  assert.equal(await page.getByRole("region", { name: "Ranking history" }).count(), 0);
  assert.equal(await keywordTrigger.getAttribute("aria-expanded"), "false");
  await keywordTrigger.press("Enter");
  history = page.getByRole("region", { name: "Ranking history" });
  await history.waitFor();
  const viewResults = history.getByRole("button", { name: "View results" });
  await viewResults.scrollIntoViewIfNeeded();
  const scrollBeforeDetail = await page.evaluate(() => scrollY);
  await viewResults.click();
  const detailDialog = page.getByRole("dialog", { name: "Rank Check detail" });
  await detailDialog.waitFor();
  assert.equal(await page.evaluate(() => scrollY), scrollBeforeDetail);
  const dialogPresentation = await detailDialog.evaluate((element) => {
    const style = getComputedStyle(element);
    const backdrop = getComputedStyle(element, "::backdrop");
    const box = element.getBoundingClientRect();
    return {
      background: style.backgroundColor,
      animation: style.animationName,
      backdropFilter: backdrop.backdropFilter,
      withinViewport:
        box.left >= 0 &&
        box.top >= 0 &&
        box.right <= innerWidth &&
        box.bottom <= innerHeight,
    };
  });
  assert.equal(dialogPresentation.background, "rgb(255, 255, 255)");
  assert.notEqual(dialogPresentation.animation, "none");
  assert(dialogPresentation.backdropFilter.includes("blur"));
  assert(dialogPresentation.withinViewport);
  const detail = detailDialog.getByRole("region", { name: "Rank Check detail" });
  await detail.getByText("Top 10 Organic Results").waitFor();
  await detail.getByText("Tracked · Browser Owned Site").waitFor();
  await detail.getByText("competitor.example", { exact: true }).waitFor();
  assert.equal(await detail.getByText(/Data source:/).count(), 0);
  await detailDialog.getByRole("button", { name: "Close dialog" }).click();

  execFileSync(process.env.DOCKER_BIN ?? "docker", ["compose", "exec", "-T", "backend", "python", "-m", "scripts.verification_plan", email], { env: process.env, stdio: "pipe" });
  const schedule = page.getByRole("form", { name: "Rank schedule" });
  await schedule.getByLabel("Local time").fill("07:00");
  await schedule.getByLabel("Timezone").fill("Asia/Ho_Chi_Minh");
  await schedule.getByRole("button", { name: "Save schedule" }).click();
  await page.getByText("Schedule saved.", { exact: true }).waitFor();
  await page.getByText(/Next check:/).waitFor();
  await verifyResponsive(page,"batch-daily-schedule");
  await schedule.getByLabel("Frequency").selectOption("weekly");
  await schedule.getByLabel("Weekly day").selectOption("2");
  await schedule.getByLabel("Local time").fill("08:30");
  const updatedSchedule = page.waitForResponse((response) => response.request().method() === "PUT" && response.url().endsWith("/rank-schedule"));
  await schedule.getByRole("button", { name: "Save schedule" }).click();
  const updated = await updatedSchedule;
  assert.equal(updated.status(), 200);
  const saved = await updated.json();
  assert.equal(saved.frequency, "weekly");
  assert.equal(saved.weekday, 2);
  assert.equal(saved.local_time, "08:30");
  await verifyResponsive(page,"batch-weekly-schedule");
  const deletedSchedule = page.waitForResponse((response) => response.request().method() === "DELETE" && response.url().endsWith("/rank-schedule"));
  await schedule.getByRole("button", { name: "Delete schedule" }).click();
  await page.getByRole("button", { name: "Confirm action" }).click();
  assert.equal((await deletedSchedule).status(), 204);
  await page.getByText("Schedule deleted.", { exact: true }).waitFor();
  assert.equal(await page.getByText(/Next check:/).count(), 0);
  assert.equal(await page.getByRole("combobox", { name: /provider/i }).count(), 0);
  assert(!/gserviceaccount|cloud tasks|gcp_project|rank-checks queue/i.test(await page.locator("body").innerText()));
  await page.getByRole("table", { name: "Batch history" }).getByText("Completed", { exact: true }).waitFor();
  await page.reload();
  await page.getByText("tracked.example #2", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "browser rank query" }).click();
  await page.getByRole("region", { name: "Ranking history" }).waitFor();

  const overviewResponse = page.waitForResponse(r => r.url().endsWith("/api/v1/overview") && r.status() === 200);
  await page.goto(`${base}/app`);
  const overview = await (await overviewResponse).json();
  assert.equal(overview.active_tracked_sites, 1);
  assert.equal(overview.billing.devices.reduce((n,d)=>n+d.projects_used,0), 1);
  assert.equal(overview.billing.devices.reduce((n,d)=>n+d.keywords_used,0), 1);
  assert(overview.billing.devices.every(d=>d.usage.used >= 0));
  assert(overview.recent_batches.some(b=>b.id === batchId && b.succeeded_keyword_count === 1));
  await page.getByRole("table",{name:"Recent ranking activity"}).waitFor();
  await verifyResponsive(page,"overview-populated");
  const billingResponse = page.waitForResponse(r => r.url().endsWith("/api/v1/billing/me") && r.status() === 200);
  await page.goto(`${base}/settings/billing`);
  const currentBilling = await (await billingResponse).json();
  assert.deepEqual(overview.billing, currentBilling, "Overview must preserve existing billing counters after Plan activation");
  await page.goto(`${base}/app/rankings`);
  await page.getByRole("table",{name:"Latest rankings"}).waitFor();
  await verifyResponsive(page,"rankings-populated");
  assert.deepEqual(exceptions, []);
  // Chromium can report a bodyless 204 DELETE as ERR_ABORTED. Accept it only
  // after observing the successful response and the deleted UI state above.
  const expectedEmptyResponses = failures.filter((failure) => failure.method === "DELETE" && failure.reason === "net::ERR_ABORTED" && responses.some((response) => response.path === failure.path && response.status === 204));
  const unexpectedFailures = failures.filter((failure) => !expectedEmptyResponses.includes(failure));
  assert.deepEqual(unexpectedFailures, []);
  assert(
    responses.every(
      (response) =>
        response.status < 400 ||
        (response.path.endsWith("/auth/refresh") && response.status === 401),
    ),
  );
  process.stdout.write(
    `${JSON.stringify({
      milestone_5_browser: "passed",
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
        "provider_metadata_hidden",
        "batch_progress_history",
        "schedule_timezone",
        "schedule_update_delete",
        "progress_polling",
        "terminal_polling_stopped",
        "job_details",
        "no_cloud_details",
        "reload_persistence",
      ],
      browserExceptions: 0,
      unexpectedNetworkFailures: 0,
      successful204BodyAborts: expectedEmptyResponses.length,
    })}\n`,
  );
} finally {
  await browser.close();
}
