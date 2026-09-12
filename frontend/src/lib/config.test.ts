import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("fails clearly when the API URL is missing", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
  vi.stubEnv("NEXT_PUBLIC_APP_ENV", "test");
  await expect(import("./config")).rejects.toThrow("NEXT_PUBLIC_API_BASE_URL");
});

it("rejects credentials in the public API URL", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://user:secret@example.com");
  vi.stubEnv("NEXT_PUBLIC_APP_ENV", "test");
  await expect(import("./config")).rejects.toThrow("without credentials");
});

it("loads the deployment environment and normalizes the URL", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/");
  vi.stubEnv("NEXT_PUBLIC_APP_ENV", "production");
  const { config } = await import("./config");
  expect(config).toEqual({
    apiBaseUrl: "http://api.test",
    environment: "production",
  });
});
