# M7K — Production-hosted SePay Sandbox setup

Requested on 2026-10-12. Target project: `serp-saas`, region: `asia-southeast1`; services: `serp-api`, `serp-worker`, `serp-web`. Deploy application code with the existing GitHub/Cloud Build pipelines. Keep `APP_ENV=production`, and configure only the SePay gateway with `SEPAY_ENV=sandbox`.

## Release

Source commit: [`b45cd2f`](https://github.com/haunguyen0603/serp-saas/commit/b45cd2f89aaaf6fca5db62cb1cda72412b4a309f), pushed normally to `main` following explicit deployment authorization.

- [Backend build `0e61aa7a-c9ed-46bb-80a0-8fdbfb282eb9`](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/0e61aa7a-c9ed-46bb-80a0-8fdbfb282eb9?project=833917440392): success, completed 2026-10-12 02:52:26 UTC (09:52:26 Vietnam time). The existing pipeline ran its checks, built/pushed the image, executed the migration job before API/worker release and checked database health.
- [Frontend build `e3690dde-db5b-421f-91ac-45928502060d`](https://console.cloud.google.com/cloud-build/builds;region=europe-west1/e3690dde-db5b-421f-91ac-45928502060d?project=833917440392): success, completed 2026-10-12 02:54:50 UTC (09:54:50 Vietnam time). Its pipeline ran frontend checks, built/pushed and released `serp-web`.

Gateway secret bindings are not created by these image-only releases. Checkout remains unavailable until Cloud Shell configuration. Release evidence is from the successful checks for the exact commit and public HTTPS tests; this workstation has no authenticated gcloud session, so it does not independently query Cloud Run revision names/digests or secret versions.

## Cloud Shell configuration

After the backend pipeline has deployed M7K, open [Cloud Shell](https://console.cloud.google.com/cloudshell/editor?project=serp-saas), enter an up-to-date checkout and run:

```sh
cd ~/serp-saas
# Use the existing clean checkout; this command does not discard local changes.
git pull --ff-only
python3 infrastructure/gcp/configure-sepay-sandbox.py
```

If there is no checkout yet, clone `https://github.com/haunguyen0603/serp-saas.git` using your existing GitHub authentication. The helper needs the Google Cloud identity already signed in on Cloud Shell. It prompts for:

1. Sandbox Merchant ID from your local `.env`.
2. `SEPAY_SECRET_KEY` from your local `.env`, with hidden input.
3. `SEPAY_IPN_SECRET_KEY` from your local `.env`, with hidden input. A separate random key was generated locally when the value was missing.

Do not paste keys into this chat or shell commands. Open the ignored local `.env` in the IDE and copy the values into the helper's hidden prompts. Do not upload the complete `.env` to Cloud Shell: it contains other application credentials.

If Cloud Shell cannot clone the private repository, use the local `dist/serp-saas-sepay-sandbox.tar.gz` package. It contains only this helper, its tests and this guide, with no `.env` or keys. Upload the archive through Cloud Shell's Upload menu, then run:

```sh
cd ~
tar -xzf serp-saas-sepay-sandbox.tar.gz
python3 ~/serp-saas-sepay/infrastructure/gcp/configure-sepay-sandbox.py
```

The helper validates M7K's public API is deployed before mutation. It creates/adds versions of `serp-sepay-sandbox-key` and `serp-sepay-sandbox-ipn-key`, grants only the current API runtime service account `Secret Manager Secret Accessor` on those two secrets, then updates `serp-api` with numeric version bindings. Existing image, other secrets, environment variables, Cloud SQL connection, runtime identity, IAM and scaling are preserved. It routes API traffic to the new ready revision and checks the nonsecret configuration and secret references. It never prints secret values or subprocess error output that could include them.

The Cloud Shell identity needs permission to manage these secrets and their IAM, update the existing Cloud Run API and act as its existing runtime service account. This session has no authenticated Google Cloud control-plane access; running this Cloud Shell step is required to create actual secrets/bindings.

## Sandbox access

Sandbox checkout on a production app is restricted to verified platform administrators and explicitly allowed QA user UUIDs. Other users see online checkout unavailable. To allow a dedicated normal QA account:

```sh
python3 infrastructure/gcp/configure-sepay-sandbox.py \
  --sandbox-user-id <QA_USER_UUID>
```

Repeat `--sandbox-user-id` to allow multiple QA accounts. The backend rechecks eligibility during checkout creation. This restriction does not apply to `SEPAY_ENV=production`, or local/test application environments.

The helper sets:

```text
SEPAY_ENABLED=true
SEPAY_ENV=sandbox
SEPAY_SANDBOX_ALLOWED_USER_IDS=[] (or explicitly supplied QA UUIDs)
SEPAY_CHECKOUT_URL=https://pay-sandbox.sepay.vn/v1/checkout/init
SEPAY_SUCCESS_URL=https://app.serpsaas.com/app/change-plan/payment/success
SEPAY_ERROR_URL=https://app.serpsaas.com/app/change-plan/payment/error
SEPAY_CANCEL_URL=https://app.serpsaas.com/app/change-plan/payment/cancel
SEPAY_PENDING_MINUTES=45
```

Merchant ID is a regular backend environment value. Both keys are Secret Manager references. The documented [SePay Sandbox checkout URL](https://developer.sepay.vn/vi/cong-thanh-toan/sandbox) matches the locally supplied endpoint. Merchant credentials must be the Sandbox pair. There is no real bank/card payment, but accepted Sandbox IPNs change real application subscription records; use an isolated QA account.

## Configure SePay merchant IPN

In SePay **Sandbox** merchant configuration, set:

```text
IPN URL: https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn
Authentication type: SECRET_KEY
Secret: the same SEPAY_IPN_SECRET_KEY entered into Cloud Shell
```

The IPN key is independent of the merchant signing key. Application authentication rejects unauthenticated IPN with 401; no user login is required on that endpoint. Keep existing Cloud Run public API ingress/IAM; do not make the worker public.

## Verify

- Sign in at `https://app.serpsaas.com` as a verified platform admin or allowed QA user.
- Open Change Plan and choose a non-current paid VND plan.
- Verify hosted checkout goes to `pay-sandbox.sepay.vn` with the expected amount.
- Complete the simulated payment; verify status becomes `paid`, the subscription changes once and Change Plan refreshes.
- Replay the same Sandbox IPN and confirm expiry stays unchanged.
- Verify cancelled/error checkout leaves the subscription unchanged.
- Verify a regular unlisted user cannot create Sandbox checkout.

If key configuration fails, the helper returns a generic error without leaking values. Inspect Google Cloud IAM/Secret Manager and the revision status in Cloud Console. Rerunning adds new pinned secret versions; it does not delete previous versions. To stop new Sandbox checkouts while retaining IPN reconciliation for outstanding orders:

```sh
gcloud run services update serp-api \
  --project=serp-saas --region=asia-southeast1 \
  --update-env-vars=SEPAY_ENABLED=false
```

A future real-production payment rollout needs a separate merchant/credential change after Sandbox E2E succeeds. This request authorizes deployment on production infrastructure with the gateway kept in Sandbox.

## Public production verification

After both builds succeeded, [13 HTTPS checks](verification-artifacts/milestone-7k/production-http.json) passed: API/database health, M7K OpenAPI endpoints, VND catalog, owner/authentication boundaries, public IPN authentication, Change Plan, all callback routes, noindex headers and the existing public site. Missing provider key returns the application JSON error `PAYMENT_PROVIDER_AUTH_FAILED` with 401; the IPN endpoint is not blocked by Cloud Run authentication or a login redirect.

[Browser verification](verification-artifacts/milestone-7k/production-browser/browser-report.json) used the deployed frontend at `https://app.serpsaas.com`, with every API/hosted-checkout request intercepted using synthetic fixtures. Change Plan, signed POST, callback/payment states, timeout and refresh passed at 375/768/1024/1440 px, with zero page errors and no overflow/clipped controls. No production account, payment order, financial event or subscription was mutated by this browser verification. It is not merchant Sandbox E2E.

Local release checks: backend mypy, lint/format and 41 payment/signature tests plus 136 non-integration tests passed; the preceding full implementation suite passed 347 backend and 308 frontend tests. The new production Sandbox restriction accounts for one additional backend test. Helper security tests passed 4 cases. Credentials were scanned against versionable files before committing, with no matches; local `.env` remains ignored and was not included in any source/upload archive.

## Status

- Local M7K implementation: verified (see [implementation report](verification-milestone-7k.md)).
- Cloud Shell helper security tests: 4 passed; keys use stdin and Cloud Run uses partial updates.
- Production Sandbox customer restriction: 41 payment/signature tests passed, including the new restriction; 136 non-integration backend tests passed.
- Application code deployment: backend and frontend pipelines succeeded for `b45cd2f`.
- Secret Manager / Cloud Run SePay binding: pending operator Cloud Shell execution.
- Merchant Sandbox E2E: pending merchant IPN setup and QA journey.
