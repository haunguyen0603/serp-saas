import { expect, it, vi } from "vitest";
import type { AuthenticatedRequest } from "@/features/auth/session";
import {
  addTrackedDomain,
  createTrackedSite,
  deleteTrackedDomain,
  deleteTrackedSite,
  getTrackedSite,
  listTrackedSites,
  updateTrackedDomain,
  updateTrackedSite,
} from "./api";

it("uses authenticated user-global Tracked Site routes", async () => {
  const request = vi
    .fn()
    .mockResolvedValue({}) as unknown as AuthenticatedRequest;
  await createTrackedSite(request, {
    name: "Site",
    primary_domain: "new.example",
    aliases: ["old.example"],
  });
  await listTrackedSites(request, { status: "all", search: "Site" });
  await getTrackedSite(request, "site-1");
  await updateTrackedSite(request, "site-1", { status: "archived" });
  await addTrackedDomain(request, "site-1", {
    domain: "newer.example",
    make_primary: false,
  });
  await updateTrackedDomain(request, "site-1", "domain-1", {
    is_primary: true,
  });
  await deleteTrackedDomain(request, "site-1", "domain-1");
  await deleteTrackedSite(request, "site-1");
  const calls = vi.mocked(request).mock.calls;
  expect(calls.map((call) => call[0])).toEqual([
    "/api/v1/tracked-sites",
    "/api/v1/tracked-sites?status=all&search=Site",
    "/api/v1/tracked-sites/site-1",
    "/api/v1/tracked-sites/site-1",
    "/api/v1/tracked-sites/site-1/domains",
    "/api/v1/tracked-sites/site-1/domains/domain-1",
    "/api/v1/tracked-sites/site-1/domains/domain-1",
    "/api/v1/tracked-sites/site-1",
  ]);
  expect(JSON.parse(String(calls[0][1]?.body))).not.toHaveProperty("user_id");
});
