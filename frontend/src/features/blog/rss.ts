import type { BlogPost } from "./content";
import { blogDescription, blogTitle, blogUrl } from "./seo";
import { getCanonicalSiteUrl } from "@/lib/site";

const escapeXml = (value: string) =>
  value.replace(
    /[<>&"']/g,
    (character) =>
      ({
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
      })[character]!,
  );

export function blogFeed(posts: BlogPost[]) {
  const items = posts
    .filter((post) => !post.draft)
    .map((post) => {
      const url = escapeXml(blogUrl(post.slug));
      return `<item><title>${escapeXml(post.title)}</title><link>${url}</link><guid isPermaLink="true">${url}</guid><description>${escapeXml(post.description)}</description><pubDate>${new Date(`${post.publishedAt}T00:00:00Z`).toUTCString()}</pubDate></item>`;
    })
    .join("");
  const feedUrl = new URL("/feed.xml", getCanonicalSiteUrl()).toString();
  return `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>${escapeXml(blogTitle)} | SERP SaaS</title><link>${escapeXml(blogUrl())}</link><description>${escapeXml(blogDescription)}</description><language>en</language><atom:link href="${escapeXml(feedUrl)}" rel="self" type="application/rss+xml"/>${items}</channel></rss>`;
}
