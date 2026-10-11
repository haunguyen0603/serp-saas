// Local-only production browser smoke; all API responses are synthetic fixtures.
// Run with the same QA_TOOLS_DIRECTORY and QA_CHROME_PATH as verify-blog-browser.mjs.
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
const base = process.env.QA_BASE_URL ?? "http://localhost:3010";
const origin = new URL(base).origin;
assert(["localhost", "127.0.0.1"].includes(new URL(base).hostname));
const artifactDirectory = resolve(
  process.env.QA_ARTIFACT_DIRECTORY ??
    "../docs/verification-artifacts/milestone-7g1",
);
const date = "2026-10-07T00:00:00Z";
const user = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "security-qa@example.test",
  status: "active",
  email_verified: true,
  is_platform_admin: false,
  terms_accepted_at: date,
  last_login_at: null,
  created_at: date,
  updated_at: date,
};
const project = {
  id: "security-qa-project",
  name: "Security QA Project",
  search_engine: "google",
  country_code: "US",
  language_code: "en",
  device: "desktop",
  location: null,
  status: "active",
  keyword_count: 0,
  created_at: date,
  updated_at: date,
};
const emptyPage = { items: [], next_cursor: null, has_more: false };
const billing = {
  user_id: user.id,
  email: user.email,
  account_status: "active",
  devices: [],
};
const plans = ["desktop", "mobile"].flatMap((device) =>
  ["free", "starter", "pro"].map((tier, index) => ({
    code: `${device}_${tier}`,
    name: `QA ${device} ${tier}`,
    device_scope: device,
    price_monthly_minor_units: index * 100,
    currency: "USD",
    max_projects: index + 1,
    max_keywords: (index + 1) * 10,
    monthly_keyword_checks: (index + 1) * 100,
    scheduled_checks_enabled: index > 0,
    max_scheduled_frequency: index ? "weekly" : "none",
  })),
);
const browser = await chromium.launch({
  ...(process.env.QA_CHROME_PATH
    ? { executablePath: process.env.QA_CHROME_PATH }
    : {}),
});
const results = [];
try {
  for (const mode of ["anonymous", "verified", "unverified"]) {
    const context = await browser.newContext();
    const sessionUser = { ...user, email_verified: mode !== "unverified" };
    const apiRequests = [];
    const errors = [];
    await context.route("**/*", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (!url.pathname.startsWith("/api/v1/")) {
        if (url.origin === origin) return route.continue();
        errors.push(
          `Unexpected external request: ${url.origin}${url.pathname}`,
        );
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
      apiRequests.push(`${request.method()} ${url.pathname}`);
      let body;
      let status = 200;
      if (url.pathname === "/api/v1/auth/refresh") {
        status = mode === "anonymous" ? 401 : 200;
        body =
          mode === "anonymous"
            ? { detail: "Anonymous QA session" }
            : {
                access_token: "qa-fixture-not-a-real-token",
                token_type: "bearer",
                expires_in: 3600,
                email_verification_required: true,
                user: sessionUser,
              };
      } else if (request.method() !== "GET") {
        errors.push(`Unexpected mutation: ${request.method()} ${url.pathname}`);
        return route.abort();
      } else if (url.pathname === "/api/v1/users/me") body = sessionUser;
      else if (url.pathname === "/api/v1/billing/plans") body = plans;
      else if (url.pathname === "/api/v1/billing/me") body = billing;
      else if (url.pathname === "/api/v1/auth/email-verification")
        body = {
          verified: false,
          delivery_status: "sent",
          retry_after_seconds: 0,
          expires_at: null,
        };
      else if (url.pathname === "/api/v1/overview")
        body = { billing, active_tracked_sites: 0, recent_batches: [] };
      else if (url.pathname === "/api/v1/projects")
        body = { ...emptyPage, items: [project] };
      else if (url.pathname === "/api/v1/tracked-sites") body = emptyPage;
      else if (url.pathname === `/api/v1/projects/${project.id}`)
        body = project;
      else if (
        /\/(keywords|keyword-groups|keyword-tags|rank-check-batches|reports)$/.test(
          url.pathname,
        )
      )
        body = emptyPage;
      else if (url.pathname.endsWith("/rankings/latest")) body = { items: [] };
      else if (url.pathname.endsWith("/rank-schedule")) body = null;
      else if (url.pathname.endsWith("/analytics/movers"))
        body = { winners: [], losers: [] };
      else if (url.pathname.endsWith("/analytics/summary"))
        body = {
          project_id: project.id,
          device: "desktop",
          range: "30d",
          as_of: date,
          comparison_basis: "none",
          ...Object.fromEntries(
            [
              "total_keywords",
              "observed_keywords",
              "never_checked",
              "ranked_keywords",
              "not_found_in_depth",
              "top_3",
              "top_10",
              "improved",
              "declined",
              "unchanged",
              "newly_ranked",
              "lost_ranking",
              "entered_checked_depth",
              "left_checked_depth",
              "no_previous_data",
            ].map((key) => [key, 0]),
          ),
          distribution: { effective_depth: 10, buckets: {} },
        };
      else if (url.pathname.endsWith("/ranking-explorer"))
        body = {
          project_id: project.id,
          device: "desktop",
          range: "30d",
          compare_from: null,
          compare_to: null,
          comparison_basis: "none",
          effective_depth: 10,
          supported_position_buckets: [],
          summary: Object.fromEntries(
            [
              "total",
              "improved",
              "declined",
              "unchanged",
              "entered_checked_depth",
              "left_checked_depth",
              "no_previous_data",
              "never_checked",
            ].map((key) => [key, 0]),
          ),
          page: { limit: 50, next_cursor: null },
          items: [],
        };
      else if (url.pathname.endsWith("/competitor-sites"))
        body = {
          project_id: project.id,
          primary_site: null,
          competitor_sites: [],
          max_competitors: 5,
          selection_basis: "current_selection",
          historical_alias_semantics: "current_active_aliases",
        };
      else if (url.pathname.endsWith("/report-schedules"))
        body = {
          items: [],
          delivery_configured: false,
          recipient_mode: "verified_account",
        };
      else if (url.pathname.endsWith("/reports/preview"))
        body = {
          project_id: project.id,
          project_name: project.name,
          device: "desktop",
          period_start_utc: date,
          period_end_utc: date,
          report_timezone: "UTC",
          active_scope: "active_keywords_and_tracked_sites",
          no_matching_keywords: true,
          matching_keywords_without_observations: false,
          filters: {},
          metrics: {
            distinct_keywords: 0,
            keyword_site_pairs: 0,
            distinct_tracked_sites: 0,
            observed_pairs: 0,
            never_checked: 0,
            effective_depth: 10,
            latest_successful_check_at: null,
            comparison_basis: "none",
            distribution: {},
            movements: {},
            biggest_winners: [],
            biggest_losers: [],
          },
          sample: [],
        };
      else {
        errors.push(`Unexpected API request: ${url.pathname}`);
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
    const protectedRoutes = [
      ["/app", "Overview"],
      ["/app/projects", "Projects"],
      ["/app/tracked-sites", "Tracked Sites"],
      ["/app/rankings", "Rankings"],
      ["/app/settings", "Account settings"],
      ["/settings/billing", "Billing & Usage"],
      ["/app/change-plan", "Change Plan"],
      [`/app/projects/${project.id}`, project.name],
      [`/app/projects/${project.id}/rankings`, "Ranking Explorer"],
      [`/app/projects/${project.id}/reports`, "Reports"],
      [`/app/projects/${project.id}/competitors`, "Competitors"],
      ["/admin/plans", "Administrator access required"],
    ];
    const routes =
      mode === "anonymous"
        ? [
            ["/", null],
            ["/pricing", "Choose the capacity your rankings need."],
            ["/login", null],
            ["/register", null],
            ["/verify-email", "Verify your email"],
            ...protectedRoutes,
          ]
        : protectedRoutes;
    for (const [path, heading] of routes) {
      const response = await page.goto(`${base}${path}`, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      if (
        protectedRoutes.some(([protectedPath]) => protectedPath === path) &&
        mode !== "verified"
      )
        await page.waitForURL(
          `${base}${mode === "anonymous" ? "/login" : "/verify-email"}`,
        );
      else if (heading)
        await page
          .getByRole("heading", { level: 1, name: heading, exact: true })
          .waitFor();
      assert.equal(await page.locator("h1").count(), 1);
      if (mode === "anonymous" && path === "/pricing")
        assert.equal(await page.locator(".pricing-card").count(), 6);
      assert.deepEqual(errors, []);
      results.push({
        mode,
        path,
        status: response.status(),
        finalPath: new URL(page.url()).pathname,
        heading: await page.locator("h1").textContent(),
        pageErrors: [...errors],
      });
    }
    assert(
      !apiRequests.some((request) => request.includes("/api/v1/admin/")),
      "Non-admin must not fetch admin data",
    );
    await context.close();
  }
  await mkdir(artifactDirectory, { recursive: true });
  await writeFile(
    resolve(artifactDirectory, "app-browser-qa.json"),
    `${JSON.stringify({ apiMode: "intercepted synthetic fixtures; no real backend, accounts, mutations or providers", results, adminRequests: 0 }, null, 2)}\n`,
  );
  console.log(
    `Security browser regression passed: ${results.length} cases, no page/hydration errors or admin requests.`,
  );
} finally {
  await browser.close();
}
