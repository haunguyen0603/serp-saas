import Link from "next/link";
import { getRelatedPosts, type BlogPost } from "@/features/blog/content";
import {
  ArticleImage,
  BlogCta,
  BlogMarkdown,
  formatBlogDate,
  PostCard,
} from "@/features/blog/blog-components";
import {
  articleStructuredData,
  serializeStructuredData,
} from "@/features/blog/seo";
import { siteHref } from "@/lib/site";

export function BlogArticle({ post }: { post: BlogPost }) {
  const vi = post.locale === "vi";
  const locale = post.locale ?? "en";
  const related = getRelatedPosts(post);
  return (
    <main className="public-main blog-main">
      <nav
        className="blog-breadcrumbs"
        aria-label={vi ? "Đường dẫn" : "Breadcrumb"}
      >
        <ol>
          <li>
            <Link href={siteHref(vi ? "/vi" : "/")}>
              {vi ? "Trang chủ" : "Home"}
            </Link>
          </li>
          <li>
            <Link href={siteHref(vi ? "/vi/blog" : "/blog")}>Blog</Link>
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
            <span>
              {vi ? "Tác giả:" : "By"} {post.author}
            </span>
            <span>
              {vi ? "Đăng ngày" : "Published"}{" "}
              <time dateTime={post.publishedAt}>
                {formatBlogDate(post.publishedAt, locale)}
              </time>
            </span>
            {post.updatedAt !== post.publishedAt && (
              <span>
                {vi ? "Cập nhật" : "Updated"}{" "}
                <time dateTime={post.updatedAt}>
                  {formatBlogDate(post.updatedAt, locale)}
                </time>
              </span>
            )}
            <span>
              {post.readingMinutes} {vi ? "phút đọc" : "min read"}
            </span>
          </div>
        </header>
        <ArticleImage post={post} />
        <BlogMarkdown content={post.content} locale={locale} />
      </article>
      {!!related.length && (
        <section className="blog-related" aria-labelledby="related-heading">
          <h2 id="related-heading">{vi ? "Đọc thêm" : "Keep reading"}</h2>
          <div className="blog-post-grid">
            {related.map((item) => (
              <PostCard key={item.slug} post={item} headingLevel={3} />
            ))}
          </div>
        </section>
      )}
      <BlogCta locale={locale} />
    </main>
  );
}
