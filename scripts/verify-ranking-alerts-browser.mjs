import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const modulePath = process.env.PLAYWRIGHT_MODULE;
const axePath = process.env.AXE_MODULE;
assert(modulePath && axePath, "Set PLAYWRIGHT_MODULE and AXE_MODULE");
const { chromium } = await import(pathToFileURL(modulePath).href);
const { default: AxeBuilder } = await import(pathToFileURL(axePath).href);
const fixture = JSON.parse(
  execFileSync(
    process.env.QA_SEED_PYTHON ?? "docker",
    process.env.QA_SEED_PYTHON
      ? ["-m", "scripts.seed_ranking_alerts_qa"]
      : [
          "exec",
          process.env.QA_CONTAINER ?? "serp-m7d-runtime",
          "python",
          "-m",
          "scripts.seed_ranking_alerts_qa",
        ],
    { encoding: "utf8", cwd: process.env.QA_SEED_WORKDIR },
  ),
);
const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.CHROME_EXECUTABLE ??
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const base = process.env.QA_BASE_URL ?? "http://localhost:3000";
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const folder =
  process.env.QA_ARTIFACT_DIRECTORY ??
  "docs/verification-artifacts/milestone-7d";
await mkdir(folder, { recursive: true });
const report = {
  runtime: "local production standalone",
  providers: "fake SERP and email; outbound alerts off",
  widths: [375, 768, 1024, 1440],
  checks: [],
  screenshots: [],
  violations: [],
  pageErrors: [],
  consoleErrors: [],
};
try {
  const context = await browser.newContext({ timezoneId: "Asia/Ho_Chi_Minh" });
  const page = await context.newPage();
  page.on("pageerror", (error) => report.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /hydration|Minified React|Warning:/.test(message.text())
    )
      report.consoleErrors.push(message.text());
  });
  async function login(account) {
    await page.goto(`${base}/login`);
    await page.getByLabel("Email", { exact: true }).fill(account.email);
    await page.getByLabel("Password", { exact: true }).fill(account.password);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
  }
  async function audit(name, selector = undefined) {
    if (name !== "inbox-loading") await page.waitForLoadState("networkidle");
    for (const width of report.widths) {
      await page.setViewportSize({ width, height: 900 });
      await page.waitForTimeout(120);
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${name} overflow at ${width}`,
      );
      let axe = new AxeBuilder({ page }).withTags([
        "wcag2a",
        "wcag2aa",
        "wcag21a",
        "wcag21aa",
      ]);
      if (selector) axe = axe.include(selector);
      const result = await axe.analyze();
      report.violations.push(
        ...result.violations.map((item) => ({
          name,
          width,
          id: item.id,
          impact: item.impact,
          nodes: item.nodes.map((node) => node.target),
        })),
      );
      const file = `${folder}/${name}-${width}.png`;
      await page.screenshot({ path: file, fullPage: true });
      report.screenshots.push(file);
      if (name === "inbox-populated" && [375, 1440].includes(width)) {
        const viewportFile = `${folder}/${name}-viewport-${width}.png`;
        await page.screenshot({ path: viewportFile, fullPage: false });
        report.screenshots.push(viewportFile);
      }
    }
    report.checks.push(name);
  }
  await page.goto(`${base}/app/ranking-alerts`);
  await page.waitForURL(`${base}/login`);
  report.checks.push("anonymous redirect");
  await login(fixture.owner);
  await page.waitForURL(`${base}/app`);
  await page.goto(`${base}/app/ranking-alerts`);
  await page
    .getByRole("heading", { name: "Ranking Alerts", exact: true })
    .waitFor();
  await page.getByText("25 alerts on this page", { exact: true }).waitFor();
  await audit("inbox-populated");
  await page.emulateMedia({ colorScheme: "dark" });
  await audit("inbox-dark-scheme");
  await page.emulateMedia({ colorScheme: "light" });
  await page.getByLabel("Show", { exact: true }).focus();
  await page.keyboard.press("Tab");
  assert(
    await page
      .getByLabel("Project", { exact: true })
      .evaluate((el) => el === document.activeElement),
  );
  report.checks.push("keyboard filter focus order");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByText("6 alerts on this page", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await page.getByText("25 alerts on this page", { exact: true }).waitFor();
  await page.getByLabel("Show", { exact: true }).selectOption("unread");
  const first = page.getByRole("button", { name: /^Mark read:/ }).first();
  await first.click();
  await page.getByText("Read status updated.", { exact: true }).waitFor();
  assert(
    await page
      .getByText("Read status updated.", { exact: true })
      .evaluate((el) => el === document.activeElement),
  );
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(fixture.project_id);
  await page
    .getByRole("link", { name: "Manage project alert preferences" })
    .waitFor();
  await page
    .getByRole("button", { name: "Mark all read", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "No unread ranking alerts" })
    .waitFor();
  await audit("inbox-unread-empty");
  await page.getByLabel("Show", { exact: true }).selectOption("all");
  await page
    .getByRole("link", { name: "View ranking history" })
    .first()
    .click();
  await page
    .getByRole("heading", { name: "Ranking Explorer", exact: true })
    .waitFor();
  report.checks.push("ranking history deep link");
  await page.goto(
    `${base}/app/projects/${fixture.project_id}#ranking-alert-preferences`,
  );
  await page.getByLabel("Minimum movement (positions)").waitFor();
  await page.getByText(/Email delivery is currently unavailable/).waitFor();
  await page.getByLabel("Minimum movement (positions)").fill("5");
  await page.getByLabel("Also email my verified account").check();
  await page
    .getByRole("button", { name: "Save Alert Preferences", exact: true })
    .click();
  await page.getByText("Alert preferences saved.", { exact: true }).waitFor();
  await page.reload();
  await page.getByLabel("Minimum movement (positions)").waitFor();
  assert.equal(
    await page.getByLabel("Minimum movement (positions)").inputValue(),
    "5",
  );
  assert(await page.getByLabel("Also email my verified account").isChecked());
  await page.getByLabel("Enable ranking alerts").uncheck();
  await page
    .getByRole("button", { name: "Save Alert Preferences", exact: true })
    .click();
  await page.getByText("Alert preferences saved.", { exact: true }).waitFor();
  await page.getByLabel("Enable ranking alerts").check();
  await page
    .getByRole("button", { name: "Save Alert Preferences", exact: true })
    .click();
  await page.getByText("Alert preferences saved.", { exact: true }).waitFor();
  // Audit the added preferences section; existing project panels have separate regression coverage.
  await audit("project-preferences", "#ranking-alert-preferences");
  await page.goto(`${base}/app/ranking-alerts`);
  await page.getByText("25 alerts on this page", { exact: true }).waitFor();
  await page.route("**/api/v1/ranking-alerts?*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "QA_UNAVAILABLE", message: "Unavailable" },
      }),
    }),
  );
  await page.reload();
  await page
    .getByText("Ranking alerts could not be loaded.", { exact: false })
    .waitFor();
  await audit("inbox-error");
  await page.unroute("**/api/v1/ranking-alerts?*");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await page.getByText("25 alerts on this page", { exact: true }).waitFor();
  report.checks.push("error retry recovery");
  let release;
  const held = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/ranking-alerts?*", async (route) => {
    await held;
    await route.continue();
  });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByLabel("Loading ranking alerts…").waitFor();
  await audit("inbox-loading");
  release();
  await page.getByText("25 alerts on this page", { exact: true }).waitFor();
  await page.unroute("**/api/v1/ranking-alerts?*");
  await page.locator('summary[aria-label="Account"]').click();
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.waitForURL(`${base}/login`);
  await login(fixture.empty);
  await page.waitForURL(`${base}/app`);
  await page.goto(`${base}/app/ranking-alerts`);
  await page.getByRole("heading", { name: "No ranking alerts yet" }).waitFor();
  await audit("inbox-empty-other-account");
  assert.equal(await page.getByText("25 alerts on this page").count(), 0);
  report.checks.push("account switch cache isolation");
  await page.locator('summary[aria-label="Account"]').click();
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.waitForURL(`${base}/login`);
  await login(fixture.unverified);
  await page.waitForURL(`${base}/verify-email`);
  await page.goto(`${base}/app/ranking-alerts`);
  await page.waitForURL(`${base}/verify-email`);
  report.checks.push("unverified redirect");
  assert.deepEqual(report.violations, []);
  assert.deepEqual(report.pageErrors, []);
  assert.deepEqual(report.consoleErrors, []);
  await writeFile(
    `${folder}/browser-qa.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      result: "passed",
      screens: report.checks,
      widths: report.widths,
      screenshots: report.screenshots.length,
      axeViolations: 0,
      pageErrors: 0,
    }),
  );
} finally {
  await writeFile(
    `${folder}/browser-qa.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  await browser.close();
}
