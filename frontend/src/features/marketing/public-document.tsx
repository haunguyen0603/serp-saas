import type { ReactNode } from "react";
import { publicLocale } from "@/lib/public-locales";
import { getCanonicalSiteUrl } from "@/lib/site";
import { serializeStructuredData } from "@/features/blog/seo";
import { landingMetadata } from "./seo";

export type PublicPageInfo = {
  path: string;
  title: string;
  description: string;
  heading: string;
};
export const publicPageMetadata = landingMetadata;

export function PublicPageSchema({ page }: { page: PublicPageInfo }) {
  const url = new URL(page.path, getCanonicalSiteUrl()).toString();
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: serializeStructuredData({
          "@context": "https://schema.org",
          "@type": "WebPage",
          "@id": url,
          url,
          name: page.heading,
          description: page.description,
          inLanguage: publicLocale(page.path),
        }),
      }}
    />
  );
}

export function PublicDocument({
  page,
  eyebrow,
  updatedAt,
  introduction,
  sections,
}: {
  page: PublicPageInfo;
  eyebrow?: string;
  updatedAt?: { date: string; label: string };
  introduction: ReactNode;
  sections: { id: string; heading: string; content: ReactNode }[];
}) {
  return (
    <main className="public-main py-12 sm:py-16">
      <PublicPageSchema page={page} />
      <article className="mx-auto max-w-3xl space-y-8">
        <header className="space-y-4">
          {eyebrow && <p className="public-eyebrow">{eyebrow}</p>}
          <h1 className="text-3xl font-semibold sm:text-4xl">{page.heading}</h1>
          {updatedAt && (
            <p className="text-sm text-secondary">
              Cập nhật lần cuối:{" "}
              <time dateTime={updatedAt.date}>{updatedAt.label}</time>
            </p>
          )}
          {introduction}
        </header>
        {sections.map((section) => (
          <section
            className="space-y-3"
            aria-labelledby={section.id}
            key={section.id}
          >
            <h2 id={section.id} className="text-xl font-semibold">
              {section.heading}
            </h2>
            {section.content}
          </section>
        ))}
      </article>
    </main>
  );
}
