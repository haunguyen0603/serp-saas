import { publicLocalePairs } from "@/lib/public-locales";
import type { MetadataRoute } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";
import { getPublishedPosts } from "@/features/blog/content";
import { landingPageLinks } from "@/lib/landing-pages";

export default function sitemap(): MetadataRoute.Sitemap {
  const site = getCanonicalSiteUrl();
  return [
    {
      url: new URL("/", site).toString(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: new URL("/pricing", site).toString(),
      changeFrequency: "daily",
      priority: 0.9,
    },
    { url: new URL("/terms", site).toString(), priority: 0.3 },
    { url: new URL("/privacy", site).toString(), priority: 0.3 },
    { url: new URL("/about", site).toString(), priority: 0.5 },
    ...landingPageLinks.map((link) => ({
      url: new URL(link.href, site).toString(),
      priority: 0.8,
    })),
    {
      url: new URL("/blog", site).toString(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    ...publicLocalePairs
      .filter((pair) => !pair.vi.startsWith("/vi/blog/"))
      .map((pair) => ({
        url: new URL(pair.vi, site).toString(),
        priority: pair.vi === "/vi" ? 1 : 0.8,
      })),
    ...getPublishedPosts(undefined, "vi").map((post) => ({
      url: new URL(`/vi/blog/${post.slug}`, site).toString(),
      lastModified: post.updatedAt,
      priority: 0.6,
    })),
    ...getPublishedPosts().map((post) => ({
      url: new URL(`/blog/${post.slug}`, site).toString(),
      lastModified: post.updatedAt,
      priority: 0.6,
    })),
  ];
}
