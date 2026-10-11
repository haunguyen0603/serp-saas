import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import GooglePage, {
  metadata as googleMetadata,
} from "@/app/(en)/google-serp-rank-tracker/page";
import DailyPage, {
  metadata as dailyMetadata,
} from "@/app/(en)/daily-serp-tracker/page";
import AgencyPage, {
  metadata as agencyMetadata,
} from "@/app/(en)/serp-tracking-for-agencies/page";
import HomePage from "@/app/(en)/page";
import BlogArticlePage from "@/app/(en)/blog/[slug]/page";
import sitemap from "@/app/sitemap";
import robots from "@/app/robots";
import { AppShell } from "@/design-system/app-shell";
import { landingMetadata } from "./seo";
import {
  googleRankTracker,
  dailySerpTracker,
  agencySerpTracking,
} from "./landing-content";

const state = vi.hoisted(() => ({ path: "/" }));
vi.mock("next/navigation", () => ({
  usePathname: () => state.path,
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ isAuthenticated: false }),
}));

const pages = [
  {
    content: googleRankTracker,
    Component: GooglePage,
    metadata: googleMetadata,
  },
  { content: dailySerpTracker, Component: DailyPage, metadata: dailyMetadata },
  {
    content: agencySerpTracking,
    Component: AgencyPage,
    metadata: agencyMetadata,
  },
];

afterEach(() => vi.unstubAllEnvs());

it.each(pages)(
  "renders $content.path with a public shell, one H1 and three CTA placements",
  ({ content, Component }) => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://serpsaas.com");
    vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
    state.path = content.path;
    const { container } = render(
      <AppShell>
        <Component />
      </AppShell>,
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      content.heading,
    );
    expect(container.querySelector(".public-shell")).toBeInTheDocument();
    const main = screen.getByRole("main");
    const registerLinks = main.querySelectorAll(
      'a[href="https://app.serpsaas.com/register"]',
    );
    expect(registerLinks).toHaveLength(3);
    expect(
      within(main).getAllByRole("link", { name: "View pricing" }),
    ).toHaveLength(3);
    for (const link of within(main).getAllByRole("link", {
      name: "View pricing",
    }))
      expect(link).toHaveAttribute("href", "https://serpsaas.com/pricing");
    expect(
      within(main).getByRole("link", { name: `${content.guide.label} →` }),
    ).toHaveAttribute("href", `https://serpsaas.com${content.guide.path}`);
    const footer = within(screen.getByRole("contentinfo"));
    for (const page of pages)
      expect(
        footer.getByRole("link", {
          name:
            page.content.path === agencySerpTracking.path
              ? "SERP Tracking for Agencies"
              : page.content.heading,
        }),
      ).toHaveAttribute("href", `https://serpsaas.com${page.content.path}`);
    expect(container.querySelector("h3")).toBeNull();
    for (const section of content.sections)
      expect(
        within(main).getByRole("heading", { name: section.heading, level: 2 }),
      ).toBeVisible();
  },
);

it("exports unique complete route metadata", () => {
  expect(
    new Set(
      pages.map(
        (page) => page.metadata.title && JSON.stringify(page.metadata.title),
      ),
    ).size,
  ).toBe(3);
  expect(new Set(pages.map((page) => page.metadata.description)).size).toBe(3);
  for (const { content, metadata } of pages) {
    const url = `https://serpsaas.com${content.path}`;
    expect(metadata.title).toEqual({ absolute: content.title });
    expect(metadata.description).toBe(content.description);
    expect(metadata.alternates?.canonical).toBe(url);
    expect(metadata.robots).toEqual({ index: true, follow: true });
    expect(metadata.openGraph).toMatchObject({
      type: "website",
      url,
      title: content.title,
      description: content.description,
    });
    expect(metadata.twitter).toMatchObject({
      card: "summary",
      title: content.title,
      description: content.description,
    });
  }
});

it.each([
  "http://localhost:3000",
  "http://serpsaas.com",
  "https://www.serpsaas.com",
  "https://preview.run.app",
  "https://app.serpsaas.com",
  "https://api.serpsaas.com",
])("retains HTTPS apex canonicals when configured with %s", (origin) => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", origin);
  for (const { content } of pages) {
    expect(landingMetadata(content).alternates?.canonical).toBe(
      `https://serpsaas.com${content.path}`,
    );
    expect(landingMetadata(content).openGraph).toMatchObject({
      url: `https://serpsaas.com${content.path}`,
    });
  }
});

