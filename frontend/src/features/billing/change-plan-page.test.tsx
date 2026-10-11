import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import Page from "@/app/(en)/app/change-plan/page";
import { AppShell } from "@/design-system/app-shell";
import type { BillingSummary, Plan } from "./types";

const state = vi.hoisted(() => ({
  status: "authenticated",
  verified: true,
  userId: "user-1",
  request: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
  fetch: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: state.replace }),
  usePathname: () => "/app/change-plan",
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: state.status,
    isAuthenticated: state.status === "authenticated",
    isLoading: state.status === "loading",
    requiresEmailVerification: !state.verified,
    user:
      state.status === "authenticated"
        ? {
            id: state.userId,
            email_verified: state.verified,
            email: "qa@example.test",
          }
        : null,
    error: "Session could not be restored.",
    request: state.request,
    refresh: state.refresh,
  }),
}));

const plans: Plan[] = ["desktop", "mobile"].flatMap((device, di) =>
  ["free", "starter", "pro"].map((tier, ti) => ({
    id: `${device}-${tier}`,
    code: `${device}_${tier}`,
    name: `${device === "desktop" ? "Desktop" : "Mobile"} ${tier}`,
    device_scope: device as Plan["device_scope"],
    price_monthly_minor_units: ti ? 2789 + ti * 100 + di * 1000 : 0,
    currency: di ? "EUR" : "USD",
    max_projects: 2 + ti,
    max_keywords: 37 + ti * 101,
    monthly_keyword_checks: 1234 + ti * 222,
    scheduled_checks_enabled: ti > 0,
    max_scheduled_frequency: ti === 2 ? "daily" : ti === 1 ? "weekly" : "none",
  })),
);
function summary(desktop = "free", mobile = "free"): BillingSummary {
  return {
    user_id: state.userId,
    email: "qa@example.test",
    account_status: "active",
    devices: (["desktop", "mobile"] as const).map((device, i) => {
      const plan = {
        ...plans.find((p) => p.code === `${device}_${i ? mobile : desktop}`)!,
      };
      delete plan.id; // Backend snapshots contain code + scope, without catalog ID.
      return {
        device_scope: device,
        subscription_id: `${device}-sub`,
        plan,
        status: "active",
        period_start: "2026-10-01T00:00:00Z",
        period_end: plan.price_monthly_minor_units
          ? "2026-11-01T00:00:00Z"
          : null,
        projects_used: 0,
        keywords_used: 0,
        over_limit: false,
        usage: {
          id: device,
          period_start: "2026-10-01T00:00:00Z",
          period_end: "2026-11-01T00:00:00Z",
          limit: 100,
          used: 0,
          reserved: 0,
          remaining: 100,
          adjustment: 0,
        },
      };
    }),
  };
}
function show(shell = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const content = () => (
    <QueryClientProvider client={client}>
      {shell ? (
        <AppShell>
          <Page />
        </AppShell>
      ) : (
        <Page />
      )}
    </QueryClientProvider>
  );
  return { ...render(content()), rerenderPage: () => content() };
}
const card = (code: string) =>
  within(document.querySelector(`[data-plan-code="${code}"]`)! as HTMLElement);

beforeEach(() => {
  vi.clearAllMocks();
  state.status = "authenticated";
  state.verified = true;
  state.userId = "user-1";
  state.request.mockResolvedValue(summary());
  state.refresh.mockResolvedValue(undefined);
  state.fetch.mockImplementation(
    async () => new Response(JSON.stringify(plans)),
  );
  vi.stubGlobal("fetch", state.fetch);
});

it("allows verified users and includes an active sidebar link", async () => {
  show(true);
  expect(
    await screen.findByRole("heading", { level: 1, name: "Change Plan" }),
  ).toBeVisible();
  expect(
    screen
      .getByRole("navigation", { name: "Customer navigation" })
      .querySelector('[href="/app/change-plan"]'),
  ).toHaveAttribute("aria-current", "page");
  await screen.findByText("Current Desktop plan");
  expect(state.request).toHaveBeenCalledExactlyOnceWith("/api/v1/billing/me");
  expect(state.fetch).toHaveBeenCalledWith(
    "http://api.test/api/v1/billing/plans",
    expect.any(Object),
  );
});

it("redirects anonymous users to Login without requesting any billing data", async () => {
  state.status = "anonymous";
  show();
  await waitFor(() => expect(state.replace).toHaveBeenCalledWith("/login"));
  expect(state.request).not.toHaveBeenCalled();
  expect(state.fetch).not.toHaveBeenCalled();
  expect(screen.queryByText("Change Plan")).not.toBeInTheDocument();
});

it("gates unverified users even when the page is rendered without the shell", async () => {
  state.verified = false;
  show();
  await waitFor(() =>
    expect(state.replace).toHaveBeenCalledWith("/verify-email"),
  );
  expect(state.request).not.toHaveBeenCalled();
  expect(state.fetch).not.toHaveBeenCalled();
});

it("shows skeleton cards while the catalog loads", () => {
  state.fetch.mockImplementation(() => new Promise(() => {}));
  show();
  expect(
    screen.getAllByRole("status", { name: "Loading plans…" }),
  ).toHaveLength(3);
  expect(document.querySelectorAll("[data-plan-code]")).toHaveLength(0);
});

it("shows a recoverable session error and restores no catalog data", async () => {
  state.status = "error";
  show();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Session could not be restored.",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(state.refresh).toHaveBeenCalledOnce();
  expect(state.fetch).not.toHaveBeenCalled();
});

