import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { RankingExplorer } from "./ranking-explorer";

const { push, replace, request, refresh, state } = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  request: vi.fn(),
  refresh: vi.fn(),
  state: { query: "" },
}));
let explorerMode: "success" | "empty" | "error" | "loading" = "success";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  usePathname: () => "/app/projects/project-1/rankings",
  useSearchParams: () => new URLSearchParams(state.query),
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    isAuthenticated: true,
    error: null,
    request,
    refresh,
  }),
}));

const project = {
  id: "project-1",
  name: "Explorer Project",
  search_engine: "google",
  country_code: "VN",
  language_code: "vi",
  device: "desktop",
  location: null,
  status: "active",
  keyword_count: 2,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const observation = {
  checked_at: "2026-09-22T00:00:00Z",
  position: 2,
  status: "ranked",
  depth: 10,
  rank_check_id: "check-current",
};
const response = {
  project_id: project.id,
  device: "desktop",
  range: "30d",
  compare_from: null,
  compare_to: null,
  comparison_basis: "range_boundary",
  effective_depth: 10,
  supported_position_buckets: ["top_3", "positions_4_10", "not_found_in_depth"],
  summary: {
    total: 2,
    improved: 1,
    declined: 0,
    unchanged: 0,
    entered_checked_depth: 0,
    left_checked_depth: 1,
    no_previous_data: 0,
    never_checked: 0,
  },
  page: { limit: 50, next_cursor: "next-page" },
  items: [
    {
      keyword_id: "keyword-1",
      keyword: "vinfast winner",
      keyword_status: "active",
      tracked_site: { id: "site-1", name: "CafeBiz" },
      device: "desktop",
      comparison: { ...observation, position: 8, rank_check_id: "check-old" },
      current: observation,
      movement: { type: "improved", change: 6 },
    },
    {
      keyword_id: "keyword-2",
      keyword: "vinfast left",
      keyword_status: "active",
      tracked_site: { id: "site-1", name: "CafeBiz" },
      device: "desktop",
      comparison: { ...observation, position: 4, rank_check_id: "check-old-2" },
      current: { ...observation, position: null, status: "not_found_in_depth" },
      movement: { type: "left_checked_depth", change: null },
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  state.query = "";
  explorerMode = "success";
  request.mockImplementation(async (path: string) => {
    if (path === "/api/v1/projects/project-1") return project;
    if (path.startsWith("/api/v1/tracked-sites"))
      return {
        items: [
          {
            id: "site-1",
            name: "CafeBiz",
            status: "active",
            primary_domain: "cafebiz.example",
            domain_alias_count: 0,
            domains: [],
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      };
    if (path.includes("/ranking-explorer")) {
      if (explorerMode === "error") throw new Error("Explorer unavailable");
      if (explorerMode === "loading") return await new Promise(() => {});
      if (explorerMode === "empty")
        return {
          ...response,
          summary: {
            ...response.summary,
            total: 0,
            improved: 0,
            left_checked_depth: 0,
          },
          page: { limit: 50, next_cursor: null },
          items: [],
        };
      return response;
    }
    if (path.includes("/ranking-history"))
      return {
        keyword_id: "keyword-1",
        keyword: "vinfast winner",
        tracked_site: { id: "site-1", name: "CafeBiz" },
        device: "desktop",
        range: "30d",
        points: [
          {
            checked_at: observation.checked_at,
            position: 2,
            status: "ranked",
            checked_depth: 10,
            rank_check_id: "check-current",
          },
        ],
      };
    if (path.includes("/rank-checks"))
      return { items: [], next_cursor: null, has_more: false };
    throw new Error(`Unexpected request: ${path}`);
  });
});

const view = () =>
  render(
    <Providers>
      <RankingExplorer projectId="project-1" />
    </Providers>,
  );

it("renders depth-aware comparison rows, sorting, pagination, and history", async () => {
  view();
  expect(
    await screen.findByRole("heading", { name: "Ranking Explorer" }),
  ).toBeVisible();
  expect(screen.getByText("2 results")).toBeVisible();
  const table = screen.getByRole("table", { name: "Ranking comparison" });
  expect(within(table).getByText("Not found in Top 10")).toBeVisible();
  expect(within(table).getByText("Left Top 10")).toBeVisible();
  const keyword = within(table).getByRole("button", { name: "vinfast winner" });
  expect(keyword).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(keyword);
  expect(
    await screen.findByRole("region", { name: "Ranking history" }),
  ).toBeVisible();
  expect(keyword).toHaveAttribute("aria-expanded", "true");
  expect(
    await screen.findByRole("img", { name: /Ranking positions/ }),
  ).toBeVisible();
  const secondKeyword = within(table).getByRole("button", {
    name: "vinfast left",
  });
  fireEvent.click(secondKeyword);
  expect(
    await screen.findByText("Ranking history · vinfast left"),
  ).toBeVisible();
  expect(keyword).toHaveAttribute("aria-expanded", "false");
  expect(secondKeyword).toHaveAttribute("aria-expanded", "true");

  fireEvent.click(within(table).getByRole("button", { name: "Current" }));
  expect(push).toHaveBeenCalledWith(
    expect.stringContaining("sort=current_position"),
    { scroll: false },
  );
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  expect(push).toHaveBeenCalledWith(
    expect.stringContaining("cursor=next-page"),
    {
      scroll: false,
    },
  );
});

it("drives filters from URL, debounces search, exposes chips, and clears them", async () => {
  state.query =
    "movement=improved&position_bucket=top_3&tracked_site_id=site-1&q=vinfast";
  view();
  await screen.findByText("2 results");
  expect(screen.getByLabelText("Movement")).toHaveValue("improved");
  expect(screen.getByLabelText("Current position")).toHaveValue("top_3");
  expect(screen.getByLabelText("Tracked Site")).toHaveValue("site-1");
  expect(
    screen.getByRole("button", { name: "Remove Improved filter" }),
  ).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Remove Improved filter" }),
  );
  expect(push).toHaveBeenCalledWith(expect.not.stringContaining("movement="), {
    scroll: false,
  });
  fireEvent.change(screen.getByLabelText("Search Keywords"), {
    target: { value: "electric car" },
  });
  await waitFor(
    () =>
      expect(push).toHaveBeenCalledWith(
        expect.stringContaining("q=electric+car"),
        { scroll: false },
      ),
    { timeout: 1000 },
  );
  fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
  expect(push).toHaveBeenCalledWith("/app/projects/project-1/rankings", {
    scroll: false,
  });
});

it("shows custom UTC dates and a collapsible mobile filter panel", async () => {
  state.query = "range=custom&compare_from=2026-08-01&compare_to=2026-09-01";
  view();
  await screen.findByText("2 results");
  expect(screen.getByLabelText("Date comparison")).toHaveValue("custom");
  expect(screen.getByLabelText("From date (UTC)")).toHaveValue("2026-08-01");
  expect(screen.getByLabelText("To date (UTC)")).toHaveValue("2026-09-01");
  const filters = screen.getByRole("button", { name: "Filters" });
  expect(filters).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(filters);
  expect(filters).toHaveAttribute("aria-expanded", "true");
  fireEvent.change(screen.getByLabelText("Sort by"), {
    target: { value: "current_position" },
  });
  expect(push).toHaveBeenCalledWith(
    expect.stringContaining("sort=current_position"),
    { scroll: false },
  );
});

it("keeps the Explorer local while the result query is loading", async () => {
  explorerMode = "loading";
  view();
  expect(
    await screen.findByRole("status", { name: "Loading ranking results…" }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Ranking Explorer" }),
  ).toBeVisible();
});

it("shows a filter-aware empty state without starting a Rank Check", async () => {
  explorerMode = "empty";
  state.query = "q=missing";
  view();
  expect(
    await screen.findByRole("heading", {
      name: "No Keywords match these filters",
    }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Clear filters" })).toBeVisible();
  expect(
    request.mock.calls.some(([path]) => String(path).includes("rank-check")),
  ).toBe(false);
});

it("keeps Explorer errors local and retries the query", async () => {
  explorerMode = "error";
  view();
  expect(
    await screen.findByText("Unable to load ranking results."),
  ).toBeVisible();
  explorerMode = "success";
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("2 results")).toBeVisible();
});
