import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InvoiceDetailPage, InvoicesPage } from "./invoices-page";
import type { InvoiceDetail } from "./invoices";

const state = vi.hoisted(() => ({
  request: vi.fn(),
  download: vi.fn(),
  replace: vi.fn(),
  status: "authenticated",
  verified: true,
  userId: "user-1",
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: state.replace }),
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    isAuthenticated: state.status === "authenticated",
    status: state.status,
    user: { id: state.userId, email_verified: state.verified },
    request: state.request,
    download: state.download,
    refresh: vi.fn(),
    error: null,
  }),
}));
const invoice: InvoiceDetail = {
  id: "invoice-1",
  invoice_number: "PAY_TEST_1",
  status: "paid",
  product_line: "desktop",
  plan_code: "desktop_starter",
  plan_name: "Desktop Starter",
  amount_minor: 495330,
  currency: "VND",
  provider: "sepay",
  provider_environment: "sandbox",
  created_at: "2026-10-12T00:00:00Z",
  updated_at: "2026-10-12T01:00:00Z",
  paid_at: "2026-10-12T01:00:00Z",
  expires_at: "2026-10-12T00:45:00Z",
  cancelled_at: null,
  failed_at: null,
  account_email: "buyer@example.test",
  payment_method: "CARD",
  provider_order_id: "order-123",
  provider_transaction_id: "transaction-123",
  provider_transaction_uuid: null,
  terms: {
    billing_months: 1,
    max_projects: 5,
    max_keywords: 100,
    monthly_keyword_checks: 1000,
    scheduled_checks_enabled: true,
    max_scheduled_frequency: "weekly",
  },
};
const page = (items = [invoice], next: string | null = null) => ({
  items,
  has_more: !!next,
  next_cursor: next,
});
function show(detail = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = () => (
    <QueryClientProvider client={client}>
      {detail ? <InvoiceDetailPage invoiceId="invoice-1" /> : <InvoicesPage />}
    </QueryClientProvider>
  );
  const result = render(view());
  return { ...result, refreshView: () => result.rerender(view()) };
}
beforeEach(() => {
  vi.resetAllMocks();
  state.status = "authenticated";
  state.verified = true;
  state.userId = "user-1";
  state.request.mockResolvedValue(page());
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("lists invoices, links details and keeps Sandbox and paid state visible", async () => {
  show();
  expect(
    await screen.findByRole("link", { name: "PAY_TEST_1" }),
  ).toHaveAttribute("href", "/app/invoices/invoice-1");
  expect(screen.getByText("Sandbox", { selector: "span" })).toBeVisible();
  expect(screen.getByText("Paid", { selector: "span" })).toBeVisible();
  expect(screen.getByText(/495\.330/)).toBeVisible();
  expect(state.request).toHaveBeenCalledExactlyOnceWith(
    "/api/v1/billing/invoices?limit=20",
  );
});

it("loads the next cursor and resets pagination when filtering", async () => {
  state.request
    .mockResolvedValueOnce(page([invoice], "next-cursor"))
    .mockResolvedValueOnce(
      page([{ ...invoice, id: "invoice-2", invoice_number: "PAY_TEST_2" }]),
    )
    .mockResolvedValue(page([]));
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Load more" }));
  expect(await screen.findByRole("link", { name: "PAY_TEST_2" })).toBeVisible();
  expect(screen.getByRole("link", { name: "PAY_TEST_1" })).toBeVisible();
  expect(state.request).toHaveBeenCalledWith(
    "/api/v1/billing/invoices?limit=20&cursor=next-cursor",
  );
  fireEvent.change(screen.getByLabelText("Payment status"), {
    target: { value: "failed" },
  });
  expect(await screen.findByText("No invoices found")).toBeVisible();
  expect(state.request).toHaveBeenLastCalledWith(
    "/api/v1/billing/invoices?limit=20&status=failed",
  );
  expect(screen.queryByText("PAY_TEST_1")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Product line"), {
    target: { value: "mobile" },
  });
  fireEvent.change(screen.getByLabelText("Environment"), {
    target: { value: "sandbox" },
  });
  await waitFor(() =>
    expect(state.request).toHaveBeenLastCalledWith(
      "/api/v1/billing/invoices?limit=20&status=failed&product_line=mobile&environment=sandbox",
    ),
  );
});

it("renders immutable terms and provider references in details", async () => {
  state.request.mockResolvedValue(invoice);
  show(true);
  expect(await screen.findByText("transaction-123")).toBeVisible();
  expect(screen.getByText("buyer@example.test")).toBeVisible();
  expect(screen.getByText("Desktop Starter")).toBeVisible();
  expect(screen.getByText("Plan terms at checkout")).toBeVisible();
  expect(screen.getByText("1 month(s)")).toBeVisible();
  expect(screen.getByText(/Sandbox test transaction/)).toBeVisible();
  expect(state.request).toHaveBeenCalledExactlyOnceWith(
    "/api/v1/billing/invoices/invoice-1",
  );
});

it("does not present pending or voided transactions as completed payments", async () => {
  state.request.mockResolvedValue({ ...invoice, status: "voided" });
  show(true);
  expect(await screen.findByText("Voided")).toBeVisible();
  expect(
    screen.getByText(/Payment is not currently confirmed as completed/),
  ).toBeVisible();
  expect(
    screen.queryByText(/Payment confirmed by SePay/),
  ).not.toBeInTheDocument();
});

it("downloads authenticated PDF with filename and releases its blob URL", async () => {
  const blob = new Blob(["%PDF-test"], { type: "application/pdf" });
  state.download.mockResolvedValue({
    blob,
    filename: "invoice-PAY_TEST_1.pdf",
  });
  const create = vi.fn().mockReturnValue("blob:test");
  const revoke = vi.fn();
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = create;
      static revokeObjectURL = revoke;
    },
  );
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("invoice-PAY_TEST_1.pdf");
      expect(this.href).toBe("blob:test");
    });
  show();
  fireEvent.click(
    await screen.findByRole("button", { name: "Download PDF for PAY_TEST_1" }),
  );
  await waitFor(() => expect(click).toHaveBeenCalledOnce());
  expect(state.download).toHaveBeenCalledExactlyOnceWith(
    "/api/v1/billing/invoices/invoice-1/pdf",
  );
  expect(create).toHaveBeenCalledWith(blob);
  expect(revoke).toHaveBeenCalledExactlyOnceWith("blob:test");
});

