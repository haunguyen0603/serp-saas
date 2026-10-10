import type { Metadata } from "next";
import Link from "next/link";
import { appHref, siteHref } from "@/lib/site";
import { landingPageLinks } from "@/lib/landing-pages";
import { softwareApplication } from "@/features/marketing/seo";
import { serializeStructuredData } from "@/features/blog/seo";

export const metadata: Metadata = {
  title: { absolute: "Google Rank Tracker for Desktop & Mobile | SERP SaaS" },
  description:
    "Track Google keyword rankings across Desktop and Mobile, schedule rank checks, monitor ranking history, and manage SEO sites in one place.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    title: "Google Rank Tracker for Desktop & Mobile | SERP SaaS",
    description:
      "Track Google keyword rankings, schedules and history across Desktop and Mobile.",
    siteName: "SERP SaaS",
  },
  twitter: {
    card: "summary_large_image",
    title: "Google Rank Tracker for Desktop & Mobile | SERP SaaS",
    description:
      "Track Google keyword rankings, schedules and history across Desktop and Mobile.",
  },
};

const features = [
  [
    "Keyword rank tracking",
    "See current Google positions and keep every completed check in history.",
  ],
  [
    "Desktop and Mobile",
    "Create focused Projects for each search experience and measure them independently.",
  ],
  [
    "Scheduled checks",
    "Run checks manually, weekly or daily according to your Plan.",
  ],
  [
    "Tracked Sites",
    "Match owned sites in results while keeping current and historical domains together.",
  ],
  [
    "Batch progress",
    "Follow queued, running, completed and failed keyword checks without losing context.",
  ],
  [
    "Usage and limits",
    "Know your Projects, Keywords and monthly checks before starting more work.",
  ],
];

const structuredData = {
  "@context": "https://schema.org",
  ...softwareApplication,
};

