# M7L final release gate verification

Verification checkpoint: **2026-11-01, Asia/Saigon**. **NOT READY FOR PRODUCTION.** This report records completed checks and the remaining mandatory gates; it is not a release approval. Windows requires a restart after enabling VirtualMachinePlatform, and Docker Desktop currently cannot start its Linux backend. No production deployment, push, merge or release commit was performed by this verification task.

## Git identity and upstream reconciliation

Reviewed the existing M7L implementation, security-remediation, integration and M7D verification reports before proceeding. Their historical evidence remains unchanged.

| Item | Exact identity |
| --- | --- |
| Starting integrated worktree HEAD | `84f549e02f6fd9541e139af20df853b05c242580` |
| Starting integrated branch | `codex/m7l-integration-20261031` |
| Newly fetched remote main | `25dd7806a1385818541196785dc44c80261d5c29` |
| New upstream implementation commit | `7f905b8` — SEO optimization and internal linking audit |
| New upstream merge | `25dd7806a1385818541196785dc44c80261d5c29`, parents `7f905b8` and `84f549e` |
| Final candidate branch | `codex/m7l-final-release-20261101` |
| Final candidate HEAD / ending commit | `25dd7806a1385818541196785dc44c80261d5c29` |
| Final candidate path | `C:\Users\Admin\Desktop\serp-saas-main\.tools\m7l-final-release` |
| Main workspace HEAD observed during this session | `25dd7806a1385818541196785dc44c80261d5c29`, branch `main` |

`git fetch origin main` succeeded at **2026-11-01T06:32:43Z**. The remote now includes the previously uncommitted M7L product changes and verification reports. This task did not perform that upstream merge. The original integration worktree remains untouched at its old HEAD, with its changes retained. A new isolated worktree was created directly from the fetched merge commit, without reset, clean, force-push or duplicate application of M7L.

Git blob comparisons confirm the M7L content/components/tests, its SEO verification script and both frontend dependency files already match the integrated implementation. Upstream changes relative to `84f549e` introduce no backend, migration, production Dockerfile, infrastructure or Ranking Alerts product changes. Only these four reviewed test-harness changes were carried into the new candidate:

- `frontend/scripts/verify-security-regression.mjs`: Ranking Alerts read fixtures and protected-route coverage. The existing SePay options read fixture is already upstream; no payment logic changed.
- `scripts/verify-ranking-alerts-browser.mjs`: optional native seed support and local base/artifact directory overrides; default Docker seeding remains available, and remote targets remain rejected.
- `infrastructure/gcp/tests/test_cloud_run_ci.py`: executable fixture LF newlines and platform PATH separator.
- `infrastructure/gcp/tests/test_auth_email_tools.py`: Windows SYSTEMROOT retained in isolated SMTP test environments.

No app/backend source, SePay, billing, subscription, migration, dependency manifest or lockfile differs from the new upstream HEAD. New files are this report and `verification-artifacts/milestone-7l-final/`. There is no final release commit because the required gates have not passed. Fetch and inspect main again before preparing that commit after successful verification.

Evidence: [fetch identity](verification-artifacts/milestone-7l-final/git-final-preflight.json), [source comparisons](verification-artifacts/milestone-7l-final/upstream-source-comparison.json). A second fetch at **2026-11-01T06:38:00Z** confirmed remote main still equals the final candidate HEAD: [final checkpoint](verification-artifacts/milestone-7l-final/final-checkpoint.json). Recovery snapshot `.tools/m7l-final-backup-20261031/` contains 208 files from the prior candidate. All 208 hashes were revalidated unchanged after setup/reconciliation: [preservation check](verification-artifacts/milestone-7l-final/previous-candidate-preservation.json). The earlier `.tools/m7l-integration-backup-20261031/` and both older worktrees remain available.

## Windows, WSL and Docker setup

The user explicitly selected local Docker Desktop/WSL setup. Installed the official signed packages, enabled VirtualMachinePlatform with `-NoRestart`, and opened Docker Desktop. The installer command did not auto-accept its license or initiate a reboot.

| Component | Observed version / result |
| --- | --- |
| Host | Windows 11 Pro x64, `10.0.26300.9818`, 31.8 GiB RAM, Intel i5-12400F |
| Last host boot observed | `2026-10-31T07:30:05.5000000Z` |
| VirtualMachinePlatform | Disabled → Enabled; **RestartNeeded=true** |
| WSL MSI | `3.0.3.0`, installation exit **0** |
| WSL Linux kernel | `6.18.54.1-1`, as reported by `wsl --version` |
| Docker Desktop | `4.97.0.244584`, per-user install, WSL 2 backend, Linux containers |
| Docker CLI | `29.9.2`, build `a82e528` |
| Docker context | `desktop-linux`, `npipe:////./pipe/dockerDesktopLinuxEngine` |
| Engine | **Unavailable**; info request returns HTTP 500; backend reports no virtualization available |

