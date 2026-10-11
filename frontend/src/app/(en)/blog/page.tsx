import { BlogIndex } from "@/features/blog/blog-index";
import { blogMetadata } from "@/features/blog/seo";
export const metadata = blogMetadata(undefined, "en");
export default function BlogPage() {
  return <BlogIndex locale="en" />;
}
