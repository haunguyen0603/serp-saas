import { localeLanguages, publicLocale } from "@/lib/public-locales";
import type { Metadata } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";
import type { LandingContent } from "./landing-content";

export const softwareApplication = {
  "@type": "SoftwareApplication",
  name: "SERP SaaS",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description:
    "Google keyword rank tracking for separate Desktop and Mobile Projects, schedules and ranking history.",
};

export function landingMetadata(
  page: Pick<LandingContent, "path" | "title" | "description" | "heading">,
): Metadata {
  const url = new URL(page.path, getCanonicalSiteUrl()).toString();
  return {
    title: { absolute: page.title },
    description: page.description,
    alternates: { canonical: url, languages: localeLanguages(page.path) },
    robots: { index: true, follow: true },
    openGraph: {
      type: "website",
      url,
      title: page.title,
      description: page.description,
      siteName: "SERP SaaS",
    },
    twitter: {
      card: "summary",
      title: page.title,
      description: page.description,
    },
  };
}

export function landingStructuredData(
  page: Pick<LandingContent, "path" | "title" | "description" | "heading">,
) {
  const vi = publicLocale(page.path) === "vi";
  const site = getCanonicalSiteUrl();
  const url = new URL(page.path, site).toString();
  const applicationId = `${site.origin}/#software`;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "@id": url,
        url,
        inLanguage: vi ? "vi" : "en",
        name: page.heading,
        description: page.description,
        about: { "@id": applicationId },
        breadcrumb: { "@id": `${url}#breadcrumbs` },
      },
      {
        ...softwareApplication,
        ...(vi
          ? {
              description:
                "Theo dõi thứ hạng từ khóa Google, lịch kiểm tra và lịch sử trên các dự án Desktop và Mobile riêng biệt.",
              inLanguage: "vi",
            }
          : {}),
        "@id": applicationId,
        url: site.origin,
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${url}#breadcrumbs`,
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: vi ? "Trang chủ" : "Home",
            item: new URL(vi ? "/vi" : "/", site).toString(),
          },
          { "@type": "ListItem", position: 2, name: page.heading, item: url },
        ],
      },
    ],
  };
}
