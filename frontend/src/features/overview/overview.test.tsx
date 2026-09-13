import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Overview } from "./overview";
const request = vi.fn();
vi.mock("@/features/projects/protected", () => ({
  useProtectedAuth: () => ({
    isAuthenticated: true,
    user: { id: "customer" },
    request,
  }),
  ProtectedStatus: () => null,
}));
function view() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Overview />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  request.mockReset();
});
it("shows real empty workspace guidance and separate device allowances", async () => {
  request.mockResolvedValue({
    active_tracked_sites: 0,
    recent_batches: [],
    billing: {
      devices: ["desktop", "mobile"].map((device) => ({
        device_scope: device,
        status: "active",
        projects_used: 0,
        keywords_used: 0,
        plan: { name: device + " Free" },
        usage: {
          used: 0,
          limit: 100,
          reserved: 0,
          remaining: 100,
          period_end: "2026-10-01",
        },
      })),
    },
  });
  view();
  expect(await screen.findByText("Your first check starts here")).toBeVisible();
  expect(screen.getByText("desktop Free")).toBeVisible();
  expect(screen.getByText("mobile Free")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Add a Tracked Site" }),
  ).toBeVisible();
  expect(request).toHaveBeenCalledWith("/api/v1/overview");
});
it("offers a recoverable summary error", async () => {
  request.mockRejectedValue(new Error("offline"));
  view();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "summary could not be loaded",
  );
  expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
});
