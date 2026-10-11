import { getPublishedPosts } from "@/features/blog/content";
import { blogFeed } from "@/features/blog/rss";

export const dynamic = "force-static";

export function GET() {
  return new Response(blogFeed(getPublishedPosts()), {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
}
