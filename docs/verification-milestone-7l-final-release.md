# M7L final release gate verification

**Production follow-up, 2026-11-01:** user-authorized frontend release of commit `18d3a19862a504c052f38533237bc01162b62d57` completed successfully at **14:40:34 Asia/Saigon**. Live production verification passed 27 public URLs, 88 M7L browser cases, 23 HTTP smoke checks and 3 anonymous Ranking Alerts browser checks. See [rollout and production evidence](deployment-milestone-7l.md). The report below preserves the pre-deployment release-gate checkpoint and its original Git state; the later authorization and deployment supersede its no-deployment status.

Verified **2026-11-01, Asia/Saigon**, after the Windows restart and successful Docker/WSL startup.

**Recommendation: READY FOR PRODUCTION for the reviewed release-candidate snapshot. All mandatory technical release gates passed.** Runtime npm audit has **zero vulnerabilities**. Full audit retains **16 moderate development-only affected packages**, reviewed separately below. This recommendation does not authorize deployment, push or merge; none was performed. The tested changes remain in the dedicated worktree, not merged into the main workspace.

The earlier blocked checkpoint is preserved byte-for-byte in [pre-reboot-checkpoint.md](verification-artifacts/milestone-7l-final/linux-20261101/pre-reboot-checkpoint.md). All M7L, security-remediation, integration and M7D reports and their historical artifacts remain intact. Fresh evidence is isolated under `docs/verification-artifacts/milestone-7l-final/linux-20261101/`.

## 1. Exact Git state and preservation

| Item | Identity |
| --- | --- |
| Original integration HEAD | `84f549e02f6fd9541e139af20df853b05c242580` |
| Final candidate starting HEAD | `25dd7806a1385818541196785dc44c80261d5c29` |
| Final candidate ending HEAD | `25dd7806a1385818541196785dc44c80261d5c29` |
| Latest fetched remote main | `25dd7806a1385818541196785dc44c80261d5c29` |
| Final upstream verification | `2026-11-01T06:56:59Z` / 13:56:59 Asia/Saigon |
| Candidate branch | `codex/m7l-final-release-20261101` |
| Candidate worktree | `C:\Users\Admin\Desktop\serp-saas-main\.tools\m7l-final-release` |
| Local release commit | Not created; reviewed source changes and verification deliverables remain uncommitted for review |

Remote main already contains M7L through `7f905b8`, merged with M7D/current Project behavior in `25dd780`. A separate worktree was created from that remote merge; R1–R5 were not applied twice. The four necessary integration test-harness changes were retained. No reset, clean, force-push, upstream merge or production operation was performed by this task. Remote main was fetched both before and after the Linux gates and remained unchanged. [Starting Git evidence](verification-artifacts/milestone-7l-final/linux-20261101/git-start.json), [ending Git evidence](verification-artifacts/milestone-7l-final/linux-20261101/git-end.json).

Before the resumed work, 45 modified/untracked files were copied into `.tools/m7l-final-backup-20261101-resume/`, with SHA-256 manifest and binary patch. Previous backups and worktrees remain available. The prior integration snapshot's 208 files had already been revalidated unchanged in the [preservation check](verification-artifacts/milestone-7l-final/previous-candidate-preservation.json).

Only six tracked files have content changes relative to the final remote baseline:

- `frontend/package.json`: Vitest 4.1.11 → **4.1.12**.
- `frontend/package-lock.json`: matching Vitest packages, Vite 8.2.2 → **8.2.4**, Zod 4.6.1 → **4.6.6**. Every runtime lock entry is unchanged.
- `frontend/scripts/verify-security-regression.mjs`: Ranking Alerts read fixtures and protected-route coverage; existing upstream SePay options fixture retained.
- `scripts/verify-ranking-alerts-browser.mjs`: local base/artifact directory overrides and optional native seeding; default Docker seed path preserved and used for this verification.
- `infrastructure/gcp/tests/test_cloud_run_ci.py`: portable fixture newlines and PATH separator.
- `infrastructure/gcp/tests/test_auth_email_tools.py`: preserve SYSTEMROOT for Windows OpenSSL in isolated test environments.

