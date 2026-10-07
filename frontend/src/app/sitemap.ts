import type { MetadataRoute } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";
import { getPublishedPosts } from "@/features/blog/content";

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
    {
      url: new URL("/blog", site).toString(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    ...getPublishedPosts().map((post) => ({
      url: new URL(`/blog/${post.slug}`, site).toString(),
      lastModified: post.updatedAt,
      priority: 0.6,
    })),
  ];
}
