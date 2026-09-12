import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import HealthPage from "@/app/health/page";
import { Providers } from "@/components/providers";

vi.mock("@/lib/config", () => ({
  config: { apiBaseUrl: "http://api.test", environment: "test" },
}));

describe("health dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it.each([HomePage, HealthPage])(
    "renders a page and real API client results",
    async (Page) => {
      vi.mocked(fetch).mockImplementation(
        async () => new Response(JSON.stringify({ status: "ok" })),
      );
      render(
        <Providers>
          <Page />
        </Providers>,
      );
      expect(screen.getByRole("heading", { level: 1 })).toBeVisible();
      expect(screen.getByText("test")).toBeVisible();
      for (const service of ["API", "Database", "Redis"]) {
        expect(
          await screen.findByLabelText(`${service}: connected`),
        ).toBeVisible();
      }
      expect(fetch).toHaveBeenCalledTimes(3);
    },
  );

  it("shows unavailable dependencies independently", async () => {
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (String(url).endsWith("/health"))
        return new Response(JSON.stringify({ status: "ok" }));
      return new Response("failure", { status: 503 });
    });
    render(
      <Providers>
        <HomePage />
      </Providers>,
    );
    expect(await screen.findByLabelText("API: connected")).toBeVisible();
    expect(await screen.findByLabelText("Database: unavailable")).toBeVisible();
    expect(await screen.findByLabelText("Redis: unavailable")).toBeVisible();
  });

  it("handles an unreachable backend", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Failed to fetch"));
    render(
      <Providers>
        <HomePage />
      </Providers>,
    );
    expect(await screen.findAllByText("unavailable")).toHaveLength(3);
  });
});
