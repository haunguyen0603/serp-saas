import { localeLanguages } from "@/lib/public-locales";
import type { Metadata } from "next";
import { PricingCatalog } from "@/features/marketing/pricing-catalog";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Compare Desktop and Mobile rank-tracking Plans, keyword limits, monthly checks and scheduling options.",
  alternates: {
    canonical: "https://serpsaas.com/pricing",
    languages: localeLanguages("/pricing"),
  },
  openGraph: {
    type: "website",
    url: "https://serpsaas.com/pricing",
    title: "Pricing | SERP SaaS",
    description:
      "Compare separate Desktop and Mobile rank-tracking Plans and their current limits.",
    siteName: "SERP SaaS",
  },
  twitter: {
    card: "summary_large_image",
    title: "Pricing | SERP SaaS",
    description:
      "Compare separate Desktop and Mobile rank-tracking Plans and their current limits.",
  },
};

export default function PricingPage() {
  return <PricingCatalog />;
}
