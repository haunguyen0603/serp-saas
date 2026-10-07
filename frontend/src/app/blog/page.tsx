import type { Metadata } from "next";
import { getPublishedPosts } from "@/features/blog/content";
import { BlogCta, PostCard } from "@/features/blog/blog-components";
import { blogDescription, blogMetadata, blogTitle } from "@/features/blog/seo";

export const metadata: Metadata = blogMetadata();

export default function BlogPage() {
  const posts = getPublishedPosts().sort(
    (left, right) => Number(right.featured) - Number(left.featured),
  );
  return (
    <main className="public-main blog-main">
      <header className="blog-index-header">
        <p className="public-eyebrow">The SERP SaaS Blog</p>
        <h1>{blogTitle}</h1>
        <p>{blogDescription}</p>
      </header>
      <section className="blog-post-grid" aria-label="Published guides">
        {posts.map((post) => (
          <PostCard key={post.slug} post={post} featured={post.featured} />
        ))}
      </section>
      <BlogCta />
    </main>
  );
}