Additional deliverables are this report and its evidence directory. **No backend implementation, migration, frontend product source/content, Dockerfile, Compose configuration, SePay, billing or subscription behavior changed.** `git diff --exit-code HEAD -- backend frontend/src frontend/content infrastructure/docker docker-compose.yml docker-compose.checks.yml` and `git diff --check` pass.

The build context is a clean copy of the current working contents of **1,998 tracked files**, avoiding an unreadable ignored Windows pytest cache. All final context files match the candidate by SHA-256: [final source manifest](verification-artifacts/milestone-7l-final/linux-20261101/build-context-final-manifest.json). The production backend additionally verifies all **244 backend source files** inside its image against the source manifest. The manifest, dependency diff and image digests identify the tested uncommitted snapshot; any subsequent source/lockfile change requires the affected gates to run again.

## 2. Environment and actual production artifacts

Windows 11 Pro x64 `10.0.26300.9818`, 31.8 GiB host RAM; restarted after enabling VirtualMachinePlatform. Docker Desktop **4.97.0 (244584)**, Engine/CLI **29.9.2**, Linux/amd64, WSL **3.0.3.0**, kernel **6.18.54.1-microsoft-standard-WSL2**, approximately 15.53 GiB available to Docker. [Docker version](verification-artifacts/milestone-7l-final/linux-20261101/docker-version.json), [engine information](verification-artifacts/milestone-7l-final/linux-20261101/docker-info.json). The installer signature/checksum evidence remains in the parent evidence directory.

Used dedicated network `m7l-final-20261101`, containers labeled `serp.qa=m7l-final-20261101`, real **PostgreSQL 16.13** and **Redis 7.4.8**. PostgreSQL/Redis data used tmpfs, without published database ports. Separate fresh databases: `m7l_test`, `m7l_browser`, `m7l_migrations`. Browser/API HTTP ports were restricted to `127.0.0.1:3010` and `127.0.0.1:8000`. [Service setup](verification-artifacts/milestone-7l-final/linux-20261101/disposable-services-setup.txt), [PostgreSQL version](verification-artifacts/milestone-7l-final/linux-20261101/postgres-version.txt), [Redis version](verification-artifacts/milestone-7l-final/linux-20261101/redis-version.txt), [real Redis PONG](verification-artifacts/milestone-7l-final/linux-20261101/redis-ping.txt).

Existing repository Dockerfiles built both production targets successfully. Docker reports these local image IDs/manifest digests:

| Image | Exact ID/digest | Linux runtime |
| --- | --- | --- |
| `serp-m7l-final-frontend:local` | `sha256:f8030d431f1a9e7e525869d5ac86faad3b7c73cc6b4bcb34099db23043c19ef4` | Node **22.22.0**, Next **16.4.3**, React **19.3.0**, sharp **0.35.5**, uid **1000** |
| `serp-m7l-final-backend:local` | `sha256:5eeea0a8903e1e821052d8e2c3bbcef5edf2478a8ff72fd1102b5631f7ea4279` | Python **3.12.12**, uid **10001**, DejaVu font installed |
| Backend test image | `sha256:41d32125ebab221c13635e243b27b32b5da514b31d6d34d4c73c7d3193df1687` | Repository `development` target, frozen uv.lock |
| Frontend test image | `sha256:c027a73b1e19a49e60632f7935d7655083a016bdd04beea0e7473731e1d4a796` | Repository `development` target, same successful npm-ci dependency layer |

