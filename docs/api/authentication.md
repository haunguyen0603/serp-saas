# Authentication API

Base path: `/api/v1`. Interactive docs remain `/docs`; OpenAPI remains `/openapi.json`.
All auth POSTs use `Content-Type: application/json` and credentialed browser fetch.
Use an empty JSON object for refresh/logout. Raw refresh credentials are read only
from the HttpOnly cookie; unknown body fields are rejected.

| Endpoint | Body / authentication | Success |
| --- | --- | --- |
| `POST /auth/register` | `{ "email": "person@example.com", "password": "<10–128 characters>", "accept_terms": true }` | 201 session response + refresh cookie |
| `POST /auth/login` | `{ "email": "person@example.com", "password": "<password>" }` | 200 session response + refresh cookie |
| `POST /auth/refresh` | `{}` + refresh cookie | 200 session response + rotated cookie |
| `POST /auth/logout` | `{}` + optional refresh cookie | 200 `{ "status": "ok" }` + expired cookie; idempotent |
| `GET /users/me` | `Authorization: Bearer <access-token>` | 200 safe user response |

A session response contains `access_token`, `token_type: "bearer"`, `expires_in`
(seconds), and `user`. The user response contains only `id`, normalized `email`,
`status`, derived `email_verified`, `terms_accepted_at`, `last_login_at`,
`created_at`, and `updated_at`. It never contains password/refresh hashes, raw
refresh tokens, or internal database records. Timestamps include UTC timezone.

The refresh cookie defaults to `serp_refresh_token`, Path `/api/v1/auth`, HttpOnly,
SameSite=Lax, and a 30-day Max-Age. Secure is false for local HTTP and required in
production. Frontend JavaScript cannot read it. Cookie rotation is transactional;
the previous value fails immediately after rotation commits. Logout invalidates
the current refresh session; an already issued JWT expires normally (15 minutes).

All sensitive responses, including authentication failures, are `Cache-Control:
no-store`. 401 responses include `WWW-Authenticate: Bearer`. Errors retain the
Milestone 1 `{ "error": { "code": "...", "message": "..." } }` format.

| Code | HTTP status | Meaning |
| --- | --- | --- |
| `INVALID_CREDENTIALS` | 401 | Same response for unknown email and incorrect password |
| `EMAIL_ALREADY_REGISTERED` | 409 | Normalized email already exists |
| `PASSWORD_POLICY_VIOLATION` | 422 | Password outside the 10–128 character bound |
| `TERMS_NOT_ACCEPTED` | 422 | Terms were explicitly declined |
| `VALIDATION_ERROR` | 422 | Invalid email/types, missing or forbidden input fields |
| `AUTHENTICATION_REQUIRED` | 401 | No valid Bearer authorization header |
| `INVALID_ACCESS_TOKEN` | 401 | Invalid signature/type/claims or absent user |
| `EXPIRED_ACCESS_TOKEN` | 401 | JWT expired |
| `INVALID_REFRESH_TOKEN` | 401 | Missing, expired, revoked, or unknown refresh credential |
| `DISABLED_USER` | 403 | Correctly authenticated account is disabled |
| `UNTRUSTED_ORIGIN` | 403 | Auth mutation from a non-allowed browser origin |
| `JSON_REQUIRED` | 415 | Auth POST uses a simple form or non-JSON content type |

The existing `/health`, `/health/db`, and `/health/redis` APIs remain public and
unchanged. No listing of users, account administration, or business resources is
provided. The authenticated user's ID is the only future ownership boundary.
