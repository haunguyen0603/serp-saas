import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PlanCatalog, type AdminPlan } from "./plan-catalog";

const state = vi.hoisted(() => ({ admin: true, request: vi.fn() }));
vi.mock("@/features/projects/protected", () => ({
  useProtectedAuth: () => ({
    isAuthenticated: true,
    status: "authenticated",
    user: { id: "admin", is_platform_admin: state.admin },
    request: state.request,
  }),
}));
const plans: AdminPlan[] = (["desktop", "mobile"] as const).flatMap((device) =>
  ["free", "starter", "pro"].map((tier) => ({
    code: `${device}_${tier}`,
    name: `${device === "desktop" ? "Desktop" : "Mobile"} ${tier[0].toUpperCase() + tier.slice(1)}`,
    device_scope: device,
    price_monthly_minor_units: tier === "free" ? 0 : 1900,
    currency: "USD",
    max_projects: 5,
    max_keywords: 500,
    monthly_keyword_checks: 5000,
    scheduled_checks_enabled: tier !== "free",
    max_scheduled_frequency: "weekly",
    updated_at: "2026-09-20T00:00:00Z",
  })),
);
function show() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <PlanCatalog />
    </QueryClientProvider>,
  );
  return client;
}
beforeEach(() => {
  state.admin = true;
  state.request.mockReset();
  state.request.mockImplementation(async (path: string) =>
    path.endsWith("/history") ? [] : plans,
  );
});

it("blocks normal users without requesting the catalog", () => {
  state.admin = false;
  show();
  expect(screen.getByText("Administrator access required")).toBeVisible();
  expect(state.request).not.toHaveBeenCalled();
});

it("edits six device-specific Plans and saves exact cents with the loaded version", async () => {
  const client = show();
  const form = await screen.findByRole("form", {
    name: "Edit Desktop Starter",
  });
  expect(screen.getAllByRole("form")).toHaveLength(6);
  expect(
    screen.getByText(/Existing subscriptions, including Free Plans/),
  ).toBeVisible();
  expect(
    within(
      screen.getByRole("form", { name: "Edit Mobile Free" }),
    ).getByLabelText(/Monthly price/),
  ).toHaveAttribute("readonly");
  const original = plans.find((p) => p.code === "desktop_starter")!;
  const saved = {
    ...original,
    price_monthly_minor_units: 2950,
    max_projects: 9,
    max_keywords: 999,
    monthly_keyword_checks: 9999,
    updated_at: "2026-09-20T01:00:00Z",
  };
  state.request.mockImplementation(
    async (path: string, options?: RequestInit) => {
      if (options?.method === "PATCH") return saved;
      return path.endsWith("/history") ? [] : plans;
    },
  );
  fireEvent.change(within(form).getByLabelText(/Monthly price/), {
    target: { value: "29.50" },
  });
  fireEvent.change(within(form).getByLabelText("Max projects"), {
    target: { value: "9" },
  });
  fireEvent.change(within(form).getByLabelText("Max keywords"), {
    target: { value: "999" },
  });
  fireEvent.change(within(form).getByLabelText("Monthly checks"), {
    target: { value: "9999" },
  });
  fireEvent.submit(form);
  await screen.findByText("Saved. New activations will use these terms.");
  expect(state.request).toHaveBeenCalledWith(
    "/api/v1/admin/plans/desktop_starter",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_updated_at: original.updated_at,
        price_monthly_minor_units: 2950,
        max_projects: 9,
        max_keywords: 999,
        monthly_keyword_checks: 9999,
      }),
    },
  );
  expect(
    client
      .getQueryData<AdminPlan[]>(["admin-plans", "admin"])
      ?.find((p) => p.code === "desktop_starter"),
  ).toEqual(saved);
  expect(
    within(
      screen.getByRole("form", { name: "Edit Mobile Starter" }),
    ).getByLabelText(/Monthly price/),
  ).toHaveValue(19);
});

it("keeps unsaved fields on conflict and reloads them explicitly", async () => {
  show();
  const form = await screen.findByRole("form", { name: "Edit Mobile Pro" });
  state.request.mockImplementation(
    async (path: string, options?: RequestInit) => {
      if (options?.method === "PATCH")
        throw new Error("This Plan has changed. Reload it before saving.");
      return path.endsWith("/history")
        ? []
        : plans.map((plan) => ({ ...plan, max_projects: 7 }));
    },
  );
  fireEvent.change(within(form).getByLabelText("Max projects"), {
    target: { value: "9" },
  });
  fireEvent.submit(form);
  expect(await screen.findByText(/This Plan has changed/)).toBeVisible();
  expect(within(form).getByLabelText("Max projects")).toHaveValue(9);
  fireEvent.click(
    screen.getByRole("button", { name: "Reload catalog (discard edits)" }),
  );
  await waitFor(() =>
    expect(
      within(
        screen.getByRole("form", { name: "Edit Mobile Pro" }),
      ).getByLabelText("Max projects"),
    ).toHaveValue(7),
  );
});

it("shows local loading, retryable catalog failure, and retries", async () => {
  state.request.mockImplementation(async () => {
    throw new Error("offline");
  });
  show();
  expect(
    screen.getByRole("status", { name: "Loading Plan catalog…" }),
  ).toBeVisible();
  expect(
    await screen.findByText("Plan catalog could not be loaded."),
  ).toBeVisible();
  state.request.mockImplementation(async (path: string) =>
    path.endsWith("/history") ? [] : plans,
  );
  fireEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
  expect(
    await screen.findByRole("form", { name: "Edit Desktop Starter" }),
  ).toBeVisible();
});