it.each(["free", "starter"])(
  "detects current %s plans by code and scope, with true disabled buttons",
  async (tier) => {
    state.request.mockResolvedValue(summary(tier, tier));
    show();
    await screen.findByText("Current Desktop plan");
    await screen.findAllByRole("button", { name: "Select" });
    expect(
      card(`desktop_${tier}`).getByRole("button", { name: "Current Plan" }),
    ).toBeDisabled();
    expect(
      card(`desktop_${tier}`).getByText("Current Plan", { selector: "span" }),
    ).toBeVisible();
    if (tier === "starter")
      expect(screen.getByText("Nov 1, 2026 (UTC)")).toBeVisible();
    else expect(screen.queryByText("Active until")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Mobile" }));
    expect(
      card(`mobile_${tier}`).getByRole("button", { name: "Current Plan" }),
    ).toBeDisabled();
    expect(
      document.querySelector('[data-plan-code="desktop_free"]'),
    ).toBeNull();
  },
);

it("renders actual prices, currencies and limits, switching scopes with keyboard", async () => {
  show();
  await screen.findAllByRole("button", { name: "Select" });
  expect(card("desktop_starter").getByText("$28.89")).toBeVisible();
  expect(card("desktop_starter").getByText("138")).toBeVisible();
  expect(card("desktop_starter").getByText("1,456")).toBeVisible();
  expect(card("desktop_free").getByText("Not included")).toBeVisible();
  expect(card("desktop_pro").getByText("Up to daily")).toBeVisible();
  fireEvent.keyDown(screen.getByRole("tab", { name: "Desktop" }), {
    key: "ArrowRight",
  });
  expect(screen.getByRole("tab", { name: "Mobile" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(card("mobile_starter").getByText("€38.89")).toBeVisible();
  expect(document.querySelectorAll("[data-plan-code]")).toHaveLength(3);
});

it("Select only opens information, restores focus on close, and makes ZERO new API calls", async () => {
  show();
  await screen.findByText("Current Desktop plan");
  await screen.findAllByRole("button", { name: "Select" });
  const before = {
    auth: state.request.mock.calls.length,
    public: state.fetch.mock.calls.length,
  };
  const trigger = card("desktop_starter").getByRole("button", {
    name: "Select",
  });
  trigger.focus();
  fireEvent.click(trigger);
  const modal = screen.getByRole("dialog", {
    name: "Plan upgrade coming soon",
  });
  expect(
    within(modal).getByText(/Your current subscription has not been changed/),
  ).toBeVisible();
  fireEvent.click(within(modal).getByRole("button", { name: "Close" }));
  expect(trigger).toHaveFocus();
  fireEvent.click(trigger);
  fireEvent(modal, new Event("cancel", { cancelable: true }));
  expect(modal).not.toHaveAttribute("open");
  expect(trigger).toHaveFocus();
  expect(state.request).toHaveBeenCalledTimes(before.auth);
  expect(state.fetch).toHaveBeenCalledTimes(before.public);
  for (const [, options] of [
    ...state.request.mock.calls,
    ...state.fetch.mock.calls,
  ]) {
    expect(options?.method ?? "GET").toBe("GET");
  }
  expect(
    card("desktop_free").getByRole("button", { name: "Current Plan" }),
  ).toBeDisabled();
});

it("catalog error shows no fallback prices, and Retry recovers authoritative data", async () => {
  state.fetch.mockResolvedValueOnce(new Response("{}", { status: 503 }));
  show();
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Unable to load plans.");
  expect(document.querySelectorAll("[data-plan-code]")).toHaveLength(0);
  expect(screen.queryByText("$0")).not.toBeInTheDocument();
  fireEvent.click(within(alert).getByRole("button", { name: "Retry" }));
  await screen.findAllByRole("button", { name: "Select" });
  expect(card("desktop_starter").getByText("$28.89")).toBeVisible();
});

it("never guesses the current plan on a subscription failure, and supports retry", async () => {
  state.request.mockRejectedValueOnce(new Error("Unavailable"));
  show();
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Unable to load your current subscription.");
  await screen.findAllByRole("button", { name: "Select" });
  expect(
    screen.queryByRole("button", { name: "Current Plan" }),
  ).not.toBeInTheDocument();
  fireEvent.click(within(alert).getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("button", { name: "Current Plan" }),
  ).toBeDisabled();
});

it("handles an empty catalog in both product lines", async () => {
  state.fetch.mockResolvedValue(new Response("[]"));
  show();
  await screen.findByText("No plans are currently available.");
  expect(document.querySelectorAll("[data-plan-code]")).toHaveLength(0);
  fireEvent.click(screen.getByRole("tab", { name: "Mobile" }));
  expect(screen.getByText("No plans are currently available.")).toBeVisible();
});

it("does not mark a missing subscription or an absent catalog plan as current", async () => {
  state.request.mockResolvedValue({ ...summary(), devices: [] });
  show();
  await screen.findByText("No current Desktop subscription was returned.");
  await screen.findAllByRole("button", { name: "Select" });
  expect(
    screen.queryByRole("button", { name: "Current Plan" }),
  ).not.toBeInTheDocument();
});

it("scopes current subscription queries to the signed-in account", async () => {
  const view = show();
  expect(
    await screen.findByRole("button", { name: "Current Plan" }),
  ).toBeDisabled();
  state.userId = "user-2";
  state.request.mockResolvedValue(summary("pro"));
  view.rerender(view.rerenderPage());
  await waitFor(() =>
    expect(
      card("desktop_pro").getByRole("button", { name: "Current Plan" }),
    ).toBeDisabled(),
  );
  expect(state.request).toHaveBeenCalledTimes(2);
  expect(
    card("desktop_free").getByRole("button", { name: "Select" }),
  ).toBeEnabled();
});
