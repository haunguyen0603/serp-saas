import Image from "next/image";
import Link from "next/link";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { siteHref } from "@/lib/site";
import { localizedPublicPath } from "@/lib/public-locales";
import type { BlogPost } from "./content";

export function formatBlogDate(value: string, locale: "en" | "vi" = "en") {
  return new Intl.DateTimeFormat(locale, {
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
  const vi = post.locale === "vi";
  const postPath = `${vi ? "/vi" : ""}/blog/${post.slug}`;
  const Heading = headingLevel === 3 ? "h3" : "h2";
  return (
    <article className={`blog-card${featured ? " blog-card-featured" : ""}`}>
      <p className="public-eyebrow">{post.category}</p>
      <Heading>
        <Link href={siteHref(postPath)}>{post.title}</Link>
      </Heading>
      <p className="blog-card-description">{post.description}</p>
      <div className="blog-card-meta">
        <time dateTime={post.updatedAt}>
          {post.updatedAt === post.publishedAt
            ? vi
              ? "Đăng ngày"
              : "Published"
            : vi
              ? "Cập nhật"
              : "Updated"}{" "}
          {formatBlogDate(post.updatedAt, post.locale)}
        </time>
        <span>
          {post.readingMinutes} {vi ? "phút đọc" : "min read"}
        </span>
      </div>
      <Link
        className="public-text-link"
        href={siteHref(postPath)}
        aria-label={`${vi ? "Đọc hướng dẫn" : "Read guide"}: ${post.title}`}
      >
        {vi ? "Đọc hướng dẫn" : "Read guide"} <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

export function BlogMarkdown({
  content,
  locale = "en",
}: {
  content: string;
  locale?: "en" | "vi";
}) {
  return (
    <div className="blog-prose">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          pre: ({ children }) => (
            <pre
              tabIndex={0}
              aria-label={locale === "vi" ? "Ví dụ mã" : "Code example"}
            >
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div
              className="blog-table-scroll"
              role="region"
              aria-label={
                locale === "vi" ? "Bảng trong bài viết" : "Article table"
              }
              tabIndex={0}
            >
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => {
            if (!href) return <span>{children}</span>;
            return href.startsWith("/") && !href.startsWith("//") ? (
              <Link href={siteHref(localizedPublicPath(href, locale))}>
                {children}
              </Link>
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

export function BlogCta({ locale = "en" }: { locale?: "en" | "vi" }) {
  if (locale === "vi")
    return (
      <aside className="blog-cta" aria-labelledby="blog-cta-title">
        <p className="public-eyebrow">Áp dụng vào công việc SEO</p>
        <h2 id="blog-cta-title">Theo dõi thứ hạng Google của bạn</h2>
        <p>
          Giữ môi trường tìm kiếm, phạm vi kiểm tra và lịch sử trong cùng dự án.
          So sánh gói Desktop và Mobile trước khi bắt đầu.
        </p>
        <Link
          href={siteHref("/vi/cong-cu-kiem-tra-thu-hang-tu-khoa")}
          className="public-text-link"
        >
          Tìm hiểu công cụ kiểm tra thứ hạng →
        </Link>
        <Link href={siteHref("/vi/bang-gia")} className="ui-link-button">
          Xem các gói dịch vụ
        </Link>
      </aside>
    );
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
