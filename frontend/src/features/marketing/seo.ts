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

export function landingMetadata(page: LandingContent): Metadata {
  const url = new URL(page.path, getCanonicalSiteUrl()).toString();
  return {
    title: { absolute: page.title },
    description: page.description,
    alternates: { canonical: url },
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

export function landingStructuredData(page: LandingContent) {
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
        name: page.heading,
        description: page.description,
        about: { "@id": applicationId },
        breadcrumb: { "@id": `${url}#breadcrumbs` },
      },
      { ...softwareApplication, "@id": applicationId, url: site.origin },
      {
        "@type": "BreadcrumbList",
        "@id": `${url}#breadcrumbs`,
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${site}` },
          { "@type": "ListItem", position: 2, name: page.heading, item: url },
        ],
      },
    ],
  };
}
