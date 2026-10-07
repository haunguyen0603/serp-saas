import { readBlogPosts } from "../src/features/blog/content.ts";

const posts = readBlogPosts();
console.log(
  `Blog content validated: ${posts.filter((post) => !post.draft).length} published, ${posts.filter((post) => post.draft).length} drafts.`,
);
