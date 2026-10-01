import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { CompetitorsPage } from "./competitors-page";

const { push, request, refresh, state } = vi.hoisted(() => ({
  push: vi.fn(),
  request: vi.fn(),
  refresh: vi.fn(),
  state: { query: "", configured: true },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/app/projects/project-1/competitors",
  useSearchParams: () => new URLSearchParams(state.query),
}));
vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
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
  name: "Competitor Project",
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
const trackedSites = [
  { id: "site-primary", name: "My Site", primary_domain: "mine.example" },
  {
    id: "site-competitor",
    name: "Competitor A",
    primary_domain: "other.example",
  },
].map((site) => ({
  ...site,
  status: "active",
  domain_alias_count: 0,
  domains: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
}));
const selection = {
  project_id: project.id,
  primary_site: {
    tracked_site_id: "site-primary",
    name: "My Site",
    primary_domain: "mine.example",
    role: "primary",
  },
  competitor_sites: [
    {
      tracked_site_id: "site-competitor",
      name: "Competitor A",
      primary_domain: "other.example",
      role: "competitor",
    },
  ],
  max_competitors: 5,
  selection_basis: "current_selection",
  historical_alias_semantics: "current_active_aliases",
};
const siteMetrics = [
  {
    tracked_site_id: "site-primary",
    name: "My Site",
    top_3: 1,
    top_n: 1,
    comparable_keywords: 2,
    observed_top_n_coverage_pct: 50,
    not_found_in_checked_depth: 1,
    not_observed: 0,
    ambiguous_match: 0,
  },
  {
    tracked_site_id: "site-competitor",
    name: "Competitor A",
    top_3: 1,
    top_n: 2,
    comparable_keywords: 2,
    observed_top_n_coverage_pct: 100,
    not_found_in_checked_depth: 0,
    not_observed: 0,
    ambiguous_match: 0,
  },
];
const overview = {
  project_id: project.id,
  device: "desktop",
  range: "30d",
  as_of: "2026-09-27T00:00:00Z",
  effective_depth: 10,
  top_n: 10,
  keyword_cohort: 2,
  qualifying_keywords: 2,
  partial_or_unobserved_keywords: 1,
  primary_site: selection.primary_site,
  sites: siteMetrics,
  comparisons: [
    {
      opponent_site_id: "site-competitor",
      opponent_name: "Competitor A",
      both_numeric_ranked: 1,
      primary_ahead: 1,
      tied: 0,
      competitor_ahead: 0,
      excluded_unpaired: 1,
      opportunities: 1,
    },
  ],
  coverage_quality: "partial",
  latest_successful_check_at: "2026-09-26T00:00:00Z",
};
const ranked = (id: string, name: string, position: number) => ({
  tracked_site_id: id,
  name,
  status: "ranked",
  position,
  checked_depth: 10,
  matched_url: `https://${id}.example/page`,
  matched_hostname: `${id}.example`,
});
const keywordList = {
  project_id: project.id,
  items: [
    {
      keyword_id: "keyword-1",
      keyword: "same check keyword",
      checked_at: "2026-09-26T00:00:00Z",
      rank_check_id: "check-1",
      checked_depth: 10,
      snapshot_complete: true,
      sites: [
        ranked("site-primary", "My Site", 2),
        ranked("site-competitor", "Competitor A", 5),
      ],
      opponent_site_id: "site-competitor",
      position_gap: 3,
      comparison_state: "my_site_ahead",
      opportunity: false,
    },
  ],
  next_cursor: null,
  has_more: false,
  total: 1,
  top_n: 10,
  opponent_site_id: "site-competitor",
};
const trends = {
  project_id: project.id,
  range: "30d",
  top_n: 10,
  gaps_are_not_interpolated: true,
  points: [
    {
      date: "2026-09-26",
      observed_keywords: 2,
      coverage_quality: "partial",
      sites: siteMetrics.map((site) => ({
        tracked_site_id: site.tracked_site_id,
        name: site.name,
        top_n_appearances: site.top_n,
        comparable_keywords: site.comparable_keywords,
        observed_top_n_coverage_pct: site.observed_top_n_coverage_pct,
        not_observed: site.not_observed,
      })),
    },
  ],
};

