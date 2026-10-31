# M7L security remediation verification

Verified locally on **2026-10-29, Asia/Saigon**. Starting local HEAD: `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`, with the uncommitted M7L R1–R5 implementation already present.

**The reported Next.js runtime blocker is resolved locally:** Next.js and eslint-config-next are now **16.4.3**, installed from the updated lockfile with `npm ci`. Runtime audit returns **zero findings**. No production deployment, commit, push, backend change or billing/SePay application change was performed.

This does **not** approve deploying this older checkout over current production. Remote `main` contains newer product commits missing locally; the release must integrate M7L onto that current baseline. Full development audit also retains four affected packages, documented below.

## 1. Baseline reconciliation: M7D versus M7L

The mismatch was a **stale local baseline**, not a security upgrade reverted by M7L and not divergent Git ancestry:

- The local repository is not shallow. Local `main`, cached `origin/main` and HEAD were at `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`.
- Local package history shows `7edae61` (M7G.1) pinning Next/eslint-config-next to 16.3.6 and `aab5b04` (M7H) raising them to 16.3.8. Subsequent local M7I/M7I.1/M7J reports also use 16.3.8. There is no local M7D report or 16.4.3 package-history change.
- Read-only connected GitHub inspection found current remote `main` at **`84f549e02f6fd9541e139af20df853b05c242580`**. The GitHub commit comparison reports **ahead by 4, behind by 0**, with merge base exactly the local HEAD. No fetch, merge, reset or history rewrite was performed.
- The remote [M7D verification report at that exact commit](https://github.com/haunguyen0603/serp-saas/blob/84f549e02f6fd9541e139af20df853b05c242580/docs/verification-milestone-7d.md) records the 16.4.3 security upgrade and zero runtime audit findings. Remote manifest and lockfile confirm those pins. That upgrade **is already merged on remote main**, but was absent from the local checkout used for M7L.
- The remote delta also contains Ranking Alerts, its migration/backend/UI/verification, and later Project deletion guidance. Those unrelated feature changes were inspected for baseline identification, not imported as part of this dependency-only remediation. Deploying the entire older local tree would omit them.

Evidence: [GitHub comparison](verification-artifacts/milestone-7l-security/remote-compare.json), [pinned remote M7D report and source identities](verification-artifacts/milestone-7l-security/remote-evidence.json). The earlier [M7L report](verification-milestone-7l.md) accurately described its local baseline; its audit result does not prove that the newer deployed M7D artifact has the same dependency vulnerability.

## 2. Exact versions and vulnerable dependency paths

Before remediation, manifest, lockfile, installed packages and M7L build all consistently used **Next 16.3.8**. This was not merely stale node_modules or an inaccurate version label.

| Package | Before locked/installed | After locked/installed |
| --- | --- | --- |
| `next` | 16.3.8 | **16.4.3** |
| `eslint-config-next` | 16.3.8 | **16.4.3** |
| `@next/env`, `@next/eslint-plugin-next` | 16.3.8 | **16.4.3** |
| All eight optional platform `@next/swc-*` lock entries | 16.3.8 | **16.4.3** |
| Installed native compiler | `@next/swc-win32-x64-msvc` 16.3.8 | **16.4.3** |
| `sharp` | 0.35.5 | **0.35.5**, unchanged |
| `react`, `react-dom` | 19.3.0 | **19.3.0**, unchanged |
| Node / npm | 22.22.0 / 10.9.4 | unchanged |

The runtime audit path was **application → direct `next@16.3.8` → `node_modules/next`**. npm aggregates three underlying advisories into **one critical affected package**; it does not mean there was only one underlying issue. The matching ESLint config/plugin are development dependencies, not the source of the runtime critical finding.

| Official upstream advisory | Severity / affected 16.x range | First patched 16.x | Exposure review |
| --- | --- | --- | --- |
| [GHSA-2464-fhr4-w9xw](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw): image optimization / upstream image processing | Critical; through 16.4.0 | **16.4.1** | Relevant upstream path is Next → optional sharp → platform image-processing binaries. Existing sharp 0.35.5 already meets the advisory's sharp workaround. Production Docker uses glibc-based Bookworm, but local QA is Windows; no claim of verified exploitability is made. |
| [GHSA-p3m5-59mp-jv5r](https://github.com/vercel/next.js/security/advisories/GHSA-p3m5-59mp-jv5r): Server Action CPU denial of service | High; 16.0.0–16.4.0 | **16.4.1** | App Router is present. No application `use server` directives were found; this limits the observed application path and does not replace a framework update. |
| [GHSA-673q-mjm6-r5xr](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr): typed-array Cache Component code execution | Critical; 16.0.0–16.4.0 | **16.4.1** | `cacheComponents` is not enabled and no application `use cache` directive was found. Upstream still recommends upgrading. |

The official [16.4.1 security release](https://github.com/vercel/next.js/releases/tag/v16.4.1) fixes all three, so **16.4.1 is the minimum compatible patched 16.x version** for the reported advisories. Staying on 16.3.x cannot meet their patched-version requirement.

Selected **16.4.3** to match the already-reviewed remote M7D dependency baseline and avoid introducing a framework downgrade relative to that release. It carries the 16.4.1 fixes plus upstream bug fixes; [16.4.3 release notes](https://github.com/vercel/next.js/releases/tag/v16.4.3) include proxy runtime and standalone bootstrap fixes. [16.4.2](https://github.com/vercel/next.js/releases/tag/v16.4.2) contains intervening maintenance fixes. This is a same-major minor upgrade from 16.3.8, not a claim that 16.3.8→16.4.3 is a patch-only change.

Official npm registry metadata for [16.4.1](verification-artifacts/milestone-7l-security/registry-next-16.4.1.json) and [16.4.3](verification-artifacts/milestone-7l-security/registry-next-16.4.3.json) confirms Node `>=20.9.0`, compatible React 19 peers and sharp `^0.35.5`. Existing Node 22.22.0 and React 19.3.0 satisfy those contracts.

The earlier omit-dev audit's `fixAvailable: false` was the audit resolver's result for that invocation, not evidence that upstream had published no security fix. The fresh full baseline audit explicitly offered Next 16.4.3. Official advisories/registry and successful clean installation establish the available remediation.

## 3. Smallest applied change and preservation

Copied only the dependency manifest pins and reviewed lockfile dependency delta from pinned remote `main`, after verifying that every changed package record belongs to Next. The resulting lockfile has the exact remote blob identity **`bf6da34a9143676b9782356e791d3e055ec9ff41`**. Root manifest blob identity matches remote **`7140f91195bcaaaa3c615ff52994353d1c53b883`**.

Only **12 package entries** changed, all 16.3.8→16.4.3: Next, its ESLint config/plugin, env package and eight SWC bundles. The root package record additionally changes the two direct pins. **No package entry was added/removed, no unrelated transitive package record changed**, and all cross-platform native lock entries remain. No overrides, audit suppression, forced audit fix, React change or lockfile-wide re-resolution was used. npm verified the locked registry tarball integrity during clean installation.

New changes attributable to this remediation:

- `frontend/package.json` — two exact pins.
- `frontend/package-lock.json` — matching reviewed Next-only records.
- `frontend/scripts/verify-milestone-7l.mjs` — configurable artifact directory and baseline input path, preserving all acceptance assertions and original M7L evidence.
- `frontend/scripts/verify-security-regression.mjs` — one missing synthetic read-only payment-options response for the existing application API contract; no billing/payment behavior edit.
- `docs/verification-milestone-7l-security-remediation.md`, its evidence directory and a follow-up pointer in the historical M7L report.

All four M7L application/editorial files have identical SHA-256 values before/after security work. Existing M7L test/fixture changes are preserved. Every post-security page inventory field is identical to the prior verified M7L inventory, including all prose, links, titles, descriptions, headings, locale mappings and structured data. Backend, billing/SePay logic, routes, Next configuration, product implementation and infrastructure were untouched.

Evidence: [dependency records before/after](verification-artifacts/milestone-7l-security/dependency-changes.json), [installed before](verification-artifacts/milestone-7l-security/before-installed.json), [installed after](verification-artifacts/milestone-7l-security/after-installed.json), [source preservation](verification-artifacts/milestone-7l-security/preservation.json), [semantic/standalone preservation](verification-artifacts/milestone-7l-security/semantic-preservation.json).

## 4. Audits and remaining development findings

All audit commands below are real fresh runs against this checkout; no severity threshold or ignore list was applied.

| Audit | Critical | High | Moderate | Total | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before `npm audit --omit=dev --json` | 1 | 0 | 0 | 1 | 1 |
| After `npm audit --omit=dev --json` | **0** | **0** | **0** | **0** | **0** |
| Before full `npm audit --json` | 1 | 2 | 2 | 5 | 1 |
| After full `npm audit --json` | **0** | 2 | 2 | 4 | 1 |

Raw evidence: [before runtime](verification-artifacts/milestone-7l-security/before-runtime.json), [after runtime](verification-artifacts/milestone-7l-security/after-runtime.json), [before full](verification-artifacts/milestone-7l-security/before-full.json), [after full](verification-artifacts/milestone-7l-security/after-full.json).

The full-audit failure was investigated rather than hidden. Four remaining affected packages are pre-existing and development-only:

| Dependency path | Installed version / findings | Disposition |
| --- | --- | --- |
| dev `vitest` → `@vitest/mocker` | both 4.1.11; moderate mock registration and Windows traversal findings, propagated to Vitest | Official [manual-mock advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-qxg6-89mg-rqv8) and [Windows traversal advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-xp26-3454-mjgp) identify 4.1.12 as a patched backport. Retained for separate test-tool remediation. |
| dev `vitest` / `@vitest/mocker` → `vite` | 8.2.2; aggregate high severity, launch-editor and development-server exposure advisories listed in raw audit | Used by test tooling; this Next app does not use Vite as its production server. Retained rather than widening this exact Next/remote-baseline fix. |
| dev `eslint-config-next` → `eslint-plugin-react-hooks` → `zod` (also via `zod-validation-error`) | zod 4.6.1; high collection-validation memory exhaustion, `GHSA-mrhx-c7xc-m3w5`; audit reports `<4.6.6` affected | Lint/compiler tooling path, unchanged by the matching Next config update. Retained for separate compatible dev-tool resolution. |

[Dependency-chain evidence](verification-artifacts/milestone-7l-security/dev-dependency-chains.json) identifies the installed paths. All four packages are absent from generated standalone `node_modules`; the Docker production stage copies standalone output rather than the builder's full node_modules. Runtime audit likewise excludes them and is clean. They remain build/developer risks: avoid exposing test/Vite/mock servers to untrusted clients and processing untrusted tooling inputs with deployment credentials. No new CI policy or claim of a globally vulnerability-free dependency tree is made.

## 5. Commands, environment and regression results

Windows/PowerShell, Node **22.22.0**, npm **10.9.4**, Next **16.4.3**, React **19.3.0**, Vitest **4.1.11**. Browser tools remain external to project dependencies: Playwright **1.58.2**, axe Playwright **4.11.1**, Chrome **156.0.8078.49**.

Node PATH used the existing temporary official distribution. npm's default profile cache was outside permitted writes, so metadata/download operations used `npm_config_cache=$env:TEMP\serp-m7l-security-cache`; no permission bypass or repository configuration change. The clean install emitted existing whatwg-encoding/ESLint deprecation warnings and exited 0.

Commands run from `frontend/`, with output in `docs/verification-artifacts/milestone-7l-security/`:

| Command | Result / evidence |
| --- | --- |
| `npm ci --no-audit --no-fund` | PASS; 555 packages, [install.txt](verification-artifacts/milestone-7l-security/install.txt); audits run separately |
| `npm ls next eslint-config-next @next/env @next/eslint-plugin-next @next/swc-win32-x64-msvc sharp react react-dom --json` | PASS, [after-installed.json](verification-artifacts/milestone-7l-security/after-installed.json) |
| `npm run prebuild` | PASS; 9 published / 0 drafts, [prebuild.txt](verification-artifacts/milestone-7l-security/prebuild.txt) |
| `npm test` | **331 passed / 36 files**, [test.txt](verification-artifacts/milestone-7l-security/test.txt); includes existing auth/ranking/report/billing/SePay suites |
| `npm run lint` | PASS, [lint.txt](verification-artifacts/milestone-7l-security/lint.txt) |
| `npm run typecheck` | PASS, [typecheck.txt](verification-artifacts/milestone-7l-security/typecheck.txt) |
| `npm run format:check` | PASS, [format-check.txt](verification-artifacts/milestone-7l-security/format-check.txt) |
| `npm run build` | PASS, Next 16.4.3 Webpack / standalone, [build.txt](verification-artifacts/milestone-7l-security/build.txt) |
| `node scripts/verify-milestone-7l.mjs` | PASS — 27-route SSR, 88 browser cases, 44 axe analyses; [ssr-browser.txt](verification-artifacts/milestone-7l-security/ssr-browser.txt) |
| `node scripts/verify-security-regression.mjs` | **41 passed** synthetic app/auth/navigation cases, [app-browser-qa.json](verification-artifacts/milestone-7l-security/app-browser-qa.json) |
| `npx prettier --check scripts/verify-milestone-7l.mjs scripts/verify-security-regression.mjs` and matching `npx eslint` | PASS after final QA-harness edit; [format](verification-artifacts/milestone-7l-security/final-script-format.txt), [lint](verification-artifacts/milestone-7l-security/final-script-lint.txt) |
| `git diff --check` (repository root) | PASS; Git LF/CRLF informational warnings only |

Unit environment: `NEXT_PUBLIC_APP_ENV=test`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. Build environment: `NEXT_PUBLIC_APP_ENV=production`, same local API URL, `NEXT_PUBLIC_SITE_URL=https://serpsaas.com`, `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`, telemetry disabled. No production credential or backend was used.

Standalone QA uses `PORT=3010`, `HOSTNAME=127.0.0.1` and `node frontend/.next/standalone/server.js`; `.next/static` and `public` copied into generated output for asset serving. For M7L QA set:

```text
QA_BASE_URL=http://127.0.0.1:3010
QA_ARTIFACT_DIRECTORY=../docs/verification-artifacts/milestone-7l-security
QA_BASELINE_FILE=../docs/verification-artifacts/milestone-7l/baseline.json
QA_TOOLS_DIRECTORY=<temporary browser tools>/node_modules
QA_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

Run the existing M7L script **without `--baseline`**, preserving the original baseline and evidence. The app regression script uses the same URL/tools/artifact directory and intercepts every API request with synthetic responses; no real account, provider or payment mutation is possible in that harness.

### Failure investigation

The optional older M7G.1 app-browser smoke initially failed at `/app/change-plan` because the current application reads `/api/v1/billing/payments/sepay/options`, which did not exist when that smoke fixture was written. [Initial failure](verification-artifacts/milestone-7l-security/app-browser-initial.txt) is retained. Inspected `PaymentOptions` in `frontend/src/features/billing/payments.ts` and the existing Change Plan unit tests; added the exact synthetic contract `{ enabled: false, eligible_plan_ids: [] }`. The harness still rejects unexpected API calls/mutations and all page/hydration errors. All 41 cases then passed. This repairs the fixture, without bypassing assertions or changing SePay logic.

No functional, type, lint, format or build failure occurred after the dependency update. The full-audit nonzero exit remains explicitly documented rather than relabeled a pass.

## 6. M7L SEO/browser acceptance

The fresh production standalone crawl confirms **all 27 sitemap URLs return 200**, with one H1 each, 27 unique titles/descriptions, self-canonical, correct lang, unchanged robots and parsed JSON-LD. **12 reciprocal EN/VI/x-default pairs** remain; the **three unpaired VI articles** remain unpaired. Counts stay **3 EN + 6 VI articles**, and English RSS stays **3 items**. Internal targets return 200; five missing-article probes retain 404.

Every field in the new [27-page inventory](verification-artifacts/milestone-7l-security/after.json) is identical to the previously verified M7L `after.json`, including main copy and markup fragments. This confirms preservation of the exact Vietnamese product H1/lead, all three guide assignments, the definition-body handoff and article dates, the four EN shared CTAs with Pricing, unchanged VI CTAs, and the homepage scope/example disclosures. See [semantic equality check](verification-artifacts/milestone-7l-security/semantic-preservation.json).

Browser coverage reran all **11 routes × 4 widths (375/768/1024/1440) × JS on/off**: **88/88 passed**, **44/44 axe analyses had zero violations**, with no horizontal overflow or page/hydration errors. It checked disclosure visibility, keyboard Tab/visible focus/Enter navigation, and full-page axe WCAG 2/2.1 A/AA in JS-enabled cases without exclusions. Same-host routing kept public navigation local. [Browser results](verification-artifacts/milestone-7l-security/browser-qa.json) and 20 screenshots are saved separately from the preserved original M7L artifacts.

The additional app smoke covers anonymous, verified and unverified access/navigation across existing app routes with fixture APIs. It does not validate actual backend billing/auth integrations. A benign native image optimization request `/_next/image?url=%2Fapple-icon.png&w=64&q=75` returns **200**, `image/png`, nonempty bytes, using sharp 0.35.5; [evidence](verification-artifacts/milestone-7l-security/image-smoke.json). No attack payload or production endpoint was exercised.

## 7. Remaining release risks, rollout and final decision

**Runtime dependency gate: resolved locally.** No critical/high runtime audit finding remains. Full audit still has four development affected packages (2 high, 2 moderate), with their paths and scope above.

**Production release approval: withheld for this stale checkout.** Before shipping, integrate the M7L/editorial changes and this already-matching dependency pin onto current remote `main`, retaining M7D Ranking Alerts and the later Project behavior. Rerun combined M7D/M7L regressions on that integrated candidate. The 331 local tests and 41 local app browser cases do not cover M7D source absent from this tree. Do not deploy this whole older tree over the newer application. No unrelated feature commits were merged here.

No Linux/Docker image build, remote CI job, authenticated production check, real SePay/provider/email operation, GSC inspection or production rollout was performed. The Windows build/SSR/browser/image smoke does not establish every Linux native-platform behavior, Google indexing or SEO impact. Existing absent-static-slug probes can log Next `NoFallbackError` while returning correct HTTP 404, as already observed in M7L; this does not occur as a published-page hydration error.

After integration/review, use the existing frontend release path; this security/editorial delta requires no database migration or billing change. Verify the deployed artifact's exact Next 16.4.3 and lockfile, production HTML/links/disclosures/canonicals/alternates, sitemap/feed counts and representative mobile navigation. Roll back only to an approved **patched** artifact retaining current product features; reverting to vulnerable 16.3.8 does not resolve this security gate.

**NOT DEPLOYED.** No production readiness claim is made for the stale local release candidate. The specific critical Next.js blocker is fixed, with remaining development risks and integration work stated explicitly.
