import {
  readFileSync,
  mkdtempSync,
  mkdirSync,
  writeFileSync,
  rmSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import {
  publicLocalePairs,
  localePath,
  localeLanguages,
  publicLocale,
} from "@/lib/public-locales";
import { isMarketingPath } from "@/lib/site";
import { PublicShell } from "@/design-system/public-shell";
import { LanguageSelect } from "@/design-system/language-select";
import { RootDocument } from "@/components/root-document";
import { proxy } from "@/proxy";
import sitemap from "@/app/sitemap";
import robots from "@/app/robots";
import { GET as feedRoute } from "@/app/(en)/feed.xml/route";
import Home, { metadata as homeMetadata } from "@/app/vi/page";
import { metadata as englishHomeMetadata } from "@/app/(en)/page";
import BlogIndex, { metadata as indexMetadata } from "@/app/vi/blog/page";
import BlogArticle, {
  generateMetadata,
  generateStaticParams,
} from "@/app/vi/blog/[slug]/page";
import {
  getPublishedPosts,
  getPublishedPost,
  getRelatedPosts,
  parseBlogPost,
  readBlogPosts,
} from "@/features/blog/content";
import { blogMetadata, articleStructuredData } from "@/features/blog/seo";
import { LandingPage } from "./landing-page";
import { landingMetadata, landingStructuredData } from "./seo";
import { vietnameseLandingPages } from "./vietnamese-content";
import {
  googleRankTracker,
  dailySerpTracker,
  agencySerpTracking,
} from "./landing-content";

const state = vi.hoisted(() => ({ path: "/" }));
vi.mock("next/navigation", () => ({
  usePathname: () => state.path,
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ isAuthenticated: false }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));
afterEach(() => {
  vi.unstubAllEnvs();
  state.path = "/";
});
const origin = "https://serpsaas.com";

it("uses all twelve explicit pairs reciprocally and falls back to locale Home", () => {
  expect(publicLocalePairs).toHaveLength(12);
  for (const pair of publicLocalePairs) {
    expect(localePath(pair.en, "vi")).toBe(pair.vi);
    expect(localePath(pair.vi, "en")).toBe(pair.en);
    expect(localeLanguages(pair.vi)).toEqual(localeLanguages(pair.en));
    expect(localeLanguages(pair.vi)).toEqual({
      en: `${origin}${pair.en}`,
      vi: `${origin}${pair.vi}`,
      "x-default": `${origin}${pair.en}`,
    });
    expect(isMarketingPath(pair.vi)).toBe(true);
  }
  expect(localePath("/pricing", "vi")).toBe("/vi/bang-gia");
  expect(localePath("/blog/serp-tracking-for-agencies", "vi")).toBe(
    "/vi/blog/serp-tracking-cho-agency",
  );
  expect(localePath("/vi/unknown", "en")).toBe("/");
  expect(localeLanguages("/unmapped")).toBeUndefined();
  expect(publicLocale("/vietnam")).toBe("en");
  expect(RootDocument({ children: null }).props.lang).toBe("en");
  expect(RootDocument({ children: null, locale: "vi" }).props.lang).toBe("vi");
});

it.each(publicLocalePairs)(
  "provides crawlable accessible language links for $vi",
  ({ en, vi: translated }) => {
    render(<LanguageSelect path={translated} />);
    const select = document.querySelector("details")!;
    select.open = true;
    const english = screen.getByRole("link", { name: "English" });
    const vietnamese = screen.getByRole("link", { name: "Tiếng Việt" });
    expect(english).toHaveAttribute("href", en);
    expect(english).toHaveAttribute("hreflang", "en");
    expect(vietnamese).toHaveAttribute("href", translated);
    expect(vietnamese).toHaveAttribute("aria-current", "page");
    expect(vietnamese).not.toHaveAttribute("rel", "nofollow");
  },
);

it.each(["/", "/vi"])(
  "keeps Home language controls in the header and localizes mobile navigation: %s",
  (path) => {
    state.path = path;
    const vietnamese = path === "/vi";
    render(
      <PublicShell>
        <Home />
      </PublicShell>,
    );
    const header = within(screen.getByRole("banner"));
    document.querySelector<HTMLDetailsElement>(
      ".public-language-select",
    )!.open = true;
    expect(header.getByRole("link", { name: "English" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(header.getByRole("link", { name: "Tiếng Việt" })).toHaveAttribute(
      "href",
      "/vi",
    );
    fireEvent.click(
      header.getByRole("button", {
        name: vietnamese ? "Mở menu điều hướng" : "Open public navigation",
      }),
    );
    const drawer = within(screen.getByRole("dialog"));
    expect(
      drawer.getByRole("link", { name: vietnamese ? "Trang chủ" : "Home" }),
    ).toHaveAttribute("href", path);
    expect(drawer.getByRole("link", { name: "Blog" })).toHaveAttribute(
      "href",
      vietnamese ? "/vi/blog" : "/blog",
    );
    expect(
      drawer.getByRole("link", {
        name: vietnamese ? "Bắt đầu" : "Get Started",
      }),
    ).toHaveAttribute("href", "/register");
  },
);

it("renders Vietnamese Home links without requiring a public API", () => {
  render(<Home />);
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  for (const pair of publicLocalePairs.slice(1, 5))
    expect(document.querySelector(`main a[href="${pair.vi}"]`)).not.toBeNull();
  expect(document.body).toHaveTextContent(/Top 10/);
  expect(document.body).toHaveTextContent(/hàng tuần tùy theo gói/);
});

it.each(vietnameseLandingPages)(
  "renders localized landing content and links: $path",
  (page) => {
    const { container } = render(<LandingPage page={page} />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      page.heading,
    );
    expect(screen.getByRole("link", { name: "Trang chủ" })).toHaveAttribute(
      "href",
      "/vi",
    );
    expect(
      container.querySelector(`a[href="${page.guide.path}"]`),
    ).not.toBeNull();
    for (const link of container.querySelectorAll('main a[href^="/"]')) {
      expect(link.getAttribute("href")).toMatch(
        /^\/(vi(?:\/|$)|pricing$|register$)/,
      );
    }
    expect(container).not.toHaveTextContent(/Top 100|real-time|client portal/);
    const graph = landingStructuredData(page)["@graph"];
    expect(graph[0]).toMatchObject({
      "@type": "WebPage",
      inLanguage: "vi",
      url: origin + page.path,
    });
    expect(graph[1]).toMatchObject({ "@type": "SoftwareApplication" });
    expect(JSON.stringify(graph)).not.toMatch(
      /aggregateRating|FAQPage|reviewCount/,
    );
  },
);

it("identifies the checking tool and assigns task-specific Vietnamese guides", () => {
  expect(vietnameseLandingPages[0].heading).toBe(
    "Công cụ kiểm tra thứ hạng từ khóa Google",
  );
  expect(vietnameseLandingPages[0].lead).toContain("kiểm tra hoàn tất");
  expect(
    vietnameseLandingPages.map((page) => [page.guide.path, page.guide.label]),
  ).toEqual([
    [
      "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
      "Đọc cách kiểm tra thứ hạng từ khóa",
    ],
    [
      "/vi/blog/co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay",
      "Khi nào nên theo dõi thứ hạng hàng ngày?",
    ],
    [
      "/vi/blog/serp-tracking-cho-agency",
      "Đọc quy trình báo cáo thứ hạng cho agency",
    ],
  ]);
});

it("hands definition readers to one practical checking guide while preserving article history and the product link", async () => {
  const post = getPublishedPost("cong-cu-rank-tracker-la-gi", "vi")!;
  expect(post.publishedAt).toBe("2026-10-17");
  expect(post.updatedAt).toBe("2026-10-29");
  const { container } = render(
    await BlogArticle({ params: Promise.resolve({ slug: post.slug }) }),
  );
  const prose = container.querySelector(".blog-prose")!;
  expect(
    prose.querySelectorAll('a[href="/vi/blog/cach-kiem-tra-thu-hang-tu-khoa"]'),
  ).toHaveLength(1);
  expect(
    prose.querySelectorAll('a[href="/vi/cong-cu-kiem-tra-thu-hang-tu-khoa"]'),
  ).toHaveLength(1);
  expect(container.querySelectorAll("h1")).toHaveLength(1);
  expect(container.querySelector(".blog-cta")).not.toHaveTextContent(
    "Explore the Google rank tracker",
  );
});

it("isolates Vietnamese articles and retains English validation and feed content", async () => {
  const posts = getPublishedPosts(undefined, "vi");
  expect(posts).toHaveLength(6);
  expect(getPublishedPosts()).toHaveLength(3);
  expect(generateStaticParams()).toEqual(
    posts.map((post) => ({ slug: post.slug })),
  );
  render(<BlogIndex />);
  expect(document.querySelectorAll(".blog-card")).toHaveLength(posts.length);
  expect(
    document.querySelector('a[href="/blog/how-to-track-google-rankings"]'),
  ).toBeNull();
  for (const post of posts) {
    expect(getPublishedPost(post.slug)).toBeUndefined();
    expect(getRelatedPosts(post).every((item) => item.locale === "vi")).toBe(
      true,
    );
    expect(
      await generateMetadata({ params: Promise.resolve({ slug: post.slug }) }),
    ).toEqual(blogMetadata(post));
    const graph = articleStructuredData(post)["@graph"];
    expect(graph[0]).toMatchObject({
      "@type": "BlogPosting",
      inLanguage: "vi",
    });
    expect(post.content).toMatch(/\]\(\/vi\//);
    expect(post.content).not.toMatch(/\]\(\/blog\//);
    expect(post.readingMinutes).toBeGreaterThanOrEqual(3);
  }
  await expect(
    BlogArticle({
      params: Promise.resolve({ slug: "how-to-track-google-rankings" }),
    }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
  await expect(
    generateMetadata({ params: Promise.resolve({ slug: "unknown" }) }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
});

it.each([
  "cong-cu-rank-tracker-la-gi",
  "co-nen-theo-doi-thu-hang-tu-khoa-hang-ngay",
  "cach-theo-doi-thu-hang-doi-thu-seo",
])(
  "publishes unpaired Vietnamese article %s without invented alternates or English feed entries",
  async (slug) => {
    const path = `/vi/blog/${slug}`;
    const post = getPublishedPost(slug, "vi")!;
    expect(post).toBeDefined();
    expect(getPublishedPost(slug)).toBeUndefined();
    const metadata = await generateMetadata({
      params: Promise.resolve({ slug }),
    });
    expect(metadata.alternates?.canonical).toBe(origin + path);
    expect(metadata.alternates?.languages).toBeUndefined();
    expect(metadata.alternates?.types).toBeUndefined();
    expect(metadata.robots).toEqual({ index: true, follow: true });
    expect(sitemap()).toContainEqual(
      expect.objectContaining({
        url: origin + path,
        lastModified: post.updatedAt,
      }),
    );
    expect(await feedRoute().text()).not.toContain(slug);

    render(<LanguageSelect path={path} />);
    document.querySelector("details")!.open = true;
    expect(screen.getByRole("link", { name: "English" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "Tiếng Việt" })).toHaveAttribute(
      "href",
      "/vi",
    );
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", origin);
    vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
    const response = proxy(
      new NextRequest(origin + path, {
        headers: { host: "serpsaas.com", "accept-language": "en" },
      }),
    );
    expect(response.headers.get("location")).toBeNull();
    expect(response.headers.get("X-Robots-Tag")).toBeNull();
  },
);

it.each(getPublishedPosts(undefined, "vi"))(
  "renders one Vietnamese article H1 and localized byline: $slug",
  async (post) => {
    const { container } = render(
      await BlogArticle({ params: Promise.resolve({ slug: post.slug }) }),
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(container).toHaveTextContent("Đăng ngày");
    expect(container).toHaveTextContent("phút đọc");
    expect(screen.getByRole("link", { name: "Trang chủ" })).toHaveAttribute(
      "href",
      "/vi",
    );
    expect(
      container.querySelector('.blog-related a[href^="/vi/blog/"]'),
    ).not.toBeNull();
  },
);

it("validates locale and excludes Vietnamese drafts from lookups, routes and sitemap", () => {
  const root = mkdtempSync(join(tmpdir(), "m7i-blog-"));
  const source = readFileSync(
    "content/blog/vi/cach-kiem-tra-thu-hang-tu-khoa.md",
    "utf8",
  );
  expect(() =>
    parseBlogPost(
      source.replace("locale: vi", "locale: xx"),
      "cach-kiem-tra-thu-hang-tu-khoa.md",
    ),
  ).toThrow("locale");
  const directory = join(root, "content/blog/vi");
  mkdirSync(directory, { recursive: true });
  writeFileSync(
    join(directory, "cach-kiem-tra-thu-hang-tu-khoa.md"),
    source.replace("draft: false", "draft: true"),
  );
  const cwd = vi.spyOn(process, "cwd").mockReturnValue(root);
  try {
    expect(getPublishedPosts(undefined, "vi")).toEqual([]);
    expect(generateStaticParams()).toEqual([]);
    expect(
      getPublishedPost("cach-kiem-tra-thu-hang-tu-khoa", "vi"),
    ).toBeUndefined();
    expect(sitemap().some((entry) => entry.url.includes("cach-kiem-tra"))).toBe(
      false,
    );
    expect(() => readBlogPosts(directory)).toThrow("locale");
  } finally {
    cwd.mockRestore();
    rmSync(root, { recursive: true, force: true });
  }
});

it("emits unique Vietnamese metadata and self canonicals at the fixed production origin", () => {
  const metas = [
    homeMetadata,
    indexMetadata,
    ...vietnameseLandingPages.map(landingMetadata),
    ...getPublishedPosts(undefined, "vi").map((post) => blogMetadata(post)),
  ];
  expect(new Set(metas.map((meta) => JSON.stringify(meta.title))).size).toBe(
    metas.length,
  );
  expect(new Set(metas.map((meta) => meta.description)).size).toBe(
    metas.length,
  );
  for (const meta of metas) {
    const path = new URL(String(meta.alternates?.canonical)).pathname;
    expect(meta.alternates?.languages).toEqual(localeLanguages(path));
    expect(meta.robots).toEqual({ index: true, follow: true });
    expect(meta.openGraph).toMatchObject({
      url: origin + path,
      description: meta.description,
    });
    expect(meta.twitter).toMatchObject({ description: meta.description });
  }
  for (const alternateOrigin of [
    "http://localhost:3000",
    "https://app.serpsaas.com",
    "https://www.serpsaas.com",
    "https://preview.run.app",
  ]) {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", alternateOrigin);
    for (const page of vietnameseLandingPages)
      expect(landingMetadata(page).alternates?.canonical).toBe(
        origin + page.path,
      );
  }
  expect(englishHomeMetadata.title).toEqual({
    absolute: "Google Rank Tracker for Desktop & Mobile | SERP SaaS",
  });
  expect(englishHomeMetadata.alternates?.canonical).toBe(origin + "/");
  for (const page of [
    googleRankTracker,
    dailySerpTracker,
    agencySerpTracking,
  ]) {
    expect(landingMetadata(page).title).toEqual({ absolute: page.title });
    expect(landingMetadata(page).description).toBe(page.description);
    expect(landingMetadata(page).alternates?.languages).toEqual(
      localeLanguages(page.path),
    );
  }
});

it("includes all Vietnamese URLs in sitemap, allows crawling, and preserves paths in host redirects", () => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", origin);
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
  const urls = sitemap().map((page) => page.url);
  expect(new Set(urls).size).toBe(urls.length);
  const rules = robots().rules;
  expect(rules).toMatchObject({
    allow: expect.arrayContaining(["/vi"]),
    disallow: expect.arrayContaining(["/app", "/admin", "/login"]),
  });
  const rule = Array.isArray(rules) ? rules[0] : rules;
  expect(rule.disallow).not.toContain("/vi");
  for (const pair of publicLocalePairs) {
    expect(urls).toContain(origin + pair.vi);
    const request = (host: string) =>
      new NextRequest(`https://${host}${pair.vi}?source=test`, {
        headers: { host, "accept-language": "en" },
      });
    const response = proxy(request("serpsaas.com"));
    expect(response.headers.get("location")).toBeNull();
    expect(response.headers.get("X-Robots-Tag")).toBeNull();
    expect(proxy(request("app.serpsaas.com")).headers.get("location")).toBe(
      origin + pair.vi + "?source=test",
    );
  }
  const english = proxy(
    new NextRequest(origin + "/", {
      headers: { host: "serpsaas.com", "accept-language": "vi-VN" },
    }),
  );
  expect(english.headers.get("location")).toBeNull();
});
