import { verifyResponsive } from "./browser-responsive.mjs";
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
  const explorerResponses = [];
  page.on("pageerror", (error) => exceptions.push(error.message));
  page.on("requestfailed", (request) => {
    const path = new URL(request.url()).pathname;
    if (
      request.failure()?.errorText === "net::ERR_ABORTED" &&
      request.method() === "GET" &&
      path.startsWith("/app/")
    )
      return;
    failures.push({
      method: request.method(),
      path,
      reason: request.failure()?.errorText,
    });
  });
  page.on("response", (response) => {
    if (response.url().includes("/ranking-explorer"))
      explorerResponses.push(response.status());
  });

  const provider = execFileSync(
    process.env.DOCKER_BIN ?? "docker",
    [
      "compose",
      "exec",
      "-T",
      "worker",
      "python",
      "-c",
      "from app.core.config import get_settings; print(get_settings().serp_provider)",
    ],
    { env: process.env, encoding: "utf8" },
  ).trim();
  assert.equal(provider, "fake", "Browser QA must never use a real provider");

  const base = process.env.FRONTEND_URL ?? "http://localhost:3000";
  const email = `milestone-7b-${randomUUID()}@example.com`;
  const password = randomBytes(24).toString("base64url");
  const keywords = Array.from(
    { length: 26 },
    (_, index) => `explorer keyword ${String(index).padStart(2, "0")}`,
  );

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
  await page.getByLabel("Site Name").fill("Explorer Browser Site");
  await page.getByLabel("Primary Domain").fill("tracked.example");
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
  await page.getByLabel("Project name").fill("Explorer Browser Project");
  await page.getByLabel("Country", { exact: true }).fill("vn");
  await page.getByLabel("Language", { exact: true }).fill("vi");
  await page.getByLabel("Keywords, one per line").fill(keywords.join("\n"));
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.waitForURL(/\/app\/projects\/[0-9a-f-]+$/);
  const projectUrl = page.url();
  const projectId = projectUrl.split("/").at(-1);
  assert(projectId);

  const keywordRow = page
    .getByRole("row")
    .filter({ hasText: "explorer keyword 00" });
  await keywordRow.getByRole("button", { name: "Check now" }).click();
  await page.getByText("Keyword check queued.", { exact: true }).waitFor();
  await keywordRow
    .getByText(`#2`, { exact: false })
    .waitFor({ timeout: 30_000 });

  await page.getByRole("link", { name: "Ranking Explorer" }).click();
  await page.waitForURL(`${projectUrl}/rankings`);
  await page.getByRole("heading", { name: "Ranking Explorer" }).waitFor();
  const table = page.getByRole("table", { name: "Ranking comparison" });
  await table.waitFor();
  await page.getByText("26 results", { exact: true }).waitFor();
  const rankedRow = table
    .getByRole("row")
    .filter({ hasText: "explorer keyword 00" });
  await rankedRow.getByText("#2", { exact: true }).waitFor();
  await rankedRow.getByText("No previous data", { exact: true }).waitFor();

  const search = page.getByLabel("Search Keywords");
  await search.fill("explorer keyword 00");
  await page.waitForURL(/q=explorer(\+|%20)keyword(\+|%20)00/);
  await page.getByText("1 results", { exact: true }).waitFor();
  assert.equal(await table.getByRole("row").count(), 2);
  await page
    .getByRole("button", { name: /Remove .*explorer keyword 00.* filter/ })
    .click();
  await page.getByText("26 results", { exact: true }).waitFor();

  await page.getByLabel("Movement").selectOption("no_previous_data");
  await page.waitForURL(/movement=no_previous_data/);
  await page.getByText("1 results", { exact: true }).waitFor();
  await page.goBack();
  await page.getByText("26 results", { exact: true }).waitFor();
  assert(!page.url().includes("movement="));
  await page.goForward();
  await page.getByText("1 results", { exact: true }).waitFor();
  assert(page.url().includes("movement=no_previous_data"));
  for (const movement of [
    "improved",
    "declined",
    "unchanged",
    "entered_checked_depth",
    "left_checked_depth",
  ]) {
    await page.getByLabel("Movement").selectOption(movement);
    await page.waitForURL(
      (url) => url.searchParams.get("movement") === movement,
    );
    await page
      .getByRole("heading", { name: "No Keywords match these filters" })
      .waitFor();
  }
  await page.getByRole("button", { name: "Clear all" }).click();
  await page.waitForURL((url) => url.search === "");
  await page.getByText("26 results", { exact: true }).waitFor();

  const position = page
    .locator("label")
    .filter({ hasText: /^Current position/ })
    .locator("select");
  for (const bucket of ["positions_4_10", "not_found_in_depth"]) {
    await position.selectOption(bucket);
    await page.waitForURL(
      (url) => url.searchParams.get("position_bucket") === bucket,
    );
    await page
      .getByRole("heading", { name: "No Keywords match these filters" })
      .waitFor();
  }
  await position.selectOption("top_3");
  await page.waitForURL(/position_bucket=top_3/);
  await page.getByText("1 results", { exact: true }).waitFor();
  await page.getByLabel("Tracked Site").selectOption({
    label: "Explorer Browser Site",
  });
  await page.waitForURL(/tracked_site_id=/);
  await page.getByLabel("Current status").selectOption("ranked");
  await page.waitForURL(/status=ranked/);
  await page.getByText("1 results", { exact: true }).waitFor();
  assert(page.url().includes("position_bucket=top_3"));
  assert(page.url().includes("tracked_site_id="));
  assert(page.url().includes("status=ranked"));
  await page.getByRole("button", { name: "Clear all" }).click();
  await page.waitForURL((url) => url.search === "");
  await page.getByText("26 results", { exact: true }).waitFor();

  await page.getByLabel("Date comparison").selectOption("7d");
  await page.waitForURL(/range=7d/);
  await page.getByLabel("Date comparison").selectOption("90d");
  await page.waitForURL(/range=90d/);
  await page.getByLabel("Date comparison").selectOption("custom");
  await page.getByLabel("From date (UTC)").waitFor();
  assert(page.url().includes("range=custom"));
  assert(page.url().includes("compare_from="));
  assert(page.url().includes("compare_to="));
  await page.goto(
    `${projectUrl}/rankings?range=custom&compare_from=2026-09-02&compare_to=2026-09-01`,
  );
  await page
    .getByText("Choose valid UTC dates. From date must not be after To date.", {
      exact: true,
    })
    .waitFor();
  await page.getByLabel("Date comparison").selectOption("30d");

  const currentHeader = table.getByRole("button", { name: "Current" });
  await currentHeader.click();
  await page.waitForURL(/sort=current_position/);
  assert.equal(
    await currentHeader.locator("xpath=ancestor::th").getAttribute("aria-sort"),
    "ascending",
  );
  await currentHeader.click();
  await page.waitForURL(/order=desc/);
  assert.equal(
    await currentHeader.locator("xpath=ancestor::th").getAttribute("aria-sort"),
    "descending",
  );

  await page.getByLabel("Page size").selectOption("25");
  await page.waitForURL(/limit=25/);
  await page.getByRole("button", { name: "Next page" }).click();
  await page.waitForURL(/cursor=/);
  await page.waitForFunction(
    () =>
      document.querySelectorAll(
        'table[aria-label="Ranking comparison"] tbody > tr',
      ).length === 1,
  );
  assert.equal(await table.getByRole("row").count(), 2);
  await page.getByRole("button", { name: "First page" }).click();
  await page.waitForURL((url) => !url.searchParams.has("cursor"));
  await page.waitForFunction(
    () =>
      document.querySelectorAll(
        'table[aria-label="Ranking comparison"] tbody > tr',
      ).length === 25,
  );

  const keywordTrigger = table.getByRole("button", {
    name: "explorer keyword 00",
  });
  await keywordTrigger.click();
  const history = page.getByRole("region", { name: "Ranking history" });
  await history.waitFor();
  await history
    .getByText("Ranking history · explorer keyword 00", { exact: true })
    .waitFor();
  await history.getByText("tracked.example #2", { exact: true }).waitFor();
  const secondKeyword = table.getByRole("button", {
    name: "explorer keyword 01",
  });
  await secondKeyword.click();
  await page
    .getByText("Ranking history · explorer keyword 01", { exact: true })
    .waitFor();
  await page.getByText("No ranking history yet.", { exact: true }).waitFor();
  assert.equal(await keywordTrigger.getAttribute("aria-expanded"), "false");
  assert.equal(await secondKeyword.getAttribute("aria-expanded"), "true");
  await keywordTrigger.click();
  await page
    .getByText("Ranking history · explorer keyword 00", { exact: true })
    .waitFor();
  await page.getByText("tracked.example #2", { exact: true }).waitFor();
  await verifyResponsive(page, "ranking-explorer-populated");

  assert.deepEqual(exceptions, []);
  assert.deepEqual(failures, []);
  assert(explorerResponses.length >= 18);
  assert.equal(explorerResponses.filter((status) => status === 422).length, 1);
  assert(explorerResponses.every((status) => status === 200 || status === 422));
  process.stdout.write(
    `${JSON.stringify({
      milestone_7b_browser: "passed",
      provider,
      realProviderCredits: 0,
      explorerRequests: explorerResponses.length,
      checks: [
        "project_navigation",
        "default_comparison",
        "search_debounce",
        "movement_filter",
        "all_movement_options",
        "position_filter",
        "all_depth_10_position_options",
        "tracked_site_filter",
        "status_filter",
        "range_and_custom_dates",
        "invalid_custom_dates",
        "active_filter_chips",
        "clear_all",
        "url_back_forward",
        "sorting",
        "server_pagination",
        "inline_history",
        "single_expanded_history",
        "responsive_375_to_1440",
      ],
      browserExceptions: 0,
      networkFailures: 0,
      expectedValidationErrors: 1,
    })}\n`,
  );
} finally {
  await browser.close();
}
