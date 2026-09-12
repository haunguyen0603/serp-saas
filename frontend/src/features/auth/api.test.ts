import { afterEach, expect, it, vi } from "vitest";
import { login, logout, refreshSession, register } from "./api";

vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
afterEach(() => vi.unstubAllGlobals());

it.each([register, login, refreshSession])(
  "sends credentialed JSON authentication requests",
  async (call) => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "token",
          token_type: "bearer",
          user: { id: "test", email: "test@example.com" },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    await call({
      email: "test@example.com",
      password: "test-password",
      accept_terms: true,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/"),
      expect.objectContaining({
        credentials: "include",
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );
  },
);

it("handles the completed logout response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response('{"status":"ok"}')),
  );
  await expect(logout()).resolves.toBeUndefined();
});

it("maps known errors without displaying server internals", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          '{"error":{"code":"INVALID_CREDENTIALS","message":"private database credentials"}}',
          { status: 401 },
        ),
      ),
  );
  await expect(
    login({ email: "test@example.com", password: "test-password" }),
  ).rejects.toThrow("Invalid email or password.");
});
