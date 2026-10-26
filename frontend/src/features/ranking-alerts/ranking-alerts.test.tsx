import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { RankingAlertsPage } from "./ranking-alerts-page";
import { RankingAlertPreferences } from "./alert-preferences";
import { RankingAlertUnreadBadge } from "./unread-badge";
import { alertKeys, rankLabel } from "./api";

const { request, replace, state } = vi.hoisted(() => ({
  request: vi.fn(),
  replace: vi.fn(),
  state: { status: "authenticated" },
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/app/ranking-alerts",
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: state.status,
    isAuthenticated: state.status === "authenticated",
    user: { id: "owner" },
    error: null,
    request,
    refresh: vi.fn(),
  }),
}));
const alert = {
  id: "alert-1",
  project_id: "project-1",
  keyword_id: "keyword-1",
  tracked_site_id: "site-1",
  alert_type: "entered_top10",
  keyword: "từ khóa dài để theo dõi thứ hạng",
  project_name: "My Project",
  site_name: "My site",
  device: "desktop",
  previous_rank: null,
  current_rank: 7,
  rank_delta: null,
  observed_at: "2026-10-26T01:00:00Z",
  read_at: null,
};
const preferences = {
  enabled: true,
  notify_entered_top10: true,
  notify_left_top10: true,
  notify_improvement: true,
  notify_decline: true,
  movement_threshold: 3,
  email_enabled: false,
  email_available: false,
};
let mode = "success";
beforeEach(() => {
  vi.clearAllMocks();
  mode = "success";
  state.status = "authenticated";
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.includes("ranking-alert-preferences"))
      return options?.method === "PUT"
        ? { ...JSON.parse(options.body as string), email_available: false }
        : preferences;
    if (path.includes("unread-count")) return { count: 102 };
    if (path.includes("/api/v1/projects"))
      return {
        items: [{ id: "project-1", name: "My Project", device: "desktop" }],
        next_cursor: null,
        has_more: false,
      };
    if (options?.method) return { ...alert, read_at: "2026-10-26T02:00:00Z" };
    if (mode === "error") throw new Error("Offline");
    if (mode === "loading") return new Promise(() => {});
    return {
      items: mode === "empty" ? [] : [alert],
      next_cursor: path.includes("cursor=next") ? null : "next",
      has_more: !path.includes("cursor=next"),
    };
  });
});
function view() {
  return render(
    <Providers>
      <RankingAlertsPage />
    </Providers>,
  );
}
it("renders honest Top 10 positions, context and history link", async () => {
  view();
  expect(await screen.findByText(alert.keyword)).toBeInTheDocument();
  expect(screen.getByText("Not found in Top 10 → #7")).toBeInTheDocument();
  expect(
    screen.getByText("My Project · desktop · My site"),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "View ranking history" }),
  ).toHaveAttribute("href", expect.stringContaining("tracked_site_id=site-1"));
});
it("filters and paginates on server, resetting cursors", async () => {
  view();
  await screen.findByText(alert.keyword);
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      expect.stringContaining("cursor=next"),
    ),
  );
  fireEvent.change(screen.getByLabelText("Show"), {
    target: { value: "unread" },
  });
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      expect.stringContaining("unread_only=true"),
    ),
  );
  expect(request.mock.calls.at(-1)![0]).not.toContain("cursor=");
  fireEvent.change(screen.getByLabelText("Project"), {
    target: { value: "project-1" },
  });
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      expect.stringContaining("project_id=project-1"),
    ),
  );
});
it("marks individual and all alerts read", async () => {
  view();
  await screen.findByText(alert.keyword);
  fireEvent.click(
    screen.getByRole("button", { name: `Mark read: ${alert.keyword}` }),
  );
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/ranking-alerts/alert-1/read",
      { method: "PATCH" },
    ),
  );
  await screen.findByText("Read status updated.");
  fireEvent.click(screen.getByRole("button", { name: "Mark all read" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/ranking-alerts/mark-all-read",
      { method: "POST" },
    ),
  );
});
it("provides loading, empty and retry states", async () => {
  mode = "loading";
  const loading = view();
  expect(screen.getByLabelText("Loading ranking alerts…")).toBeInTheDocument();
  loading.unmount();
  mode = "empty";
  const empty = view();
  await screen.findByText("No ranking alerts yet");
  empty.unmount();
  mode = "error";
  view();
  await screen.findByText("Ranking alerts could not be loaded.");
  mode = "success";
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText(alert.keyword);
});
it("saves preferences and explains unavailable email", async () => {
  render(
    <Providers>
      <RankingAlertPreferences projectId="project-1" />
    </Providers>,
  );
  const threshold = await screen.findByLabelText(
    "Minimum movement (positions)",
  );
  expect(
    screen.getByText(/Email delivery is currently unavailable/),
  ).toBeInTheDocument();
  fireEvent.change(threshold, { target: { value: "5" } });
  fireEvent.click(screen.getByLabelText("Also email my verified account"));
  fireEvent.click(
    screen.getByRole("button", { name: "Save Alert Preferences" }),
  );
  await screen.findByText("Alert preferences saved.");
  const save = request.mock.calls.find(
    ([, options]) => options?.method === "PUT",
  )!;
  expect(JSON.parse(save[1].body)).toMatchObject({
    movement_threshold: 5,
    email_enabled: true,
    enabled: true,
  });
  expect(JSON.parse(save[1].body)).not.toHaveProperty("email_available");
});
it("shows unread badge with full accessible count", async () => {
  render(
    <Providers>
      <RankingAlertUnreadBadge />
    </Providers>,
  );
  expect(
    await screen.findByLabelText("102 unread ranking alerts"),
  ).toHaveTextContent("99+");
});
it("redirects anonymous sessions and scopes account caches", async () => {
  state.status = "anonymous";
  view();
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  expect(request).not.toHaveBeenCalled();
  expect(alertKeys("one")).not.toEqual(alertKeys("two"));
  expect(rankLabel(null)).toBe("Not found in Top 10");
});
