import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import { EmailVerification } from "./email-verification";

const state = vi.hoisted(() => ({
  authenticated: false,
  verified: false,
  request: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
  verify: vi.fn(),
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
vi.mock("./api", () => ({ verifyEmail: state.verify }));
vi.mock("./auth-provider", () => ({
  useAuth: () => ({
    status: state.authenticated ? "authenticated" : "anonymous",
    isAuthenticated: state.authenticated,
    isLoading: false,
    requiresEmailVerification: state.authenticated && !state.verified,
    user: state.authenticated
      ? {
          id: "user-1",
          email: "person@example.com",
          email_verified: state.verified,
        }
      : null,
    request: state.request,
    refresh: state.refresh,
    logout: state.logout,
  }),
}));

function view() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <EmailVerification />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  state.authenticated = false;
  state.verified = false;
  state.refresh.mockResolvedValue(undefined);
  state.logout.mockResolvedValue(undefined);
  state.request.mockResolvedValue({
    verified: false,
    delivery_status: "sent",
    retry_after_seconds: 0,
    expires_at: null,
  });
  window.history.replaceState({}, "", "/verify-email");
});
afterEach(() => window.history.replaceState({}, "", "/"));

it("removes the secret fragment and waits for explicit confirmation", async () => {
  window.history.replaceState({}, "", "/verify-email#token=one-use-secret");
  state.verify.mockResolvedValue({ status: "verified", user_id: "user-1" });
  view();
  const button = await screen.findByRole("button", { name: "Verify email" });
  expect(window.location.hash).toBe("");
  expect(state.verify).not.toHaveBeenCalled();
  fireEvent.click(button);
  expect(
    await screen.findByRole("heading", { name: "Email verified" }),
  ).toBeVisible();
  expect(state.verify).toHaveBeenCalledExactlyOnceWith("one-use-secret");
  expect(
    screen.getByRole("link", { name: "Log in to continue" }),
  ).toHaveAttribute("href", "/login");
  expect(state.refresh).not.toHaveBeenCalled();
});

it("allows a signed-in verified user to confirm a different account without switching sessions", async () => {
  state.authenticated = true;
  state.verified = true;
  window.history.replaceState(
    {},
    "",
    "/verify-email#token=another-account-token",
  );
  state.verify.mockResolvedValue({ status: "verified", user_id: "user-2" });
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Verify email" }));
  expect(
    await screen.findByText(/Sign out, then log in with the account/),
  ).toBeVisible();
  expect(
    screen.queryByRole("link", { name: "Continue to workspace" }),
  ).not.toBeInTheDocument();
  expect(state.refresh).toHaveBeenCalledOnce();
});

it("shows an expired link and provides a path to resend", async () => {
  window.history.replaceState({}, "", "/verify-email#token=expired-token");
  state.verify.mockRejectedValue(
    new ApiError(
      410,
      "VERIFICATION_TOKEN_EXPIRED",
      "This verification link has expired. Request a new email.",
    ),
  );
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Verify email" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("expired");
  fireEvent.click(
    screen.getByRole("link", { name: "open email verification" }),
  );
  expect(await screen.findByRole("link", { name: "Log in" })).toHaveAttribute(
    "href",
    "/login",
  );
});

it("sends a credentialed resend request and enforces the server cooldown", async () => {
  state.authenticated = true;
  state.request.mockImplementation(async (_path, options) => ({
    verified: false,
    delivery_status: options?.method === "POST" ? "pending" : "sent",
    retry_after_seconds: options?.method === "POST" ? 60 : 0,
    expires_at: null,
  }));
  view();
  const button = await screen.findByRole("button", {
    name: "Resend verification email",
  });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  expect(await screen.findByText(/Email requested/)).toBeVisible();
  expect(state.request).toHaveBeenCalledWith(
    "/api/v1/auth/email-verification/resend",
    expect.objectContaining({
      method: "POST",
      body: "{}",
      headers: { "Content-Type": "application/json" },
    }),
  );
  expect(
    screen.getByRole("button", { name: /Resend email in/ }),
  ).toBeDisabled();
});

it("keeps delivery failure recoverable", async () => {
  state.authenticated = true;
  state.request.mockResolvedValue({
    verified: false,
    delivery_status: "failed",
    retry_after_seconds: 0,
    expires_at: null,
  });
  view();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not be delivered",
  );
  expect(
    screen.getByRole("button", { name: "Resend verification email" }),
  ).toBeEnabled();
});
