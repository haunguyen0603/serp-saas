import { localeLanguages } from "@/lib/public-locales";
import type { Metadata } from "next";
import Link from "next/link";
import { SUPPORT_EMAIL, SUPPORT_EMAIL_HREF } from "@/lib/contact";

const description =
  "Learn how SERP SaaS handles account information, keyword tracking data, cookies, reports and subscription records.";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description,
  alternates: {
    canonical: "https://serpsaas.com/privacy",
    languages: localeLanguages("/privacy"),
  },
  openGraph: {
    type: "website",
    url: "https://serpsaas.com/privacy",
    title: "Privacy Policy | SERP SaaS",
    description,
    siteName: "SERP SaaS",
  },
};

export default function PrivacyPage() {
  return (
    <main className="public-main py-12 sm:py-16">
      <article className="mx-auto max-w-3xl space-y-8">
        <header className="space-y-4">
          <h1 className="text-3xl font-semibold sm:text-4xl">Privacy Policy</h1>
          <p className="text-sm text-secondary">
            Last updated: <time dateTime="2026-10-05">October 5, 2026</time>
          </p>
          <p>
            This policy explains how SERP SaaS handles information when you
            create an account, track Google rankings and use reports or paid
            Plans. Read it alongside our{" "}
            <Link className="ui-text-link" href="/terms">
              Terms of Service
            </Link>
            .
          </p>
        </header>

        <section className="space-y-3" aria-labelledby="privacy-information">
          <h2 id="privacy-information" className="text-xl font-semibold">
            1. Information handled by the service
          </h2>
          <p>
            Account records include your email address, a password hash, account
            status, sign-in timestamps and the time you accepted the Terms of
            Service. Passwords are stored as hashes rather than plain text.
          </p>
          <p>
            We store the Projects, Keywords, Tracked Sites, domain aliases,
            groups, tags and search settings you provide. We also store ranking
            results, check history, job status, schedules and generated reports
            so you can review your tracking activity over time.
          </p>
          <p>
            Subscription records include your selected Plans, subscription
            periods, usage and limits. Administrators may record payment
            references and activation notes when confirming a bank transfer. The
            service currently uses manual paid activation and does not collect
            payment card details through a checkout.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-use">
          <h2 id="privacy-use" className="text-xl font-semibold">
            2. How information is used
          </h2>
          <p>
            We use your email to send account-verification links and record when
            verification succeeds. We use this information to authenticate your
            account, run ranking checks, match your sites in search results,
            display history, generate reports and manage subscriptions and usage
            limits. When report email delivery is available and you enable a
            schedule, we use your verified account email to deliver the report.
          </p>
          <p>
            Technical records, such as request paths, response status,
            processing times and job errors, help diagnose failures and operate
            the service. Hosting services may also process connection
            information, such as IP addresses, in their operational logs.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-cookies">
          <h2 id="privacy-cookies" className="text-xl font-semibold">
            3. Cookies and sign-in sessions
          </h2>
          <p>
            We use an essential, HttpOnly refresh-session cookie to keep you
            signed in. Access tokens are held in application memory. Signing out
            revokes the current refresh session and clears its cookie. Blocking
            this cookie can prevent sign-in from working correctly.
          </p>
          <p>
            The current application does not include advertising cookies or
            third-party analytics trackers.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-providers">
          <h2 id="privacy-providers" className="text-xl font-semibold">
            4. Service providers and data sharing
          </h2>
          <p>
            Ranking checks send your keyword query and relevant search settings,
            such as country, language, location and device, to the configured
            search-data provider. The service supports Serper and SerpApi. Avoid
            entering passwords or confidential personal information in Keywords
            or domain fields.
          </p>
          <p>
            Hosting, database and file-storage providers process information
            needed to run the service. If email delivery is enabled, the email
            provider processes the recipient address and report message or
            attachment. Depending on the deployment and provider, processing may
            take place in a country other than your own.
          </p>
          <p>
            Account administrators can access information needed to manage
            customers and subscriptions. Customer access to tracking data and
            report downloads is restricted to the owning account.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-retention">
          <h2 id="privacy-retention" className="text-xl font-semibold">
            5. Storage and retention
          </h2>
          <p>
            Account, subscription and ranking-history records are kept to
            support the service and its history features. Removing a current
            Keyword or Tracked Site does not necessarily remove snapshots
            already saved in ranking history or reports.
          </p>
          <p>
            Generated report files have an expiry date shown in the service; the
            default retention period is 30 days. Expired files are removed
            through background cleanup. Report metadata and delivery records may
            remain after a file expires. Other records do not currently have an
            automatic deletion period.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-security">
          <h2 id="privacy-security" className="text-xl font-semibold">
            6. Protecting your information
          </h2>
          <p>
            The service uses password hashing, account authorization and
            authenticated report downloads to protect access. Keep your password
            private and sign out on shared devices. No online service can
            guarantee that information is completely secure.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-choices">
          <h2 id="privacy-choices" className="text-xl font-semibold">
            7. Your choices and requests
          </h2>
          <p>
            You can manage your Keywords and Tracked Sites, pause schedules, and
            export ranking information using the available CSV and PDF reports.
            For account-information corrections, account closure or requests
            about access to or deletion of your personal information, email{" "}
            <a className="ui-text-link" href={SUPPORT_EMAIL_HREF}>
              {SUPPORT_EMAIL}
            </a>
            . These requests currently require administrator assistance.
          </p>
          <p>
            Depending on the laws that apply to you, you may have additional
            rights concerning your personal information. We may need to verify
            your identity before handling a request. Do not send your password
            or sign-in tokens when requesting assistance.
          </p>
        </section>

        <section className="space-y-3" aria-labelledby="privacy-updates">
          <h2 id="privacy-updates" className="text-xl font-semibold">
            8. Questions and policy updates
          </h2>
          <p>
            If you have questions about this policy or how your information is
            handled, contact us at{" "}
            <a className="ui-text-link" href={SUPPORT_EMAIL_HREF}>
              {SUPPORT_EMAIL}
            </a>
            . We may update this page as the service changes. The date above
            identifies the current version.
          </p>
        </section>
      </article>
    </main>
  );
}
