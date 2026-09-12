import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Providers } from "@/components/providers";
import { ApiError } from "@/lib/api/client";
import { TrackedSiteDetail } from "./site-detail";
import { TrackedSiteForm } from "./site-form";
import { TrackedSiteList } from "./site-list";
import type { TrackedSite } from "./types";
const { replace, request, refresh } = vi.hoisted(() => ({
  replace: vi.fn(),
  request: vi.fn(),
  refresh: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    isAuthenticated: true,
    error: null,
    request,
    refresh,
  }),
}));
const site: TrackedSite = {
  id: "site-1",
  name: "SEO Site A",
  status: "active",
  primary_domain: "old.example",
  domain_alias_count: 0,
  domains: [
    {
      id: "old-1",
      domain: "old.example",
      is_primary: true,
      active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const view = (node: React.ReactNode) => render(<Providers>{node}</Providers>);
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal(
    "confirm",
    vi.fn(() => true),
  );
});

it("lists tracked sites with primary domain, alias count, and actions", async () => {
  request.mockResolvedValue({
    items: [site],
    next_cursor: null,
    has_more: false,
  });
  view(<TrackedSiteList />);
  expect(await screen.findByText("SEO Site A")).toBeVisible();
  expect(screen.getByText("old.example")).toBeVisible();
  expect(screen.getByRole("button", { name: "Archive" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Delete" })).toBeVisible();
});

it("creates a site with primary and alias domains", async () => {
  request.mockResolvedValue(site);
  view(<TrackedSiteForm />);
  fireEvent.change(screen.getByLabelText("Site Name"), {
    target: { value: "SEO Site A" },
  });
  fireEvent.change(screen.getByLabelText("Primary Domain"), {
    target: { value: "new.example" },
  });
  fireEvent.change(screen.getByLabelText("Previous / Alias Domains"), {
    target: { value: "old.example\nolder.example" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Add tracked site" }));
  await waitFor(() =>
    expect(replace).toHaveBeenCalledWith("/app/tracked-sites/site-1"),
  );
  expect(JSON.parse(String(request.mock.calls[0][1].body))).toEqual({
    name: "SEO Site A",
    primary_domain: "new.example",
    aliases: ["old.example", "older.example"],
  });
});

it("supports the 301 flow by adding and promoting a new domain", async () => {
  const promoted = {
    ...site.domains[0],
    id: "new-1",
    domain: "new.example",
    is_primary: true,
  };
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (!options) return site;
    if (path.endsWith("/domains") && options.method === "POST")
      return { ...promoted, is_primary: false };
    if (path.endsWith("/new-1") && options.method === "PATCH") return promoted;
    return site;
  });
  view(<TrackedSiteDetail siteId="site-1" />);
  await screen.findByRole("heading", { name: "SEO Site A" });
  expect(screen.getAllByText("old.example")[0]).toBeVisible();
  fireEvent.change(screen.getByLabelText("Domain"), {
    target: { value: "new.example" },
  });
  fireEvent.click(screen.getByLabelText("Make primary"));
  fireEvent.submit(screen.getByRole("form", { name: "Add domain" }));
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/tracked-sites/site-1/domains",
      expect.objectContaining({
        body: '{"domain":"new.example","make_primary":true}',
      }),
    ),
  );
});

it("exposes primary-domain safeguards in domain controls", async () => {
  request.mockResolvedValue(site);
  view(<TrackedSiteDetail siteId="site-1" />);
  await screen.findByRole("heading", { name: "SEO Site A" });
  expect(screen.getByRole("button", { name: "Deactivate" })).toBeDisabled();
  expect(
    screen.queryByRole("button", { name: "Make primary" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("PRIMARY")).toBeVisible();
});

it("allows an alias to deactivate and reactivate", async () => {
  let alias = {
    ...site.domains[0],
    id: "alias-1",
    domain: "alias.example",
    is_primary: false,
  };
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (options?.method === "PATCH" && path.endsWith("alias-1")) {
      alias = { ...alias, ...JSON.parse(String(options.body)) };
      return alias;
    }
    return {
      ...site,
      domain_alias_count: 1,
      domains: [...site.domains, alias],
    };
  });
  view(<TrackedSiteDetail siteId="site-1" />);
  await screen.findByRole("heading", { name: "SEO Site A" });
  const cards = screen.getAllByRole("article");
  const target = cards.find((card) =>
    card.textContent?.includes("alias.example"),
  );
  expect(target).toBeDefined();
  fireEvent.click(within(target!).getByRole("button", { name: "Deactivate" }));
  const activate = await screen.findByRole("button", { name: "Activate" });
  fireEvent.click(activate);
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      "/api/v1/tracked-sites/site-1/domains/alias-1",
      expect.objectContaining({ body: '{"active":true}' }),
    ),
  );
});

it("displays a duplicate-domain API error", async () => {
  request
    .mockResolvedValueOnce(site)
    .mockRejectedValueOnce(
      new ApiError(
        409,
        "DOMAIN_ALREADY_TRACKED",
        "This domain is already tracked in your account.",
      ),
    );
  view(<TrackedSiteDetail siteId="site-1" />);
  await screen.findByRole("heading", { name: "SEO Site A" });
  fireEvent.change(screen.getByLabelText("Domain"), {
    target: { value: "old.example" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Add domain" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("already tracked");
});