Docker installer SHA-256: `2668273F82B342A058A28F9AB53EA7BDDDE10BB6D51307CE2EC54C2D36459744`, valid Docker Inc signature. WSL MSI SHA-256: `AE977286974255BD26BF925F00F40F5692C6B2084155CBC0563C09AEA091F211`, matches Microsoft's published release digest, valid Microsoft Corporation signature. No installer was executed before verification.

Official references: [Docker Windows installation](https://docs.docker.com/desktop/setup/install/windows-install/), [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install), [Microsoft release assets and checksum](https://github.com/microsoft/WSL/releases/expanded_assets/3.0.3).

Evidence: [installers](verification-artifacts/milestone-7l-final/installers.json), [admin setup result](verification-artifacts/milestone-7l-final/wsl-admin-result.json), [setup transcript](verification-artifacts/milestone-7l-final/wsl-admin-setup.txt), [Docker installer log](verification-artifacts/milestone-7l-final/docker-install-log.txt), [host environment](verification-artifacts/milestone-7l-final/environment.json), [WSL version](verification-artifacts/milestone-7l-final/wsl-version.txt), [WSL status](verification-artifacts/milestone-7l-final/wsl-status.txt), [Docker error](verification-artifacts/milestone-7l-final/docker-info-error.txt), [virtualization diagnostics](verification-artifacts/milestone-7l-final/docker-virtualization-blocker.txt).

**Restart Windows, then recheck Docker Engine.** The observed firmware/SLAT flags are false while `HypervisorPresent=true`; these flags alone do not establish that the processor lacks virtualization support. If Docker still reports missing virtualization after the required restart, investigate firmware or host virtualization configuration. No firmware settings were changed and no reboot was initiated.

## Dependency baseline and audits

Final candidate manifest/lockfile remain identical to upstream main and the prior integrated candidate. Exact baseline: **Next.js / eslint-config-next / @next/env / @next/eslint-plugin-next / platform SWC packages 16.4.3**, **React / React DOM 19.3.0**, **sharp 0.35.5**, **TypeScript 5.9.3**, **Vitest / @vitest/mocker 4.1.11**, **Vite 8.2.2**, **Zod 4.6.1**, **ESLint 9.39.4**, **Prettier 3.8.1**. Existing Windows dependencies belong to the prior integration worktree; installed Next there is also 16.4.3. No Linux installation/artifact is claimed for the new worktree. Audits use Node **22.22.0** / npm **10.9.4** and the final candidate lockfile. [Exact lock and installed-version evidence](verification-artifacts/milestone-7l-final/dependency-versions.json).

| Exact command, from final candidate `frontend/` | Exit / fresh result |
| --- | --- |
| `npm audit --omit=dev --json` | **0 — zero vulnerabilities**, including zero critical/high |
| `npm audit --json` | **1 — 20 affected development packages: 2 high, 18 moderate, 0 critical** |

Final audit completed at **2026-11-01T06:35:56Z**. [Runtime JSON](verification-artifacts/milestone-7l-final/runtime-audit-final.json), [full JSON](verification-artifacts/milestone-7l-final/full-audit-final.json), [exit codes](verification-artifacts/milestone-7l-final/audit-exit-codes.json), [existing dependency chains](verification-artifacts/milestone-7l-final/dev-dependency-tree-before.json). These are affected-package totals, not counts of distinct CVEs. Runtime Next security remediation remains preserved.

Development risks were reviewed separately:

| Dependency path / issue | Review and disposition |
| --- | --- |
| Vitest → @vitest/mocker | [Manual mock registration](https://github.com/vitest-dev/vitest/security/advisories/GHSA-qxg6-89mg-rqv8) and [Windows traversal bypass](https://github.com/vitest-dev/vitest/security/advisories/GHSA-xp26-3454-mjgp). Compatible 4.x patch: **4.1.12**. Applies to reachable mocker/Vite development tooling; not included in the production runtime audit. |
| Vitest → Vite 8.2.2 | Development-server/launch-editor advisories recorded in full audit. Official [Wasm file disclosure advisory](https://github.com/vitejs/vite/security/advisories/GHSA-vfpm-58rq-9qcg) includes the **8.2.4** patch line; 8.2.2 also has other advisory paths. Full audit must be rerun against any selected version. |
| eslint-config-next → eslint-plugin-react-hooks → Zod 4.6.1 | [Collection validation memory exhaustion](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5), patched in **4.6.6**. Development lint dependency; exposure requires oversized collection validation input. |
| ESLint/Next/TypeScript lint tooling → minimatch 3.1.5 / 10.2.6 | [Glob-pattern amplification](https://github.com/isaacs/minimatch/security/advisories/GHSA-g3hv-75wg-m249), published patch **11.0.1**. npm broadly flags older branches; upstream advisory describes the 10.2.6 optimization path. A forced major override across older lint callers requires separate compatibility review. |

Attempted `npm install --save-dev --save-exact --package-lock-only vitest@4.1.12` with npm 10.9.4. It failed inside Arborist peer resolution with `Cannot read properties of null (reading 'edgesOut')`, both in the existing frontend and a clean scratch directory containing only its manifest/lockfile. The installed tree was therefore not the cause. Original dependency files remained unchanged.

Investigated using temporary **npm 11.21.1** with the same Node version in scratch only. Its compatible engine range is met; lock resolution succeeds without legacy-peer flags or forced downgrades. Also tried `npm update vite zod --package-lock-only` there. The resulting proposal selects Vitest 4.1.12, Vite 8.3.5 and Zod 4.6.7, but refreshes additional packages, including runtime-shared nanoid **3.3.18 → 3.3.20**. The proposal was **not applied** to the candidate: it is broader than the intended development-only patch and Linux regression gates cannot currently validate it. No overrides, audit suppression or assertion changes were introduced.

Evidence: [npm 10 failure](verification-artifacts/milestone-7l-final/npm-vitest-resolver-failure.log), [clean reproduction](verification-artifacts/milestone-7l-final/npm-clean-lock-resolution.txt), [npm 11 resolution](verification-artifacts/milestone-7l-final/npm11-lock-resolution.txt), [transitive proposal](verification-artifacts/milestone-7l-final/npm11-transitive-update.txt), [reviewed version drift](verification-artifacts/milestone-7l-final/proposed-dev-lock-changes.json). Development findings remain unresolved risks, with no exception approval claimed. A future narrowly scoped patch must pass `npm ci`, audit, unit/lint/type/format/build and browser gates before adoption.

## Checks run against the final worktree

Python commands use the existing isolated Python 3.12.12 environment at `../m7l-integration/backend/.venv/Scripts/python.exe`, with working directory in the **new final worktree**. No production database, provider, SMTP or payment endpoint was accessed.

| Command | Result / evidence |
| --- | --- |
| `python -m unittest discover -s infrastructure/gcp/tests -v` | **56 passed**; [log](verification-artifacts/milestone-7l-final/infrastructure-final.txt). Native Git `sh` and Python on PATH. |
| `python -m pytest -m 'not integration' -q --junitxml=../docs/verification-artifacts/milestone-7l-final/backend-unit-junit.xml` | Initial environment failure: 22 failed, 80 passed, 54 setup errors, 246 deselected; [original log](verification-artifacts/milestone-7l-final/backend-unit.txt). Missing required DATABASE_URL/REDIS_URL, not assertion failures waived. |
| Same unit selection after configuring URLs, tzdata and report storage | **147 passed, 9 failed, 246 deselected**; [log](verification-artifacts/milestone-7l-final/backend-unit-configured.txt). All remaining failures report `REPORT_FONT_UNAVAILABLE`. |
| `python -m pytest -m 'not integration' -q --junitxml=../docs/verification-artifacts/milestone-7l-final/backend-unit-complete-junit.xml`, with temporary DejaVu font | **156 passed, 246 deselected**, exit 0; [log](verification-artifacts/milestone-7l-final/backend-unit-complete.txt), [JUnit](verification-artifacts/milestone-7l-final/backend-unit-complete-junit.xml). One Windows pytest-cache write warning, retained in log. |
| `python -m ruff check infrastructure/gcp/tests/test_auth_email_tools.py infrastructure/gcp/tests/test_cloud_run_ci.py` | PASS |
| `python -m ruff format --check infrastructure/gcp/tests/test_auth_email_tools.py infrastructure/gcp/tests/test_cloud_run_ci.py` | PASS |
| `node --check frontend/scripts/verify-security-regression.mjs` | PASS |
| `node --check scripts/verify-ranking-alerts-browser.mjs` | PASS |
| `git -c core.safecrlf=false diff --check` | PASS |

Native unit environment: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/serp_m7l_final_test`, `REDIS_URL=redis://127.0.0.1:56379/0`, task-local `PYTHONTZPATH` and `REPORT_STORAGE_ROOT`. The URLs supply required configuration; no live-service success is claimed for the unit selection. A temporary DejaVuSans.ttf 2.37 was supplied at the existing renderer's Windows-resolved Linux font path, then removed only after its hash matched. [Font cleanup evidence](verification-artifacts/milestone-7l-final/native-font-support.json). This supplies the same prerequisite installed by the backend Dockerfile; no invoice/billing implementation was edited. Unit selection is explicitly separate from the mandatory full backend execution.

## Mandatory Linux production gates — still blocked

**No frontend or backend production Docker image was built in this verification session. No image ID, image digest or Linux build ID exists to validate or approve.** Intended local-only tags are `serp-m7l-final-frontend:local` and `serp-m7l-final-backend:local`; these are planned names, not build evidence. Repository Dockerfiles remain unchanged:

- Backend production/development base: `python:3.12.12-slim-bookworm`, `uv:0.12.12`, DejaVu fonts, non-root user.
- Frontend production: `node:22.22.0-bookworm-slim`, `npm ci`, Webpack standalone build, non-root user.
- Disposable service versions required for the resumed run: PostgreSQL `16.13-bookworm`, real Redis `7.4.8-bookworm`.

Pending commands, to execute from the final candidate once `docker info` succeeds (not executed/passed here):

```powershell
docker build --target development -f infrastructure/docker/backend.Dockerfile -t serp-m7l-final-backend-tests:local .
docker build --target production -f infrastructure/docker/backend.Dockerfile -t serp-m7l-final-backend:local .
docker build --target production -f infrastructure/docker/frontend.Dockerfile -t serp-m7l-final-frontend:local --build-arg NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 --build-arg NEXT_PUBLIC_APP_ENV=production --build-arg NEXT_PUBLIC_SITE_URL=https://serpsaas.com --build-arg NEXT_PUBLIC_APP_URL=https://app.serpsaas.com .
```

Create a dedicated disposable network and fresh test/browser/migration databases with real PostgreSQL and Redis, bind test HTTP ports to loopback, keep outbound email and SePay disabled, and use test fake SERP fixtures. Do not reuse production credentials or volumes. Then execute the **complete** `python -m pytest -q --junitxml=<fresh-artifact-path>` in one clean Linux run with no deselection, followed by applicable lint/type/format/infrastructure and migration upgrade/check/downgrade/upgrade checks. Validate `/health`, `/health/db`, `/health/redis` on the production backend container and inspect both generated image identities/artifacts.

Run fresh frontend `npm ci`, `npm test`, `npm run lint`, `npm run typecheck`, `npm run format:check`, production build and audits on the actual final dependency tree. Rerun `node scripts/verify-milestone-7l.mjs`, `node scripts/verify-security-regression.mjs`, and repository-root `node scripts/verify-ranking-alerts-browser.mjs` against the generated Linux production frontend and a real disposable backend/PostgreSQL/Redis runtime. Use fresh artifact directories and the existing original M7L baseline through `QA_BASELINE_FILE`, never overwrite the historical baseline. Validate Ranking Alerts compiled routes, actual persisted inbox/preferences flows, canonical/hreflang/sitemap/metadata/internal links, all 27 public URLs, 404 behavior, JS on/off, responsive widths and accessibility.

## Preserved M7D/M7L evidence and its limits

The [prior integration report](verification-milestone-7l-integration.md) retains these passing observations: 342 frontend tests / 37 files; lint/typecheck/format/Windows production build; 59 focused M7D backend tests; migration roundtrip through `0017_ranking_alerts`; real API/DB M7D browser flows with 30 screenshots and zero axe/page/hydration errors; M7L 27-URL SSR inventory, 12 reciprocal locale pairs plus three VI-only articles, 88 responsive/JS browser cases and 44 zero-violation axe analyses; 44 synthetic app smoke cases. M7L R1–R5 and newer Project behavior remain unchanged in the source comparison. The prior standalone Windows Build ID is `QSVSbHyjXrc3TKsQ_MhYs`.

These are **historical integration results**, not fresh Linux final-release results. The previous backend full execution was 386 passed / 16 failed, followed by focused environment reruns; 401 distinct tests eventually passed across runs, with real Redis health unresolved. It never established a clean complete 402-test pass. Neither the old Windows standalone build nor today's 156-test unit pass substitutes for the mandatory Linux backend/build/browser gates.

## Release decision and continuation

**NOT READY FOR PRODUCTION.** Runtime dependency audit is clean and the latest upstream M7L/M7D baseline is reconciled safely. Mandatory blockers remain:

1. Restart Windows and establish a functioning Linux Docker Engine; investigate virtualization configuration if the error persists after restart.
2. Obtain one clean complete backend pytest pass with disposable PostgreSQL and real Redis.
3. Build both production Docker images, record their IDs/digests and validate backend health, Linux frontend artifacts and combined M7D/M7L SEO/browser/migration regressions.
4. Finish narrowly scoped development dependency remediation or document the residual risk decision, rerunning all affected gates after any accepted dependency change.

No test assertion was relaxed and Redis was never replaced with a fake. Existing source and verification evidence are preserved. Docker Desktop remains installed for the user to continue after a manual restart; no reboot, deployment, push or merge was initiated. The release commit remains intentionally unprepared until the required gates pass and remote main is checked again.
