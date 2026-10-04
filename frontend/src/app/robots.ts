import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/pricing", "/about", "/privacy", "/terms"],
      disallow: [
        "/app",
        "/admin",
        "/settings",
        "/api",
        "/verify-email",
        "/login",
        "/register",
        "/signup",
      ],
    },
    sitemap: new URL("/sitemap.xml", getSiteUrl()).toString(),
  };
}
