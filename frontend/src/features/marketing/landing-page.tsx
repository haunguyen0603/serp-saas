import { publicLocale, vietnameseProductLinks } from "@/lib/public-locales";
import Link from "next/link";
import { appHref, siteHref } from "@/lib/site";
import { landingPageLinks } from "@/lib/landing-pages";
import { serializeStructuredData } from "@/features/blog/seo";
import type { LandingContent } from "./landing-content";
import { landingStructuredData } from "./seo";

function LandingActions({
  label,
  vi = false,
}: {
  label: string;
  vi?: boolean;
}) {
  return (
    <div className="public-cta-row">
      <Link
        href={appHref("/register")}
        className="ui-link-button public-cta-primary"
      >
        {label}
      </Link>
      <Link
        href={siteHref(vi ? "/vi/bang-gia" : "/pricing")}
        className="public-secondary-link"
      >
        {vi ? "Xem bảng giá" : "View pricing"}
      </Link>
    </div>
  );
}

export function LandingPage({ page }: { page: LandingContent }) {
  const vi = publicLocale(page.path) === "vi";
  return (
    <main className="public-main landing-main">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: serializeStructuredData(landingStructuredData(page)),
        }}
      />
      <nav
        className="landing-breadcrumbs"
        aria-label={vi ? "Đường dẫn" : "Breadcrumb"}
      >
        <ol>
          <li>
            <Link href={siteHref(vi ? "/vi" : "/")}>
              {vi ? "Trang chủ" : "Home"}
            </Link>
          </li>
          <li aria-current="page">{page.heading}</li>
        </ol>
      </nav>
      <section className="landing-hero" aria-labelledby="landing-heading">
        <div>
          <p className="public-eyebrow">{page.eyebrow}</p>
          <h1 id="landing-heading">{page.heading}</h1>
          <p className="public-lead">{page.lead}</p>
          <LandingActions vi={vi} label={page.finalCta.label} />
          <p className="public-cta-note">{page.note}</p>
        </div>
        <aside className="landing-workflow" aria-label={page.workflow.heading}>
          <h2>{page.workflow.heading}</h2>
          <ol>
            {page.workflow.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </aside>
      </section>
      <div className="landing-section-grid">
        {page.sections.slice(0, 2).map((section) => (
          <LandingSection key={section.heading} section={section} />
        ))}
      </div>
      <section className="landing-mid-cta" aria-labelledby="mid-cta-heading">
        <h2 id="mid-cta-heading">{page.midCta.heading}</h2>
        <p>{page.midCta.description}</p>
        <LandingActions vi={vi} label={page.midCta.label} />
      </section>
      <div className="landing-section-grid">
        {page.sections.slice(2).map((section) => (
          <LandingSection key={section.heading} section={section} />
        ))}
      </div>
      <section className="landing-guides" aria-labelledby="guides-heading">
        <h2 id="guides-heading">
          {vi
            ? "Áp dụng vào công việc SEO"
            : "Put your tracking workflow into practice"}
        </h2>
        <p>{page.guide.description}</p>
        <Link href={siteHref(page.guide.path)} className="public-text-link">
          {page.guide.label} →
        </Link>
        <nav
          aria-label={vi ? "Công cụ liên quan" : "Related product workflows"}
        >
          {(vi ? vietnameseProductLinks : landingPageLinks)
            .filter((link) => link.href !== page.path)
            .map((link) => (
              <Link key={link.href} href={siteHref(link.href)}>
                {link.label} →
              </Link>
            ))}
        </nav>
      </section>
      <section className="public-final-cta" aria-labelledby="final-cta-heading">
        <h2 id="final-cta-heading">{page.finalCta.heading}</h2>
        <p>{page.finalCta.description}</p>
        <LandingActions vi={vi} label={page.finalCta.label} />
      </section>
    </main>
  );
}

function LandingSection({
  section,
}: {
  section: LandingContent["sections"][number];
}) {
  return (
    <section className="landing-section">
      <h2>{section.heading}</h2>
      {section.paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
      {section.items && (
        <ul>
          {section.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
