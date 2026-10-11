import { join } from "node:path";
import { readBlogPosts } from "../src/features/blog/content.ts";

const posts = [
  ...readBlogPosts(),
  ...readBlogPosts(join(process.cwd(), "content/blog/vi"), "vi"),
];
console.log(
  `Blog content validated: ${posts.filter((post) => !post.draft).length} published, ${posts.filter((post) => post.draft).length} drafts.`,
);
