import { afterEach, expect, it, vi } from "vitest";
import { getDatabaseHealth, getHealth, getRedisHealth } from "./client";

vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
afterEach(() => vi.unstubAllGlobals());

it.each([
  [getHealth, "/health"],
  [getDatabaseHealth, "/health/db"],
  [getRedisHealth, "/health/redis"],
] as const)("calls the configured endpoint", async (check, path) => {
  const fetchMock = vi.fn().mockResolvedValue(new Response('{"status":"ok"}'));
  vi.stubGlobal("fetch", fetchMock);
  expect(await check()).toEqual({ status: "ok" });
  expect(fetchMock).toHaveBeenCalledWith(
    `http://api.test${path}`,
    expect.objectContaining({ method: "GET" }),
  );
});

it("rejects malformed success responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response('{"status":"broken"}')),
  );
  await expect(getHealth()).rejects.toThrow("The service is unavailable.");
});

it("does not expose error response content", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("secret", { status: 500 })),
  );
  await expect(getHealth()).rejects.toThrow("The service is unavailable.");
});
