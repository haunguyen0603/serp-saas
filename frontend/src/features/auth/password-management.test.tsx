import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import { ForgotPassword, ResetPassword } from "./password-recovery";
import { ChangePassword } from "./change-password";

const state = vi.hoisted(() => ({
  forgot: vi.fn(),
  reset: vi.fn(),
  change: vi.fn(),
  clear: vi.fn(),
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
vi.mock("./api", () => ({
  forgotPassword: state.forgot,
  resetPassword: state.reset,
}));
vi.mock("./auth-provider", () => ({
  useAuth: () => ({ changePassword: state.change, clearSession: state.clear }),
}));
beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState({}, "", "/reset-password");
  state.forgot.mockResolvedValue({ status: "ok" });
  state.reset.mockResolvedValue({ status: "ok" });
  state.change.mockResolvedValue(undefined);
});

function fillPassword(password = "a new secure password", confirm = password) {
  fireEvent.change(screen.getByLabelText("New Password", { exact: true }), {
    target: { value: password },
  });
  fireEvent.change(screen.getByLabelText("Confirm New Password"), {
    target: { value: confirm },
  });
}

it("normalizes recovery email and shows a generic response without leaking account existence", async () => {
  render(<ForgotPassword />);
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "Person@Example.COM" },
  });
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "If an active account exists",
  );
  expect(state.forgot).toHaveBeenCalledExactlyOnceWith("person@example.com");
});

it("allows retry when requesting an email fails", async () => {
  state.forgot.mockRejectedValueOnce(
    new ApiError(
      503,
      "AUTH_EMAIL_UNAVAILABLE",
      "Email delivery is unavailable.",
    ),
  );
  render(<ForgotPassword />);
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "person@example.com" },
  });
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Email delivery is unavailable",
  );
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "If an active account exists",
  );
});

it("removes the reset secret from the URL and submits only after explicit confirmation", async () => {
  window.history.replaceState({}, "", "/reset-password#token=reset-secret");
  render(<ResetPassword />);
  await screen.findByRole("form");
  expect(window.location.hash).toBe("");
  expect(state.reset).not.toHaveBeenCalled();
  fillPassword();
  fireEvent.submit(screen.getByRole("form"));
  expect(
    await screen.findByRole("heading", { name: "Password reset" }),
  ).toBeVisible();
  expect(state.reset).toHaveBeenCalledExactlyOnceWith(
    "reset-secret",
    "a new secure password",
  );
  expect(state.clear).toHaveBeenCalledOnce();
  expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute(
    "href",
    "/login",
  );
});

it("provides recovery when a reset token is missing or expired", async () => {
  const view = render(<ResetPassword />);
  expect(
    await screen.findByText(/Open the link from your latest/),
  ).toBeVisible();
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  view.unmount();
  window.history.replaceState({}, "", "/reset-password#token=expired-secret");
  state.reset.mockRejectedValue(
    new ApiError(
      410,
      "PASSWORD_RESET_TOKEN_EXPIRED",
      "This reset link has expired. Request a new link.",
    ),
  );
  render(<ResetPassword />);
  await screen.findByRole("form");
  fillPassword();
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent("expired");
  expect(
    screen.getByRole("link", { name: "Request a new reset link" }),
  ).toHaveAttribute("href", "/forgot-password");
  expect(state.clear).not.toHaveBeenCalled();
});

it.each([
  ["short", "short", "10 to 128"],
  ["a valid new password", "a different password", "do not match"],
])(
  "validates passwords before submitting",
  async (password, confirm, error) => {
    render(<ChangePassword />);
    fillPassword(password, confirm);
    fireEvent.submit(screen.getByRole("form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(error);
    expect(state.change).not.toHaveBeenCalled();
  },
);

it("changes the password and clears password fields while keeping the account session", async () => {
  render(<ChangePassword />);
  fireEvent.change(screen.getByLabelText("Current Password"), {
    target: { value: "old secure password" },
  });
  fillPassword();
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Other sessions have been signed out",
  );
  expect(state.change).toHaveBeenCalledExactlyOnceWith(
    "old secure password",
    "a new secure password",
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Current Password")).toHaveValue(""),
  );
  expect(screen.getByLabelText("New Password", { exact: true })).toHaveValue(
    "",
  );
  expect(state.clear).not.toHaveBeenCalled();
});

it("keeps the form available when the current password is incorrect", async () => {
  state.change.mockRejectedValue(
    new ApiError(
      400,
      "INVALID_CURRENT_PASSWORD",
      "Your current password is incorrect.",
    ),
  );
  render(<ChangePassword />);
  fireEvent.change(screen.getByLabelText("Current Password"), {
    target: { value: "wrong password" },
  });
  fillPassword();
  fireEvent.submit(screen.getByRole("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "current password is incorrect",
  );
  expect(screen.getByRole("button", { name: "Change password" })).toBeEnabled();
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});
