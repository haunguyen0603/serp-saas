# Milestone 7G.1 — Dependency Security Remediation

## 1. Objective

Remediate the unresolved dependency security findings reported after M7G without introducing unrelated framework changes or regressions.

The M7G verification reported:

```text
npm install:
9 findings
- 8 high
- 1 critical

npm audit --omit=dev --json:
3 runtime findings
- Next.js: critical
- sharp: high
- source-map-js: high
```

The affected locked versions were reported as:

```text
next: 16.3.4
sharp: 0.35.4
source-map-js: 1.2.1
```

The M7G report explicitly states that these findings were pre-existing and were not introduced by the new Markdown/YAML dependencies.

This milestone must focus only on dependency remediation and verification.

Do not implement new product features.

---

## 2. Primary Goal

After remediation:

```text
npm audit --omit=dev
```

should report no high/critical runtime vulnerabilities, unless an upstream package has no safe compatible release.

If a remaining vulnerability cannot be resolved safely, document:

```text
package
advisory
severity
affected dependency path
reason remediation is blocked
runtime exposure
mitigation
upgrade path
```

Do not silently accept unresolved critical/high findings.

---

## 3. Pre-Implementation Audit

Before editing package versions:

1. inspect:
   - `frontend/package.json`
   - lockfile
   - current Node engine
   - Next.js configuration
   - Docker frontend build
   - production runtime image
   - M7G Blog implementation

2. run:

```bash
npm audit --omit=dev --json
npm ls next sharp source-map-js
```

3. identify the exact advisory IDs/CVEs and dependency paths.

4. determine whether each package is:
   - direct dependency;
   - transitive dependency;
   - runtime dependency;
   - build-only dependency.

5. determine the minimum safe version that resolves each advisory.

Do not upgrade dependencies before identifying the exact vulnerable path.

---

## 4. Upgrade Strategy

Use the smallest safe compatible upgrades.

Priority:

```text
patch
→ minor
→ major only if required
```

Do not perform broad dependency modernization.

Do not run:

```text
npm audit fix --force
```

without an explicit package-by-package review.

Do not upgrade unrelated libraries just because newer versions exist.

---

## 5. Next.js Remediation

The M7G report identified a critical finding associated with:

```text
next 16.3.4
```

Requirements:

1. identify the exact advisory affecting the installed Next.js version;
2. find the first safe release in the same compatible release line if available;
3. upgrade to the minimum safe version;
4. inspect release notes/changelog for:
   - App Router changes;
   - middleware/proxy behavior;
   - metadata routes;
   - sitemap/robots;
   - standalone output;
   - server actions;
   - image behavior;
   - Node version requirements.

5. verify the following routes after upgrade:

```text
/
 /pricing
 /about
 /privacy
 /terms

 /blog
 /blog/how-to-track-google-rankings
 /blog/serp-tracking-for-agencies
 /blog/how-to-monitor-keyword-ranking

 /login
 /register
 /verify-email

 /app
 /app/projects
```

Do not move to a new major version unless required to resolve the advisory and compatibility has been reviewed.

---

## 6. sharp Remediation

The M7G report identified a high-severity finding associated with:

```text
sharp 0.35.4
```

Requirements:

1. determine whether `sharp` is direct or transitive;
2. identify which package requires it;
3. upgrade to the minimum safe compatible version;
4. verify Next.js image/build behavior;
5. verify production Docker build on the target architecture;
6. verify no native binary/install issue is introduced.

If the project does not directly use `sharp` but Next.js does, prefer upgrading through the owning dependency rather than forcing an unsafe override unless the override is officially compatible.

---

## 7. source-map-js Remediation

The M7G report identified a high-severity finding associated with:

```text
source-map-js 1.2.1
```

Requirements:

1. determine the full dependency chain;
2. identify whether a parent dependency update resolves it;
3. prefer parent dependency upgrade over package-manager overrides;
4. use an override/resolution only when:
   - there is no upstream compatible release;
   - compatibility is verified;
   - the override is documented.

Do not add an override without explaining why.

---

## 8. Lockfile Integrity

After package changes:

```text
package.json
package-lock.json / equivalent lockfile
```

must be consistent.

Do not manually edit the lockfile.

Do not switch package managers.

Do not regenerate unrelated dependency versions unnecessarily.

---

## 9. Node Runtime

M7G verification used:

```text
Node 22.22.0
```

and noted that the host Node 20 did not meet the repository engine requirement.

Requirements:

- preserve the repository's Node engine contract;
- verify local/CI/Docker frontend builds use a supported Node version;
- do not lower the engine requirement just to make local tooling pass;
- document the actual Node version used for verification.

---

## 10. Docker Build Verification

Rebuild the production frontend image.

Verify:

```text
docker compose build frontend
```

or the repository's actual production build command.

Confirm:

- dependency install succeeds;
- native dependencies install correctly;
- Next.js standalone output is produced;
- Blog Markdown files remain traced into `.next/standalone/content/blog/`;
- no runtime dependency is accidentally omitted.

---

## 11. M7G Regression Requirements

M7G functionality must remain unchanged.

Verify:

```text
/blog
/blog/[slug]
/feed.xml
/sitemap.xml
/robots.txt
```

Required:

- 3 published Blog posts still present;
- draft exclusion still works;
- unknown slug returns 404;
- canonical URLs still use `https://serpsaas.com`;
- JSON-LD remains valid;
- RSS still returns three items;
- sitemap contains Blog index + 3 articles;
- robots still permits Blog crawling;
- PublicShell navigation still contains Blog.

---

## 12. Existing Application Regression

Do not limit testing only to Blog.

At minimum verify:

```text
Home
Pricing
Login
Register
Verify Email
App shell
Projects
Project detail
Ranking Explorer
Reports
Competitor Analytics
Admin route protection
```

The dependency patch must not alter authentication, ranking, billing, report, or analytics behavior.

---

## 13. Automated Verification

Run:

```bash
npm test
npm run lint
npm run typecheck
npm run format:check
npm audit --omit=dev
npm run build
git diff --check
```

Use the repository's required environment variables.

If the full frontend test suite requires:

```text
NEXT_PUBLIC_API_BASE_URL
NEXT_PUBLIC_APP_ENV
```

supply safe test values as done in M7G verification.

Do not skip failing suites.

---

## 14. Security Verification

Record before/after audit output.

Required evidence:

```text
Before:
critical = ?
high = ?
moderate = ?
low = ?

After:
critical = ?
high = ?
moderate = ?
low = ?
```

For each remediated advisory, document:

```text
package
old version
new version
advisory
why fixed
```

If any high/critical issue remains, explain why.

---

## 15. Browser QA

Re-run browser verification for:

```text
/blog
/blog/how-to-track-google-rankings
/blog/serp-tracking-for-agencies
/blog/how-to-monitor-keyword-ranking
```

At:

```text
375
768
1024
1440
```

Check:

- no browser exceptions;
- no hydration errors;
- no broken styles;
- no horizontal overflow;
- Blog metadata renders;
- PublicShell navigation works;
- mobile navigation works;
- JavaScript-disabled article readability remains.

Also smoke-test:

```text
/
/pricing
/login
/register
/app
```

---

## 16. Standalone Production Verification

Run the generated Next.js standalone server, not only `next dev`.

Verify:

```text
HTTP 200:
/
 /blog
 /blog/how-to-track-google-rankings
 /feed.xml
 /sitemap.xml
 /robots.txt

HTTP 404:
 /blog/unknown-slug
```

Investigate whether the M7G-observed:

```text
Internal: NoFallbackError
```

diagnostic on unknown slugs still appears after the Next.js remediation.

If it disappears, record that.

If it remains while responses are correctly 404, document it as a known framework diagnostic.

---

## 17. Production Deployment Gate

Do not deploy automatically unless deployment is explicitly authorized.

Before production deployment, all of these should pass:

```text
0 unresolved critical runtime vulnerabilities
0 unresolved high runtime vulnerabilities
frontend tests
lint
typecheck
format
production build
browser QA
standalone QA
```

If a high/critical issue remains due to an upstream blocker, stop and report before deployment.

---

## 18. No Unrelated Changes

Do not modify:

```text
backend
database schema
Alembic
Cloud Run architecture
Cloud SQL
Cloud Tasks
billing
rank checks
reports
competitor analytics
email verification
Blog content wording
SEO strategy
```

unless required strictly for compatibility with the dependency remediation.

Any compatibility edit must be minimal and documented.

---

## 19. Files Expected to Change

Likely:

```text
frontend/package.json
frontend/package-lock.json
```

Potentially:

```text
Next.js config
Docker frontend definition
small compatibility code
```

Do not create broad unrelated diffs.

---

## 20. Definition of Done

- [ ] Exact advisories identified.
- [ ] Vulnerable dependency paths documented.
- [ ] Minimum safe upgrades selected.
- [ ] Next.js critical issue remediated.
- [ ] sharp high issue remediated.
- [ ] source-map-js high issue remediated.
- [ ] No force audit fix.
- [ ] Lockfile consistent.
- [ ] Full frontend test suite passes.
- [ ] ESLint passes.
- [ ] TypeScript passes.
- [ ] Prettier passes.
- [ ] Production build passes.
- [ ] Docker frontend build passes.
- [ ] M7G Blog behavior unchanged.
- [ ] Browser QA passes.
- [ ] Standalone QA passes.
- [ ] `npm audit --omit=dev` contains no unresolved high/critical runtime findings.
- [ ] No backend/business behavior changed.

---

## 21. Final Verification Report

Create:

```text
docs/verification-milestone-7g1.md
```

Include:

```text
baseline dependency versions
advisory IDs / CVEs
dependency chains
versions changed
reason for each upgrade
before/after audit results
files changed
frontend test results
lint
typecheck
format
build
Docker build
browser QA
standalone QA
known limitations
production deployment status
```

Do not claim production verification unless the production deployment was actually performed.

---

## 22. Final Instruction to Codex

Treat this as a security maintenance milestone, not a feature milestone.

First identify the exact advisories and dependency chains.

Then apply the smallest safe compatible upgrades.

Do not use broad forced upgrades.

Do not upgrade unrelated packages.

Preserve M7G Blog behavior and the existing production architecture.

Stop and report if a critical/high advisory cannot be safely resolved without a major architectural/framework migration.
