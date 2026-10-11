import { localeLanguages } from "@/lib/public-locales";
import type { Metadata } from "next";
import Link from "next/link";
import { appHref } from "@/lib/site";
import { SUPPORT_EMAIL, SUPPORT_EMAIL_HREF } from "@/lib/contact";

const description =
  "Learn about SERP SaaS, a focused workspace for Google keyword rankings, Desktop and Mobile tracking, and ranking history.";

export const metadata: Metadata = {
  title: "About us",
  description,
  alternates: {
    canonical: "https://serpsaas.com/about",
    languages: localeLanguages("/about"),
  },
  openGraph: {
    type: "website",
    url: "https://serpsaas.com/about",
    title: "About us | SERP SaaS",
    description,
    siteName: "SERP SaaS",
  },
};

export default function AboutPage() {
  return (
    <main className="public-main py-12 sm:py-16">
      <article className="mx-auto max-w-3xl space-y-8">
        <header className="space-y-4">
          <p className="public-eyebrow">A focused workspace for SEO</p>
          <h1 className="text-3xl font-semibold sm:text-4xl">About us</h1>
          <p className="public-lead">
            SERP SaaS helps site owners and SEO teams understand how their
            websites appear in Google search and how those rankings change over
            time.
          </p>
        </header>

        <section className="space-y-3" aria-labelledby="about-purpose">
          <h2 id="about-purpose" className="text-xl font-semibold">
            Why SERP SaaS exists
          </h2>
          <p>
            A position alone does not tell the whole story. The keyword, device,
            location and time of a check all matter. Our aim is to keep that
            context beside your results, so you can review changes and make
            informed decisions about your SEO work.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="about-workflow">
          <h2 id="about-workflow" className="text-xl font-semibold">
            What you can do
          </h2>
          <p>
            Organize Keywords into Projects with a specific country, language,
            location and device. Track Desktop and Mobile independently, run
            checks manually or on a schedule supported by your Plan, and review
            completed results in ranking history.
          </p>
          <p>
            Tracked Sites bring current and historical domain aliases together.
            Groups and tags help organize Keywords, while CSV and PDF exports
            let you share ranking observations outside the workspace.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="about-approach">
          <h2 id="about-approach" className="text-xl font-semibold">
            Clear results and expectations
          </h2>
          <p>
            Each completed check is a snapshot of a particular search
            environment. Results can differ from your own browser and change
            between checks. A site that is not found within the checked depth
            may still appear further down the search results.
          </p>
          <p>
            We show check progress, failures and Plan usage so you can see what
            has run and what remains available. SERP SaaS helps measure
            rankings; it does not guarantee positions, traffic or business
            outcomes.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="about-start">
          <h2 id="about-start" className="text-xl font-semibold">
            Start with the work you need to track
          </h2>
          <p>
            Every account starts with Free Desktop and Mobile Plans. Paid Plans
            provide additional capacity and scheduling options, with activation
            handled by an administrator after bank-transfer confirmation. Review
            the current limits and prices before choosing a Plan.
          </p>
          <div className="public-cta-row">
            <Link href={appHref("/register")} className="ui-link-button">
              Start Free
            </Link>
            <Link href="/pricing" className="public-text-link">
              Explore Plans
            </Link>
          </div>
        </section>

        <section className="space-y-3" aria-labelledby="about-contact">
          <h2 id="about-contact" className="text-xl font-semibold">
            Questions about the service
          </h2>
          <p>
            For account support, Plan changes or paid activation, email us at{" "}
            <a className="ui-text-link" href={SUPPORT_EMAIL_HREF}>
              {SUPPORT_EMAIL}
            </a>
            . For details about using the service and how information is
            handled, read our{" "}
            <Link className="ui-text-link" href="/terms">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link className="ui-text-link" href="/privacy">
              Privacy Policy
            </Link>
            .
          </p>
        </section>
      </article>
    </main>
  );
}
