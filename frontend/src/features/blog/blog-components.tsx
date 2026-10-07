import Image from "next/image";
import Link from "next/link";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { siteHref } from "@/lib/site";
import type { BlogPost } from "./content";

export function formatBlogDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

export function PostCard({
  post,
  featured = false,
  headingLevel = 2,
}: {
  post: BlogPost;
  featured?: boolean;
  headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 3 ? "h3" : "h2";
  return (
    <article className={`blog-card${featured ? " blog-card-featured" : ""}`}>
      <p className="public-eyebrow">{post.category}</p>
      <Heading>
        <Link href={siteHref(`/blog/${post.slug}`)}>{post.title}</Link>
      </Heading>
      <p className="blog-card-description">{post.description}</p>
      <div className="blog-card-meta">
        <time dateTime={post.updatedAt}>
          {post.updatedAt === post.publishedAt ? "Published" : "Updated"}{" "}
          {formatBlogDate(post.updatedAt)}
        </time>
        <span>{post.readingMinutes} min read</span>
      </div>
      <Link
        className="public-text-link"
        href={siteHref(`/blog/${post.slug}`)}
        aria-label={`Read ${post.title}`}
      >
        Read guide <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

export function BlogMarkdown({ content }: { content: string }) {
  return (
    <div className="blog-prose">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          pre: ({ children }) => (
            <pre tabIndex={0} aria-label="Code example">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div
              className="blog-table-scroll"
              role="region"
              aria-label="Article table"
              tabIndex={0}
            >
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => {
            if (!href) return <span>{children}</span>;
            return href.startsWith("/") && !href.startsWith("//") ? (
              <Link href={siteHref(href)}>{children}</Link>
            ) : (
              <a href={href}>{children}</a>
            );
          },
        }}
      >
        {content}
      </Markdown>
    </div>
  );
}

export function ArticleImage({ post }: { post: BlogPost }) {
  if (!post.image) return null;
  return (
    <Image
      className="blog-hero-image"
      src={post.image}
      alt={post.imageAlt!}
      width={post.imageWidth!}
      height={post.imageHeight!}
      sizes="(max-width: 800px) 100vw, 760px"
    />
  );
}

export function BlogCta() {
  return (
    <aside className="blog-cta" aria-labelledby="blog-cta-title">
      <p className="public-eyebrow">Put the workflow into practice</p>
      <h2 id="blog-cta-title">Track your own Google rankings.</h2>
      <p>
        Keep the search environment, checked depth and ranking history together
        in SERP SaaS. Compare Desktop and Mobile Plan limits before getting
        started.
      </p>
      <Link href={siteHref("/pricing")} className="ui-link-button">
        Explore rank-tracking Plans
      </Link>
    </aside>
  );
}
