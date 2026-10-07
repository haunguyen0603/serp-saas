import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getPublishedPost,
  getPublishedPosts,
  getRelatedPosts,
} from "@/features/blog/content";
import {
  ArticleImage,
  BlogCta,
  BlogMarkdown,
  formatBlogDate,
  PostCard,
} from "@/features/blog/blog-components";
import {
  articleStructuredData,
  blogMetadata,
  serializeStructuredData,
} from "@/features/blog/seo";
import { siteHref } from "@/lib/site";

export const dynamicParams = false;

export function generateStaticParams() {
  return getPublishedPosts().map((post) => ({ slug: post.slug }));
}

type ArticleProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({
  params,
}: ArticleProps): Promise<Metadata> {
  const post = getPublishedPost((await params).slug);
  if (!post) notFound();
  return blogMetadata(post);
}

export default async function BlogArticlePage({ params }: ArticleProps) {
  const post = getPublishedPost((await params).slug);
  if (!post) notFound();
  const related = getRelatedPosts(post);
  return (
    <main className="public-main blog-main">
      <nav className="blog-breadcrumbs" aria-label="Breadcrumb">
        <ol>
          <li>
            <Link href={siteHref("/")}>Home</Link>
          </li>
          <li>
            <Link href={siteHref("/blog")}>Blog</Link>
          </li>
          <li aria-current="page">{post.title}</li>
        </ol>
      </nav>
      <article className="blog-article">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: serializeStructuredData(articleStructuredData(post)),
          }}
        />
        <header className="blog-article-header">
          <p className="public-eyebrow">{post.category}</p>
          <h1>{post.title}</h1>
          <p className="blog-article-lead">{post.description}</p>
          <div className="blog-byline">
            <span>By {post.author}</span>
            <span>
              Published{" "}
              <time dateTime={post.publishedAt}>
                {formatBlogDate(post.publishedAt)}
              </time>
            </span>
            {post.updatedAt !== post.publishedAt && (
              <span>
                Updated{" "}
                <time dateTime={post.updatedAt}>
                  {formatBlogDate(post.updatedAt)}
                </time>
              </span>
            )}
            <span>{post.readingMinutes} min read</span>
          </div>
        </header>
        <ArticleImage post={post} />
        <BlogMarkdown content={post.content} />
      </article>
      {!!related.length && (
        <section className="blog-related" aria-labelledby="related-heading">
          <h2 id="related-heading">Keep reading</h2>
          <div className="blog-post-grid">
            {related.map((item) => (
              <PostCard key={item.slug} post={item} headingLevel={3} />
            ))}
          </div>
        </section>
      )}
      <BlogCta />
    </main>
  );
}
