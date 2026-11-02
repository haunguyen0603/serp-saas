import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import BlogPage from "@/app/(en)/blog/page";
import BlogArticlePage, {
  dynamicParams,
  generateMetadata,
  generateStaticParams,
} from "@/app/(en)/blog/[slug]/page";
import sitemap from "@/app/sitemap";
import robots from "@/app/robots";
import { GET as feedRoute } from "@/app/(en)/feed.xml/route";
import { BlogMarkdown } from "./blog-components";
import {
  getPublishedPost,
  getPublishedPosts,
  getRelatedPosts,
  parseBlogPost,
  readBlogPosts,
} from "./content";
import {
  articleStructuredData,
  blogMetadata,
  serializeStructuredData,
} from "./seo";
import { blogFeed } from "./rss";

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

const originalDirectory = process.cwd();
const firstSource = readFileSync(
  join(originalDirectory, "content/blog/how-to-track-google-rankings.md"),
  "utf8",
);
const first = parseBlogPost(firstSource, "how-to-track-google-rankings.md");
const temporaryDirectories: string[] = [];

function fixture() {
  const root = mkdtempSync(join(tmpdir(), "m7g-content-test-"));
  temporaryDirectories.push(root);
  const directory = join(root, "content/blog");
  mkdirSync(join(directory, "vi"), { recursive: true });
  writeFileSync(join(directory, `${first.slug}.md`), firstSource);
  const draft = firstSource
    .replaceAll(first.slug, "private-draft")
    .replace(first.title, "Private draft title")
    .replace(first.description, "Not for publication.")
    .replace("draft: false", "draft: true");
  writeFileSync(join(directory, "private-draft.md"), draft);
  vi.spyOn(process, "cwd").mockReturnValue(root);
  return { root, directory };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  for (const directory of temporaryDirectories.splice(0))
    rmSync(directory, { recursive: true, force: true });
});

it("validates three distinct published guides with deterministic order and reading time", () => {
  const posts = getPublishedPosts();
  expect(posts).toHaveLength(3);
  expect(new Set(posts.map((post) => post.title)).size).toBe(3);
  expect(new Set(posts.map((post) => post.description)).size).toBe(3);
  expect(posts.every((post) => post.readingMinutes >= 3)).toBe(true);
  expect(posts.map((post) => post.slug)).toEqual(
    [...posts.map((post) => post.slug)].sort(),
  );
});

it("renders the blog listing with article cards and a contextual pricing CTA", () => {
  render(<BlogPage />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "SERP Tracking & SEO Insights",
  );
  for (const post of getPublishedPosts()) {
    expect(screen.getByRole("link", { name: post.title })).toHaveAttribute(
      "href",
      `/blog/${post.slug}`,
    );
  }
  expect(
    screen.getByRole("link", { name: "Explore rank-tracking Plans" }),
  ).toHaveAttribute("href", "/pricing");
  expect(document.querySelectorAll(".blog-card")).toHaveLength(3);
  expect(
    within(document.querySelector(".blog-cta") as HTMLElement).getByRole(
      "link",
      { name: "Explore the Google rank tracker" },
    ),
  ).toHaveAttribute("href", "/google-serp-rank-tracker");
});

it.each(getPublishedPosts())(
  "offers product exploration and Pricing in the shared CTA: $slug",
  async (post) => {
    const { container } = render(
      await BlogArticlePage({ params: Promise.resolve({ slug: post.slug }) }),
    );
    const cta = within(container.querySelector(".blog-cta") as HTMLElement);
    expect(
      cta.getByRole("link", {
        name: "Explore the Google rank tracker",
      }),
    ).toHaveAttribute("href", "/google-serp-rank-tracker");
    expect(
      cta.getByRole("link", { name: "Explore rank-tracking Plans" }),
    ).toHaveAttribute("href", "/pricing");
  },
);

it("renders one article H1, Markdown tables, breadcrumbs, related articles and safe JSON-LD", async () => {
  const { container } = render(
    await BlogArticlePage({ params: Promise.resolve({ slug: first.slug }) }),
  );
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    first.title,
  );
  expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeVisible();
  expect(screen.getByRole("table")).toBeVisible();
  expect(screen.getByRole("columnheader", { name: "Approach" })).toBeVisible();
  expect(container.querySelectorAll(".blog-related .blog-card")).toHaveLength(
    2,
  );
  const structured = JSON.parse(
    container.querySelector('script[type="application/ld+json"]')!.textContent!,
  );
  expect(structured["@graph"][0].headline).toBe(first.title);
  expect(structured["@graph"][1]["@type"]).toBe("BreadcrumbList");
});