function mockApi() {
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/projects/project-1") return project;
    if (path.startsWith("/api/v1/tracked-sites"))
      return { items: trackedSites, next_cursor: null, has_more: false };
    if (path.endsWith("/keyword-groups") || path.endsWith("/keyword-tags"))
      return { items: [] };
    if (path.endsWith("/competitor-sites") && options?.method === "PUT")
      return selection;
    if (path.endsWith("/competitor-sites"))
      return state.configured
        ? selection
        : { ...selection, primary_site: null, competitor_sites: [] };
    if (path.includes("/competitors/overview")) return overview;
    if (path.includes("/competitors/trends")) return trends;
    if (path.includes("/observations"))
      return {
        project_id: project.id,
        keyword_id: "keyword-1",
        keyword: "same check keyword",
        rank_check_id: "check-1",
        checked_at: "2026-09-26T00:00:00Z",
        search_engine: "google",
        country_code: "VN",
        language_code: "vi",
        device: "desktop",
        location: null,
        checked_depth: 10,
        snapshot_complete: true,
        coverage_quality: "complete",
        sites: keywordList.items[0].sites.map((site) => ({
          ...site,
          matched_results: [
            {
              position: site.position,
              url: site.matched_url,
              hostname: site.matched_hostname,
              title: site.name,
            },
          ],
        })),
      };
    if (path.includes("/competitors/keywords")) return keywordList;
    throw new Error(`Unexpected request: ${path}`);
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  state.query = "";
  state.configured = true;
  mockApi();
});

const view = () =>
  render(
    <Providers>
      <CompetitorsPage projectId="project-1" />
    </Providers>,
  );

it("configures a primary site and bounded competitor selection", async () => {
  state.configured = false;
  view();
  expect(await screen.findByText("Select a primary site")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Primary site"), {
    target: { value: "site-primary" },
  });
  fireEvent.click(screen.getByLabelText("Competitor A"));
  fireEvent.click(screen.getByRole("button", { name: "Save selection" }));
  await waitFor(() =>
    expect(
      request.mock.calls.some(
        ([path, options]) =>
          String(path).endsWith("/competitor-sites") &&
          options?.method === "PUT" &&
          String(options.body).includes("site-competitor"),
      ),
    ).toBe(true),
  );
});

it("shows denominators, partial evidence, URL filters, and on-demand detail", async () => {
  view();
  expect(
    await screen.findByRole("heading", { name: "Competitors" }),
  ).toBeVisible();
  expect(await screen.findByText(/Partial coverage:/)).toBeVisible();
  expect(screen.getByText(/1 paired numeric keywords/)).toBeVisible();
  expect(screen.getByText("50%")).toBeVisible();
  expect(screen.getByText(/Missing UTC days are gaps/)).toBeVisible();

  fireEvent.change(screen.getByLabelText("Range"), { target: { value: "7d" } });
  expect(push).toHaveBeenCalledWith(
    "/app/projects/project-1/competitors?range=7d",
    { scroll: false },
  );

  fireEvent.click(screen.getByRole("button", { name: "same check keyword" }));
  expect(await screen.findByText(/complete snapshot/)).toBeVisible();
  expect(
    screen.getAllByRole("link", { name: /site-primary\.example/ }),
  ).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "same check keyword" }));
  await waitFor(() =>
    expect(screen.queryByText(/complete snapshot/)).toBeNull(),
  );
});

it("distinguishes a cohort with no successful observations", async () => {
  const original = request.getMockImplementation();
  request.mockImplementation((path: string, options?: RequestInit) => {
    if (path.includes("/competitors/overview"))
      return Promise.resolve({
        ...overview,
        qualifying_keywords: 0,
        partial_or_unobserved_keywords: 0,
        coverage_quality: "insufficient_data",
        latest_successful_check_at: null,
      });
    if (path.includes("/competitors/keywords"))
      return Promise.resolve({ ...keywordList, items: [], total: 0 });
    if (path.includes("/competitors/trends"))
      return Promise.resolve({ ...trends, points: [] });
    return original?.(path, options);
  });

  view();
  expect(
    await screen.findByText(/No successful observations exist in this range/),
  ).toBeVisible();
  expect(screen.getByText("No matching keyword observations")).toBeVisible();
});
