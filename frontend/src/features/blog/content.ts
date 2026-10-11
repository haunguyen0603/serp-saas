import { readdirSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { parseDocument } from "yaml";

export interface BlogPost {
  locale?: "en" | "vi";
  title: string;
  slug: string;
  description: string;
  publishedAt: string;
  updatedAt: string;
  author: string;
  category: string;
  tags: string[];
  featured: boolean;
  draft: boolean;
  image?: string;
  imageAlt?: string;
  imageWidth?: number;
  imageHeight?: number;
  content: string;
  readingMinutes: number;
}

const contentDirectory = (locale: "en" | "vi" = "en") =>
  join(process.cwd(), "content", "blog", ...(locale === "vi" ? ["vi"] : []));

export function parseBlogPost(source: string, filename: string): BlogPost {
  const fail = (message: string): never => {
    throw new Error(`Invalid blog content (${filename}): ${message}`);
  };
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]+)$/.exec(source);
  if (!match) fail("YAML frontmatter and article content are required.");
  const document = parseDocument(match![1], { uniqueKeys: true });
  if (document.errors.length) fail(document.errors[0].message);
  const parsed: unknown = document.toJS({ maxAliasCount: 0 });
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    fail("Frontmatter must be a mapping.");
  const data = parsed as Record<string, unknown>;
  const string = (field: string, max = 200) => {
    const value = data[field];
    if (typeof value !== "string" || !value.trim() || value.length > max)
      fail(`${field} must be a nonempty string of at most ${max} characters.`);
    return (value as string).trim();
  };
  const date = (field: string) => {
    const value = string(field, 10);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
      Number.isNaN(Date.parse(`${value}T00:00:00Z`)) ||
      new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value
    )
      fail(`${field} must be a valid YYYY-MM-DD date.`);
    return value;
  };
  if (data.locale !== undefined && data.locale !== "en" && data.locale !== "vi")
    fail("locale must be en or vi.");
  const slug = string("slug", 100);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug))
    fail("slug must use lowercase words separated by hyphens.");
  if (slug !== basename(filename, ".md"))
    fail("slug must match its Markdown filename.");
  const publishedAt = date("publishedAt");
  const updatedAt = date("updatedAt");
  if (updatedAt < publishedAt) fail("updatedAt must not precede publishedAt.");
  for (const field of ["draft", "featured"])
    if (typeof data[field] !== "boolean") fail(`${field} must be a boolean.`);
  if (
    !Array.isArray(data.tags) ||
    !data.tags.length ||
    data.tags.length > 12 ||
    data.tags.some(
      (tag) => typeof tag !== "string" || !tag.trim() || tag.length > 60,
    )
  )
    fail("tags must contain 1–12 nonempty strings of at most 60 characters.");
  const tags = (data.tags as string[]).map((tag) => tag.trim());
  if (new Set(tags.map((tag) => tag.toLowerCase())).size !== tags.length)
    fail("tags must be unique.");
  const content = match![2].trim();
  if (/^#\s/m.test(content))
    fail("Use H2–H4; the article page supplies its H1.");
  if (!/^##\s/m.test(content)) fail("At least one H2 is required.");

  const image = data.image;
  if (image !== undefined) {
    if (
      typeof image !== "string" ||
      !/^\/images\/blog\/[a-z0-9-]+\.(?:png|jpg|jpeg|webp|avif)$/.test(image)
    )
      fail("image must be a local /images/blog/ raster asset.");
    string("imageAlt");
    for (const field of ["imageWidth", "imageHeight"])
      if (!Number.isInteger(data[field]) || Number(data[field]) <= 0)
        fail(`${field} must be a positive integer when an image is supplied.`);
  }
  const wordCount = content
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .split(/\s+/)
    .filter(Boolean).length;
  return {
    ...(data.locale ? { locale: data.locale as "en" | "vi" } : {}),
    title: string("title", 140),
    slug,
    description: string("description", 220),
    publishedAt,
    updatedAt,
    author: string("author", 80),
    category: string("category", 80),
    tags,
    featured: data.featured as boolean,
    draft: data.draft as boolean,
    ...(image !== undefined
      ? {
          image: image as string,
          imageAlt: string("imageAlt"),
          imageWidth: data.imageWidth as number,
          imageHeight: data.imageHeight as number,
        }
      : {}),
    content,
    readingMinutes: Math.max(1, Math.ceil(wordCount / 220)),
  };
}

export function readBlogPosts(
  directory = contentDirectory(),
  locale: "en" | "vi" = "en",
): BlogPost[] {
  const posts = readdirSync(directory)
    .filter((filename) => filename.endsWith(".md"))
    .sort()
    .map((filename) =>
      parseBlogPost(readFileSync(join(directory, filename), "utf8"), filename),
    );
  for (const post of posts) {
    if ((post.locale ?? "en") !== locale)
      throw new Error(
        `Blog locale must match its content directory: ${post.slug}`,
      );
  }
  for (const field of ["slug", "title", "description"] as const) {
    const values = posts.map((post) => post[field].toLowerCase());
    if (new Set(values).size !== values.length)
      throw new Error(`Duplicate blog ${field}; each article must be unique.`);
  }
  return posts.sort(
    (left, right) =>
      right.publishedAt.localeCompare(left.publishedAt) ||
      left.slug.localeCompare(right.slug),
  );
}

export function getPublishedPosts(
  directory?: string,
  locale: "en" | "vi" = "en",
): BlogPost[] {
  return readBlogPosts(directory ?? contentDirectory(locale), locale).filter(
    (post) => !post.draft,
  );
}

export function getPublishedPost(
  slug: string,
  locale: "en" | "vi" = "en",
): BlogPost | undefined {
  return getPublishedPosts(undefined, locale).find(
    (post) => post.slug === slug,
  );
}

export function getRelatedPosts(
  post: BlogPost,
  posts = getPublishedPosts(undefined, post.locale ?? "en"),
) {
  return posts
    .filter(
      (candidate) =>
        !candidate.draft &&
        candidate.slug !== post.slug &&
        (candidate.locale ?? "en") === (post.locale ?? "en"),
    )
    .sort((left, right) => {
      const score = (candidate: BlogPost) =>
        candidate.tags.filter((tag) => post.tags.includes(tag)).length +
        Number(candidate.category === post.category);
      return score(right) - score(left) || left.slug.localeCompare(right.slug);
    })
    .slice(0, 3);
}