it("allows retry after export fails and disables duplicate exports while downloading", async () => {
  let reject!: (reason: Error) => void;
  state.download
    .mockReturnValueOnce(
      new Promise((_, rejectPromise) => {
        reject = rejectPromise;
      }),
    )
    .mockRejectedValue(new Error("Export failed"));
  show();
  const button = await screen.findByRole("button", {
    name: "Download PDF for PAY_TEST_1",
  });
  fireEvent.click(button);
  expect(button).toBeDisabled();
  fireEvent.click(button);
  expect(state.download).toHaveBeenCalledOnce();
  reject(new Error("Export failed"));
  expect(await screen.findByText("Export failed")).toBeVisible();
  expect(button).toBeEnabled();
  fireEvent.click(button);
  await waitFor(() => expect(state.download).toHaveBeenCalledTimes(2));
});

it.each(["list", "detail"])(
  "blocks %s requests for unverified and anonymous sessions",
  async (mode) => {
    state.verified = false;
    const view = show(mode === "detail");
    expect(screen.getByText(/Redirecting to email verification/)).toBeVisible();
    expect(state.replace).toHaveBeenCalledWith("/verify-email");
    expect(state.request).not.toHaveBeenCalled();
    state.status = "anonymous";
    view.refreshView();
    expect(screen.getByText(/Redirecting to login/)).toBeVisible();
    expect(state.request).not.toHaveBeenCalled();
  },
);

it("isolates cached invoices when account identity changes", async () => {
  const view = show();
  expect(await screen.findByText("PAY_TEST_1")).toBeVisible();
  state.userId = "user-2";
  state.request.mockResolvedValue(page([]));
  view.refreshView();
  expect(screen.queryByText("PAY_TEST_1")).not.toBeInTheDocument();
  expect(await screen.findByText("No invoices found")).toBeVisible();
});

it("shows failures with a retry that can recover", async () => {
  state.request
    .mockRejectedValueOnce(new Error("Service unavailable"))
    .mockResolvedValue(page());
  show();
  expect(await screen.findByText("Unable to load invoices.")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("PAY_TEST_1")).toBeVisible();
});
