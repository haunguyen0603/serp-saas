import { afterEach, expect, it, vi } from "vitest";
import {
  appHref,
  getAppUrl,
  getSiteUrl,
  hasSeparateAppDomain,
  shouldRestoreSession,
  siteHref,
} from "./site";

afterEach(() => vi.unstubAllEnvs());

it("keeps one-origin localhost navigation when app URL is unset", () => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "");
  expect(hasSeparateAppDomain()).toBe(false);
  expect(appHref("/register")).toBe("/register");
  expect(siteHref("/terms")).toBe("/terms");
  expect(shouldRestoreSession("localhost:3000")).toBe(true);
});

it("routes account and legal links to their configured origins", () => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://serpsaas.com");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
  expect(appHref("/register")).toBe("https://app.serpsaas.com/register");
  expect(siteHref("/privacy")).toBe("https://serpsaas.com/privacy");
  expect(shouldRestoreSession("serpsaas.com")).toBe(false);
  expect(shouldRestoreSession("app.serpsaas.com")).toBe(true);
});

it.each([
  "https://user:password@site.test",
  "https://site.test/path",
  "https://site.test?x=y",
  "https://site.test#token",
  "javascript:alert(1)",
])("rejects an invalid origin: %s", (url) => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", url);
  expect(getSiteUrl).toThrow("NEXT_PUBLIC_SITE_URL");
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://serpsaas.com");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", url);
  expect(getAppUrl).toThrow("NEXT_PUBLIC_APP_URL");
});

it.each(["//evil.test/login", "/\\evil.test/login", "https://evil.test"])(
  "rejects links that could leave the configured origin: %s",
  (path) => {
    expect(() => appHref(path)).toThrow();
  },
);
