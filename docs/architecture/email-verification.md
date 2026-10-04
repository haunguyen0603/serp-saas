# Signup email verification

New registrations receive a limited authenticated session and a verification
email. With `AUTH_REQUIRE_VERIFIED_EMAIL=true` (default), registration and login
route unverified users to `/verify-email`. Private pages redirect there without
mounting their contents. Business APIs independently reject unverified users with
`403 EMAIL_NOT_VERIFIED`.

Unverified users can restore/end their session, read `/api/v1/users/me`, check
delivery status and request another email. Login and refresh do not verify an
address. Existing unverified accounts must log in and request an email. Migration
0013 adds the token table without verifying existing users or deleting resources.
Already verified users retain access.

## API

| Endpoint                                      | Access                               | Behavior                                                                     |
| --------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| `POST /api/v1/auth/register`                  | Public JSON                          | Create account, session and challenge atomically; deliver email after commit |
| `GET /api/v1/auth/email-verification`         | Authenticated, verification optional | Return verified flag, delivery state, resend wait and expiry                 |
| `POST /api/v1/auth/email-verification/resend` | Authenticated, verification optional | Rotate challenge with database-enforced cooldown/hourly limit                |
| `POST /api/v1/auth/verify-email`              | Public JSON with `token`             | Return `status=verified` and owning `user_id`; no login/session switching    |

Session responses include `email_verification_required`. Status responses expose
no raw token. Auth outcomes use `Cache-Control: no-store`. Rate limits return
`429 VERIFICATION_RATE_LIMITED`, `retry_after_seconds` and `Retry-After`.

## Tokens and delivery

Challenges use 48 cryptographically random bytes. Only SHA-256 digests are stored,
alongside owner, expiry, used/revoked timestamps and delivery state. Defaults are a
60-minute lifetime, 60-second resend cooldown and five emails per account in a
rolling hour. Resending invalidates older links. Verification and resending lock
the same user row to serialize concurrent operations. Disabled users cannot verify.

Links use `AUTH_SITE_URL`, never the request Host or a user-supplied redirect. The
token is in a URL fragment (`/verify-email#token=...`), which does not reach server
request logs. The page removes the fragment, applies no-referrer and is excluded
from indexing/sitemap. Opening a link performs no verification: pressing **Verify
email** sends a JSON POST. This avoids consuming links through ordinary email-link
prefetching. See [OWASP email verification guidance](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html).

Email is sent by an HTTP background task after the account/session/challenge
transaction commits. SMTP failure sets delivery state to `failed` and preserves
the account for login/resend. Raw tokens are not logged or persisted in an outbox.
If the API process stops before delivery, the challenge may remain `pending`; the
user can resend after the cooldown. Automatic background delivery retries are not
implemented. Failed delivery attempts also count toward resend limits.

Verification does not create a login or change another account's session. The
browser refreshes its own session after confirmation; another browser/device must
log in with the verified account's password. A user already signed in to another
verified account still needs to explicitly confirm the email link.

## Local workflow

