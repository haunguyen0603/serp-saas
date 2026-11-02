import { NextRequest } from "next/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { proxy } from "./proxy";
import sitemap from "./app/sitemap";

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://serpsaas.com");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
});
afterEach(() => vi.unstubAllEnvs());

it("publishes only commercial pages in the main site's sitemap", () => {
  expect(
    sitemap()
      .map((page) => page.url)
      .sort(),
  ).toEqual(
    [
      "/",
      "/vi",
      "/vi/blog",
      "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
      "/vi/theo-doi-thu-hang-tu-khoa-hang-ngay",
      "/vi/seo-rank-tracking-cho-agency",
      "/vi/blog/cach-theo-doi-thu-hang-google",
      "/vi/blog/cong-cu-rank-tracker-la-gi",
      "/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay",
      "/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo",
      "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
      "/vi/blog/serp-la-gi",
      "/vi/bang-gia",
      "/vi/gioi-thieu",
      "/vi/chinh-sach-bao-mat",
      "/vi/dieu-khoan-dich-vu",
      "/vi/blog/serp-tracking-cho-agency",
      "/pricing",
      "/about",
      "/terms",
      "/privacy",
      "/blog",
      "/blog/how-to-track-google-rankings",
      "/blog/serp-tracking-for-agencies",
      "/blog/how-to-monitor-keyword-ranking",
      "/google-serp-rank-tracker",
      "/daily-serp-tracker",
      "/serp-tracking-for-agencies",
    ]
      .map((path) => `https://serpsaas.com${path}`)
      .sort(),
  );
});

function request(host: string, path: string) {
  return new NextRequest(`https://${host}${path}`, { headers: { host } });
}

it.each([
  "/app",
  "/app/projects/123",
  "/settings/billing",
  "/admin/customers",
  "/register",
  "/signup",
  "/login",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
])("moves app routes off the commercial domain: %s", (path) => {
  const response = proxy(request("serpsaas.com", `${path}?source=test`));
  expect(response.status).toBe(307);
  expect(response.headers.get("location")).toBe(
    `https://app.serpsaas.com${path}?source=test`,
  );
});

it.each([
  "/pricing",
  "/terms",
  "/privacy",
  "/about",
  "/sitemap.xml",
  "/blog",
  "/blog/how-to-track-google-rankings",
  "/feed.xml",
  "/google-serp-rank-tracker",
  "/daily-serp-tracker",
  "/serp-tracking-for-agencies",
])("moves commercial pages back to the primary domain: %s", (path) => {
  expect(proxy(request("app.serpsaas.com", path)).headers.get("location")).toBe(
    `https://serpsaas.com${path}`,
  );
});

it("opens the workspace at the app root and allows its authentication gate to run", () => {
  expect(proxy(request("app.serpsaas.com", "/")).headers.get("location")).toBe(
    "https://app.serpsaas.com/app",
  );
  const workspace = proxy(request("app.serpsaas.com", "/app"));
  expect(workspace.headers.get("location")).toBeNull();
  expect(workspace.headers.get("X-Robots-Tag")).toBe("noindex, nofollow");
});

it("allows marketing pages and prevents app indexing", async () => {
  expect(
    proxy(request("serpsaas.com", "/pricing")).headers.get("location"),
  ).toBeNull();
  const robots = proxy(request("app.serpsaas.com", "/robots.txt"));
  expect(await robots.text()).toBe("User-agent: *\nDisallow: /\n");
});

it.each([
  "/google-serp-rank-tracker",
  "/daily-serp-tracker",
  "/serp-tracking-for-agencies",
])("keeps the canonical landing page indexable: %s", (path) => {
  const response = proxy(request("serpsaas.com", path));
  expect(response.headers.get("location")).toBeNull();
  expect(response.headers.get("X-Robots-Tag")).toBeNull();
});

it("uses the original Host header behind a reverse proxy and configured redirect targets", () => {
  const incoming = new NextRequest(
    "http://localhost:3000/login?redirect=https://evil.test",
    { headers: { host: "serpsaas.com", "x-forwarded-host": "evil.test" } },
  );
  expect(proxy(incoming).headers.get("location")).toBe(
    "https://app.serpsaas.com/login?redirect=https://evil.test",
  );
  expect(
    proxy(request("serpsaas.com", "/application")).headers.get("location"),
  ).toBeNull();
});

it("keeps localhost and pre-domain run.app checks accessible", () => {
  expect(
    proxy(request("serp-web.run.app", "/pricing")).headers.get("location"),
  ).toBeNull();
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "");
  expect(
    proxy(request("localhost:3000", "/app")).headers.get("location"),
  ).toBeNull();
});
