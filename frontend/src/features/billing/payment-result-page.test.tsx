import { act, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PaymentResultPage } from "./payment-result-page";

const state = vi.hoisted(() => ({
  request: vi.fn(),
  replace: vi.fn(),
  orderId: "order-1" as string | null,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: state.replace }),
  useSearchParams: () => ({ get: () => state.orderId }),
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    status: "authenticated",
    user: { id: "user-1", email_verified: true },
    request: state.request,
    refresh: vi.fn(),
  }),
}));
const payment = (status: string) => ({
  id: "order-1",
  invoice_number: "PAY_TEST",
  status,
  plan_name_snapshot: "Desktop Pro",
  plan_code: "desktop_pro",
});
function show(result: "success" | "error" | "cancel" = "success") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <PaymentResultPage result={result} />
    </QueryClientProvider>,
  );
  return { invalidate };
}
beforeEach(() => {
  vi.clearAllMocks();
  state.orderId = "order-1";
  state.request.mockResolvedValue(payment("paid"));
});
afterEach(() => {
  vi.useRealTimers();
});
it("shows confirmed paid state and refreshes billing/entitlements", async () => {
  const { invalidate } = show();
  expect(
    await screen.findByRole("heading", { name: "Payment successful" }),
  ).toBeVisible();
  expect(screen.getByText(/Desktop Pro payment confirmed/)).toBeVisible();
  await waitFor(() =>
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["billing"] }),
  );
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["entitlements"] });
  expect(state.request).toHaveBeenCalledExactlyOnceWith(
    "/api/v1/billing/payments/order-1",
  );
});
it("polls pending state until IPN confirmation then stops", async () => {
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval"],
  });
  state.request
    .mockResolvedValueOnce(payment("checkout_created"))
    .mockResolvedValue(payment("paid"));
  show();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10);
  });
  expect(
    screen.getByRole("heading", { name: "Confirming payment" }),
  ).toBeVisible();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2510);
  });
  expect(
    screen.getByRole("heading", { name: "Payment successful" }),
  ).toBeVisible();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000);
  });
  expect(state.request).toHaveBeenCalledTimes(2);
});
it("bounds polling and never treats a success redirect as payment evidence", async () => {
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval"],
  });
  state.request.mockResolvedValue(payment("pending"));
  show();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(46000);
  });
  expect(
    screen.getByRole("heading", {
      name: "Payment confirmation is taking longer",
    }),
  ).toBeVisible();
  const calls = state.request.mock.calls.length;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000);
  });
  expect(state.request).toHaveBeenCalledTimes(calls);
  expect(screen.queryByText("Payment successful")).not.toBeInTheDocument();
});
it.each(["error", "cancel"] as const)(
  "%s redirect respects paid backend state",
  async (result) => {
    show(result);
    expect(
      await screen.findByRole("heading", { name: "Payment successful" }),
    ).toBeVisible();
    expect(
      state.request.mock.calls.every(([path]) => !path.includes("checkout")),
    ).toBe(true);
  },
);
it.each([
  ["error", "Payment was not confirmed"],
  ["cancel", "Checkout cancelled"],
] as const)("%s shows non-success for pending", async (result, title) => {
  state.request.mockResolvedValue(payment("pending"));
  show(result);
  expect(await screen.findByRole("heading", { name: title })).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Return to Change Plan" }),
  ).toHaveAttribute("href", "/app/change-plan");
});
it("displays reconciliation and fetch failures without claiming success", async () => {
  state.request.mockResolvedValue(payment("review_required"));
  show();
  expect(
    await screen.findByRole("heading", { name: "Payment needs review" }),
  ).toBeVisible();
});
it("handles a missing order reference without fetching", () => {
  state.orderId = null;
  show();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Payment reference is missing",
  );
  expect(state.request).not.toHaveBeenCalled();
});
it("handles a status fetch failure", async () => {
  state.request.mockRejectedValue(new Error("Unavailable"));
  show();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Unable to load payment status",
  );
});
