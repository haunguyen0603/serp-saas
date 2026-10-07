import type { Metadata } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";
import type { BlogPost } from "./content";

export const blogTitle = "SERP Tracking & SEO Insights";
export const blogDescription =
  "Practical guides on Google rank tracking, SERP monitoring, keyword performance, reporting, and competitor analysis.";

export function blogUrl(slug?: string) {
  return new URL(
    slug ? `/blog/${slug}` : "/blog",
    getCanonicalSiteUrl(),
  ).toString();
}

export function blogMetadata(post?: BlogPost): Metadata {
  const title = post?.title ?? blogTitle;
  const description = post?.description ?? blogDescription;
  const url = blogUrl(post?.slug);
  return {
    title,
    description,
    alternates: {
      canonical: url,
      types: {
        "application/rss+xml": new URL(
          "/feed.xml",
          getCanonicalSiteUrl(),
        ).toString(),
      },
    },
    openGraph: {
      title: `${title} | SERP SaaS`,
      description,
      url,
      siteName: "SERP SaaS",
      type: post ? "article" : "website",
      ...(post
        ? {
            publishedTime: post.publishedAt,
            modifiedTime: post.updatedAt,
            authors: [post.author],
            tags: post.tags,
          }
        : {}),
      ...(post?.image
        ? {
            images: [
              {
                url: new URL(post.image, getCanonicalSiteUrl()).toString(),
                width: post.imageWidth,
                height: post.imageHeight,
                alt: post.imageAlt,
              },
            ],
          }
        : {}),
    },
    twitter: {
      card: post?.image ? "summary_large_image" : "summary",
      title: `${title} | SERP SaaS`,
      description,
      ...(post?.image
        ? { images: [new URL(post.image, getCanonicalSiteUrl()).toString()] }
        : {}),
    },
  };
}

export function articleStructuredData(post: BlogPost) {
  const url = blogUrl(post.slug);
  const home = getCanonicalSiteUrl().origin;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BlogPosting",
        "@id": `${url}#article`,
        headline: post.title,
        description: post.description,
        datePublished: post.publishedAt,
        dateModified: post.updatedAt,
        author: { "@type": "Organization", name: post.author },
        publisher: { "@type": "Organization", name: "SERP SaaS", url: home },
        mainEntityOfPage: { "@type": "WebPage", "@id": url },
        ...(post.image ? { image: new URL(post.image, home).toString() } : {}),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${home}/` },
          { "@type": "ListItem", position: 2, name: "Blog", item: blogUrl() },
          { "@type": "ListItem", position: 3, name: post.title, item: url },
        ],
      },
    ],
  };
}

export function serializeStructuredData(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
