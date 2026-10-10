import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AuthSession } from "./session";
import * as api from "./api";
import { ApiError } from "@/lib/api/client";
import type { AuthResponse } from "./types";

vi.mock("./api", () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  refreshSession: vi.fn(),
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));

const result: AuthResponse = {
  access_token: "in-memory-token",
  token_type: "bearer",
  expires_in: 900,
  user: {
    id: "user-1",
    email: "person@example.com",
    status: "active",
    email_verified: false,
    terms_accepted_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
};
beforeEach(() => {
  vi.resetAllMocks();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

it("restores once despite repeated startup and keeps tokens out of storage", async () => {
  const storage = vi.spyOn(Storage.prototype, "setItem");
  vi.mocked(api.refreshSession).mockResolvedValue(result);
  const session = new AuthSession();
  session.start();
  session.start();
  await session.refresh();
  expect(api.refreshSession).toHaveBeenCalledTimes(1);
  expect(session.getSnapshot().user).toEqual(result.user);
  expect(session.getSnapshot().accessToken).toBe(result.access_token);
  expect(storage).not.toHaveBeenCalled();
});

it("restores an anonymous state for a missing refresh session", async () => {
  vi.mocked(api.refreshSession).mockRejectedValue(new ApiError(401));
  const session = new AuthSession();
  await expect(session.refresh()).rejects.toThrow();
  expect(session.getSnapshot().status).toBe("anonymous");
});

it("keeps network failure distinct from anonymous state and allows retry", async () => {
  vi.mocked(api.refreshSession)
    .mockRejectedValueOnce(new ApiError(0))
    .mockResolvedValueOnce(result);
  const session = new AuthSession();
  await expect(session.refresh()).rejects.toThrow();
  expect(session.getSnapshot().status).toBe("error");
  await session.refresh();
  expect(session.getSnapshot().status).toBe("authenticated");
});

it("shares one refresh across concurrent expired requests and retries once", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  vi.mocked(api.refreshSession).mockImplementation(async () => {
    await new Promise((resolve) => setTimeout(resolve, 5));
    return { ...result, access_token: "replacement" };
  });
  const fetchMock = vi
    .fn()
    .mockImplementation(async (_url, options: RequestInit) => {
      if (
        (options.headers as Record<string, string>).Authorization ===
        "Bearer in-memory-token"
      )
        return new Response('{"error":{"code":"EXPIRED_ACCESS_TOKEN"}}', {
          status: 401,
        });
      return new Response(JSON.stringify(result.user));
    });
  vi.stubGlobal("fetch", fetchMock);
  const session = new AuthSession();
  await session.login({ email: result.user.email, password: "test-password" });
  const users = await Promise.all([
    session.getCurrentUser(),
    session.getCurrentUser(),
    session.getCurrentUser(),
  ]);
  expect(users).toEqual([result.user, result.user, result.user]);
  expect(api.refreshSession).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledTimes(6);
});

it("never loops when the retried request is unauthorized", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  vi.mocked(api.refreshSession).mockResolvedValue({
    ...result,
    access_token: "replacement",
  });
  const fetchMock = vi
    .fn()
    .mockImplementation(async () => new Response("{}", { status: 401 }));
  vi.stubGlobal("fetch", fetchMock);
  const session = new AuthSession();
  await session.login({ email: result.user.email, password: "test-password" });
  await expect(session.getCurrentUser()).rejects.toThrow();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(api.refreshSession).toHaveBeenCalledTimes(1);
});

it("clears user cache and in-memory state after server-confirmed logout", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  vi.mocked(api.logout).mockResolvedValue();
  const clear = vi.fn();
  const session = new AuthSession(clear);
  await session.login({ email: result.user.email, password: "test-password" });
  await session.logout();
  expect(api.logout).toHaveBeenCalledOnce();
  expect(clear).toHaveBeenCalledTimes(2);
  expect(session.getSnapshot()).toMatchObject({
    user: null,
    accessToken: null,
    status: "anonymous",
  });
});

it("does not falsely report logout when the backend is unreachable", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  vi.mocked(api.logout).mockRejectedValue(new ApiError(0));
  const session = new AuthSession();
  await session.login({ email: result.user.email, password: "test-password" });
  await expect(session.logout()).rejects.toThrow();
  expect(session.getSnapshot().status).toBe("authenticated");
});

it("waits for rotation before revoking the replacement session on logout", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  let resolve!: (response: AuthResponse) => void;
  vi.mocked(api.refreshSession).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const session = new AuthSession();
  await session.login({ email: result.user.email, password: "test-password" });
  const refresh = session.refresh();
  const logout = session.logout();
  expect(api.logout).not.toHaveBeenCalled();
  resolve({ ...result, access_token: "replacement" });
  await Promise.all([refresh, logout]);
  expect(api.logout).toHaveBeenCalledOnce();
  expect(session.getSnapshot().accessToken).toBeNull();
});

it("accepts the renewed session after changing password", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  const renewed = { ...result, access_token: "renewed-after-password-change" };
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(renewed)));
  vi.stubGlobal("fetch", fetchMock);
  const session = new AuthSession();
  await session.login({
    email: result.user.email,
    password: "old test password",
  });
  await session.changePassword("old test password", "new test password");
  expect(fetchMock).toHaveBeenCalledWith(
    "http://api.test/api/v1/auth/change-password",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        current_password: "old test password",
        new_password: "new test password",
      }),
      headers: expect.objectContaining({
        Authorization: "Bearer in-memory-token",
      }),
    }),
  );
  expect(session.getSnapshot().accessToken).toBe(renewed.access_token);
  expect(session.getSnapshot().status).toBe("authenticated");
});

it("retains the existing session when the current password is incorrect", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: "INVALID_CURRENT_PASSWORD" } }),
          { status: 400 },
        ),
      ),
  );
  const session = new AuthSession();
  await session.login({
    email: result.user.email,
    password: "old test password",
  });
  await expect(
    session.changePassword("wrong password", "new test password"),
  ).rejects.toThrow("current password is incorrect");
  expect(session.getSnapshot().accessToken).toBe(result.access_token);
  expect(api.refreshSession).not.toHaveBeenCalled();
});

it("clears local credentials and prevents an in-flight refresh from restoring them after reset", async () => {
  let finish!: (value: AuthResponse) => void;
  vi.mocked(api.refreshSession).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const clear = vi.fn();
  const session = new AuthSession(clear);
  const restoring = session.refresh();
  session.clearSession();
  finish(result);
  await restoring;
  expect(session.getSnapshot().status).toBe("anonymous");
  expect(session.getSnapshot().accessToken).toBeNull();
  expect(session.getSnapshot().user).toBeNull();
});