Frontend final Linux Build ID: **`MsT5DOwHWYPM9hqsSV0bO`**. The standalone artifact contains compiled and prerendered `/app/ranking-alerts` output. Runtime containers' recorded image IDs match the two production image IDs above. None of Vitest, Vite, ESLint, eslint-config-next, minimatch or root Zod resolves in the final production frontend. The backend imports Ranking Alerts evaluation/email workers and worker entry point successfully; pytest/Ruff/mypy are absent from its production dependencies.

Evidence: [all image identities](verification-artifacts/milestone-7l-final/linux-20261101/image-identities.json), [raw image inspection](verification-artifacts/milestone-7l-final/linux-20261101/docker-images.json), [validated runtime containers](verification-artifacts/milestone-7l-final/linux-20261101/validated-runtime-containers.json), [frontend artifact](verification-artifacts/milestone-7l-final/linux-20261101/frontend-production-artifact.json), [backend artifact and complete installed package versions](verification-artifacts/milestone-7l-final/linux-20261101/backend-production-artifact.json).

Backend versions include FastAPI **0.141.1**, Uvicorn **0.52.4**, SQLAlchemy **2.0.52**, asyncpg **0.31.0**, Alembic **1.19.2**, redis Python client **7.4.1**, Pydantic **2.13.5**, ReportLab **4.5.1**; uv **0.12.12**, all unchanged from uv.lock. Production bases remain `python:3.12.12-slim-bookworm` and `node:22.22.0-bookworm-slim`.

## 3. Exact commands and results

Commands below run from the candidate root unless stated otherwise. `docker` is the newly installed Docker CLI; `../m7l-final-linux-context` is the SHA-256-verified clean source snapshot. All raw logs are retained, including failed initial environment checks. No assertion or release check was weakened.

```powershell
docker build --progress plain --target development -f ../m7l-final-linux-context/infrastructure/docker/backend.Dockerfile -t serp-m7l-final-backend-tests:local ../m7l-final-linux-context
docker build --progress plain --target production -f ../m7l-final-linux-context/infrastructure/docker/backend.Dockerfile -t serp-m7l-final-backend:local ../m7l-final-linux-context
docker build --progress plain --target production -f ../m7l-final-linux-context/infrastructure/docker/frontend.Dockerfile -t serp-m7l-final-frontend:local --build-arg NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 --build-arg NEXT_PUBLIC_APP_ENV=production --build-arg NEXT_PUBLIC_SITE_URL=https://serpsaas.com --build-arg NEXT_PUBLIC_APP_URL=https://app.serpsaas.com ../m7l-final-linux-context
docker build --progress plain --target development -f ../m7l-final-linux-context/infrastructure/docker/frontend.Dockerfile -t serp-m7l-final-frontend-tests:local ../m7l-final-linux-context
```

All builds **PASS**. [Backend development build](verification-artifacts/milestone-7l-final/linux-20261101/backend-test-image-build-clean-context.txt), [backend production build](verification-artifacts/milestone-7l-final/linux-20261101/backend-production-build.txt), [final frontend production build](verification-artifacts/milestone-7l-final/linux-20261101/frontend-production-build-final.txt), [frontend test build](verification-artifacts/milestone-7l-final/linux-20261101/frontend-test-image-build.txt). Frontend `npm ci` succeeds under Linux npm **10.9.4** with the final lockfile. Host `npm ci` also passes for browser harness dependencies.

