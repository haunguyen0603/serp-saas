import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const site = getSiteUrl();
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
    { url: new URL("/login", site).toString(), priority: 0.3 },
    { url: new URL("/register", site).toString(), priority: 0.7 },
    { url: new URL("/terms", site).toString(), priority: 0.3 },
  ];
}
