# SePay Production gateway rollout

On 2026-10-12 the user confirmed successful merchant Sandbox testing, authorized
real Production payment processing and confirmed Production Merchant ID and
Secret Key are available. Google Cloud configuration uses their chosen Cloud
Shell workflow. Target: project `serp-saas`, region `asia-southeast1`, API service
`serp-api`. The existing deployed application already supports Production.

**Current state:** application and Invoices are deployed. The user's Cloud Shell
diagnosis shows Production secret version 1 and a Production service template,
with `serp-api-00014-hqj` reporting `Ready=True`, but traffic remains on
`serp-api-00013-n7vv`. Promotion and post-promotion verification are still pending.
This workstation has no gcloud/authenticated Google Cloud session and has not
changed live gateway configuration or performed a real payment.

## 1. Configure the Production merchant IPN

Use the **Production** merchant on SePay, with Production payment methods enabled.
According to [SePay's IPN documentation](https://developer.sepay.vn/vi/cong-thanh-toan/IPN),
open **Cổng thanh toán → Cấu hình → IPN** and configure:

```text
IPN URL: https://api.serpsaas.com/api/v1/billing/payments/sepay/ipn
Authentication type: SECRET_KEY
Secret: an independent random Production IPN key
```

Create a separate random IPN key in your password manager (at least 32 characters).
Use this same key in SePay's Production IPN configuration and the helper's
`SEPAY_IPN_SECRET_KEY` prompt. Use the Production Merchant ID and merchant signing
Secret Key for the other prompts. Keep the Sandbox and Production key sets separate.

Finish any Sandbox checkout still in progress before switching environments.
The gateway accepts only its current environment and current IPN key. Switching
does not remove old Sandbox invoices or reset test-account subscriptions.

## 2. Run in Cloud Shell

Open [Cloud Shell](https://console.cloud.google.com/cloudshell/editor?project=serp-saas).
Cloud Shell has a separate filesystem from your computer. If `~/serp-saas` does
not exist, use the upload workflow below. `git pull` requires an existing Git
checkout; running it from the Cloud Shell home directory will fail.

If `~/serp-saas` is already an existing repository checkout, run:

```sh
cd ~/serp-saas
git pull --ff-only
python3 infrastructure/gcp/configure-sepay-production.py
```

Enter the Production Merchant ID, then the Production signing and IPN keys into
the hidden prompts. The helper deliberately does not import `.env`; your current
local `.env` can remain the Sandbox configuration. Do not put keys into shell
arguments or send them in chat.

If the repository directory is missing or the private repository cannot be pulled,
upload the local package `dist/serp-saas-sepay-production.tar.gz` through Cloud
Shell's Upload menu to your Cloud Shell home directory. Then run:

```sh
cd ~
tar -xzf serp-saas-sepay-production.tar.gz
python3 ~/serp-saas-sepay-production/infrastructure/gcp/configure-sepay-production.py
```

The package contains only this helper, its configuration tests and this guide.
It contains no environment file, credentials, account data or database dump.

The helper checks deployed SePay API routes and the existing production API before
mutation. It creates or adds numeric versions to:

```text
serp-sepay-production-key     → SEPAY_SECRET_KEY
serp-sepay-production-ipn-key → SEPAY_IPN_SECRET_KEY
```

It grants the existing API runtime identity access to these two secrets. It uses
partial environment/secret updates with `--no-traffic`, checks the candidate's own
`Ready` condition and immutable configuration,
expected URLs, image/identity and pinned secret references, then sends 100% of API
traffic to that specific verified revision. It does not print key values or
subprocess output. It records only nonsecret revision and version metadata.

The helper applies:

```text
SEPAY_ENABLED=true
SEPAY_ENV=production
SEPAY_MERCHANT_ID=<Production Merchant ID>
SEPAY_CHECKOUT_URL=https://pay.sepay.vn/v1/checkout/init
SEPAY_VOID_URL=https://pgapi.sepay.vn/v1/order/voidTransaction
SEPAY_SUCCESS_URL=https://app.serpsaas.com/app/change-plan/payment/success
SEPAY_ERROR_URL=https://app.serpsaas.com/app/change-plan/payment/error
SEPAY_CANCEL_URL=https://app.serpsaas.com/app/change-plan/payment/cancel
SEPAY_SANDBOX_ALLOWED_USER_IDS=[]
SEPAY_PENDING_MINUTES=45
```

Checkout uses the documented [Production form endpoint](https://developer.sepay.vn/vi/cong-thanh-toan/API/don-hang/form-thanh-toan).
The [void endpoint](https://developer.sepay.vn/vi/cong-thanh-toan/API/giao-dich/huy-giao-dich)
is configured for environment consistency; this rollout does not call it or
introduce customer refund/void functionality.

Eligible verified customers can create real Production checkouts, including
normal accounts outside the former Sandbox allowlist. The API image, application
environment, JWT/database secrets and runtime identity are retained. Other
services do not need merchant keys for this API-only payment flow. Existing image
release pipelines preserve this runtime gateway configuration.

## 3. Verify

After the helper reports `environment: production` and `verified: true`, run:

```sh
python3 infrastructure/gcp/configure-sepay-production.py --check
```

`--check` is read-only, requires no key prompts and verifies current configuration,
pinned Production secret references, readiness and traffic. Cloud Shell needs
permission to manage the two secrets/IAM, update the existing API and act as its
runtime service account. A read-only check only needs service read access.

In the app, use an eligible verified customer account:

1. Open Change Plan and select an eligible paid plan.
2. Confirm checkout uses `pay.sepay.vn` and the intended VND amount.
3. If you make an intended real purchase, verify server status becomes `paid`,
   the subscription changes once and Invoices shows **Production**.
4. Download the invoice PDF and compare its amount and transaction references.

Real payments use the catalog's actual prices. No real purchase was initiated
automatically by this setup work. If a Sandbox test already activated a plan on
your account, its current subscription remains; use an appropriate customer
account for the intended Production purchase.

## Stop new checkouts

To stop new purchases while keeping Production IPN reconciliation available:

```sh
gcloud run services update serp-api \
  --project=serp-saas --region=asia-southeast1 \
  --update-env-vars=SEPAY_ENABLED=false
```

Keep Production environment/keys while Production orders remain outstanding.
If setup fails before traffic promotion, the existing serving revision remains
active; inspect revision readiness and secret IAM in Cloud Console before rerunning.
Rerunning creates new pinned versions without deleting older secret versions.

## Diagnose an incomplete setup

The updated helper reports the failed stage and controlled error reason, such as
`store_production_secret:SEPAY_SECRET_KEY` plus `PERMISSION_DENIED`, or a staged
revision/secret-reference validation error. Raw gcloud output and key values are
never included in these errors. The original helper's generic failure message
cannot establish which step failed or whether any secret/revision was created.

For an existing failed attempt, upload the refreshed package
`dist/serp-saas-sepay-production-diagnostics.tar.gz` to Cloud Shell Home, then run:

```sh
cd ~
tar -xzf serp-saas-sepay-production-diagnostics.tar.gz
python3 ~/serp-saas-sepay-production/infrastructure/gcp/configure-sepay-production.py --diagnose
```

`--diagnose` does not prompt for keys, create versions, change the service or
promote traffic. It reports created/ready revision names, traffic, gateway mode,
secret binding types and the latest five version numbers/states for each
Production secret. It uses [Secret Manager metadata listing](https://docs.cloud.google.com/sdk/gcloud/reference/secrets/versions/list),
without accessing secret payloads. Environment literals and revision error
messages are deliberately excluded. This JSON can be shared for troubleshooting.

If service conditions are `True` but `latest_created_revision` differs from
`latest_ready_revision`, inspect the new revision itself. Service-level readiness
does not establish that the new revision is ready to receive traffic. The user's
2026-10-12 report showed Production secret version 1 bound to the template,
`serp-api-00014-hqj` created and all traffic still on `serp-api-00013-n7vv`.
The next read-only check for that exact revision is:

```sh
gcloud run revisions describe serp-api-00014-hqj \
  --project=serp-saas --region=asia-southeast1 \
  --format=json | python3 -c 'import json,sys; d=json.load(sys.stdin); s=d.get("status",d); print(json.dumps({"response_fields":sorted(d.keys()),"conditions":[{"type":c.get("type"),"status":c.get("status",c.get("state")),"reason":c.get("reason")} for c in s.get("conditions",[])]},indent=2))'
```

The previous nested projection can produce `null` for a repeated conditions
field. Fetch the JSON object and filter locally instead, supporting both nested
v1 status and top-level v2 conditions. The printed output excludes environment
values and condition messages. Inspect the
revision's own `Ready` condition before deciding whether to promote it or repair
startup. [Cloud Run revision status](https://docs.cloud.google.com/run/docs/reference/rest/v1/namespaces.revisions)
is the evidence for that decision. The existing enabled secret versions do not
need to be recreated merely to perform this readiness check.

### Resume the ready Production revision

The user's subsequent revision response reported `Ready=True`,
`ContainerReady=True`, `Active=False` and reason `Retired`. A non-current revision
can be retired while not serving traffic; see
[Cloud Run revision management](https://docs.cloud.google.com/run/docs/managing/revisions).
The original helper incorrectly required the service's latest-created and
latest-ready revision names to match before promotion. The corrected helper
reads the candidate revision directly, verifies its Production configuration,
runtime identity and pinned secret bindings, and requires its own `Ready=True`.
It does not treat `Active=False` or `Retired` as a startup failure.

For this exact ready candidate, continue directly in Cloud Shell:

```sh
gcloud run services update-traffic serp-api \
  --project=serp-saas --region=asia-southeast1 \
  --to-revisions=serp-api-00014-hqj=100

gcloud run services describe serp-api \
  --project=serp-saas --region=asia-southeast1 \
  --format='yaml(status.traffic)'

python3 ~/serp-saas-sepay-production/infrastructure/gcp/configure-sepay-production.py --check
```

The expected serving traffic is 100% on `serp-api-00014-hqj`. The final read-only
check should report `environment: production` and `verified: true`. This traffic
update reuses the existing revision and secrets; do not rerun initial setup just
to recreate them. The command is documented in
[gcloud update-traffic](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/update-traffic).

Alternatively, upload `dist/serp-saas-sepay-production-resume.tar.gz` to Cloud Shell
Home and use the corrected helper to validate the immutable candidate before
promoting it:

```sh
cd ~
tar -xzf serp-saas-sepay-production-resume.tar.gz
python3 ~/serp-saas-sepay-production/infrastructure/gcp/configure-sepay-production.py \
  --resume-revision serp-api-00014-hqj
```

`--resume-revision` creates no secret versions and does not update environment
variables or prompt for keys. It refuses to promote if the requested revision
is no longer the service's current candidate, is not ready, or differs from the
expected Production configuration. It verifies 100% traffic after promotion.

## Verification evidence

The configuration/helper tests run without cloud mutations:

```sh
python3 -m unittest discover -s infrastructure/gcp/tests -p 'test_sepay_*.py' -v
```

16 Production helper tests and 4 existing Sandbox helper tests passed, covering hidden key handling, stdin-only secret creation,
Production secret separation, partial updates, verified revision promotion,
read-only checks, mismatched/unready revisions and sanitized subprocess failures.
Additional coverage verifies failed-stage reporting, code-only cloud errors,
read-only diagnosis and filtering literal keys/revision messages from output.
Regression coverage reproduces the user's ready/retired candidate with an old
service-level latest-ready name, rejects a genuinely unready candidate even when
the service is ready, checks immutable candidate configuration/secret pins and
verifies resuming without key prompts or secret creation. All 56 infrastructure
unit tests passed; Ruff format/lint checks also passed for the changed scripts.
The user supplied Sandbox acceptance; helper tests use synthetic credentials.

A local PostgreSQL/ASGI acceptance test also passed for a normal verified customer
in `APP_ENV=production` + `SEPAY_ENV=production`: Production checkout, confirmed
activation, duplicate-IPN idempotency, old Sandbox order rejection and the
Production invoice label. This used synthetic keys and made no provider calls.
The reproducible test is `infrastructure/gcp/tests/sepay_production_acceptance.py`;
run it inside the backend development test image as
`/app/tests/test_production_acceptance.py` with the backend fixtures installed.