it.each(pages)(
  "renders supported linked JSON-LD on $content.path",
  ({ content, Component }) => {
    const { container } = render(<Component />);
    const graph = JSON.parse(
      container.querySelector('script[type="application/ld+json"]')!
        .textContent!,
    )["@graph"];
    const url = `https://serpsaas.com${content.path}`;
    expect(graph.map((item: { "@type": string }) => item["@type"])).toEqual([
      "WebPage",
      "SoftwareApplication",
      "BreadcrumbList",
    ]);
    expect(graph[0]).toMatchObject({
      "@id": url,
      url,
      name: content.heading,
      about: { "@id": "https://serpsaas.com/#software" },
    });
    expect(graph[1]).toMatchObject({
      "@id": "https://serpsaas.com/#software",
      name: "SERP SaaS",
      operatingSystem: "Web",
    });
    expect(
      graph[2].itemListElement.map((item: { item: string }) => item.item),
    ).toEqual(["https://serpsaas.com/", url]);
    expect(JSON.stringify(graph)).not.toMatch(
      /AggregateRating|Review|FAQPage|offers/,
    );
  },
);

it("publishes crawlable landing URLs alongside existing public and Blog routes", () => {
  const urls = sitemap().map((page) => page.url);
  const rules = robots().rules as { allow: string[]; disallow: string[] };
  for (const { content } of pages) {
    expect(
      urls.filter((url) => url === `https://serpsaas.com${content.path}`),
    ).toHaveLength(1);
    expect(urls).toContain(`https://serpsaas.com${content.guide.path}`);
    expect(rules.allow).toContain(content.path);
    expect(rules.disallow.some((path) => content.path.startsWith(path))).toBe(
      false,
    );
  }
  expect(robots().sitemap).toBe("https://serpsaas.com/sitemap.xml");
  expect(
    urls.some((url) => /app\.|\/app(?:\/|$)|\/login|\/register/.test(url)),
  ).toBe(false);
});

it("exposes each workflow from the homepage", () => {
  render(<HomePage />);
  const section = document.querySelector(
    'section[aria-labelledby="tracking-use-cases"]',
  )! as HTMLElement;
  for (const { content } of pages)
    expect(
      section.querySelector(`a[href="${content.path}"]`),
    ).toBeInTheDocument();
});

it.each(pages)(
  "links the informational guide to $content.path without duplicating its copy",
  async ({ content }) => {
    const slug = content.guide.path.split("/").at(-1)!;
    const { container } = render(
      await BlogArticlePage({ params: Promise.resolve({ slug }) }),
    );
    expect(
      container.querySelector(`.blog-prose a[href="${content.path}"]`),
    ).toBeInTheDocument();
    const guideText = container.querySelector(".blog-prose")!.textContent!;
    for (const section of content.sections)
      for (const paragraph of section.paragraphs)
        expect(guideText).not.toContain(paragraph);
  },
);

it.each(pages)(
  "keeps claims and checked-depth limitations explicit on $content.path",
  ({ Component }) => {
    render(<Component />);
    const text = screen.getByRole("main").textContent!;
    expect(text).toContain("Top 10");
    expect(text).toMatch(/incomplete/);
    expect(text).not.toMatch(
      /Top 100|real.time|unlimited|AI recommendations|white.label|client portal|team workspace|Slack alerts|Developer API|backlink analysis|site audit/gi,
    );
  },
);

it("qualifies daily scheduling and user-based agency ownership", () => {
  const daily = render(<DailyPage />);
  expect(screen.getByRole("main")).toHaveTextContent(
    "Daily or weekly scheduling is available according to Plan entitlement.",
  );
  daily.unmount();
  render(<AgencyPage />);
  expect(screen.getByRole("main")).toHaveTextContent(
    "Account ownership is user-based",
  );
  expect(screen.getByRole("main")).toHaveTextContent(
    "account’s own verified email",
  );
});
