import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import { PublicShell } from "@/design-system/public-shell";
import type { Plan } from "@/features/billing/types";
import { PricingCatalog, groupPlans } from "./pricing-catalog";

const state = vi.hoisted(() => ({ authenticated: false, request: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => "/pricing" }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ isAuthenticated: state.authenticated }),
}));
vi.mock("@/lib/api/client", () => ({ requestJson: state.request }));

const plans: Plan[] = [
  ["mobile", "pro", 24900, 10, 1000, 10000, "daily"],
  ["desktop", "free", 0, 1, 50, 100, "none"],
  ["mobile", "free", 0, 1, 20, 50, "none"],
  ["desktop", "pro", 12900, 20, 5000, 50000, "daily"],
  ["desktop", "starter", 1900, 5, 500, 5000, "weekly"],
  ["mobile", "starter", 3900, 3, 200, 1000, "weekly"],
].map(([device, tier, price, projects, keywords, checks, frequency]) => ({
  code: `${device}_${tier}`,
  name: `${String(device).replace(/^./, (c) => c.toUpperCase())} ${String(tier).replace(/^./, (c) => c.toUpperCase())}`,
  device_scope: device as "desktop" | "mobile",
  price_monthly_minor_units: Number(price),
  currency: "USD",
  max_projects: Number(projects),
  max_keywords: Number(keywords),
  monthly_keyword_checks: Number(checks),
  scheduled_checks_enabled: frequency !== "none",
  max_scheduled_frequency: String(frequency),
}));

function view(component: React.ReactNode) {
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
  state.authenticated = false;
  state.request.mockReset();
});

it("renders truthful Home sections and safe preview data", () => {
  render(<HomePage />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Track your Google rankings",
  );
  expect(screen.getByRole("heading", { name: /four steps/i })).toBeVisible();
  expect(
    screen.getByRole("heading", { name: /Desktop and Mobile rankings/i }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: /domain changes/i }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: /weekly or daily/i }),
  ).toBeVisible();
  expect(screen.getByText(/not available yet/i)).toBeVisible();
  expect(screen.getAllByText("seo-demo.com").length).toBeGreaterThan(0);
  expect(document.body).not.toHaveTextContent(
    /Serper|SerpApi|Cloud Tasks|real-time|unlimited/i,
  );
});

it("provides an accessible public mobile menu and accurate CTAs", () => {
  view(
    <PublicShell>
      <main>Page</main>
    </PublicShell>,
  );
  expect(screen.getByRole("link", { name: "Get Started" })).toHaveAttribute(
    "href",
    "/register",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Open public navigation" }),
  );
  const dialog = screen.getByRole("dialog", { name: "SERP SaaS" });
  expect(dialog).toBeVisible();
  expect(within(dialog).getByRole("link", { name: "Pricing" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  fireEvent(dialog, new Event("cancel", { bubbles: true, cancelable: true }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("groups all authoritative Plans by device and tier", () => {
  const grouped = groupPlans(plans);
  expect(grouped.map((group) => group.device)).toEqual(["desktop", "mobile"]);
  expect(grouped.map((group) => group.plans.map((plan) => plan.code))).toEqual([
    ["desktop_free", "desktop_starter", "desktop_pro"],
    ["mobile_free", "mobile_starter", "mobile_pro"],
  ]);
});

it("renders exact API values and logged-out manual activation CTAs", async () => {
  state.request.mockResolvedValue(plans);
  view(<PricingCatalog />);
  const desktopPro = await screen.findByRole("region", { name: "Desktop Pro" });
  expect(state.request).toHaveBeenCalledWith("/api/v1/billing/plans");
  expect(desktopPro).toHaveTextContent("$129");
  expect(desktopPro).toHaveTextContent("20 Projects");
  expect(desktopPro).toHaveTextContent("5,000 Keywords");
  expect(desktopPro).toHaveTextContent("50,000 monthly checks");
  expect(desktopPro).toHaveTextContent("Daily scheduling");
  expect(
    within(desktopPro).getByRole("link", {
      name: "Request Activation",
    }),
  ).toHaveAttribute("href", "/register");
  expect(screen.getAllByText("Manual bank-transfer activation")).toHaveLength(
    4,
  );
  expect(
    screen.getAllByRole("region", {
      name: /^(Desktop|Mobile) (Free|Starter|Pro)$/,
    }),
  ).toHaveLength(6);
});

it("sends authenticated paid customers to Billing without Admin actions", async () => {
  state.authenticated = true;
  state.request.mockResolvedValue(plans);
  view(<PricingCatalog />);
  const links = await screen.findAllByRole("link", {
    name: "Request Activation",
  });
  expect(links).toHaveLength(4);
  expect(
    links.every((link) => link.getAttribute("href") === "/settings/billing"),
  ).toBe(true);
  expect(
    screen.queryByRole("button", { name: /activate plan/i }),
  ).not.toBeInTheDocument();
});

it("shows a retryable error instead of fallback prices", async () => {
  state.request.mockRejectedValue(new Error("offline"));
  view(<PricingCatalog />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "authoritative Plan catalog",
  );
  expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
  expect(screen.queryByText("$19")).not.toBeInTheDocument();
});
