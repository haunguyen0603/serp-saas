// Read-only/unauthenticated production release smoke. Auth-denied mutations
// exercise gates only; never creates accounts, checks, alerts, payments or email.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";

const api = "https://api.serpsaas.com";
const app = "https://app.serpsaas.com";
const worker = "https://serp-worker-833917440392.asia-southeast1.run.app";
const backendOnly = process.argv.includes("--backend-only");
const folder = "docs/verification-artifacts/milestone-7d/production";
const checks = [];
async function check(name, url, expected = 200, options = {}) {
  const response = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(30_000),
    headers: { "Cache-Control": "no-cache", ...options.headers },
  });
  assert.equal(response.status, expected, `${name}: HTTP ${response.status}`);
  const type = response.headers.get("content-type") ?? "";
  const data = type.includes("json")
    ? await response.json()
    : await response.text();
  checks.push({ name, status: response.status });
  return { response, data };
}
await check("API health", `${api}/health`);
await check("PostgreSQL health", `${api}/health/db`);
const { data: schema } = await check(
  "M7D deployed OpenAPI",
  `${api}/openapi.json`,
);
const alertPaths = {
  "/api/v1/ranking-alerts": "get",
  "/api/v1/ranking-alerts/unread-count": "get",
  "/api/v1/ranking-alerts/{alert_id}/read": "patch",
  "/api/v1/ranking-alerts/mark-all-read": "post",
  "/api/v1/projects/{project_id}/ranking-alert-preferences": "put",
};
for (const [path, method] of Object.entries(alertPaths)) {
  assert(schema.paths[path]?.[method], `Missing ${method} ${path}`);
}
assert(
  schema.paths["/api/v1/projects/{project_id}/ranking-alert-preferences"]?.get,
);
assert.equal(
  schema.components.schemas.AlertPreferences.properties.email_enabled.default,
  false,
);
assert.equal(
  schema.components.schemas.AlertPreferences.additionalProperties,
  false,
);
const nil = "00000000-0000-0000-0000-000000000000";
for (const [method, path] of [
  ["GET", "/ranking-alerts"],
  ["GET", "/ranking-alerts/unread-count"],
  ["PATCH", `/ranking-alerts/${nil}/read`],
  ["POST", "/ranking-alerts/mark-all-read"],
  ["GET", `/projects/${nil}/ranking-alert-preferences`],
  ["PUT", `/projects/${nil}/ranking-alert-preferences`],
]) {
  const options = { method };
  if (method === "PUT") {
    options.headers = { "Content-Type": "application/json" };
    options.body = "{}";
  }
  const { data } = await check(
    `Authentication: ${method} ${path}`,
    `${api}/api/v1${path}`,
    401,
    options,
  );
  assert.equal(data.error.code, "AUTHENTICATION_REQUIRED");
}
await check(
  "Worker alerts route remains IAM protected",
  `${worker}/internal/tasks/ranking-alerts`,
  403,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  },
);
await check(
  "Worker status remains IAM protected",
  `${worker}/internal/ranking-alerts/status`,
  403,
);
for (const path of [
  "/api/v1/billing/payments/sepay/checkout",
  "/api/v1/billing/payments/sepay/ipn",
  "/api/v1/billing/invoices",
  "/api/v1/projects/{project_id}/rankings/latest",
]) {
  assert(schema.paths[path], `Existing contract removed: ${path}`);
}
await check(
  "SePay options auth boundary",
  `${api}/api/v1/billing/payments/sepay/options`,
  401,
);
await check("Invoices auth boundary", `${api}/api/v1/billing/invoices`, 401);
const { data: catalog } = await check(
  "VND plan catalog",
  `${api}/api/v1/billing/plans`,
);
assert(catalog.length >= 6 && catalog.every((plan) => plan.currency === "VND"));
if (!backendOnly) {
  const { response, data: html } = await check(
    "Ranking Alerts production app route",
    `${app}/app/ranking-alerts`,
  );
  assert.equal(response.headers.get("x-robots-tag"), "noindex, nofollow");
  const scripts = [...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map(
    (match) => match[1],
  );
  assert(scripts.length, "Missing app bundles");
  const code = await Promise.all(
    scripts.map(async (path) => {
      const response = await fetch(new URL(path, app), {
        signal: AbortSignal.timeout(30_000),
      });
      assert.equal(response.status, 200);
      return response.text();
    }),
  );
  assert(
    code.some((text) =>
      text.includes("Get notified when tracked Google rankings"),
    ),
    "M7D inbox bundle missing",
  );
  assert(
    code.some((text) => text.includes("/api/v1/ranking-alerts/unread-count")),
    "M7D badge API bundle missing",
  );
  checks.push({ name: "Deployed inbox/badge bundles", status: 200 });
  for (const path of [
    "/login",
    "/app/projects",
    "/settings/billing",
    "/app/change-plan",
    "/app/invoices",
  ]) {
    await check(`Existing app route: ${path}`, `${app}${path}`);
  }
  await check("Public site", "https://serpsaas.com/");
  await check(
    "Published Vietnamese competitor guide",
    "https://serpsaas.com/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo",
  );
}
const report = {
  checked_at_utc: new Date().toISOString(),
  mode: "public unauthenticated production smoke",
  backend_only: backendOnly,
  passed: checks.length,
  checks,
  accounts_created: 0,
  rank_checks_created: 0,
  payments_created: 0,
  emails_sent: 0,
  authenticated_tenant_flow: "not performed",
  real_smtp_deliverability: "not tested",
};
await mkdir(folder, { recursive: true });
await writeFile(
  `${folder}/${backendOnly ? "backend-" : ""}http-smoke.json`,
  JSON.stringify(report, null, 2) + "\n",
);
console.log(
  JSON.stringify({ passed: report.passed, backend_only: backendOnly }),
);