| Exact command | Result / evidence |
| --- | --- |
| `docker exec m7l-final-backend-tests python -m pytest -q --junitxml=/tmp/m7l-final-full-junit.xml` | **402 passed, zero failed/errors/skipped, 241.91 seconds**, one complete clean Linux execution; [log](verification-artifacts/milestone-7l-final/linux-20261101/backend-full-pytest.txt), [JUnit](verification-artifacts/milestone-7l-final/linux-20261101/backend-full-junit.xml), [summary](verification-artifacts/milestone-7l-final/linux-20261101/backend-junit-summary.json) |
| `docker exec m7l-final-backend-tests python -m ruff check .` | PASS; [log](verification-artifacts/milestone-7l-final/linux-20261101/backend-lint.txt) |
| `docker exec m7l-final-backend-tests python -m ruff format --check .` | PASS, 240 files; [log](verification-artifacts/milestone-7l-final/linux-20261101/backend-format.txt) |
| `docker exec m7l-final-backend-tests python -m mypy app` | PASS, 162 source files; [log](verification-artifacts/milestone-7l-final/linux-20261101/backend-typecheck.txt) |
| `docker exec m7l-final-frontend-tests npm run test` | **342 passed / 37 files**, Vitest 4.1.12; [log](verification-artifacts/milestone-7l-final/linux-20261101/frontend-test.txt) |
| `docker exec m7l-final-frontend-tests npm run lint` | PASS; [log](verification-artifacts/milestone-7l-final/linux-20261101/frontend-lint.txt) |
| `docker exec m7l-final-frontend-tests npm run typecheck` | PASS; [log](verification-artifacts/milestone-7l-final/linux-20261101/frontend-typecheck.txt) |
| `docker exec m7l-final-frontend-tests npm run format:check` | PASS; [log](verification-artifacts/milestone-7l-final/linux-20261101/frontend-format-check.txt) |
| `docker exec m7l-final-frontend-tests npm run prebuild` | PASS, 9 published / 0 drafts; [log](verification-artifacts/milestone-7l-final/linux-20261101/frontend-prebuild.txt) |
| `docker run --rm --name m7l-final-infrastructure-tests-final --label serp.qa=m7l-final-20261101 --mount type=bind,source=<absolute-clean-context>,target=/repo,readonly -w /repo serp-m7l-final-backend-tests:local python -m unittest discover -s infrastructure/gcp/tests -v` | **56 passed** in Linux; [log](verification-artifacts/milestone-7l-final/linux-20261101/infrastructure-linux-final.txt) |
| `git -c core.safecrlf=false diff --check` | PASS; no substantive product/source changes beyond the six listed files |

Frontend check-container source was refreshed with `docker cp ../m7l-final-linux-context/frontend/. m7l-final-frontend-tests:/app` after LF normalization, before all checks. Its installed dependencies remain those from the successful Linux npm-ci layer. The final production frontend was rebuilt from that same finalized source and used for all browser results below.

Test containers use `APP_ENV=test`, task-local test credentials, fake SERP/email providers and outbound Ranking Alert email/SePay disabled. Backend full-test URL: `postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_test`; real Redis URL: `redis://m7l-final-redis:6379/0`. The API uses the separate `m7l_browser` database and the same service network. No production database or paid provider was accessed. Existing deliberate failure-path unit mocks remain part of the suite; the live Redis health test uses the real Redis service and passes.

## 4. Migration and production health

The production backend container executed these steps with `DATABASE_URL` overridden to the fresh **m7l_migrations** database; the browser database was unaffected:

```text
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic upgrade head
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic current
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic check
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic downgrade 0016_sepay_payments
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic upgrade head
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic check
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:disposable-local-test-only@m7l-final-postgres:5432/m7l_migrations m7l-final-backend-runtime python -m alembic current
```

**All seven steps exit 0**; head remains **0017_ranking_alerts**, no new migration or drift. [Roundtrip results](verification-artifacts/milestone-7l-final/linux-20261101/migration-results.json), with individual step logs beside it. The full suite also includes Ranking Alerts migration/metadata/index assertions.

Actual production-image API checks: **200 / `{"status":"ok"}`** at `/health`, `/health/db`, `/health/redis`. Representative public EN/VI pages and `/app/ranking-alerts` return 200 from the generated frontend; anonymous/unverified access redirects are then verified in-browser. [Health evidence](verification-artifacts/milestone-7l-final/linux-20261101/production-backend-health.json), [HTTP smoke](verification-artifacts/milestone-7l-final/linux-20261101/production-http-smoke.json).