it("excludes drafts from listing, static routes, lookups, sitemap and RSS", async () => {
  fixture();
  expect(readBlogPosts()).toHaveLength(2);
  expect(getPublishedPosts()).toHaveLength(1);
  expect(getPublishedPost("private-draft")).toBeUndefined();
  expect(dynamicParams).toBe(false);
  expect(generateStaticParams()).toEqual([{ slug: first.slug }]);
  render(<BlogPage />);
  expect(screen.queryByText("Private draft title")).not.toBeInTheDocument();
  expect(sitemap().map((page) => page.url)).toContain(
    `https://serpsaas.com/blog/${first.slug}`,
  );
  expect(JSON.stringify(sitemap())).not.toContain("private-draft");
  const response = feedRoute();
  expect(response.headers.get("content-type")).toContain("application/rss+xml");
  const xml = await response.text();
  expect(xml).toContain(first.slug);
  expect(xml).not.toContain("private-draft");
  await expect(
    BlogArticlePage({ params: Promise.resolve({ slug: "private-draft" }) }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
  await expect(
    generateMetadata({ params: Promise.resolve({ slug: "private-draft" }) }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
});

it("returns 404 for unknown article slugs", async () => {
  await expect(
    BlogArticlePage({ params: Promise.resolve({ slug: "does-not-exist" }) }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
  await expect(
    generateMetadata({ params: Promise.resolve({ slug: "does-not-exist" }) }),
  ).rejects.toThrow("NEXT_NOT_FOUND");
});

it.each([
  ["missing frontmatter", firstSource.replace(/^---/, ""), /frontmatter/],
  [
    "invalid date",
    firstSource.replaceAll("2026-10-07", "2026-02-30"),
    /valid YYYY-MM-DD/,
  ],
  [
    "earlier update",
    firstSource.replace('updatedAt: "2026-10-10"', 'updatedAt: "2026-10-06"'),
    /precede/,
  ],
  [
    "invalid boolean",
    firstSource.replace("draft: false", 'draft: "false"'),
    /draft must be a boolean/,
  ],
  ["missing field", firstSource.replace('author: "SERP SaaS"', ""), /author/],
  [
    "duplicate YAML key",
    firstSource.replace("draft: false", "draft: false\ndraft: true"),
    /unique/,
  ],
  [
    "duplicate tags",
    firstSource.replace('["Rank Tracking", "Google", "SEO"]', '["SEO", "seo"]'),
    /unique/,
  ],
  ["extra H1", `${firstSource}\n# Another heading`, /H2–H4/],
  [
    "remote image",
    firstSource.replace(
      "draft: false",
      "draft: false\nimage: https://example.com/image.png",
    ),
    /local/,
  ],
  [
    "missing image alt",
    firstSource.replace(
      "draft: false",
      "draft: false\nimage: /images/blog/guide.png",
    ),
    /imageAlt/,
  ],
] as const)(
  "rejects %s at the same validation boundary used by prebuild",
  (_, source, message) => {
    expect(() => parseBlogPost(source, `${first.slug}.md`)).toThrow(message);
  },
);

it("rejects filename/slug mismatch and duplicate article metadata", () => {
  expect(() => parseBlogPost(firstSource, "another-slug.md")).toThrow("match");
  const { directory } = fixture();
  writeFileSync(
    join(directory, "second-guide.md"),
    firstSource.replaceAll(first.slug, "second-guide"),
  );
  expect(readBlogPosts).toThrow("Duplicate blog title");
});

it("rejects an SEO title that duplicates another article's effective title", () => {
  const { directory } = fixture();
  const source = firstSource
    .replaceAll(first.slug, "second-guide")
    .replace(first.title, "Another article heading")
    .replace(first.description, "A different article description.")
    .replace(
      "draft: false",
      `draft: false\nseoTitle: ${JSON.stringify(first.title)}`,
    );
  writeFileSync(join(directory, "second-guide.md"), source);
  expect(readBlogPosts).toThrow("Duplicate blog SEO title");
});

it("runs the real prebuild gate and exits unsuccessfully for invalid content", () => {
  const { root, directory } = fixture();
  const command = [
    "--experimental-strip-types",
    join(originalDirectory, "scripts/validate-blog.mjs"),
  ];
  const valid = spawnSync(process.execPath, command, {
    cwd: root,
    encoding: "utf8",
  });
  expect(valid.status).toBe(0);
  expect(valid.stdout).toContain("1 published, 1 drafts");
  writeFileSync(
    join(directory, `${first.slug}.md`),
    firstSource.replace("featured: true", "featured: invalid"),
  );
  const invalid = spawnSync(process.execPath, command, {
    cwd: root,
    encoding: "utf8",
  });
  expect(invalid.status).toBe(1);
  expect(invalid.stderr).toContain("featured must be a boolean");
});

it.each([
  "http://localhost:3000",
  "https://preview.run.app",
  "https://app.serpsaas.com",
  "https://api.serpsaas.com",
  "https://serpsaas.com",
])(
  "always publishes HTTPS commercial canonical metadata, even on %s",
  async (origin) => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", origin);
    const metadata = await generateMetadata({
      params: Promise.resolve({ slug: first.slug }),
    });
    expect(metadata.alternates?.canonical).toBe(
      `https://serpsaas.com/blog/${first.slug}`,
    );
    expect(metadata.title).toBe(first.title);
    expect(metadata.description).toBe(first.description);
    expect(metadata.openGraph).toMatchObject({
      type: "article",
      url: `https://serpsaas.com/blog/${first.slug}`,
    });
    expect(metadata.twitter).toMatchObject({
      card: "summary",
      description: first.description,
    });
    expect(blogMetadata().alternates?.canonical).toBe(
      "https://serpsaas.com/blog",
    );
    expect(
      sitemap().every((page) => page.url.startsWith("https://serpsaas.com/")),
    ).toBe(true);
    expect(robots().sitemap).toBe("https://serpsaas.com/sitemap.xml");
  },
);

it("creates truthful article and breadcrumb schema and escapes script delimiters", () => {
  const structured = articleStructuredData(first);
  expect(structured["@graph"][0]).toMatchObject({
    "@type": "BlogPosting",
    datePublished: first.publishedAt,
    dateModified: first.updatedAt,
    author: { "@type": "Organization", name: "SERP SaaS" },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://serpsaas.com/blog/${first.slug}`,
    },
  });
  expect(JSON.stringify(structured)).not.toMatch(/AggregateRating|FAQPage/);
  const serialized = serializeStructuredData({
    title: "</script><script>alert(1)</script>",
  });
  expect(serialized).not.toContain("<");
  expect(JSON.parse(serialized).title).toContain("</script>");
});

it("selects deterministic related posts, excluding the current post and drafts", () => {
  const posts = getPublishedPosts();
  const draft = { ...first, slug: "private", draft: true };
  const related = getRelatedPosts(first, [...posts, draft]);
  expect(related).toHaveLength(2);
  expect(related.every((post) => post.slug !== first.slug && !post.draft)).toBe(
    true,
  );
  expect(getRelatedPosts(first, [...posts].reverse())).toEqual(related);
});

it("renders GFM, heading hierarchy, lists, code, callouts and safe links without runtime HTML", () => {
  const { container } = render(
    <BlogMarkdown
      content={
        "## Section\n\n### Detail\n\n#### Note\n\n- A **bold** point\n\n> A callout\n\n```text\nexample\n```\n\n[Pricing](/pricing)\n\n[Unsafe](javascript:alert(1))\n\n<script>alert(1)</script>"
      }
    />,
  );
  for (const level of [2, 3, 4])
    expect(screen.getByRole("heading", { level })).toBeVisible();
  expect(container.querySelector("ul li strong")).toHaveTextContent("bold");
  expect(container.querySelector("blockquote")).toHaveTextContent("callout");
  expect(container.querySelector("pre code")).toHaveTextContent("example");
  expect(container.querySelector("pre")).toHaveAttribute("tabindex", "0");
  expect(screen.getByRole("link", { name: "Pricing" })).toHaveAttribute(
    "href",
    "/pricing",
  );
  expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
  expect(container.querySelector("script")).toBeNull();
});

it("escapes XML and excludes drafts even when given an unfiltered RSS input", () => {
  const xml = blogFeed([
    { ...first, title: "Guide <one> & two" },
    { ...first, draft: true, slug: "secret" },
  ]);
  expect(xml).toContain("Guide &lt;one&gt; &amp; two");
  expect(xml).not.toContain("secret");
  expect(
    new DOMParser()
      .parseFromString(xml, "text/xml")
      .querySelector("parsererror"),
  ).toBeNull();
  expect(robots().rules).toMatchObject({
    allow: expect.arrayContaining(["/blog"]),
  });
});
