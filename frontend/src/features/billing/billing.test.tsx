import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BillingPage } from "./billing-page";
import { CustomerList } from "@/features/admin/customers/customer-list";
import { CustomerBilling } from "@/features/admin/billing/customer-billing";

const state = vi.hoisted(() => ({ admin: false, request: vi.fn() }));
vi.mock("@/features/projects/protected", () => ({
  useProtectedAuth: () => ({
    isAuthenticated: true,
    user: { id: "user", is_platform_admin: state.admin },
    request: state.request,
  }),
}));
const summary = {
  user_id: "user",
  email: "customer@example.com",
  account_status: "active",
  devices: ["desktop", "mobile"].map((device) => ({
    device_scope: device,
    subscription_id: device,
    plan: {
      code: `${device}_starter`,
      name: `${device === "desktop" ? "Desktop" : "Mobile"} Starter`,
      device_scope: device,
      price_monthly_minor_units: device === "desktop" ? 1900 : 3900,
      currency: "USD",
      max_projects: 5,
      max_keywords: 500,
      monthly_keyword_checks: 5000,
      scheduled_checks_enabled: true,
      max_scheduled_frequency: "weekly",
    },
    status: "active",
    period_start: "2026-09-12T00:00:00Z",
    period_end: "2026-10-12T00:00:00Z",
    projects_used: 2,
    keywords_used: 40,
    over_limit: false,
    usage: {
      used: 17,
      limit: 5000,
      reserved: 3,
      remaining: 4980,
      period_end: "2026-10-12T00:00:00Z",
    },
  })),
};
function show(component: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {component}
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  state.admin = false;
  state.request.mockReset();
  state.request.mockImplementation(async (path: string) => {
    if (path.endsWith("/subscriptions")) return [];
    if (path.endsWith("/usage")) return { events: [], audit: [] };
    if (path.endsWith("/plans")) return summary.devices.map((d) => d.plan);
    if (path.includes("customers?"))
      return { items: [summary], has_more: true, next_cursor: "next" };
    return summary;
  });
});
describe("Billing & Usage", () => {
  it("shows independent prices, usage, reset and entitlements without admin actions", async () => {
    show(<BillingPage />);
    expect(await screen.findByText("Desktop Starter")).toBeInTheDocument();
    expect(screen.getByText("Mobile Starter")).toBeInTheDocument();
    expect(screen.getByText(/\$19.00/)).toBeInTheDocument();
    expect(screen.getByText(/\$39.00/)).toBeInTheDocument();
    expect(screen.getAllByText("17 / 5000")).toHaveLength(2);
    expect(screen.getAllByText("4980")).toHaveLength(2);
    expect(screen.getAllByText("Next reset")).toHaveLength(2);
    expect(screen.getAllByText("Up to weekly")).toHaveLength(2);
    expect(
      screen.queryByRole("button", { name: "Activate Plan" }),
    ).not.toBeInTheDocument();
  });
  it("denies normal users on both admin pages without requesting billing mutations", () => {
    const view = show(<CustomerList />);
    expect(
      screen.getByText("Administrator access required"),
    ).toBeInTheDocument();
    view.unmount();
    show(<CustomerBilling userId="user" />);
    expect(
      screen.getByText("Administrator access required"),
    ).toBeInTheDocument();
    expect(state.request).not.toHaveBeenCalled();
  });
  it("loads customers and supports email search and cursor pagination", async () => {
    state.admin = true;
    show(<CustomerList />);
    expect(await screen.findByText("customer@example.com")).toHaveAttribute(
      "href",
      "/admin/customers/user",
    );
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() =>
      expect(state.request).toHaveBeenCalledWith(
        expect.stringContaining("cursor=next"),
      ),
    );
    fireEvent.change(screen.getByLabelText("Search email"), {
      target: { value: "customer" },
    });
    await waitFor(() =>
      expect(state.request).toHaveBeenCalledWith(
        "/api/v1/admin/customers?search=customer",
      ),
    );
  });
  it("activates the selected device with bank reference and refreshes history", async () => {
    state.admin = true;
    show(<CustomerBilling userId="user" />);
    await screen.findByText("Desktop Starter");
    fireEvent.change(screen.getByLabelText("Plan"), {
      target: { value: "mobile_starter" },
    });
    fireEvent.change(screen.getByLabelText("Period end"), {
      target: { value: "2027-01-12T07:00" },
    });
    fireEvent.change(screen.getByLabelText("Payment reference"), {
      target: { value: "BANK-001" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Activate Plan" }));
    await waitFor(() =>
      expect(state.request).toHaveBeenCalledWith(
        "/api/v1/admin/customers/user/subscriptions",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"plan_code":"mobile_starter"'),
        }),
      ),
    );
    const call = state.request.mock.calls.find(
      (call) => call[1]?.method === "POST",
    );
    expect(JSON.parse(call![1].body)).toMatchObject({
      payment_method: "manual_bank_transfer",
      payment_reference: "BANK-001",
    });
    expect(await screen.findByText("Billing updated.")).toBeInTheDocument();
  });
  it("submits device-specific extension, cancellation and audited adjustment", async () => {
    state.admin = true;
    show(<CustomerBilling userId="user" />);
    await screen.findByText("Desktop Starter");
    fireEvent.change(screen.getByLabelText("Extend desktop until"), {
      target: { value: "2027-02-01T07:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Extend desktop" }));
    await screen.findByText("Billing updated.");
    expect(state.request).toHaveBeenCalledWith(
      "/api/v1/admin/customers/user/subscriptions/desktop/extend",
      expect.objectContaining({ method: "POST" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Cancel mobile subscription" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm action" }));
    await screen.findByText("Billing updated.");
    expect(state.request).toHaveBeenCalledWith(
      "/api/v1/admin/customers/user/subscriptions/mobile/cancel",
      expect.objectContaining({ method: "POST" }),
    );
    fireEvent.change(screen.getByLabelText("Checks to add or subtract"), {
      target: { value: "500" },
    });
    fireEvent.change(screen.getByLabelText("Adjustment reason"), {
      target: { value: "goodwill" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adjust usage" }));
    await waitFor(() =>
      expect(state.request).toHaveBeenCalledWith(
        "/api/v1/admin/customers/user/usage-adjustments",
        expect.objectContaining({
          body: JSON.stringify({
            device_scope: "desktop",
            amount: 500,
            note: "goodwill",
          }),
        }),
      ),
    );
  });
});
