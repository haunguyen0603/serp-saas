import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { AuthProvider } from "./auth-provider";
import SignupPage from "@/app/signup/page";
import LoginPage from "@/app/login/page";
import ApplicationPage from "@/app/app/settings/page";
import * as api from "./api";
import { ApiError } from "@/lib/api/client";
import type { AuthResponse } from "./types";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
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
  access_token: "memory-only",
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
  vi.mocked(api.refreshSession).mockRejectedValue(new ApiError(401));
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(
        async () => new Response(JSON.stringify(result.user)),
      ),
  );
});

function view(Page: typeof SignupPage) {
  return render(
    <Providers>
      <AuthProvider>
        <Page />
      </AuthProvider>
    </Providers>,
  );
}
async function fill(signup = true) {
  view(signup ? SignupPage : LoginPage);
  const button = screen.getByRole("button", {
    name: signup ? "Create Account" : "Log in",
  });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "person@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), {
    target: { value: "valid test password" },
  });
  if (signup)
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "valid test password" },
    });
}

it("renders the signup fields", async () => {
  await fill();
  expect(screen.getByLabelText("Confirm Password")).toHaveAttribute(
    "type",
    "password",
  );
  expect(screen.getByRole("checkbox")).toBeRequired();
});

it.each([
  [SignupPage, "Create Account"],
  [LoginPage, "Log in"],
])("uses the primary CTA style for %s", async (Page, name) => {
  view(Page);
  const button = screen.getByRole("button", { name });
  await waitFor(() => expect(button).toBeEnabled());
  expect(button).toHaveClass("ui-button--primary");
});

it.each([
  [SignupPage, "Log in", "/login"],
  [LoginPage, "Create account", "/signup"],
])("uses the secondary text-link style for %s", async (Page, name, href) => {
  view(Page);
  const link = await screen.findByRole("link", { name });
  expect(link).toHaveAttribute("href", href);
  expect(link).toHaveClass("ui-text-link");
  expect(link).not.toHaveClass("ui-link-button");
});

it("rejects mismatching confirmation before making a request", async () => {
  await fill();
  fireEvent.change(screen.getByLabelText("Confirm Password"), {
    target: { value: "different password" },
  });
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Passwords do not match",
  );
  expect(api.register).not.toHaveBeenCalled();
});

it("requires terms acceptance", async () => {
  await fill();
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "accept the Terms",
  );
  expect(api.register).not.toHaveBeenCalled();
});

it("registers and redirects without submitting confirmation", async () => {
  vi.mocked(api.register).mockResolvedValue(result);
  await fill();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  expect(api.register).toHaveBeenCalledWith({
    email: "person@example.com",
    password: "valid test password",
    accept_terms: true,
  });
});

it.each([
  [409, "This email is already registered."],
  [0, "The service is unavailable."],
])("shows signup errors", async (status, message) => {
  vi.mocked(api.register).mockRejectedValue(
    new ApiError(status, "TEST_ERROR", message),
  );
  await fill();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
  expect(replace).not.toHaveBeenCalled();
});

it("logs in and redirects to the protected page", async () => {
  vi.mocked(api.login).mockResolvedValue(result);
  await fill(false);
  expect(screen.queryByLabelText("Confirm Password")).not.toBeInTheDocument();
  fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  expect(api.login).toHaveBeenCalledWith({
    email: "person@example.com",
    password: "valid test password",
  });
});

it.each([
  [401, "Invalid email or password."],
  [0, "The service is unavailable."],
])("shows login errors", async (status, message) => {
  vi.mocked(api.login).mockRejectedValue(
    new ApiError(status, "TEST_ERROR", message),
  );
  await fill(false);
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
});

it("restores and renders the protected account, then logs out", async () => {
  vi.mocked(api.refreshSession).mockResolvedValue(result);
  vi.mocked(api.logout).mockResolvedValue();
  view(ApplicationPage);
  expect(await screen.findByText("person@example.com")).toBeVisible();
  expect(screen.getByText("Active")).toBeVisible();
  expect(fetch).toHaveBeenCalledWith(
    "http://api.test/api/v1/users/me",
    expect.objectContaining({
      credentials: "include",
      headers: expect.objectContaining({ Authorization: "Bearer memory-only" }),
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  expect(screen.queryByText("person@example.com")).not.toBeInTheDocument();
});

it("redirects an unauthenticated protected page without showing account data", async () => {
  view(ApplicationPage);
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  expect(screen.queryByText("Signed in as:")).not.toBeInTheDocument();
});

it("shows recoverable session failure without a redirect loop", async () => {
  vi.mocked(api.refreshSession)
    .mockRejectedValueOnce(new ApiError(0))
    .mockResolvedValueOnce(result);
  view(ApplicationPage);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "service is unavailable",
  );
  expect(replace).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("person@example.com")).toBeVisible();
});
