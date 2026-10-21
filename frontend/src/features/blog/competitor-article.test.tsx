import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import BlogArticlePage from "@/app/vi/blog/[slug]/page";
import BlogIndex from "@/app/vi/blog/page";
import sitemap from "@/app/sitemap";
import { getPublishedPost, getRelatedPosts } from "./content";
import { articleStructuredData, blogMetadata } from "./seo";

const slug = "cach-theo-doi-thu-hang-doi-thu-seo";
const path = `/vi/blog/${slug}`;
const canonical = `https://serpsaas.com${path}`;

it("publishes the competitor guide once in the Vietnamese index, sitemap and related discovery", () => {
  const post = getPublishedPost(slug, "vi")!;
  expect(post).toMatchObject({
    title: "Cách theo dõi thứ hạng đối thủ SEO bằng dữ liệu SERP",
    publishedAt: "2026-10-21",
    updatedAt: "2026-10-21",
    author: "SERP SaaS",
    draft: false,
    featured: false,
  });
  render(<BlogIndex />);
  expect(screen.getAllByRole("link", { name: post.title })).toHaveLength(1);
  expect(sitemap().filter((entry) => entry.url === canonical)).toHaveLength(1);
  expect(
    getRelatedPosts(getPublishedPost("cong-cu-rank-tracker-la-gi", "vi")!).map(
      (item) => item.slug,
    ),
  ).toContain(slug);
  expect(blogMetadata(post)).toMatchObject({
    title: post.title,
    robots: { index: true, follow: true },
    alternates: { canonical },
  });
  expect(articleStructuredData(post)["@graph"][0]).toMatchObject({
    "@type": "BlogPosting",
    inLanguage: "vi",
    datePublished: "2026-10-21",
    dateModified: "2026-10-21",
    mainEntityOfPage: { "@id": canonical },
  });
});

it("renders the educational comparisons, accessible tables and both editorial links", async () => {
  const { container } = render(
    await BlogArticlePage({ params: Promise.resolve({ slug }) }),
  );
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getAllByRole("table")).toHaveLength(4);
  expect(screen.getAllByRole("columnheader")).toHaveLength(12);
  for (const region of screen.getAllByRole("region", {
    name: "Bảng trong bài viết",
  }))
    expect(region).toHaveAttribute("tabindex", "0");
  expect(
    screen.getByRole("link", { name: "Rank Tracker là gì?" }),
  ).toHaveAttribute("href", "/vi/blog/cong-cu-rank-tracker-la-gi");
  expect(
    screen.getByRole("link", {
      name: "SERP SaaS dành cho SEO Agency",
    }),
  ).toHaveAttribute("href", "/vi/seo-rank-tracking-cho-agency");
  const prose = container.querySelector(".blog-prose")!;
  for (const boundary of [
    "số liệu chỉ để minh họa",
    "dữ liệu minh họa",
    "dữ liệu SERP đã được lưu từ những lần kiểm tra",
    "tối đa năm đối thủ",
    "project thuộc tài khoản của mình",
    "Desktop và Mobile được tổ chức thành các project riêng",
    "Top 10",
    "không có nghĩa là website đứng ngoài Top 100",
    "Không nên coi average position của Search Console",
    "Nếu có lần kiểm tra thất bại hoặc dữ liệu không đầy đủ",
  ])
    expect(prose).toHaveTextContent(boundary);
});