export default function HomePage() {
  return (
    <main className="public-main">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: serializeStructuredData(structuredData),
        }}
      />
      <section className="public-hero" aria-labelledby="hero-title">
        <div className="public-hero-copy">
          <p className="public-eyebrow">Google rank tracking, made clear</p>
          <h1 id="hero-title">Track your Google rankings with clarity.</h1>
          <p className="public-lead">
            Monitor keywords across Desktop and Mobile, schedule recurring
            checks, and keep reliable ranking history in one focused workspace.
          </p>
          <div className="public-cta-row">
            <Link
              href={appHref("/register")}
              className="ui-link-button public-cta-primary"
            >
              Start Free
            </Link>
            <Link href="/pricing" className="public-secondary-link">
              View Pricing
            </Link>
          </div>
          <p className="public-cta-note">
            Free Desktop and Mobile Plans included. No card required.
          </p>
        </div>
        <div
          className="public-product-preview"
          aria-label="SERP SaaS product preview"
        >
          <div className="preview-topbar">
            <span className="preview-logo">S</span>
            <span>Overview</span>
            <span className="preview-live">Workspace</span>
          </div>
          <div className="preview-stats">
            <div>
              <span>Active keywords</span>
              <strong>184</strong>
            </div>
            <div>
              <span>Checks this month</span>
              <strong>1,248</strong>
            </div>
            <div>
              <span>Tracked sites</span>
              <strong>3</strong>
            </div>
          </div>
          <div className="preview-panel">
            <div className="preview-panel-heading">
              <strong>US Desktop</strong>
              <span>Completed</span>
            </div>
            <div className="preview-ranking-row preview-heading">
              <span>Keyword</span>
              <span>Position</span>
              <span>Site</span>
            </div>
            <div className="preview-ranking-row">
              <span>best running shoes</span>
              <strong>#4</strong>
              <span>seo-demo.com</span>
            </div>
            <div className="preview-ranking-row">
              <span>trail shoe guide</span>
              <strong>#9</strong>
              <span>seo-demo.com</span>
            </div>
          </div>
          <div className="preview-usage">
            <span>Desktop checks</span>
            <strong>1,248 / 5,000</strong>
            <div>
              <i />
            </div>
          </div>
        </div>
      </section>

      <section className="public-benefits" aria-label="Product benefits">
        {[
          "Desktop & Mobile tracking",
          "Scheduled checks",
          "Ranking history",
          "Domain alias tracking",
          "Clear Plan limits",
        ].map((benefit) => (
          <span key={benefit}>✓ {benefit}</span>
        ))}
      </section>

      <section className="public-section" aria-labelledby="workflow-title">
        <div className="public-section-heading">
          <p className="public-eyebrow">A workflow that matches SEO work</p>
          <h2 id="workflow-title">
            From site setup to a ranking history in four steps.
          </h2>
        </div>
        <ol className="public-steps">
          {[
            [
              "Add your Tracked Site",
              "Group the domains that represent one SEO asset.",
            ],
            [
              "Create a Project",
              "Set Google country, language, location and device.",
            ],
            [
              "Add Keywords",
              "Build the focused query set you want to monitor.",
            ],
            [
              "Run or schedule checks",
              "Review positions now or automate checks when your Plan allows.",
            ],
          ].map(([title, description], index) => (
            <li key={title}>
              <span>{index + 1}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </li>
          ))}
        </ol>
      </section>

      <section
        className="public-section public-tinted"
        aria-labelledby="features-title"
      >
        <div className="public-section-heading">
          <p className="public-eyebrow">
            Everything needed for consistent tracking
          </p>
          <h2 id="features-title">Useful signals, without the noise.</h2>
          <p>
            Keep the environment, result history and usage context beside every
            keyword.
          </p>
        </div>
        <div className="public-feature-grid">
          {features.map(([title, description], index) => (
            <article className="ui-card public-feature" key={title}>
              <span className="public-feature-icon" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="public-split public-section"
        aria-labelledby="devices-title"
      >
        <div>
          <p className="public-eyebrow">Two search experiences</p>
          <h2 id="devices-title">Desktop and Mobile rankings can differ.</h2>
          <p>
            Track them independently with separate Projects, usage limits and
            Plans. Choose the scope that matches how each audience searches.
          </p>
          <Link href="/pricing" className="public-text-link">
            Compare Desktop and Mobile Plans →
          </Link>
        </div>
        <div
          className="device-comparison"
          aria-label="Desktop and Mobile ranking example"
        >
          <article>
            <span>Desktop</span>
            <strong>#4</strong>
            <p>best running shoes</p>
          </article>
          <article>
            <span>Mobile</span>
            <strong>#7</strong>
            <p>best running shoes</p>
          </article>
        </div>
      </section>

      <section className="public-section public-detail-grid">
        <article className="public-detail-card">
          <p className="public-eyebrow">Tracked Sites</p>
          <h2>Keep one SEO asset through domain changes.</h2>
          <p>
            Add current and historical domain aliases so matching rankings stay
            associated with the same site after a migration or redirect.
          </p>
          <div className="alias-demo">
            <strong>seo-demo.com</strong>
            <span>Primary</span>
            <strong>example.com</strong>
            <span>Alias</span>
          </div>
        </article>
        <article className="public-detail-card public-dark-card">
          <p className="public-eyebrow">Flexible cadence</p>
          <h2>Check manually, weekly or daily.</h2>
          <p>
            Run a check when you need it. Starter Plans support weekly
            scheduling; Pro Plans support daily or weekly scheduling.
          </p>
          <div className="schedule-demo">
            <span>Mon</span>
            <span>Tue</span>
            <strong>Wed</strong>
            <span>Thu</span>
            <span>Fri</span>
          </div>
        </article>
      </section>

      <section
        className="public-section public-usage-section"
        aria-labelledby="plans-title"
      >
        <div>
          <p className="public-eyebrow">Predictable usage</p>
          <h2 id="plans-title">A Plan for the work you track.</h2>
          <p>
            Every Plan clearly defines Project, Keyword and monthly logical
            check limits, plus its scheduling entitlement. Start small and
            request a manual upgrade when you need more.
          </p>
          <Link href="/pricing" className="ui-link-button">
            Explore Plans
          </Link>
        </div>
        <div className="public-limit-list">
          <span>
            Projects <i>Separate by device</i>
          </span>
          <span>
            Keywords <i>Clear capacity</i>
          </span>
          <span>
            Monthly checks <i>Visible usage</i>
          </span>
          <span>
            Schedules <i>Plan-based cadence</i>
          </span>
        </div>
      </section>

      <section className="public-section" aria-labelledby="tracking-use-cases">
        <div className="public-section-heading">
          <p className="public-eyebrow">Choose your tracking workflow</p>
          <h2 id="tracking-use-cases">
            Built for different rank-tracking workflows
          </h2>
        </div>
        <div className="public-feature-grid">
          {landingPageLinks.map((link) => (
            <article className="ui-card public-feature" key={link.href}>
              <h3>
                <Link href={siteHref(link.href)}>{link.label}</Link>
              </h3>
              <p>{link.description}</p>
              <Link href={siteHref(link.href)} className="public-text-link">
                Explore {link.label} →
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="public-developer" aria-labelledby="developer-title">
        <p className="public-eyebrow">Coming in a future milestone</p>
        <h2 id="developer-title">Built with teams and integrations in mind.</h2>
        <p>
          A customer API and developer documentation are planned next. They are
          not available yet.
        </p>
      </section>
      <section className="public-final-cta" aria-labelledby="final-cta-title">
        <h2 id="final-cta-title">Start building a clearer ranking history.</h2>
        <p>
          Create your account, add a site and run your first small keyword set
          on the Free Plans.
        </p>
        <div className="public-cta-row">
          <Link href={appHref("/register")} className="ui-link-button">
            Start Free
          </Link>
          <Link href="/pricing" className="public-secondary-link">
            View Pricing
          </Link>
        </div>
      </section>
    </main>
  );
}
