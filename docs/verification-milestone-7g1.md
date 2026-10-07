# Milestone 7G.1 — Dependency Security Remediation verification

**Production follow-up, 2026-10-07:** the user subsequently authorized deployment. Commit `7edae61` was released successfully through Cloud Build; 23 real-domain HTTP checks and 16 public Blog browser cases passed. See [production release evidence and limitations](deployment-milestone-7g1.md). The report below preserves the initial local verification and its then-undeployed status.

Verified locally on 2026-10-07. **All three reported runtime vulnerabilities are fixed; `npm audit --omit=dev` reports 0 findings.** Full audit still reports **5 high development-tool findings** from one unpatched `braces` advisory. This is not a claim that the entire dependency tree is vulnerability-free. No production deployment, production-domain verification, GitHub push or Search Console inspection was performed.

## Baseline and scope

The baseline was the existing M7G working tree on base commit `abb3beb`, including its Markdown dependencies and shared Blog CTA width fix, not an empty checkout of HEAD. Baseline lockfile versions were Next / eslint-config-next 16.3.4, sharp 0.35.4, source-map-js 1.2.1, brace-expansion 1.1.18 and 5.0.9. The M7G changes already present in the worktree were preserved.

Changes attributable to this milestone:

- `frontend/package.json`: pin Next and its ESLint config to matching 16.3.6 patches. The Node engine remains `>=22.22.0`; React and all other direct dependencies stay unchanged.
- `frontend/package-lock.json`: compatible targeted resolutions for Next, sharp, source-map-js and brace-expansion, including their matching native bundles. No overrides, new direct dependencies, major upgrades or `npm audit fix --force`.
- `frontend/scripts/verify-blog-browser.mjs`: selectable artifact directory and explicit hydration-console detection, preserving M7G assertions.
- `frontend/scripts/verify-security-regression.mjs`: local-only browser smoke with intercepted synthetic APIs and no real backend writes.
- This report, audit/browser artifacts, the README version row and a follow-up note in the historical M7G report.

No application compatibility edits were needed. Backend, database, auth, billing, rank checks, reports, competitor behavior, Blog wording, metadata strategy, Next configuration, Docker definition, CI/Cloud Run architecture and `.env` were not changed by M7G.1.

## Exact advisories, paths and minimum-safe resolutions

