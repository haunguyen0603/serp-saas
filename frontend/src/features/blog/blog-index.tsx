import { getPublishedPosts } from "@/features/blog/content";
import { BlogCta, PostCard } from "@/features/blog/blog-components";
import {
  blogDescription,
  blogTitle,
  vietnameseBlogTitle,
  vietnameseBlogDescription,
  blogIndexStructuredData,
  serializeStructuredData,
} from "@/features/blog/seo";

export function BlogIndex({ locale = "en" }: { locale?: "en" | "vi" }) {
  const vi = locale === "vi";
  const posts = getPublishedPosts(undefined, locale).sort(
    (left, right) => Number(right.featured) - Number(left.featured),
  );
  return (
    <main className="public-main blog-main">
      {vi && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: serializeStructuredData(blogIndexStructuredData(locale)),
          }}
        />
      )}
      <header className="blog-index-header">
        <p className="public-eyebrow">
          {vi ? "Blog SERP SaaS" : "The SERP SaaS Blog"}
        </p>
        <h1>{vi ? vietnameseBlogTitle : blogTitle}</h1>
        <p>{vi ? vietnameseBlogDescription : blogDescription}</p>
      </header>
      <section
        className="blog-post-grid"
        aria-label={vi ? "Hướng dẫn đã xuất bản" : "Published guides"}
      >
        {posts.map((post) => (
          <PostCard key={post.slug} post={post} featured={post.featured} />
        ))}
      </section>
      <BlogCta locale={locale} />
    </main>
  );
}
