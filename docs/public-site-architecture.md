# M6.5B public site architecture

The public site uses a dedicated `PublicShell` for `/`, `/pricing`, `/about`, `/privacy`, `/terms`, `/login`, `/register` and the existing `/signup` alias. It lives inside the existing top-level providers so navigation can adapt after login, but it does not render the authenticated sidebar, account navigation or Admin controls. `/app`, `/settings/billing` and `/admin` continue to use the M6.5A `AppShell`; `/health` keeps its small diagnostic layout.

## Route ownership

| Route          | Rendering and responsibility                                                    |
| -------------- | ------------------------------------------------------------------------------- |
| `/`            | Static Home page and accurate synthetic product preview                         |
| `/pricing`     | Static page metadata plus a client catalog query to `GET /api/v1/billing/plans` |
| `/about`       | Static product introduction and links to Plans, Terms and Privacy               |
| `/privacy`     | Static privacy policy reflecting current data handling                          |
| `/terms`       | Static Terms of Service                                                         |
| `/login`       | Existing login form inside the public shell                                     |
| `/register`    | Existing signup workflow exposed at the requested public route                  |
| `/robots.txt`  | Next.js metadata route with public allowance and private-path exclusions        |
| `/sitemap.xml` | Next.js metadata route containing only implemented public pages                 |

`frontend/src/lib/site.ts` provides the canonical origin from `NEXT_PUBLIC_SITE_URL`. Local and Docker development default to `http://localhost:3000`; deployments should set the public HTTPS origin.

## Public shell

The shell owns the sticky header, logo, Home/Pricing navigation, login/account link, primary start/app link, mobile drawer, skip link and footer. It reuses the M6.5A `Drawer`, `Icon`, `IconButton`, button styles and focus-management behavior. One shared navigation definition supplies desktop and mobile active-route state. The footer only links to implemented Product and Account routes, so there are no placeholder routes in navigation.

Logged-out users see Log in and Get Started. Logged-in users see Account and Open App. The mobile drawer traps keyboard focus, closes with Escape or navigation, restores trigger focus and releases page scrolling.

## Home

Home remains a server/static component. Its ordered sections are:

1. Hero with Start Free and View Pricing actions.
2. A concise product-benefit strip.
3. The real four-step site, project, keyword and check workflow.
4. Core feature cards.
5. Separate Desktop and Mobile search experiences.
6. Tracked Site and historical domain-alias continuity.
7. manual, weekly and daily scheduling with Plan-qualified language.
8. Project, Keyword, monthly logical-check and schedule limits.
9. A future-facing customer API/developer-documentation teaser that explicitly says it is unavailable.
10. Final registration and Pricing actions.

The product preview is code-native and uses synthetic `seo-demo.com` data. It contains no customer identity, bank reference, provider metadata, Admin notes or secrets. Public copy does not market provider routing, queue infrastructure, automatic billing, analytics or unimplemented API access.

## Pricing

`PricingCatalog` uses TanStack Query and `requestJson` to read the public authoritative Plan catalog. `groupPlans` filters by backend `device_scope` and orders Free, Starter and Pro within separate Desktop and Mobile sections. Each card renders the API price, currency, Project limit, Keyword limit, monthly logical-check limit and scheduling entitlement. Frontend constants contain only tier order and audience copy; they do not contain fallback prices or limits.

While loading, Pricing uses the shared `Skeleton`. A failed catalog request shows the shared retryable `ErrorState` and explicitly withholds fallback prices. The pricing page therefore cannot silently drift from M6A Plan values.

Free CTAs lead logged-out visitors to `/register` and authenticated visitors to `/app`. Paid cards say Request Activation: logged-out visitors register first, while authenticated visitors go to `/settings/billing`. The page explains manual bank-transfer confirmation by an administrator. It has no checkout, payment provider, self-activation or Admin action.

## SEO and public boundary

Root metadata defines the product title template and `metadataBase`. Home and Pricing each supply a description, canonical URL, Open Graph fields and Twitter summary metadata. Home emits a limited `SoftwareApplication` JSON-LD object with no invented offers, reviews or ratings.

The sitemap contains only `/`, `/pricing`, `/login`, `/register`, `/terms`, `/privacy` and `/about`. Robots rules disallow `/app`, `/admin`, `/settings` and `/api`. Backend authorization and route guards remain responsible for security; robots directives only guide crawlers.

## Responsive and accessibility rules