| Package / role | Dependency path before remediation | Advisory / CVE | Before → selected first-safe version | Reason |
| --- | --- | --- | --- | --- |
| Next, direct runtime | application → next | [GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j); no CVE listed on the advisory | 16.3.4 → **16.3.6** | Critical `next/og` Node ImageResponse upstream code-execution issue; affected 16.2.0 through versions below 16.3.6. |
| sharp, optional transitive runtime | next → sharp → platform-specific `@img/*` native bundles | [GHSA-wq5f-xc86-pv6w](https://github.com/advisories/GHSA-wq5f-xc86-pv6w); upstream librsvg **CVE-2026-96889** | 0.35.4 → **0.35.5** | High SVG processing issue; this patch ships corrected prebuilt librsvg dependencies. Next's existing `^0.35.4` range accepts it. |
| source-map-js, transitive runtime/build | next → postcss 8.5.23 → source-map-js; also Tailwind's postcss / `@tailwindcss/node` paths | [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q); **CVE-2026-93749** | 1.2.1 → **1.2.2** | High denial of service involving indexed source-map section offsets. Owning `^1.2.1` ranges already accept the patch. |
| brace-expansion, transitive dev | eslint 9.39.4 → minimatch 3.1.5 → brace-expansion; eslint-config-next → typescript-eslint → typescript-estree → minimatch 10.2.6 → brace-expansion | Three advisories below | 1.1.18 → **1.1.21**, 5.0.9 → **5.0.12** | Smallest compatible versions fixing all three reported advisories, without upgrading ESLint or changing majors. |

The three brace-expansion advisories have different individual first-safe versions:

- [GHSA-6j4f-fj2g-mc7p / CVE-2026-102276](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p): high; first safe 1.1.19 / 5.0.10.
- [GHSA-qhr7-859c-m2p7 / CVE-2026-102278](https://github.com/advisories/GHSA-qhr7-859c-m2p7): high; first safe 1.1.20 / 5.0.11.
- [GHSA-q2hr-2g5m-vwhr / CVE-2026-102277](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr): moderate; first safe 1.1.21 / 5.0.12. These therefore determine the minimum-safe combined selection.

`eslint-config-next` and `@next/eslint-plugin-next` move with Next from 16.3.4 to 16.3.6 to retain matching framework/tooling patches, not as an unrelated tooling upgrade. `@next/env` and all SWC bundles follow the same version. sharp native bundles move to 0.35.5 and libvips bundles to 1.3.4. PostCSS, Tailwind, React, the Markdown/YAML libraries and their direct pins are unchanged.

The [complete lockfile version comparison](verification-artifacts/milestone-7g1/dependency-version-changes.json) records **42 package entries updated, none removed**. An initial npm update on macOS omitted the Windows x64 optional sharp entry. Its 0.35.5 entry was restored with the official npm registry tarball/integrity metadata to preserve cross-platform lockfile completeness, then clean installation and Docker builds were repeated. No invented version or forced override was used.

### Exposure classification

The application does not currently import `next/og` / ImageResponse or expose untrusted CSS/source-map processing. That limits observed application exposure, but does not justify leaving vulnerable runtime packages installed. sharp is present in standalone for Next image optimization. source-map-js is primarily build tooling but also traced into the actual standalone image; it is therefore treated as runtime, not dismissed as dev-only. Native image processing was exercised after remediation.

## Before / after audit

| Audit | Critical | High | Moderate | Low | Info | Total |
| --- | --- | --- | --- | --- | --- | --- |
| Before, runtime (`--omit=dev`) | 1 | 2 | 0 | 0 | 0 | 3 |
| After, runtime (`--omit=dev`) | **0** | **0** | 0 | 0 | 0 | **0** |
| Before, full | 1 | 8 | 0 | 0 | 0 | 9 |
| After, full | **0** | **5** | 0 | 0 | 0 | **5** |

Raw npm evidence: [before runtime](verification-artifacts/milestone-7g1/before-runtime.json), [before full](verification-artifacts/milestone-7g1/before-full.json), [after runtime](verification-artifacts/milestone-7g1/after-runtime.json), [after full](verification-artifacts/milestone-7g1/after-full.json). The after audits were recaptured following clean installation of the final lockfile. Runtime audit exits 0; full audit exits nonzero because of the remaining development findings.

### Remaining upstream blocker — development tools only

Path: `eslint-config-next@16.3.6 → @next/eslint-plugin-next@16.3.6 → fast-glob@3.3.1 → micromatch@4.0.8 → braces@3.0.3`.

[GHSA-vfj7-8cjw-p6xm / CVE-2026-93687](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) is a high stack-exhaustion denial of service caused by deeply nested glob patterns. The advisory has no patched release, and npm's published latest is still braces 3.0.3 at verification time. Audit propagates this single underlying advisory to five dev packages: braces, micromatch, fast-glob, @next/eslint-plugin-next and eslint-config-next. They are not five distinct runtime CVEs.

The audit's offered `eslint-config-next@14.2.35` downgrade is an incompatible framework/tooling rollback, not a suitable minimum-compatible security fix. No nonexistent patched braces version, unrelated major migration, audit suppression or vendored substitute was introduced. `require.resolve("braces")` fails in the actual production standalone container, confirming it is not shipped there.

Residual risk is build/CI tooling processing hostile glob input. Recommended controls pending an upstream fix: lint only trusted repository/config patterns; isolate untrusted PR jobs from credentials and deployment permissions; enforce job time/resource limits; monitor the advisory and update the owning compatible dependency chain once a real fix is published. These are recommendations, not newly implemented CI policy. Record/approve this dev-only exception before any production release; this task stops short of deployment.

## Release-note and runtime review

[Next 16.3.6](https://github.com/vercel/next.js/releases/tag/v16.3.6) supplies the security patch. The intervening [16.3.5 release](https://github.com/vercel/next.js/releases/tag/v16.3.5) includes image cache fixes, an adapter-related standalone tracing fix and loading/template CSP nonce handling. No migration of App Router, middleware/proxy, metadata routes, sitemap/robots or server actions was announced for this patch path. Existing routes, proxy behavior, metadata output, static generation and standalone tracing were nevertheless retested, rather than assumed unaffected.

[sharp 0.35.5](https://github.com/lovell/sharp/releases/tag/v0.35.5) and [source-map-js 1.2.2](https://github.com/7rulnik/source-map-js/releases/tag/v1.2.2) were reviewed as patch-level security resolutions. The project keeps Node **22.22.0**: host QA explicitly used that executable, both Docker architectures ran it, and the existing Cloud Build verification image is also pinned to it. The host's default Node 20.11.1 is still below the repository contract and was not used for the passing checks. The configured CI was inspected, not executed remotely.

## Automated verification

All checks passed with Node 22.22.0 and npm 10.9.4. Test configuration was `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=test`; production build additionally used `NEXT_PUBLIC_SITE_URL=https://serpsaas.com NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`. No secret configuration was modified.

| Check | Result |
| --- | --- |
| Clean final-lock `npm ci` | Pass; 557 host packages installed; no lockfile regeneration |
| Full Vitest suite | **186 passed / 27 files**, repeated after final-lock installation |
| ESLint | Pass, including QA scripts |
| TypeScript | Pass |
| Prettier check | Pass |
| Host production build | Pass, Next 16.3.6, Webpack, standalone produced |
| Prebuild Blog validation | Pass: 3 published / 0 drafts; existing valid/invalid fixture tests pass |
| Production Docker AMD64 build | Pass with final lockfile |
| Production Docker ARM64 build | Pass with final lockfile |
| Runtime audit | Pass, **0 findings** |
| `git diff --check` | Pass |

The unchanged full suites cover login/register/session restoration, verify-email gating, project CRUD/detail, keyword organization, rank checks/batches, Ranking Explorer, reports/scheduling, competitor analytics, billing and normal-user admin protection. Browser checks supplement these component/API-client tests; they are not a real-account/backend end-to-end test.

The first host clean installation hit an EACCES/EEXIST rename failure in the pre-existing user npm cache. Rerunning with an isolated `/private/tmp/m7g1-npm-cache` succeeded. The existing cache was not deleted, force-overwritten or permission-modified. A repeat AMD64 command initially omitted the repository's explicit Dockerfile path and failed before building; the corrected command below was used. Neither tooling failure is presented as a dependency regression.

## Docker, native packages and standalone

Production target uses the unchanged `infrastructure/docker/frontend.Dockerfile` and `node:22.22.0-bookworm-slim`. Both native ARM64 and explicit AMD64 builds were performed. AMD64 matters because [Cloud Run's container contract](https://docs.cloud.google.com/run/docs/container-contract) requires the Linux x86_64 ABI; a successful macOS/ARM64 install alone would not prove deployable native packages.

Reproduction from the repository root:

```bash
docker build --platform linux/amd64 \
  --file infrastructure/docker/frontend.Dockerfile --target production \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_APP_ENV=production \
  --build-arg NEXT_PUBLIC_SITE_URL=https://serpsaas.com \
  --build-arg NEXT_PUBLIC_APP_URL=https://app.serpsaas.com \
  --tag serp-saas-frontend:m7g1-amd64 .
docker compose build frontend
```

The AMD64 production container runs `process.arch=x64`, Node v22.22.0, Next 16.3.6, sharp 0.35.5, source-map-js 1.2.2 and libvips 8.18.7. Native sharp converted a trusted 128×128 SVG to a 64×64 PNG successfully. Next's real `/_next/image?url=%2Fapple-icon.png&w=64&q=75` returned **200 / image/webp**, decoded by sharp as 64×64. This validates native loading and image optimization, not a malicious exploit reproduction. `sharp.versions` reported sharp/libvips only; a librsvg runtime version was not independently exposed by this API. See [native/HTTP evidence](verification-artifacts/milestone-7g1/standalone-qa.json) and [final image architectures/digests](verification-artifacts/milestone-7g1/docker-images.json).

All three original Markdown files remain present and readable under `/app/content/blog/` in the production container. No braces development package is traced into that image. The ARM64 localhost container also loaded sharp and generated a PNG successfully. The existing local frontend was recreated only with `docker compose up -d --no-deps --wait frontend`; it is healthy at port 3000 with the patched versions. Backend, worker and database were not started or restarted.

## Browser and real HTTP verification

QA ran against an actual production standalone Docker server at `http://localhost:3010`, configured with the production commercial/app origins. It did not use `next dev`. Playwright 1.63.0, axe-core Playwright 4.13.0 and locally installed Chrome were optional external QA tools, not new project runtime/development dependencies.

| Route | 375 | 768 | 1024 | 1440 |
| --- | --- | --- | --- | --- |
| `/blog` | Pass | Pass | Pass | Pass |
| `/blog/how-to-track-google-rankings` | Pass | Pass | Pass | Pass |
| `/blog/serp-tracking-for-agencies` | Pass | Pass | Pass | Pass |
| `/blog/how-to-monitor-keyword-ranking` | Pass | Pass | Pass | Pass |

All **16 cases** returned 200, had zero page exceptions/hydration errors, zero horizontal overflow and zero axe WCAG A/AA violations. One H1, canonical/OG/Twitter metadata, article JSON-LD, table headers, Blog-active navigation, footer/CTA links, keyboard skip focus and mobile-menu Escape behavior passed. CTA left edge and width still match the featured index card or related-guide block on all four routes and widths. Desktop reading width stays in the existing 680–800 px assertion range. Observed CLS was 0 in every case; final local response-start timings ranged approximately 8–208 ms and are not a production performance claim. Desktop index/mobile article screenshots were visually inspected.

All four Blog pages remained readable with JavaScript disabled. RSS contained three published items, sitemap contained all four canonical Blog URLs without draft leakage, robots allowed Blog, and app-domain article requests redirected 307 to the commercial origin. The full suite continues to cover draft exclusion, strict metadata validation, safe JSON-LD, escaped RSS and app/index/feed proxy behavior.

[Blog browser results](verification-artifacts/milestone-7g1/browser-qa.json) and 16 screenshots live in `verification-artifacts/milestone-7g1/`. [Application browser results](verification-artifacts/milestone-7g1/app-browser-qa.json) record **26 cases**:

- Anonymous Home, Pricing (six synthetic API Plan cards), Login, Register and Verify Email render without exceptions.
- Anonymous requests to Overview, Projects, project detail, Ranking Explorer, Reports, Competitors and Admin Plans redirect to Login.
- A verified normal-user fixture renders Overview, the project list/detail and empty-data Ranking Explorer, Reports and Competitors screens. Admin Plans shows “Administrator access required”; **zero admin API requests** occur.
- An unverified-user fixture is redirected from each of those seven protected routes to Verify Email.

All external APIs were intercepted; unexpected external requests and mutations fail the harness. Fixtures are QA-only, not business data or fallback prices. No real login, registration, email, ranking provider, report generation, database or live API request occurred. Populated analytics, report creation/download/schedule mutations and competitor comparisons are covered by the passing existing suites, not claimed as live backend browser journeys.

Real standalone HTTP checks independently confirmed **200** for Home, Pricing, About, Privacy, Terms, all four Blog routes, Login, Register, Verify Email, App, Projects, RSS, sitemap and robots. Auth/app routes retained `X-Robots-Tag: noindex, nofollow`. Both `/blog/unknown-slug` and `/blog/private-draft` returned **404**, not 500.

**Known framework diagnostic:** Next 16.3.6 still logs `Internal: NoFallbackError` for the deliberately unknown Blog slugs, as M7G did. Published routes and browser assertions pass; unknown/draft HTTP status is correctly 404. No change to `dynamicParams`, fallback behavior or Blog publishing was made merely to hide this diagnostic. See [standalone log](verification-artifacts/milestone-7g1/standalone.log).

To rerun browser QA from `frontend/`, start the local AMD64 image on 3010 and use:

```bash
QA_TOOLS_DIRECTORY=/path/to/temp-tools/node_modules \
QA_CHROME_PATH=/path/to/chrome \
QA_ARTIFACT_DIRECTORY=../docs/verification-artifacts/milestone-7g1 \
  node scripts/verify-blog-browser.mjs
QA_TOOLS_DIRECTORY=/path/to/temp-tools/node_modules \
QA_CHROME_PATH=/path/to/chrome \
  node scripts/verify-security-regression.mjs
```

Both harnesses reject non-local target servers. M7G evidence is preserved in its original artifact directory.

## Release gate and limitations

The milestone's runtime security gate and local tests/build/browser/standalone checks pass. Full audit is intentionally still nonzero for the documented dev-only upstream blocker. Review/accept that residual CI risk before release; when a compatible braces fix is published, refresh the owning chain and repeat the checks. `NoFallbackError` remains a known framework diagnostic with correct 404 responses.

**Production is not deployed or verified.** No Cloud Run revision, remote CI run, public DNS, production API, production indexability or Search Console state was changed/inspected. Separate explicit authorization and the normal release gate are required for deployment. Host Node 20 and a stopped local backend remain environmental limitations, not hidden passing checks.
