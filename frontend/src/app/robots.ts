import type { MetadataRoute } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/pricing", "/about", "/privacy", "/terms", "/blog"],
      disallow: [
        "/app",
        "/admin",
        "/settings",
        "/api",
        "/verify-email",
        "/forgot-password",
        "/reset-password",
        "/login",
        "/register",
        "/signup",
      ],
    },
    sitemap: new URL("/sitemap.xml", getCanonicalSiteUrl()).toString(),
  };
}