Public CSS shares the light M6.5A tokens, strong type, navy surfaces, blue actions, borders, radii and restrained shadows. The Hero changes from two columns to a stack below 980px. Pricing changes from three columns to two below 980px and one below 760px. Details, usage, footer and feature grids stack at the same responsive boundaries. At 1100px and below, desktop navigation is replaced by the accessible drawer.

Pages use header, navigation, main, section, article and footer landmarks; a single page-level `h1`; ordered `h2`/`h3` structure; textual Plan/status labels; real links for navigation and buttons only for actions. Shared `:focus-visible` styling and Drawer focus management apply to public controls.

## Future hooks

M6.5C may add the customer API and API keys, and M6.5D may add developer documentation. At that point their routes can be linked from the header/footer and advertised in the sitemap. M6.5B creates no placeholder routes or public `/api/v1` contract. Payment integration remains reserved for M6B.

## Terms of Service (2026-09-20)

`/terms` is a public, static page with English service terms, a revision date, canonical URL and Open Graph metadata. Its content lives in `frontend/src/app/terms/page.tsx` for the product owner to review and maintain. Header navigation, the mobile drawer and the footer link to the page.

The registration checkbox keeps its existing required acceptance behavior. Its inline Terms of Service link opens `/terms` in a separate tab with `noopener noreferrer`, preserving the in-progress registration form. Opening the link does not check the checkbox or submit the form. The same AuthForm covers `/register` and `/signup`.

Verification: 94 frontend tests in 18 files passed, along with ESLint, Prettier, strict TypeScript and the production Docker frontend build. Chrome checked the public page, header/footer/drawer links, metadata, sitemap, and registration popup/form preservation at 375, 768, 1024 and 1440px. Screenshots are local artifacts under `.tools/terms/`. Header navigation switches to the shared drawer at tablet widths to accommodate the additional link without wrapping the account actions. Backend authentication and acceptance persistence are unchanged.

## Privacy and About us (2026-10-03)

`/privacy` and `/about` are public static pages using the same article layout as
Terms of Service. Both provide descriptions, canonical URLs and Open Graph
metadata, and appear in the shared desktop/mobile navigation, footer and sitemap.
The public header switches to the drawer at 1100px to accommodate the added links.
Registration also links to Privacy Policy in a separate tab, preserving form input
and the existing Terms acceptance requirement.

Privacy describes account, tracking, subscription and operational records,
essential authentication cookies, search-data providers, report email delivery,
retention and administrator-assisted requests. It reflects current implementation:
report files expire (30 days by default); other records have no automatic deletion
period. It does not promise self-service account deletion or a particular
jurisdiction's compliance. About us describes the product purpose and implemented
features without inventing team members, company history or customer counts.

The owner has deferred the operator identity and contact email. Both pages currently
refer account questions to the responsible administrator, consistent with Terms.
Before public launch, add the confirmed operator/contact details and confirm actual
hosting providers, data locations and retention policies against the deployment.
Privacy notice structure was informed by the [ICO guidance on privacy information](https://cy.ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/);
this is not a claim that UK GDPR applies to this service.

Verification: all 109 existing frontend tests passed across 22 files using Node
22.22.0, alongside ESLint, TypeScript, formatting checks and the production build.
Chrome checked both pages at 375, 768, 1024 and 1440px: public layout, active
navigation, footer links, canonical/Open Graph URLs, no horizontal overflow,
mobile drawer and sitemap. Opening Privacy from registration preserved form
values and left Terms unchecked. Browser checks mocked only session refresh;
no registration request was submitted. Screenshots were inspected from temporary
files rather than committed to the repository.

## Separate commercial and application domains (2026-10-04)

Production uses `NEXT_PUBLIC_SITE_URL=https://serpsaas.com` for the five commercial
pages and `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com` for authentication and
product routes. Both hosts use the same Next.js service. `src/proxy.ts` redirects
routes to their owning host, preserving queries; the app root opens `/app` and
existing authentication/verification gates enforce access. A missing app URL keeps
one-origin local development working.

Public CTAs point to the app origin; signup legal links point to the commercial
origin. The commercial host does not restore an account session. Marketing metadata
and the five-page sitemap use the main origin; auth/app routes are excluded from
indexing. The host redirects do not authorize requests or replace backend checks.

Build arguments, Cloud Run helpers, API CORS and verification-email origin are
configured together. Follow [the domain deployment runbook](architecture/cloud-run-frontend-deployment.md#6-tách-website-thương-mại-và-ứng-dụng-theo-domain)
for HTTPS load balancing, DNS, full-source upload, build/deploy and validation.