Linux native image processing succeeds: `/_next/image?url=%2Fapple-icon.png&w=32&q=75` → **200, image/png, 282 bytes**. [Evidence](verification-artifacts/milestone-7l-final/linux-20261101/linux-image-optimization.json). An initial 16px probe was correctly rejected with 400 because that width is not allowed; the valid-width probe passed without changing configuration.

## 5. M7D and M7L regression

Browser: host Chrome **156.0.8078.74**, Playwright/axe harnesses, targeting the **Linux production containers** on loopback. No deployed website was tested or modified. Artifacts are separate from all earlier milestone evidence.

Exact harness commands: from `frontend/`, `node scripts/verify-milestone-7l.mjs` and `node scripts/verify-security-regression.mjs`; from repository root, `node scripts/verify-ranking-alerts-browser.mjs`. All exit **0**. Shared `QA_BASE_URL=http://127.0.0.1:3010`; `QA_ARTIFACT_DIRECTORY` points to separate `seo/`, `app/`, `m7d/` directories under this run. M7L uses the immutable original `docs/verification-artifacts/milestone-7l/baseline.json` through `QA_BASELINE_FILE`. M7D uses `QA_CONTAINER=m7l-final-backend-runtime` and the default Docker seed path, against the actual production backend and persisted QA database.

**M7D:** all **59 focused backend cases** from Ranking Alerts, its migration, task queue and auth invariants pass within the complete 402-test run. Evaluation eligibility, complete Top 10, rebaseline/context identity, suppression, tenancy/auth, preferences, worker retries/email/queue behavior and migration contracts remain covered. Browser flow passes **13 groups**, **30 screenshots**, widths **375/768/1024/1440**, light/dark, **zero axe violations, page errors or console errors**. Covers anonymous/unverified redirects, populated/empty inboxes, filters/pagination, mark-read/all-read, focus order, history deep links, preference persistence, error/retry/loading and account cache isolation. Frontend unit tests also retain all Ranking Alerts and newer Project deletion/archive/history behavior.

**M7L:** all **27 public sitemap URLs** return 200 with one H1 each; titles/descriptions, self-canonical, document language, robots, JSON-LD, sitemap, feed and locale mappings pass baseline comparison. **12 reciprocal EN/VI/x-default pairs**, three VI-only articles, **3 EN + 6 VI posts**, three RSS items. Discovered internal targets resolve, and five missing/untranslated article probes preserve 404. Exact R1 product H1/lead, R2 English CTA, R3 guide assignments, R4 contextual link/retained commercial link and dates, and R5 disclosures are present in raw SSR. Responsive/JavaScript browser checks pass **88/88** with **44 zero-violation axe analyses**, keyboard focus/Enter navigation, no overflow and no React hydration/page errors.

Additional synthetic app regression: **44/44 cases**, no page/hydration errors or unexpected admin requests; retained separately from the actual API/DB M7D flow. Visually inspected the 375px Ranking Alerts inbox viewport and English blog CTA screenshot; both remain readable and correctly arranged.

Evidence: [M7D log](verification-artifacts/milestone-7l-final/linux-20261101/m7d-browser.txt), [M7D detailed report](verification-artifacts/milestone-7l-final/linux-20261101/m7d/browser-qa.json), [M7L log](verification-artifacts/milestone-7l-final/linux-20261101/m7l-browser.txt), [27-page SSR inventory](verification-artifacts/milestone-7l-final/linux-20261101/seo/after.json), [88-case browser report](verification-artifacts/milestone-7l-final/linux-20261101/seo/browser-qa.json), [app smoke](verification-artifacts/milestone-7l-final/linux-20261101/app/app-browser-qa.json), [counts](verification-artifacts/milestone-7l-final/linux-20261101/browser-summary.json). Deep comparison confirms the final SSR inventory is identical to the prior verified integration inventory. [Consolidated gate reconciliation](verification-artifacts/milestone-7l-final/linux-20261101/release-gates.json). No SEO ranking/CTR improvement is claimed.

