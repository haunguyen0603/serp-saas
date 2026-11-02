import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import BlogArticlePage from "@/app/vi/blog/[slug]/page";
import BlogIndex from "@/app/vi/blog/page";
import sitemap from "@/app/sitemap";
import { localeLanguages } from "@/lib/public-locales";
import { getPublishedPost, getRelatedPosts, parseBlogPost } from "./content";
import { articleStructuredData, blogMetadata } from "./seo";

const slug = "serp-la-gi";
const canonical = `https://serpsaas.com/vi/blog/${slug}`;

it("discovers the Vietnamese-only SERP guide with a separate SEO title and unchanged schema headline", () => {
  const post = getPublishedPost(slug, "vi")!;
  expect(post).toMatchObject({
    publishedAt: "2026-11-02",
    updatedAt: "2026-11-02",
    draft: false,
    featured: false,
  });
  render(<BlogIndex />);
  expect(screen.getAllByRole("link", { name: post.title })).toHaveLength(1);
  expect(sitemap().filter((entry) => entry.url === canonical)).toHaveLength(1);
  expect(getRelatedPosts(post)).toHaveLength(3);
  expect(getRelatedPosts(post).every((item) => item.locale === "vi")).toBe(
    true,
  );
  expect(
    getRelatedPosts(
      getPublishedPost("cach-kiem-tra-thu-hang-tu-khoa", "vi")!,
    ).map((item) => item.slug),
  ).toContain(slug);
  expect(getPublishedPost(slug)).toBeUndefined();
  expect(localeLanguages(`/vi/blog/${slug}`)).toBeUndefined();
  expect(blogMetadata(post)).toMatchObject({
    title: "SERP là gì? Các thành phần SERP Google và vai trò SEO",
    alternates: { canonical, languages: undefined },
    openGraph: { title: `${post.seoTitle} | SERP SaaS`, url: canonical },
    twitter: { title: `${post.seoTitle} | SERP SaaS` },
    robots: { index: true, follow: true },
  });
  expect(articleStructuredData(post)["@graph"][0]).toMatchObject({
    "@type": "BlogPosting",
    headline: post.title,
    inLanguage: "vi",
    datePublished: post.publishedAt,
    dateModified: post.updatedAt,
    mainEntityOfPage: { "@id": canonical },
  });
});

it("renders the supplied distinctions, two accessible tables and four contextual destinations", async () => {
  const { container } = render(
    await BlogArticlePage({ params: Promise.resolve({ slug }) }),
  );
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getAllByRole("table")).toHaveLength(2);
  expect(screen.getAllByRole("columnheader")).toHaveLength(6);
  for (const region of screen.getAllByRole("region", {
    name: "Bảng trong bài viết",
  }))
    expect(region).toHaveAttribute("tabindex", "0");
  const prose = container.querySelector(".blog-prose")!;
  for (const destination of [
    "/vi/blog/cong-cu-rank-tracker-la-gi",
    "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
    "/vi/blog/cach-theo-doi-thu-hang-doi-thu-seo",
    "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
  ])
    expect(prose.querySelectorAll(`a[href="${destination}"]`)).toHaveLength(1);
  for (const distinction of [
    "Search Engine Results Page",
    "không phải thứ hạng organic",
    "Nó khác với đoạn mô tả thông thường",
    "không bảo đảm",
    "average position",
    "Top 10",
    "dự án Desktop và Mobile riêng biệt",
    "đã hoàn tất",
    "phụ thuộc vào gói dịch vụ",
    "không thể suy ra vị trí chính xác",
    "không phải kết quả SERP thực tế",
  ])
    expect(prose).toHaveTextContent(distinction);
});

it.each(["", 123, "x".repeat(141)])(
  "rejects invalid optional SEO title %s",
  (value) => {
    const source = readFileSync("content/blog/vi/serp-la-gi.md", "utf8");
    const invalid = source.replace(
      /^seoTitle:.*$/m,
      `seoTitle: ${JSON.stringify(value)}`,
    );
    expect(() => parseBlogPost(invalid, `${slug}.md`)).toThrow("seoTitle");
  },
);
