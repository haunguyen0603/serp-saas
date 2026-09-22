import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import type { Project } from "@/features/projects/types";
import { ProjectAnalytics } from "./project-analytics";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    isAuthenticated: true,
    error: null,
    request,
    refresh: vi.fn(),
  }),
}));

const project: Project = {
  id: "project-1",
  name: "Analytics",
  search_engine: "google",
  country_code: "VN",
  language_code: "vi",
  device: "desktop",
  location: null,
  status: "active",
  keyword_count: 6,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const summary = {
  project_id: project.id,
  device: "desktop",
  range: "30d",
  as_of: "2026-09-22T00:00:00Z",
  comparison_basis: "range_boundary",
  total_keywords: 6,
  observed_keywords: 6,
  never_checked: 0,
  ranked_keywords: 5,
  not_found_in_depth: 1,
  top_3: 2,
  top_10: 5,
  improved: 1,
  declined: 1,
  unchanged: 2,
  newly_ranked: 1,
  lost_ranking: 1,
  entered_checked_depth: 1,
  left_checked_depth: 1,
  no_previous_data: 0,
  distribution: {
    effective_depth: 10,
    buckets: { top_3: 2, positions_4_10: 3, not_found_in_depth: 1 },
  },
};

beforeEach(() => {
  vi.resetAllMocks();
  request.mockImplementation(async (path: string) =>
    path.includes("/movers")
      ? {
          winners: [
            {
              keyword_id: "keyword-1",
              keyword: "winner",
              tracked_site_id: "site-1",
              tracked_site_name: "Owned site",
              previous_position: 9,
              current_position: 2,
              change: 7,
            },
          ],
          losers: [
            {
              keyword_id: "keyword-2",
              keyword: "loser",
              tracked_site_id: "site-1",
              tracked_site_name: "Owned site",
              previous_position: 2,
              current_position: 8,
              change: -6,
            },
          ],
        }
      : summary,
  );
});

it("renders depth-aware summary, distribution, and numeric movers", async () => {
  render(
    <Providers>
      <ProjectAnalytics project={project} />
    </Providers>,
  );
  expect(await screen.findByText("Ranking distribution")).toBeVisible();
  expect(screen.getAllByText("Not found in Top 10")).toHaveLength(2);
  expect(screen.queryByText("Top 100")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "winner" })).toHaveAttribute(
    "href",
    "#keyword-keyword-1",
  );
  const winners = screen.getByRole("table", { name: "Biggest Winners" });
  expect(within(winners).getByText("Improved 7")).toBeVisible();
  const losers = screen.getByRole("table", { name: "Biggest Losers" });
  expect(within(losers).getByText("Declined 6")).toBeVisible();
});

it("switches between keyboard-accessible analytics ranges", async () => {
  render(
    <Providers>
      <ProjectAnalytics project={project} />
    </Providers>,
  );
  await screen.findByText("Ranking distribution");
  fireEvent.click(screen.getByRole("tab", { name: "7D" }));
  expect(screen.getByRole("tab", { name: "7D" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(request).toHaveBeenCalledWith(expect.stringContaining("range=7d"));
});
