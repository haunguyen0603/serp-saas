// Fresh anonymous context only. Does not register users or send email/checks.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

assert(process.env.PLAYWRIGHT_MODULE, "Set PLAYWRIGHT_MODULE");
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.CHROME_EXECUTABLE ??
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const folder = "docs/verification-artifacts/milestone-7d/production";
const report = {
  checked_at_utc: new Date().toISOString(),
  mode: "fresh anonymous production browser",
  checks: [],
  refresh_responses: [],
  page_errors: [],
  hydration_errors: [],
  authenticated_flow: "not performed",
};
try {
  const context = await browser.newContext({ timezoneId: "Asia/Ho_Chi_Minh" });
  const page = await context.newPage();
  page.on("pageerror", (error) => report.page_errors.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /hydration|Minified React|Warning:/.test(message.text())
    )
      report.hydration_errors.push(message.text());
  });
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname === "/api/v1/auth/refresh")
      report.refresh_responses.push({
        origin: url.origin,
        status: response.status(),
      });
  });
  for (const width of [375, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("https://app.serpsaas.com/app/ranking-alerts");
    await page.waitForURL("https://app.serpsaas.com/login");
    await page.getByRole("heading", { name: "Log in", exact: true }).waitFor();
    await page.waitForLoadState("networkidle");
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    report.checks.push({
      name: "Anonymous Ranking Alerts redirects to login",
      width,
      result: "passed",
    });
  }
  assert(report.refresh_responses.length > 0);
  assert(
    report.refresh_responses.every(
      (item) =>
        item.origin === "https://api.serpsaas.com" && item.status === 401,
    ),
  );
  assert.deepEqual(report.page_errors, []);
  assert.deepEqual(report.hydration_errors, []);
  report.checks.push({
    name: "Live frontend API origin and anonymous session gate",
    result: "passed",
  });
  console.log(
    JSON.stringify({
      passed: report.checks.length,
      page_errors: 0,
      hydration_errors: 0,
    }),
  );
} finally {
  await mkdir(folder, { recursive: true });
  await writeFile(
    `${folder}/browser-smoke.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  await browser.close();
}
