import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  outputFileTracingIncludes: {
    "/blog": ["./content/blog/*.md"],
    "/blog/*": ["./content/blog/*.md"],
    "/sitemap.xml": ["./content/blog/*.md"],
    "/feed.xml": ["./content/blog/*.md"],
  },
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
};

export default nextConfig;