Harness environment: `QA_TOOLS_DIRECTORY=%TEMP%\serp-m7l-browser-tools\node_modules`, `QA_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe`; M7D additionally uses `PLAYWRIGHT_MODULE=%TEMP%\serp-m7l-browser-tools\node_modules\playwright\index.mjs`, `AXE_MODULE=%TEMP%\serp-m7l-browser-tools\node_modules\@axe-core\playwright\dist\index.mjs`, and the same Chrome path through `CHROME_EXECUTABLE`. Node 22.22.0 and the Docker CLI are on the command-local PATH. Backend container configuration, containing only disposable QA placeholders, is retained in [qa-environment.env.txt](verification-artifacts/milestone-7l-final/linux-20261101/qa-environment.env.txt).

## 6. Dependency remediation and residual development risks

Preserved runtime baseline: Next/eslint-config-next/SWC **16.4.3**, React/React DOM **19.3.0**, sharp **0.35.5**; TypeScript **5.9.3**, ESLint **9.39.4**, Prettier **3.8.1**. Updated only **10 development package entries**, with no runtime entry drift, no nanoid refresh, no forced downgrade, no override and no new root Vite/Zod dependency.

| Dependency | Previous | Final | Reason |
| --- | --- | --- | --- |
| Vitest + matching @vitest packages | 4.1.11 | **4.1.12** | [Mock registration](https://github.com/vitest-dev/vitest/security/advisories/GHSA-qxg6-89mg-rqv8) and [Windows traversal bypass](https://github.com/vitest-dev/vitest/security/advisories/GHSA-xp26-3454-mjgp) fixes |
| Vite | 8.2.2 | **8.2.4** | Compatible patched 8.2 line, including [Wasm file disclosure](https://github.com/vitejs/vite/security/advisories/GHSA-vfpm-58rq-9qcg); final audit no longer reports Vite/launch-editor findings |
| Zod | 4.6.1 | **4.6.6** | [Collection validation memory exhaustion](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) fix on the existing 4.x line |

The earlier npm 10.9.4 `edgesOut` resolver error was reproduced in clean scratch. Temporary npm **11.21.1** generated registry-backed lock entries in scratch with explicit temporary pins and `--prefer-dedupe`; only the targeted entries were adopted. Their direct dependency ranges were checked against the retained lock graph, and **every runtime entry was compared unchanged**. npm 11 was not added to the repository or Dockerfile. Both host and repository-standard Linux npm **10.9.4 `npm ci`** accept and install the final lockfile; all affected unit/lint/type/format/build/browser gates passed afterwards. [Minimal patch proof](verification-artifacts/milestone-7l-final/linux-20261101/minimal-dev-patch.json), [resolver log](verification-artifacts/milestone-7l-final/linux-20261101/dev-patch-resolution.txt), [actual Linux installed versions](verification-artifacts/milestone-7l-final/linux-20261101/linux-installed-dependencies.json).

| Exact Linux command | Exit | Final findings |
| --- | --- | --- |
| `docker exec m7l-final-frontend-tests npm audit --omit=dev --json` | **0** | **0 total / 0 high / 0 critical** |
| `docker exec m7l-final-frontend-tests npm audit --json` | **1** | **16 moderate / 0 high / 0 critical**, development-only |
| `docker exec m7l-final-frontend-tests npm ls next react react-dom sharp vitest vite zod minimatch --all --json` | **0** | Installed tree valid |

Linux audit timestamp: **2026-11-01T06:54:51Z**. Host lockfile audits agree. [Runtime audit](verification-artifacts/milestone-7l-final/linux-20261101/linux-runtime-audit.json), [full audit](verification-artifacts/milestone-7l-final/linux-20261101/linux-full-audit.json), [exit codes](verification-artifacts/milestone-7l-final/linux-20261101/linux-audit-results.json). Before this patch the full audit had 20 affected packages, including two high; all high findings are resolved.

The 16 remaining affected packages propagate a **single minimatch advisory family** through ESLint/Next/TypeScript lint tooling: [GHSA-g3hv-75wg-m249 / CVE-2026-118764](https://github.com/isaacs/minimatch/security/advisories/GHSA-g3hv-75wg-m249). Locked minimatch versions are **3.1.5** and **10.2.6**; upstream's published patch is **11.0.1**, a major upgrade outside the current callers' ranges. npm aggregates older versions broadly; the upstream report describes the 10.2.6 optimization path. Affected-package count is not a count of 16 distinct CVEs.

Residual exposure is CPU/memory denial of service during development/CI glob processing if untrusted patterns reach the affected path. Current lint configuration is repository-controlled; these lint packages/minimatch do not resolve in the inspected production frontend. No claim of universal non-exploitability is made. Forced minimatch 11 overrides or npm's suggested ESLint 4 / eslint-config-next 0.2.4 downgrades would expand compatibility risk and were not applied. ESLint's unsupported-version warning is also retained as tooling maintenance debt. Track an upstream-compatible lint-toolchain upgrade separately and continue to avoid exposing development tooling to untrusted inputs. These are documented **development risks**, not unresolved runtime critical findings; no full-audit-zero result or exception approval is claimed.

## 7. Failure investigation, cleanup and release boundary

- Initial direct Docker context upload failed on unreadable ignored `backend/.pytest_cache`. Used a clean working-source copy with complete SHA-256 comparison; Dockerfiles/source were not bypassed or rewritten. Production backend source hashes are verified inside the image.
- Initial Linux frontend format check reported 213 files because Windows checkout used CRLF. Normalized **218 frontend text files** to LF, proving every Git blob unchanged. All frontend checks then passed and the final production image was rebuilt. [Normalization proof](verification-artifacts/milestone-7l-final/linux-20261101/frontend-eol-normalization.json), [original failure](verification-artifacts/milestone-7l-final/linux-20261101/frontend-format-initial.txt).
- Initial Linux infrastructure run had 8 failures/2 errors because CRLF shell scripts failed at `set`. Normalized **six shell files**, proving unchanged Git blobs, then reran all 56 tests successfully. [Shell proof](verification-artifacts/milestone-7l-final/linux-20261101/shell-eol-normalization.json), [original failure](verification-artifacts/milestone-7l-final/linux-20261101/infrastructure-linux.txt). No assertions or cloud-release behavior changed.
- Refreshed index metadata only for 224 files whose Git blobs exactly equal HEAD; **zero content was staged**. [Index proof](verification-artifacts/milestone-7l-final/linux-20261101/index-line-ending-refresh.json). The six substantive source changes remain reviewable and uncommitted.

The previous missing real-Redis, incomplete full-pytest and unbuilt Linux-artifact blockers are **resolved**. The remaining risks are the development lint advisory/support debt described above and existing external operational limits: real SMTP deliverability, paid SERP behavior and production infrastructure/deployment were outside these disposable QA gates. SePay/payment/subscription code was not changed, and no real transaction or outbound alert email was sent.

After evidence capture, only the six labeled QA containers and their dedicated network are stopped/removed; disposable tmpfs databases are discarded. Local image artifacts remain available. [Cleanup evidence](verification-artifacts/milestone-7l-final/linux-20261101/cleanup.json). Docker Desktop installation and the original worktrees/backups remain intact.

**Mandatory release-gate decision: PASS; recommend production release of this exact reviewed candidate after normal code review and explicit approval for push/merge/deployment.** No such operation is authorized or performed by this report. Prepare the local release commit from the dedicated worktree after review; re-fetch main and rerun affected gates if its source or dependencies change.
