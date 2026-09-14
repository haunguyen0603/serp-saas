import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/pricing", "/login", "/register"],
      disallow: ["/app", "/admin", "/settings", "/api"],
    },
    sitemap: new URL("/sitemap.xml", getSiteUrl()).toString(),
  };
}
