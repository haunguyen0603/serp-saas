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

| Endpoint | Access | Behavior |
| --- | --- | --- |
| `POST /api/v1/auth/register` | Public JSON | Create account, session and challenge atomically; deliver email after commit |
| `GET /api/v1/auth/email-verification` | Authenticated, verification optional | Return verified flag, delivery state, resend wait and expiry |
| `POST /api/v1/auth/email-verification/resend` | Authenticated, verification optional | Rotate challenge with database-enforced cooldown/hourly limit |
| `POST /api/v1/auth/verify-email` | Public JSON with `token` | Return `status=verified` and owning `user_id`; no login/session switching |

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

| Variable | Local default | Production |
| --- | --- | --- |
| `AUTH_REQUIRE_VERIFIED_EMAIL` | `true` | Keep true for the verification gate |
| `AUTH_SITE_URL` | `http://localhost:3000` | Public HTTPS frontend origin matching CORS/build config |
| `AUTH_VERIFICATION_EXPIRE_MINUTES` | `60` | 5–1440 |
| `AUTH_VERIFICATION_RESEND_SECONDS` | `60` | 10–3600 |
| `AUTH_VERIFICATION_MAX_EMAILS_PER_HOUR` | `5` | 1–20 per account |
| `AUTH_EMAIL_PROVIDER` | Compose `smtp`; tests `fake` | `smtp` required |
| `AUTH_EMAIL_FROM` | `SERP SaaS <noreply@serp-saas.local>` | Authorized sender address |
| `AUTH_SMTP_HOST` / `AUTH_SMTP_PORT` | `mailpit` / `1025` | Your SMTP relay and port |
| `AUTH_SMTP_USERNAME` / `AUTH_SMTP_PASSWORD` | Empty | Configure both when authentication is required |
| `AUTH_SMTP_STARTTLS` | `false` | Usually true for port 587 |
| `AUTH_SMTP_SSL` | `false` | True for implicit TLS (usually 465); disable STARTTLS |

Production rejects fake/disabled email, HTTP verification origins and SMTP without
TLS. SSL/STARTTLS are mutually exclusive and validate server certificates. Deploy
SMTP credentials as backend secrets. Auth mail is separate from `REPORT_EMAIL_*`,
so verification works while scheduled report email is disabled. Soft access via
`AUTH_REQUIRE_VERIFIED_EMAIL=false` still supports verification; scheduled reports
continue to require a verified email.

Before production, configure the real SMTP sender/domain and test delivery to an
authorized recipient. Local acceptance exercises SMTP through Mailpit; it does
not validate external inbox delivery or SPF/DKIM/DMARC configuration.

## Validation

The full backend suite passes (262 tests), along with all 115 frontend tests,
backend Ruff/mypy checks and frontend ESLint/TypeScript checks. Migration tests
verify the schema matches the models.

A Chrome acceptance run exercises registration, the private-page/API gate,
actual SMTP delivery to Mailpit, the real resend cooldown, replacement of older
links, explicit confirmation in another browser, single-use tokens and entry
into the workspace after refreshing the original session. The verification page
was also checked at 375, 768, 1024 and 1440 pixels wide. No external email was sent.
