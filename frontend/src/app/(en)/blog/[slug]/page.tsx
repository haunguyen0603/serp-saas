import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPublishedPost, getPublishedPosts } from "@/features/blog/content";
import { blogMetadata } from "@/features/blog/seo";
import { BlogArticle } from "@/features/blog/blog-article";
export const dynamicParams = false;
export function generateStaticParams() {
  return getPublishedPosts(undefined, "en").map((post) => ({
    slug: post.slug,
  }));
}
type ArticleProps = { params: Promise<{ slug: string }> };
export async function generateMetadata({
  params,
}: ArticleProps): Promise<Metadata> {
  const post = getPublishedPost((await params).slug, "en");
  if (!post) notFound();
  return blogMetadata(post);
}
export default async function BlogArticlePage({ params }: ArticleProps) {
  const post = getPublishedPost((await params).slug, "en");
  if (!post) notFound();
  return <BlogArticle post={post} />;
}