Compose includes [Mailpit](https://mailpit.axllent.org/docs/install/docker/), pinned
to `axllent/mailpit:v1.31.3`, with its inbox bound only to loopback. SMTP is internal
to Compose. Emails are captured locally and are not delivered externally.

```sh
docker compose up --build -d --wait
```

If the shell exports `DEBUG=release`, prefix this local development command with
`DEBUG=true` so it does not override the boolean in `.env`.

1. Open `http://localhost:3000/register` and create an account.
2. Registration opens `/verify-email`; business pages/APIs remain blocked.
3. Open `http://localhost:8025` and find the verification email.
4. Open its link, then press **Verify email**.
5. Continue to the workspace, or log in if using another browser/device.
6. For a missing or expired email, sign in and use **Resend verification email**.

The existing `.env` was supplemented with local defaults without replacing its
credentials. Mailpit messages persist in `mailpit_data`. There is no application
endpoint that exposes a raw token or bypasses verification.

## Configuration and production

| Variable                                    | Local default                         | Production                                              |
| ------------------------------------------- | ------------------------------------- | ------------------------------------------------------- |
| `AUTH_REQUIRE_VERIFIED_EMAIL`               | `true`                                | Keep true for the verification gate                     |
| `AUTH_SITE_URL`                             | `http://localhost:3000`               | Public HTTPS frontend origin matching CORS/build config |
| `AUTH_VERIFICATION_EXPIRE_MINUTES`          | `60`                                  | 5–1440                                                  |
| `AUTH_VERIFICATION_RESEND_SECONDS`          | `60`                                  | 10–3600                                                 |
| `AUTH_VERIFICATION_MAX_EMAILS_PER_HOUR`     | `5`                                   | 1–20 per account                                        |
| `AUTH_EMAIL_PROVIDER`                       | Compose `smtp`; tests `fake`          | `smtp` required                                         |
| `AUTH_EMAIL_FROM`                           | `SERP SaaS <noreply@serp-saas.local>` | Authorized sender address                               |
| `AUTH_SMTP_HOST` / `AUTH_SMTP_PORT`         | `mailpit` / `1025`                    | Your SMTP relay and port                                |
| `AUTH_SMTP_USERNAME` / `AUTH_SMTP_PASSWORD` | Empty                                 | Configure both when authentication is required          |
| `AUTH_SMTP_STARTTLS`                        | `false`                               | Usually true for port 587                               |
| `AUTH_SMTP_SSL`                             | `false`                               | True for implicit TLS (usually 465); disable STARTTLS   |

Production rejects fake/disabled email, HTTP verification origins and SMTP without
TLS. SSL/STARTTLS are mutually exclusive and validate server certificates. Deploy
SMTP credentials as backend secrets. Auth mail is separate from `REPORT_EMAIL_*`,
so verification works while scheduled report email is disabled. Soft access via
`AUTH_REQUIRE_VERIFIED_EMAIL=false` still supports verification; scheduled reports
continue to require a verified email.

Before production, configure the real SMTP sender/domain and test delivery to an
authorized recipient. Local acceptance exercises SMTP through Mailpit; it does
not validate external inbox delivery or SPF/DKIM/DMARC configuration.

## Cloud Run: missing verification email

Registration commits before SMTP delivery. A successful register response or
`GET /api/v1/auth/email-verification` does not prove email was delivered. On the
verification page, inspect the status response (not the access token): `pending`
means background delivery has not recorded an outcome, `failed` means sending
failed, and `sent` means the SMTP relay accepted the message, not that it reached
the inbox.

In Cloud Shell, run the helper from an updated checkout:

```sh
python3 infrastructure/gcp/diagnose-auth-email.py --check-smtp
```

Alternatively, upload just `infrastructure/gcp/diagnose-auth-email.py` through
Cloud Shell **More → Upload** and run `python3 ~/diagnose-auth-email.py --check-smtp`.
No backend build/redeploy is required for this helper. It reads the revisions
actually receiving traffic, displays only nonsecret SMTP settings, the password
secret name/version and CPU throttling. By default and with `--check-smtp`, it
never reads secret values, logs in to SMTP or sends a message. The connection check validates TLS/certificates
and EHLO from Cloud Shell; it does not prove Cloud Run egress or password validity.

If TLS passes, test authentication using the same pinned password version as the
serving API revision:

```sh
python3 infrastructure/gcp/diagnose-auth-email.py --check-login
```

This explicit option reads the SMTP password into memory from its configured
Secret Manager version (or the hidden inline setting), logs in over validated TLS,
then disconnects. It never prints the password, writes it to disk or sends mail.
The operator needs Secret Accessor for that secret. Exception response text is
hidden; only the exception class and numeric SMTP status are reported.
`SMTPAuthenticationError` means the server did not accept the credentials; check
mailbox username/password and hosting authentication policy. See
[Python SMTP login](https://docs.python.org/3/library/smtplib.html#smtplib.SMTP.login).
If login passes, the next evidence is Cloud Run delivery logs and cPanel Track
Delivery; Cloud Shell authentication success still does not prove Cloud Run
network access or acceptance of a particular message/recipient.

If Cloud Shell login passes but the application reports `failed`, test from a
one-off Cloud Run job. Upload `infrastructure/gcp/probe-auth-email-cloudrun.py`
through Cloud Shell **More → Upload**, then run (use your own recipient address):

```sh
python3 ~/probe-auth-email-cloudrun.py --run --recipient your-email@example.com
```

This creates and executes one diagnostic job using the serving API's immutable
image, service account, pinned SMTP password reference and VPC egress settings.
The probe does not start the app or touch the database. It sends one clearly
labelled test message without a verification link, with task retries disabled.
Cloud Shell never reads the password for this probe; Cloud Run resolves the
secret reference. Logs show the failed stage (`connect`, `starttls`, `login`,
`send` or `quit`), exception class and numeric SMTP response only. No raw response
text, password, recipient or message body is logged. Without `--recipient`, the
job checks TLS/login only; without `--run`, the helper only reads configuration
and prints a plan.

The operator needs permissions to create/execute jobs and use the API service
account, plus read its logs. A job runs on a separate instance and can have a
different outbound IP than the API; passing the probe alone does not prove the
API instance can send. The helper prints commands to reread logs (if ingestion
is delayed) and delete its uniquely named diagnostic job after diagnosis. See
[Cloud Run job configuration](https://docs.cloud.google.com/run/docs/reference/yaml/v1#cloud_run_job_yaml)
and [job secret references](https://docs.cloud.google.com/run/docs/configuring/jobs/secrets).

Interpret the probe before changing production configuration:

| Probe result                        | Next action                                                                                                                            |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `connect` / `starttls` failed       | Check Cloud Run egress, TLS/certificates and hosting SMTP access from Google Cloud                                                     |
| `login` failed                      | Compare the API secret version and hosting restrictions by source IP; Cloud Shell success does not guarantee acceptance from Cloud Run |
| `send` failed                       | Check the SMTP status and cPanel Track Delivery for sender/recipient rejection or hosting limits                                       |
| `send` accepted                     | The relay accepted the test; check Spam and cPanel Track Delivery, then retry the existing account's verification email                |
| `quit` failed after `send` accepted | SMTP accepted the message but disconnect failed; the application currently treats a disconnect exception as delivery failure           |

If the test is accepted but verification still fails, collect the API's filtered
delivery logs below. The probe is independent of HTTP background task execution.

For cPanel secure SMTP on port 465, expect `AUTH_SMTP_SSL=true`,
`AUTH_SMTP_STARTTLS=false`, full mailbox username, the exact Outgoing Server from
Connect Devices and an authorized sender. The password binding must reference a
version containing that mailbox's password. Local `mailpit` and a port number
entered as hostname are not production outgoing servers.

Click Resend once when the button permits it, then query application and POST
request logs rather than the repetitive status polling:

```sh
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="serp-api" AND (jsonPayload.logger="app.services.email_verification" OR (httpRequest.requestMethod="POST" AND (httpRequest.requestUrl:"/api/v1/auth/register" OR httpRequest.requestUrl:"/api/v1/auth/email-verification/resend")))' \
  --project=serp-saas --freshness=1h --limit=30 \
  --format='table(timestamp,httpRequest.requestMethod,httpRequest.status,jsonPayload.message)'
```

The application's current delivery log reports a generic failure and intentionally
omits raw SMTP exception text. The default `gcloud run services logs read` rendering
may omit JSON message fields, so use the explicit projection above. If no POST
appears after Resend, check the browser Network tab and resend cooldown; do not
assume SMTP was attempted from GET status logs alone.

Use the result to choose the next check:

| Evidence                          | Next check                                                                                                              |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| TLS/certificate check fails       | Use the exact certificate-compatible outgoing hostname from cPanel; keep certificate verification enabled               |
| Connection timeout / DNS failure  | Check hostname, DNS and hosting SMTP access; compare Cloud Run logs because Cloud Shell uses a different network source |
| Delivery failed, TLS check passed | Check mailbox username/password secret version and hosting relay/sender restrictions                                    |
| Status remains pending            | Check API CPU throttling, background task logs and interrupted instance; resend after cooldown                          |
| Status sent                       | Check Spam and cPanel Track Delivery for the recipient, including remote rejection/deferred delivery and SPF/DKIM       |

Background delivery expects CPU allocation outside requests. If the serving
revision's CPU throttling is enabled, apply:

```sh
gcloud run services update serp-api \
  --project=serp-saas --region=asia-southeast1 --no-cpu-throttling
```

This uses instance-based billing; see [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings).
If the confirmed problem is a password version mismatch, add the correct mailbox
password using `create-runtime-secret.py`, then update only its binding with the
actual numeric version (example `2`):

```sh
export SMTP_SECRET_VERSION=2
gcloud run services update serp-api \
  --project=serp-saas --region=asia-southeast1 \
  --update-secrets="AUTH_SMTP_PASSWORD=serp-auth-smtp-password:$SMTP_SECRET_VERSION"
```

The partial update preserves the other bindings. Keep the version export for
future deployments. Retry using Resend on the existing account; creating another
account or re-running database migrations does not fix SMTP.
For hosting-side evidence use [cPanel Track Delivery](https://docs.cpanel.net/cpanel/email/track-delivery/).

## Validation

The full backend suite passes (262 tests), along with all 115 frontend tests,
backend Ruff/mypy checks and frontend ESLint/TypeScript checks. Migration tests
verify the schema matches the models.

A Chrome acceptance run exercises registration, the private-page/API gate,
actual SMTP delivery to Mailpit, the real resend cooldown, replacement of older
links, explicit confirmation in another browser, single-use tokens and entry
into the workspace after refreshing the original session. The verification page
was also checked at 375, 768, 1024 and 1440 pixels wide. No external email was sent.
