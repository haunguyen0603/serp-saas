import { localeLanguages } from "@/lib/public-locales";
import type { Metadata } from "next";
import { getCanonicalSiteUrl } from "@/lib/site";
import type { BlogPost } from "./content";

export const blogTitle = "SERP Tracking & SEO Insights";
export const blogDescription =
  "Practical guides on Google rank tracking, SERP monitoring, keyword performance, reporting, and competitor analysis.";

export function blogUrl(slug?: string, locale: "en" | "vi" = "en") {
  return new URL(
    `${locale === "vi" ? "/vi" : ""}/blog${slug ? `/${slug}` : ""}`,
    getCanonicalSiteUrl(),
  ).toString();
}

export const vietnameseBlogTitle = "Kiến thức SEO & Theo dõi thứ hạng";
export const vietnameseBlogDescription =
  "Hướng dẫn theo dõi thứ hạng Google, kiểm tra vị trí từ khóa và đọc biến động SEO tại Việt Nam với môi trường tìm kiếm nhất quán.";

export function blogIndexStructuredData(locale: "en" | "vi") {
  const url = blogUrl(undefined, locale);
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": url,
    url,
    inLanguage: locale,
    name: locale === "vi" ? vietnameseBlogTitle : blogTitle,
    description: locale === "vi" ? vietnameseBlogDescription : blogDescription,
  };
}

export function blogMetadata(
  post?: BlogPost,
  locale: "en" | "vi" = post?.locale ?? "en",
): Metadata {
  const title =
    post?.seoTitle ??
    post?.title ??
    (locale === "vi" ? vietnameseBlogTitle : blogTitle);
  const description =
    post?.description ??
    (locale === "vi" ? vietnameseBlogDescription : blogDescription);
  const url = blogUrl(post?.slug, locale);
  return {
    title,
    description,
    alternates: {
      canonical: url,
      languages: localeLanguages(new URL(url).pathname),
      ...(locale === "en"
        ? {
            types: {
              "application/rss+xml": new URL(
                "/feed.xml",
                getCanonicalSiteUrl(),
              ).toString(),
            },
          }
        : {}),
    },
    ...(locale === "vi" ? { robots: { index: true, follow: true } } : {}),
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
  const locale = post.locale ?? "en";
  const url = blogUrl(post.slug, locale);
  const home = getCanonicalSiteUrl().origin;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BlogPosting",
        "@id": `${url}#article`,
        inLanguage: locale,
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
          {
            "@type": "ListItem",
            position: 1,
            name: locale === "vi" ? "Trang chủ" : "Home",
            item: `${home}${locale === "vi" ? "/vi" : "/"}`,
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Blog",
            item: blogUrl(undefined, locale),
          },
          { "@type": "ListItem", position: 3, name: post.title, item: url },
        ],
      },
    ],
  };
}

export function serializeStructuredData(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
