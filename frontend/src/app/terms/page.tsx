import type { Metadata } from "next";
import Link from "next/link";

const description =
  "Read the Terms of Service for SERP SaaS, including account responsibilities, rank tracking, Plan limits and subscription activation.";

export const metadata: Metadata = {
  title: "Terms of Service",
  description,
  alternates: { canonical: "/terms" },
  openGraph: {
    type: "website",
    url: "/terms",
    title: "Terms of Service | SERP SaaS",
    description,
    siteName: "SERP SaaS",
  },
};

export default function TermsPage() {
  return (
    <main className="public-main py-12 sm:py-16">
      <article className="mx-auto max-w-3xl space-y-8">
        <header className="space-y-4">
          <h1 className="text-3xl font-semibold sm:text-4xl">
            Terms of Service
          </h1>
          <p className="text-sm text-secondary">
            Last updated: <time dateTime="2026-09-20">September 20, 2026</time>
          </p>
          <p>
            These terms explain how you may use SERP SaaS and what to expect
            from the service. By creating an account and accepting these terms,
            you agree to follow them when using SERP SaaS.
          </p>
        </header>

        <section className="space-y-3" aria-labelledby="terms-service">
          <h2 id="terms-service" className="text-xl font-semibold">
            1. The service
          </h2>
          <p>
            SERP SaaS helps you track Google keyword rankings, organize
            Projects, manage Tracked Sites and domain aliases, and review
            completed ranking checks. Desktop and Mobile are separate tracking
            environments with separate Plans and limits.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-account">
          <h2 id="terms-account" className="text-xl font-semibold">
            2. Your account
          </h2>
          <p>
            Provide accurate account information and keep your sign-in
            credentials secure. You are responsible for activity carried out
            through your account. When email verification is required, confirm
            your email address before using the workspace. Do not use another
            person’s account without permission or attempt to access another
            customer’s data.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-use">
          <h2 id="terms-use" className="text-xl font-semibold">
            3. Acceptable use
          </h2>
          <p>
            Use the service lawfully and respect the rights of others. Do not
            attempt to bypass access controls or Plan limits, disrupt the
            service, introduce malicious code, or use the service to collect
            information you are not authorized to access. Access may be
            restricted to address abuse or protect the service and its users.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-rankings">
          <h2 id="terms-rankings" className="text-xl font-semibold">
            4. Ranking results and third-party services
          </h2>
          <p>
            A ranking result is a snapshot for a particular keyword, device,
            location and time. Search results can change and can differ from
            results in your own browser because of location, personalization or
            other search settings. A missing result means it was not found
            within the depth checked, not that it cannot appear elsewhere in
            search results.
          </p>
          <p>
            Search data depends on third-party services and may be delayed or
            unavailable. SERP SaaS does not guarantee a particular search
            position, traffic level or business outcome. Google and other
            third-party names belong to their respective owners; using these
            names does not imply endorsement.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-plans">
          <h2 id="terms-plans" className="text-xl font-semibold">
            5. Plans, limits and usage
          </h2>
          <p>
            Each Plan specifies limits for Projects, Keywords and monthly
            keyword checks, together with any scheduling entitlement. Desktop
            and Mobile subscriptions are managed separately. You can review
            current offers on the{" "}
            <Link className="ui-text-link" href="/pricing">
              Pricing page
            </Link>
            , and your active terms and usage in Billing &amp; Usage.
          </p>
          <p>
            Usage is measured in logical keyword checks rather than internal
            provider requests. Scheduling and new checks remain subject to your
            active Plan and available quota. Catalog changes apply to new
            activations; existing subscriptions keep their saved prices and
            limits, including when extended.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-activation">
          <h2 id="terms-activation" className="text-xl font-semibold">
            6. Paid activation and subscription changes
          </h2>
          <p>
            Paid Plans use manual bank-transfer activation by an administrator.
            Selecting a paid Plan or requesting activation does not
            automatically charge you or activate the Plan. Confirm the amount,
            payment instructions and subscription period with the administrator
            before transferring funds.
          </p>
          <p>
            Ask the administrator handling your activation about Plan changes,
            extensions, cancellation and any payment or refund questions. Review
            the confirmed subscription dates and terms in Billing &amp; Usage.
            When a paid subscription is no longer active, available access is
            subject to the applicable Free Plan limits.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-data">
          <h2 id="terms-data" className="text-xl font-semibold">
            7. Information you provide
          </h2>
          <p>
            You are responsible for the Keywords, domains and other information
            you enter. Only provide information you are authorized to use.
            Search queries and relevant search settings are sent to search-data
            providers as needed to perform checks. Avoid entering passwords,
            payment credentials or confidential personal information in keyword
            or domain fields.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="terms-availability">
          <h2 id="terms-availability" className="text-xl font-semibold">
            8. Availability and updates
          </h2>
          <p>
            Maintenance, technical issues and third-party outages can interrupt
            access or delay checks. Features and these terms may be updated as
            the service evolves. The date at the top of this page identifies the
            current version. If you have questions about these terms, contact
            the administrator responsible for your account before requesting a
            paid activation.
          </p>
        </section>
      </article>
    </main>
  );
}
