# M7L — Integration with current main and release verification

Verified **2026-10-31, Asia/Saigon**. **Result: PARTIAL / NOT READY for production.** M7L is integrated in an isolated current-main worktree, with M7D and newer Project behavior preserved and passing focused checks. Runtime audit is clean. The required complete backend gate still has an unavailable Redis dependency, and a production Docker/Linux build could not run on this host.

**NOT DEPLOYED. No push, merge, reset, clean, force-push or new commit was performed.**

## 1. Git baseline, backup and integration strategy

Reviewed [M7L verification](verification-milestone-7l.md), [security remediation](verification-milestone-7l-security-remediation.md), then the fetched [M7D verification](https://github.com/haunguyen0603/serp-saas/blob/84f549e02f6fd9541e139af20df853b05c242580/docs/verification-milestone-7d.md) before applying changes. The M7D report was absent from the original stale checkout and was read from fetched current main. No repository `AGENTS.md` was found.

| State | Commit / location |
| --- | --- |
| Original starting HEAD, branch `main` | `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb` |
| Fetched `origin/main` | `84f549e02f6fd9541e139af20df853b05c242580` |
| Integration starting and ending HEAD | `84f549e02f6fd9541e139af20df853b05c242580` |
| Integration branch | `codex/m7l-integration-20261031` |
| Integration worktree | `.tools/m7l-integration/` under the original workspace |
| Original ending HEAD | Still `8ebfb715ee6f25abb09ac2df230708d5f32b8cdb`; its uncommitted source/evidence remains unchanged |

The integration changes remain **uncommitted in the dedicated worktree**. The ending HEAD identifies its current-main base, not a newly committed release artifact. [Source hashes and protected upstream blobs](verification-artifacts/milestone-7l-integration/source-preservation.json) identify the tested worktree contents; [checks.json](verification-artifacts/milestone-7l-integration/checks.json) records the gate summary.

Before `fetch` or worktree creation, copied and SHA-256 checked **96 modified/untracked files** (5,252,281 bytes), plus a binary tracked diff, status and starting HEAD into `.tools/m7l-integration-backup-20261031/`. Additionally copied **8 ignored verification logs** before applying any integration edits. All 96 original files and 8 original logs were hash-checked again after verification and remain unchanged. No stash, checkout-over-dirty-tree or destructive operation was used. [Input backup inventory](verification-artifacts/milestone-7l-integration/input-backup-manifest.json) is retained; the full recovery copy remains in the backup directory.

Git commands:

```text
git fetch origin main
git log --oneline HEAD..origin/main
git diff --stat HEAD..origin/main
git show origin/main:docs/verification-milestone-7d.md
git worktree add -b codex/m7l-integration-20261031 .tools/m7l-integration origin/main
```

Fetched main is four commits ahead of the original checkout, with the following commits preserved:

- `052bec3ca1e0189b0ad6947bce989f3a79582d05` — durable Ranking Alerts backend and project preferences.
- `a037da0d9e415dfee82463fe9c1db513d8563476` — inbox, preferences and unread navigation.
- `4c8db7c6c54fdbe920fd804fac72c04b646445f2` — M7D rollout/verification.
- `84f549e02f6fd9541e139af20df853b05c242580` — newer Project deletion guidance and regressions.

## 2. Reconciliation and changed files

Compared the actual current-main blobs with the old base for every tracked M7L edit before copying it. The nine non-dependency tracked edit targets had unchanged upstream base blobs, so no textual three-way conflict existed. Current main did not yet contain R1–R5. Applied those existing reviewed changes once. The Next manifest and lockfile were already identical to the remediated versions after normalizing checkout line endings: **verified no-op**, rather than overwriting them.

R1–R5 retain the exact Vietnamese commercial H1/lead, the English secondary Blog CTA with Pricing, three task-specific VI guide slots, one contextual definition-to-checking link and the homepage scope/example notes. Article `publishedAt` stays `2026-10-17`; its actual original edit date `updatedAt: 2026-10-29` stays unchanged on this integration date. No new article, route or SEO metadata rewrite was introduced.

Application/editorial changes relative to fetched main:

- `frontend/src/features/marketing/vietnamese-content.ts`
- `frontend/src/features/blog/blog-components.tsx`
- `frontend/content/blog/vi/cong-cu-rank-tracker-la-gi.md`
- `frontend/src/app/(en)/page.tsx`

Test/harness changes:

- `frontend/src/features/blog/blog.test.tsx`
- `frontend/src/features/marketing/public-site.test.tsx`
- `frontend/src/features/marketing/vietnamese-localization.test.tsx`
- `frontend/scripts/verify-rank-tracker-blog-browser.mjs` — retained M7L date fixture.
- `frontend/scripts/verify-milestone-7l.mjs` — retained M7L SSR/browser verifier with selectable baseline/output directories.
- `frontend/scripts/verify-security-regression.mjs` — retained payment-options fixture; added exact M7D read fixtures (unread count, list, preferences) and the Ranking Alerts route to the existing synthetic regression. Unexpected APIs/mutations still fail.
- `scripts/verify-ranking-alerts-browser.mjs` — optional native Python seed executable/working directory, local base URL and new artifact-directory overrides. Original Docker defaults, seed safety guards and all behavioral assertions remain.
- `infrastructure/gcp/tests/test_cloud_run_ci.py` — use `os.pathsep` for child PATH and LF for executable fixture shebangs; same assertions and fake CLI behavior.
- `infrastructure/gcp/tests/test_auth_email_tools.py` — preserve Windows `SYSTEMROOT` when clearing test environment, so a real SSL context can initialize. SMTP remains mocked; no TLS verification was disabled.

Documentation/evidence added to the isolated candidate: original M7L specification, audit, both M7L reports and their original artifact directories, this report and `docs/verification-artifacts/milestone-7l-integration/`. Existing M7D evidence was not overwritten. A convenience copy of this new report and its new evidence is placed in the original workspace at the same relative paths.

Of the **88 paths changed by the four newer upstream commits, 87 are identical to current main**; the only difference is the explicitly adapted M7D browser harness. M7D models, `0017_ranking_alerts`, workers, APIs, UI, unread badge, queue behavior, Project implementation/tests and historical verification all remain intact. There is no diff in backend application/migrations, payment/subscription logic, Next configuration or dependency manifests/lockfiles. Windows CRLF checkout caused the first format check to flag 205 files; Prettier normalized line endings, producing no extra semantic Git diff in those upstream files.

## 3. Environment and exact commands

Native Windows host: Node **22.22.0**, npm **10.9.4**, Python **3.12.12**, PostgreSQL **16.13** (Windows build), pytest **9.1.1**, Ruff **0.16.6**, mypy **1.20.2**, Alembic **1.19.2**. FastAPI **0.141.1**, SQLAlchemy **2.0.52**. Dependencies were installed with `uv sync --frozen --python 3.12.12` and `npm ci --no-audit --no-fund`; neither lockfile changed.

Frontend: Next/eslint-config-next **16.4.3**, React/react-dom **19.3.0**, TypeScript **5.9.3**, Vitest **4.1.11**. External browser tools: Playwright **1.58.2**, axe Playwright **4.11.1**; actual Chrome **156.0.8078.74**. No new production dependency was added.

Temporary test support: official EDB PostgreSQL 16.13 binary archive, isolated database cluster listening only on `127.0.0.1:55432`, temporary `tzdata==2026.2`, the image's expected DejaVu Sans font and a temporary report storage directory. These supply native equivalents of Linux test prerequisites, without changing report/payment code. Databases `serp_m7l_test`, `serp_m7l_browser` and separate migration databases are disposable and contain only test data. No production credentials/database were used.

Backend environment:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/serp_m7l_test
REDIS_URL=redis://127.0.0.1:56379/0
PYTHONTZPATH=<temporary test-support>/tzdata/zoneinfo
REPORT_STORAGE_ROOT=<temporary directory>/serp-m7l-integration-reports
```

The app/browser runtime uses the separate `serp_m7l_browser` database, `APP_ENV=test`, fake SERP/email, `SERP_ENABLED_PROVIDERS=fake`, `SERP_PROVIDER_PRIORITY=fake`, local queue, outbound alert email **off**, SePay **off**, and CORS for `http://127.0.0.1:3010`. Seed code enforces test/fake-provider conditions. The API runs through `uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000`.

Frontend unit configuration: `NEXT_PUBLIC_APP_ENV=test`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. Build: `NEXT_PUBLIC_APP_ENV=production`, same API URL, `NEXT_PUBLIC_SITE_URL=https://serpsaas.com`, `NEXT_PUBLIC_APP_URL=https://app.serpsaas.com`, telemetry disabled. Local standalone runs on `127.0.0.1:3010` after copying generated `.next/static` and `public` into standalone output.

| Command | Result / evidence under `verification-artifacts/milestone-7l-integration/` |
| --- | --- |
| `npm run prebuild` | PASS — 9 published, 0 drafts; `frontend-prebuild.txt` |
| `npm test` | **342 passed / 37 files**; `frontend-test.txt` |
| `npm run lint` | PASS, repeated after QA fixture changes; `frontend-lint-final.txt` |
| `npm run typecheck` | PASS; `frontend-typecheck.txt` |
| `npm run format:check` | PASS after checkout line-ending normalization; `frontend-format-final.txt` |
| `npm run build` | PASS — production Webpack/standalone, including Ranking Alerts; `frontend-build.txt` |
| `python -m pytest -q --junitxml=<backend-junit.xml>` | Initial full run **386 passed / 16 failed / 402 total**; `backend-full.txt` |
| `python -m pytest --lf -q --junitxml=<backend-rerun-junit.xml>` | After supplying fonts: **11 passed / 5 failed**; `backend-rerun.txt` |
| `python -m pytest -q tests/test_ranking_explorer.py::test_explorer_performance_at_one_thousand_keywords_and_two_sites tests/test_reports.py::test_preview_csv_pdf_and_no_rank_usage tests/test_reports.py::test_idempotency_tenant_isolation_and_expired_download tests/test_reports.py::test_schedule_dispatch_and_fake_verified_email --junitxml=<backend-storage-junit.xml>` | With temporary report storage: **4 passed**; `backend-storage-rerun.txt` |
| `python -m pytest -m 'not integration' -q` | Final native unit run **156 passed / 246 deselected**; `backend-unit-final.txt`; does not replace integration gate |
| `python -m pytest -q tests/test_ranking_alerts.py tests/test_ranking_alert_migration.py tests/test_task_queue.py tests/test_auth_invariants.py --junitxml=<m7d-junit.xml>` | **59 passed**; `m7d-backend.txt` |
| `python -m ruff check .` / `python -m ruff format --check .` from backend | PASS; `backend-lint.txt`, `backend-format.txt` (240 files) |
| `python -m mypy app` | PASS — 162 source files; `backend-typecheck.txt` |
| Ruff check/format on the two changed infrastructure tests | PASS |
| `python -m unittest discover -s infrastructure/gcp/tests -v` | Final **56 passed**; `infrastructure-final.txt`; Git's native `sh` and native Python on PATH, no cloud/payment calls |
| `python -m alembic upgrade head`, `current`, `check`, `downgrade 0016_sepay_payments`, `upgrade head`, `check` | All PASS on a fresh dedicated migration DB; `migration-roundtrip-final.txt` |
| `node scripts/verify-milestone-7l.mjs` from frontend | **88 passed**, SEO regression and axe; `m7l-browser.txt`, `seo/` |
| `node scripts/verify-ranking-alerts-browser.mjs` from repo root | Real API/DB M7D flow PASS; `m7d-browser.txt`, `m7d/` |
| `node scripts/verify-security-regression.mjs` from frontend | **44 passed**, synthetic app/auth/navigation regression; `app-browser.txt`, `app/` |
| `git diff --check` | PASS (used `-c core.safecrlf=false` to suppress checkout conversion notices only) |

Python commands use the isolated candidate's `backend/.venv/Scripts/python.exe`; npm uses the task-local Node distribution. The exact focused commands appear above; JUnit outputs and raw earlier failure logs are retained. [checks.json](verification-artifacts/milestone-7l-integration/checks.json) summarizes current results.

## 4. Failure investigation and unresolved backend gate

No failing check was suppressed or converted into a pass:

1. Missing timezone database on Windows initially broke scheduling/invoice tests. Supplied temporary IANA tzdata through `PYTHONTZPATH`; no settings/business behavior was changed.
2. The repository's PDF renderer expects the DejaVu font installed by the Linux Dockerfile. Supplied that font temporarily at its existing expected path; the nine invoice-renderer tests and two invoice API tests then passed. Subscription/SePay code was not edited.
3. Four report-producing checks initially failed because the Linux default `/tmp/serp-saas-reports` becomes an unwritable `C:\tmp` path. Set the existing `REPORT_STORAGE_ROOT` environment variable to a task-specific temporary directory. All four passed unchanged, including the 1,000-keyword/two-site performance test. Its failure was artifact storage, not a reason to relax performance assertions.
4. Infrastructure tests assumed POSIX PATH separators/shebang newlines; corrected those fixture portability details. A cleared environment omitted Windows `SYSTEMROOT`, breaking OpenSSL construction; retained that OS prerequisite. All 56 infrastructure tests passed with the original substantive assertions and mocked cloud/SMTP clients.
5. **Redis is not installed/running.** The actual `test_live_dependencies[/health/redis]` returns **503 instead of 200**. It remains failed; Redis was not replaced with a fake server or waived.

Across the original full suite and explicit reruns, **401 distinct backend tests have an observed passing result; the Redis health test is the one unresolved test out of 402**. [Consolidated evidence](verification-artifacts/milestone-7l-integration/backend-consolidated.json) retains the latest observed outcome and source JUnit file per test. This is **not a claim that a new full 402-test run passed**. The complete backend release gate remains unmet until a real Redis service is available and the entire suite is rerun in the supported environment.

## 5. Security audit

Fresh `npm audit --omit=dev --json` exits **0**: **0 total / 0 high / 0 critical**. [Runtime audit](verification-artifacts/milestone-7l-integration/runtime-audit.json).

Fresh full `npm audit --json` exits **1**: **20 development affected packages — 2 high, 18 moderate, 0 critical**. [Full audit](verification-artifacts/milestone-7l-integration/full-audit.json). This is a later registry snapshot than the October 29 report's four affected packages; the unchanged lockfile does not imply unchanged advisory counts.

The high development paths remain Vitest → Vite 8.2.2 and eslint-config-next → React Hooks lint tooling → Zod 4.6.1. Moderate findings include Vitest/@vitest-mocker 4.1.11 and the newly reported minimatch advisory `GHSA-g3hv-75wg-m249`, propagated through ESLint/TypeScript-ESLint/plugin packages. The total is affected packages, not 20 distinct root CVEs. No forced audit fix, incompatible suggested downgrade (such as ESLint 4 or eslint-config-next 0.2.4), overrides or unrelated dependency upgrade was applied. Development-tool remediation/review remains a separately tracked risk; the runtime gate is clean.

## 6. M7D and newer Project regressions

**59 focused backend tests pass** against real PostgreSQL, including alert classification, complete-Top-10 eligibility, real fake-provider pipeline/evaluation, duplicate suppression, context rebaseline, tenant/auth restrictions, preferences, worker/email retry/concurrency behavior, queue/auth invariants and migration metadata/indexes/roundtrip. Existing `0017_ranking_alerts` stays the migration head; no new migration is introduced by M7L.

The existing M7D browser script ran against **real local API sessions and persisted fake-provider observations**, not intercepted success fixtures. It passed anonymous/unverified redirects, populated/empty inboxes, pagination, project/unread filters, mark read/all read, focus order/announcements, history links, preference save/reload/enable-disable/email opt-in, unavailable-email copy, injected error/retry and held-request loading, plus account-switch cache isolation.

Widths **375/768/1024/1440**, light/dark preferences, **30 screenshots**, **zero WCAG 2/2.1 A/AA violations**, **zero page/hydration console errors**. Full inbox axe scope; Project Details axe scope remains the new preferences region with whole-page overflow, matching prior M7D QA. [M7D browser evidence](verification-artifacts/milestone-7l-integration/m7d/browser-qa.json). Manual inspection also checked the 375 px populated inbox screenshot.

All **342 frontend tests** pass, including Ranking Alerts and the newer Project deletion/history/archive guidance tests from current main. The 44-case synthetic regression additionally covers authenticated/anonymous/unverified navigation, including Ranking Alerts; it is kept distinct from the real API/DB M7D browser evidence.

## 7. M7L SEO and responsive regression

The new [27-page raw HTML inventory](verification-artifacts/milestone-7l-integration/seo/after.json) is **identical in every captured field** to the verified post-M7L/security-remediation inventory. [Equality evidence](verification-artifacts/milestone-7l-integration/seo-preservation.json).

- **27 distinct sitemap URLs, all HTTP 200**, one H1 per page; titles/descriptions remain unique and unchanged.
- Self-canonicals, document language, robots/indexability and relevant JSON-LD remain unchanged.
- **12 reciprocal EN/VI/x-default pairs**; three Vietnamese-only articles remain unpaired.
- **3 EN + 6 VI articles**, three English RSS items; sitemap/feed/robots generation unchanged.
- Exact R1 H1/lead, one guide per R3 landing, the R4 contextual body link and original commercial link/dates, and all R5 disclosures are present in SSR.
- Exactly one R2 product CTA in each of the four EN shared CTAs; Pricing retained; VI CTAs unchanged.
- New/reassigned and existing discovered internal destinations return 200; five missing/untranslated article probes retain 404.
- No product scope, Top 10/device/schedule boundary or external app/pricing CTA destination was changed.

**88/88 route/viewport/JavaScript cases pass** (11 routes × four widths × JS on/off), including no horizontal overflow, visible copy, keyboard focus/Enter navigation and no React page/hydration errors. **44 axe analyses return zero violations** without rule/element exclusions. [M7L browser evidence](verification-artifacts/milestone-7l-integration/seo/browser-qa.json), with 20 screenshots. Manual inspection included the EN CTA at 375 px. Original October 29 evidence remains separate and unchanged; no SEO/ranking/CTR impact is claimed.

## 8. Generated artifact and Linux/Docker gate

The fresh **Windows production standalone build** passes, Build ID **`QSVSbHyjXrc3TKsQ_MhYs`**, and contains both compiled and prerendered Ranking Alerts output. Next is 16.4.3. Assets were served successfully; native image optimization returned **200**, `image/png`, 364 bytes for the benign local apple-icon probe. [Artifact evidence](verification-artifacts/milestone-7l-integration/standalone-artifact.json).

**Production Docker/Linux build: BLOCKED, not passed.** The repo supports `infrastructure/docker/frontend.Dockerfile` and the production backend image, but this machine has **no Docker executable/engine and WSL is not installed**. [Availability evidence](verification-artifacts/milestone-7l-integration/linux-build-blocker.txt). A Windows standalone artifact is not a substitute for the production Bookworm/Linux image. No remote CI/release pipeline was triggered to work around the restriction.

Required follow-up in a Linux/Docker-capable test environment: build the integrated frontend production target with its normal build arguments, start it and rerun the same SSR/M7L/M7D checks against that generated artifact; run backend/worker production build and the complete backend suite with disposable PostgreSQL 16.13 and Redis 7.4.8. The current repository Dockerfiles/configuration are unchanged.

## 9. Release recommendation and cleanup

**NOT READY for production.** Integration itself is complete and current-main product behavior is retained, but release gates remain:

1. Supply real Redis and rerun the complete backend test suite; the current live Redis health failure is unresolved.
2. Build and validate the production Docker/Linux artifacts and combined regressions in the supported environment.
3. Review/remediate or explicitly accept the recorded development-tool audit risks through the normal release process; no exception approval is claimed here.

After those gates pass, review the dedicated worktree diff, create/review the release commit and obtain explicit approval before any push or merge. No production deployment is authorized by this report. Local integration HEAD remains the fetched base because no new commit was created.

The original dirty `main` worktree and its immutable recovery copy are retained. Temporary API, frontend and PostgreSQL services are stopped after verification; the temporary font is removed only after its known hash is checked. Temporary runtimes/databases remain local test support, with no scheduled production jobs, provider/email traffic or payment activity created. This integration introduces no migration, billing or subscription behavior change and no unrelated feature.
