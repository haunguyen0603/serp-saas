# SERP SaaS — Milestone 2 Specification
## User Accounts, Authentication & User-Level Tenant Isolation
1. Objective

Implement the account and authentication foundation for the SERP SaaS platform created in Milestone 1.

Milestone 2 must allow a person or business representative to create and use an account using only an email address and password.

The system must NOT require organizations, companies, workspaces, teams, invitations, or memberships.

The ownership model for the current product is:

User
  ↓
Future Projects
  ↓
Future Keywords
  ↓
Future Rankings

The authenticated user is the tenant boundary.

Future business resources must be owned directly or indirectly by user_id.

The primary authentication flow must support:

Sign Up
   ↓
Login
   ↓
Authenticated Session
   ↓
Current User
   ↓
Protected APIs
   ↓
Logout / Refresh

Milestone 2 must build on the existing Milestone 1 architecture rather than replace it.

2. Existing Milestone 1 Foundation

Assume the repository already contains and uses:

Next.js
TypeScript
App Router
TanStack Query

FastAPI
Python 3.12+
Pydantic 2
SQLAlchemy 2
asyncpg
Alembic

PostgreSQL
Redis

Docker
Docker Compose
Pytest
Vitest
Ruff
mypy
ESLint
TypeScript strict mode

Milestone 1 already established the local startup workflow where PostgreSQL and Redis are health-checked before the backend starts.

Do not redesign or replace these technologies unless implementation correctness requires a narrowly scoped change.

3. Critical Architecture Decision
3.1 User is the tenant

DO NOT introduce:

organization_id
organizations
organization_members
workspaces
teams
tenant_memberships

The tenant identifier is:

user_id

Future ownership must follow:

users.id
   ↓
projects.user_id
   ↓
keywords.project_id
   ↓
rankings.keyword_id

Authorization must always derive the user identity from the authenticated request.

Never trust a client-provided user_id for authorization.

For example, future APIs must follow this concept:

project = await project_repository.get_for_user(
    project_id=project_id,
    user_id=current_user.id,
)

and NOT:

project = await project_repository.get(project_id)

Milestone 2 does not create projects yet, but establish this security pattern now.

4. Scope

Milestone 2 must implement:

User model
User repository
Authentication service
Password hashing
Registration
Login
Access tokens
Refresh tokens
Refresh token rotation
Logout
Current-user endpoint
Authentication dependencies
Frontend sign-up page
Frontend login page
Authenticated application state
Frontend logout
Protected frontend page
Basic Terms acceptance
Authentication tests
Security tests
Database migrations
Documentation
5. Explicitly Out of Scope

DO NOT implement:

Organizations
Teams
Roles
Permissions management
Project CRUD
Keyword CRUD
SERP tracking
SERP providers
Workers
Celery
Task queues
Billing
Subscriptions
Payment gateways
Google OAuth
GitHub OAuth
Facebook login
Enterprise SSO
MFA / 2FA
CAPTCHA / reCAPTCHA
Password reset email
Email delivery provider
Mandatory email verification
Admin dashboard
User impersonation
API keys

Email verification-related database fields may be prepared for future implementation, but Milestone 2 must not integrate an email provider.

Do not add unrelated business functionality.

6. Backend Package Structure

Extend the existing backend cleanly.

Preferred structure:

backend/app/
├── api/
│   ├── router.py
│   └── v1/
│       ├── router.py
│       ├── auth.py
│       └── users.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   ├── errors.py
│   └── ...
│
├── db/
│   ├── base.py
│   ├── session.py
│   ├── models.py
│   └── ...
│
├── models/
│   ├── user.py
│   └── refresh_token.py
│
├── repositories/
│   ├── __init__.py
│   ├── user.py
│   └── refresh_token.py
│
├── schemas/
│   ├── auth.py
│   └── user.py
│
├── services/
│   ├── auth.py
│   └── users.py
│
└── dependencies/
    └── auth.py

Exact file names may vary if there is a good reason, but preserve separation of concerns.

Required flow:

API Router
    ↓
Service
    ↓
Repository
    ↓
SQLAlchemy
    ↓
PostgreSQL

Do not place SQLAlchemy queries directly in API route handlers.

Do not place authentication business logic directly inside routers.

7. User Database Model

Create table:

users

Required fields:

id
email
password_hash
status
email_verified_at
terms_accepted_at
last_login_at
created_at
updated_at

Recommended PostgreSQL types:

id                  UUID PRIMARY KEY
email               VARCHAR / TEXT UNIQUE NOT NULL
password_hash       TEXT NOT NULL

status              VARCHAR / enum-compatible value NOT NULL

email_verified_at   TIMESTAMPTZ NULL
terms_accepted_at   TIMESTAMPTZ NOT NULL
last_login_at       TIMESTAMPTZ NULL

created_at          TIMESTAMPTZ NOT NULL
updated_at          TIMESTAMPTZ NOT NULL

Use UUID identifiers.

UUID4 is acceptable.

Do not use auto-increment IDs for public-facing user identifiers.

8. User Status

Support at minimum:

active
disabled

Represent this cleanly in Python, for example:

class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"

A disabled user:

must not be able to login
must not refresh sessions
must not access protected endpoints

Do not implement user deletion in this milestone.

9. Email Normalization

Normalize email before storage and lookup.

Minimum normalization:

email = email.strip().lower()

Do not attempt aggressive transformations such as removing Gmail dots or plus aliases.

The following must resolve to the same account:

User@Example.com
user@example.com
 user@example.com

Enforce uniqueness at the database level.

Do not rely only on an application-level duplicate check.

Registration races must still be handled correctly.

10. Password Requirements

Never store raw passwords.

Never log raw passwords.

Never return passwords or hashes through APIs.

Use Argon2id for password hashing.

Use a well-maintained Python library such as:

argon2-cffi

or another production-quality Argon2id implementation.

Do not invent custom password cryptography.

Minimum password policy:

minimum length: 10 characters
maximum accepted length: reasonable safe bound, e.g. 128 characters

Do not require arbitrary composition rules such as:

one uppercase
one number
one symbol

unless needed later.

Reject invalid passwords with a clear validation error.

11. Password Security API

Centralize password functions, for example:

def hash_password(password: str) -> str:
    ...

def verify_password(password: str, password_hash: str) -> bool:
    ...

Password hashing configuration must not be duplicated in repositories or API handlers.

12. Authentication Architecture

Use two token types:

Access Token
+
Refresh Token
Access token

Use a signed JWT.

Purpose:

authorize API requests

Recommended lifetime:

15 minutes

JWT should contain only minimal claims.

Example conceptual claims:

{
  "sub": "<user_uuid>",
  "type": "access",
  "iat": 0,
  "exp": 0
}

Do not put:

password hash
email verification secrets
sensitive profile data

inside the JWT.

13. JWT Signing Configuration

For Milestone 2, symmetric signing is acceptable.

Example:

HS256

Add required environment variables:

JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

JWT_SECRET_KEY must be required.

Production must fail startup if a secure authentication secret is missing.

Never put a production secret in .env.example.

Use an obvious local placeholder.

14. Refresh Token Design

Refresh tokens must NOT simply be long-lived JWTs with no server-side state.

Use server-side refresh token tracking.

Create table:

refresh_tokens

Required fields:

id
user_id
token_hash
expires_at
revoked_at
created_at
last_used_at

Recommended:

id             UUID PRIMARY KEY
user_id        UUID FK users.id NOT NULL
token_hash     TEXT UNIQUE NOT NULL
expires_at     TIMESTAMPTZ NOT NULL
revoked_at     TIMESTAMPTZ NULL
created_at     TIMESTAMPTZ NOT NULL
last_used_at   TIMESTAMPTZ NULL

Index:

user_id
token_hash
expires_at

Use an appropriate foreign-key delete behavior.

15. Refresh Token Generation

Refresh tokens should be cryptographically random opaque values.

For example conceptually:

secrets.token_urlsafe(...)

Do not use predictable IDs.

Do not store raw refresh tokens in PostgreSQL.

Store:

SHA-256 or equivalent deterministic cryptographic hash

of the refresh token.

Conceptual flow:

generate raw token
       ↓
return/send raw token to client
       ↓
hash raw token
       ↓
store hash in database

If the database is compromised, stored token hashes must not directly function as authentication tokens.

16. Refresh Token Rotation

Implement refresh-token rotation.

When:

POST /api/v1/auth/refresh

is successfully called:

old refresh token
      ↓
validate
      ↓
mark old token revoked
      ↓
generate new refresh token
      ↓
store new token hash
      ↓
issue new access token
      ↓
return/set new session

The old refresh token must no longer be valid.

This prevents indefinite reuse of stolen refresh tokens.

17. Refresh Token Cookie

Store the raw refresh token in an HttpOnly cookie.

Cookie requirements:

HttpOnly = true
Path = appropriate authentication path or /
SameSite = Lax by default
Secure = true in production

Development configuration must work on localhost.

Never expose the refresh token to frontend JavaScript.

Do not put the refresh token in:

localStorage
sessionStorage
React state
URL query parameters
18. Access Token Client Handling

The login/register/refresh response may return the short-lived access token to the frontend.

The frontend should keep the access token in application memory.

Do not persist the access token in localStorage.

Preferred flow:

Browser
   │
   ├── Access token → memory
   │
   └── Refresh token → HttpOnly cookie

After browser reload:

Frontend starts
      ↓
POST /auth/refresh
      ↓
refresh cookie sent automatically
      ↓
new access token
      ↓
restore authenticated user

Configure credentialed requests correctly.

19. Registration API

Implement:

POST /api/v1/auth/register

Request:

{
  "email": "user@example.com",
  "password": "example-secure-password",
  "accept_terms": true
}

Do NOT accept:

user_id
status
email_verified
role
organization
subscription

from the client.

Validate:

valid email
password policy
accept_terms == true
email uniqueness

If Terms are not accepted:

registration must fail

On success:

create user
create authentication session
issue access token
issue refresh token

The user should not be forced through a second login immediately after successful registration.

20. Confirm Password

The frontend registration form should include:

Password
Confirm Password

The frontend must verify:

password === confirmPassword

before submitting.

The backend registration request must NOT contain:

confirm_password

The API only receives the actual password once.

21. Registration Response

Return a typed response such as:

{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "...",
    "email": "user@example.com",
    "status": "active",
    "email_verified": false,
    "created_at": "..."
  }
}

Never return:

password_hash
refresh token database record
token_hash
internal authentication secrets
22. Login API

Implement:

POST /api/v1/auth/login

Request:

{
  "email": "user@example.com",
  "password": "..."
}

On valid credentials:

normalize email
      ↓
load user
      ↓
verify status
      ↓
verify password
      ↓
update last_login_at
      ↓
create refresh-token session
      ↓
issue access token
      ↓
set refresh cookie
23. Login Error Security

Do not reveal whether an account exists.

These cases:

unknown email
incorrect password

should return equivalent external authentication failure responses.

Example:

{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password."
  }
}

Avoid:

Email does not exist
Password is incorrect

because that enables account enumeration.

24. Refresh API

Implement:

POST /api/v1/auth/refresh

The refresh token must be read from the HttpOnly cookie.

Do not require the frontend to read or submit the raw refresh token manually.

Successful response:

{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    ...
  }
}

Also rotate the refresh cookie.

Invalid, expired, or revoked refresh tokens must result in an authentication failure.

25. Logout API

Implement:

POST /api/v1/auth/logout

Logout must:

read current refresh-token cookie
      ↓
revoke token server-side if found
      ↓
delete/expire refresh cookie

Logout should be safely idempotent.

Calling logout while already logged out should not produce an unexpected server error.

26. Current User API

Implement:

GET /api/v1/users/me

Require:

Authorization: Bearer <access-token>

Return:

{
  "id": "...",
  "email": "user@example.com",
  "status": "active",
  "email_verified": false,
  "terms_accepted_at": "...",
  "last_login_at": "...",
  "created_at": "...",
  "updated_at": "..."
}

Do not return internal authentication fields.

27. Current User Dependency

Create reusable FastAPI dependencies such as:

async def get_current_user(...) -> User:
    ...

and, if useful:

CurrentUser = Annotated[User, Depends(get_current_user)]

The dependency must:

read Bearer token
validate JWT signature
validate expiration
validate token type
extract user ID
load user from database
ensure user exists
ensure user is active
return authenticated user

Future protected APIs must be able to reuse this dependency.

28. User-Level Tenant Security Rule

Create and document the following mandatory rule:

No future user-owned resource may be retrieved, modified, or deleted solely by resource ID.

Future repositories must require the authenticated owner.

Example:

async def get_project_for_user(
    project_id: UUID,
    user_id: UUID,
) -> Project | None:
    ...

SQL concept:

SELECT *
FROM projects
WHERE id = :project_id
  AND user_id = :user_id;

Do not build a generic future pattern where authorization is checked only after unrestricted resource retrieval.

Milestone 2 must document this convention even though project tables are not yet created.

29. Authentication Failure Codes

Provide consistent error codes.

At minimum:

INVALID_CREDENTIALS
EMAIL_ALREADY_REGISTERED
PASSWORD_POLICY_VIOLATION
TERMS_NOT_ACCEPTED
AUTHENTICATION_REQUIRED
INVALID_ACCESS_TOKEN
EXPIRED_ACCESS_TOKEN
INVALID_REFRESH_TOKEN
DISABLED_USER

Use the Milestone 1 error response structure.

Example:

{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password."
  }
}

Avoid leaking internal exceptions.

30. HTTP Status Codes

Use appropriate HTTP status semantics.

Recommended:

201 Created       successful registration
200 OK            successful login
200 OK            refresh
200/204            logout
200 OK            GET /users/me

400 Bad Request   invalid request/business validation
401 Unauthorized  authentication failures
403 Forbidden     authenticated but account disabled / forbidden
409 Conflict      duplicate email
422               request schema validation where appropriate

Be consistent across the API.

31. Redis Usage

Redis exists from Milestone 1.

Do NOT make authentication critically dependent on Redis in Milestone 2 unless clearly justified.

PostgreSQL is the source of truth for refresh-token revocation.

Redis may be reserved for later:

rate limiting
session cache
token deny lists
abuse protection

Do not introduce unnecessary authentication cache complexity.

32. Authentication Configuration

Extend .env.example with authentication configuration.

Example:

JWT_SECRET_KEY=replace-with-a-long-random-secret-generated-locally
JWT_ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

AUTH_COOKIE_NAME=serp_refresh_token
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax

Production configuration must require:

AUTH_COOKIE_SECURE=true

where HTTPS is used.

Never place secrets in NEXT_PUBLIC_* variables.

33. CORS and Credentials

Milestone 1 already uses explicit configurable CORS instead of wildcard origins.

Update CORS configuration to support authentication cookies.

Configure:

allow_credentials=true

with explicit origins.

Never combine credentialed requests with:

allow_origins=["*"]

The frontend API client must use credentials where needed.

Conceptually:

fetch(url, {
  credentials: "include",
})
34. Database Migration

Create a new Alembic revision after the Milestone 1 baseline.

Example:

0002_authentication.py

The migration must create:

users
refresh_tokens

with:

primary keys
foreign keys
unique constraints
indexes
timestamps

The migration must support:

upgrade
downgrade
upgrade again

Do not modify the historical Milestone 1 migration.

35. Model Registration

Ensure models are properly imported into the Alembic metadata path used by the existing project.

Milestone 1 intentionally left the first revision empty and documented future model registration through the DB model import path.

Autogenerated migrations must detect the new models correctly.

36. Transaction Handling

Registration must be transactional.

Conceptually:

BEGIN
  create user
  create refresh-token record
COMMIT

If session/token persistence fails:

the registration transaction must not leave inconsistent authentication state

Handle duplicate-email database integrity violations safely.

Do not return raw database errors.

37. Frontend Routes

Add:

/signup
/login
/app

/app is a minimal protected application page.

No SERP dashboard is required yet.

38. Signup Page

Create a clean registration page.

Required fields:

Email

Password

Confirm Password

[ ] I accept the Terms of Service

Create Account

Also provide:

Already have an account?
Log in

Required states:

idle
submitting
success
validation error
duplicate account error
backend unavailable

Do not implement CAPTCHA.

Do not reproduce SERPROBOT branding, graphics, text, or copyrighted visual assets.

The supplied SERPROBOT screenshot is only a UX reference for the simple registration flow.

Create an original SERP SaaS interface.

39. Login Page

Fields:

Email
Password

Log in

Provide:

Don't have an account?
Create account

Support:

loading
invalid credentials
backend unavailable
successful login

On successful login:

redirect to /app
40. Authenticated Application Page

Create:

/app

Display minimal authenticated information:

SERP SaaS

Signed in as:
user@example.com

Account status:
Active

[ Logout ]

This is not the final product dashboard.

Its purpose is to prove authentication works end to end.

41. Frontend Authentication State

Create a centralized authentication layer.

Do not scatter authentication state across pages.

Suggested structure:

frontend/src/
├── features/
│   └── auth/
│       ├── api.ts
│       ├── types.ts
│       ├── auth-provider.tsx
│       ├── hooks.ts
│       └── ...

or equivalent.

The architecture should expose concepts such as:

user
accessToken
isAuthenticated
isLoading

login()
register()
logout()
refresh()

Use TanStack Query where appropriate.

Avoid unnecessary global state libraries if React context + TanStack Query is sufficient.

42. Frontend API Client

Extend the reusable API layer created in Milestone 1.

Add typed methods:

register(...)
login(...)
refreshSession()
logout()
getCurrentUser()

API methods must be centralized.

Do not write separate raw fetch logic inside each page component.

43. Automatic Session Restoration

On application startup:

frontend has no in-memory access token
       ↓
attempt /auth/refresh
       ↓
valid HttpOnly cookie?
       ↓
YES → obtain access token + current user
NO  → unauthenticated state

This should allow an authenticated user to refresh the browser and remain signed in.

Do not create redirect loops.

44. Authenticated API Requests

Create an authenticated request mechanism that sends:

Authorization: Bearer <access-token>

When the access token expires:

request receives authentication failure
        ↓
attempt refresh once
        ↓
obtain new access token
        ↓
retry original request once

Avoid infinite refresh loops.

Concurrent expired requests should not trigger an uncontrolled refresh storm.

Use a simple single-flight refresh mechanism if practical.

45. Protected Frontend Navigation

Unauthenticated access to:

/app

must redirect to:

/login

Authenticated access to:

/login
/signup

may redirect to:

/app

Do not depend on reading the HttpOnly refresh cookie from JavaScript.

Authentication state must be determined via the backend session flow.

46. Terms Acceptance

Registration requires:

accept_terms = true

On successful registration, store:

terms_accepted_at

using a server-generated UTC timestamp.

Do not trust a timestamp supplied by the client.

A dedicated Terms legal document is out of scope.

The frontend may use a placeholder route/link if needed, but do not invent legal terms.

47. Email Verification Preparation

Include:

email_verified_at

in the user model.

For Milestone 2:

default = NULL

Expose a derived API field:

email_verified = false

Do not prevent an unverified user from logging in during Milestone 2.

Do not send verification emails yet.

48. Rate Limiting

Full distributed rate limiting is out of scope.

However, design auth endpoints so future rate limiting can be added without rewriting authentication logic.

Do not prematurely implement a complex Redis rate limiter unless it is required to prevent tests or functionality from working.

Document these endpoints as future rate-limit targets:

/register
/login
/refresh
49. Logging

Continue structured logging from Milestone 1.

Log useful authentication events without secrets.

Allowed examples:

registration succeeded
login succeeded
login failed
refresh succeeded
refresh rejected
logout
disabled account rejected

Include identifiers only where safe.

Never log:

password
password_hash
access token
refresh token
JWT secret
Authorization header
Cookie header

Make sure request logging middleware does not accidentally log these values.

50. Security Headers and Sensitive Responses

Authentication responses containing tokens must not accidentally be cached by intermediaries.

Apply appropriate cache-control behavior such as:

Cache-Control: no-store

for sensitive auth responses.

Do not expose internal stack traces.

Do not include secrets in OpenAPI examples.

51. Backend Tests

Add comprehensive tests.

At minimum test:

registration succeeds
registration normalizes email
registration rejects duplicate email
registration rejects invalid email
registration rejects weak/short password
registration rejects terms=false

password is stored hashed
raw password is never stored

login succeeds
login rejects unknown email
login rejects wrong password
unknown email and wrong password expose equivalent external error
disabled user cannot login

access token authenticates /users/me
missing token fails
malformed token fails
expired token fails
wrong token type fails

refresh succeeds
refresh rotates token
old refresh token fails after rotation
expired refresh token fails
revoked refresh token fails

logout revokes refresh token
logout clears cookie
logout is safely repeatable

disabled user cannot refresh
disabled user cannot use protected API

database uniqueness is enforced

migration upgrade succeeds
migration downgrade succeeds
migration re-upgrade succeeds
52. Authentication Security Tests

Specifically verify that responses never expose:

password
password_hash
token_hash
JWT_SECRET_KEY
raw database errors

Test that:

HttpOnly refresh cookie is set
Secure behavior follows environment configuration
SameSite is configured

Test production configuration validation where appropriate.

53. Repository Tests

Test repositories independently where practical.

Examples:

create user
find by normalized email
find by ID
create refresh token
find token by hash
revoke token
detect expiration

Do not require API tests to be the only coverage of persistence behavior.

54. Service Tests

Authentication service should be testable independently from HTTP routing.

Test:

password verification
user creation rules
login rules
token issuing
refresh rotation
logout revocation
disabled account behavior

Keep business rules out of FastAPI decorators.

55. Frontend Tests

At minimum add tests for:

signup form renders

password confirmation mismatch
terms required
successful registration
duplicate email error
backend failure

login form renders
successful login
invalid credentials
backend failure

session restoration
authenticated /app rendering
unauthenticated protected-page behavior
logout

Use deterministic mocks.

Do not call external services during tests.

56. End-to-End Connectivity Verification

Add or extend smoke verification so the running Docker stack can verify:

Browser
   ↓
Signup
   ↓
FastAPI
   ↓
PostgreSQL
   ↓
Authenticated session
   ↓
/app
   ↓
Logout

If browser automation tooling is kept outside production dependencies, that is acceptable and consistent with Milestone 1.

Do not add heavy browser libraries to production runtime solely for verification.

57. API Documentation

FastAPI OpenAPI must document:

POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/users/me

Protected endpoints should display Bearer authentication correctly in Swagger/OpenAPI.

Document cookie behavior for refresh tokens.

58. README Updates

Update the root README with:

authentication overview
signup instructions
login flow
access/refresh token architecture
required auth environment variables
development cookie behavior
production cookie requirements
protected API example
migration instructions
test instructions

Do not remove the useful Milestone 1 documentation.

59. Architecture Documentation

Create or update documentation describing:

Browser
   │
   ├── access JWT in memory
   │
   └── HttpOnly refresh cookie
   │
   ▼
FastAPI
   │
   ├── Auth Service
   │
   ├── User Repository
   │
   └── Refresh Token Repository
   │
   ▼
PostgreSQL

Also document:

Tenant boundary = authenticated user

and:

Future resource ownership = user_id
60. API Flow — Registration

Document this flow:

POST /register
      ↓
validate request
      ↓
normalize email
      ↓
validate terms
      ↓
hash password
      ↓
insert user
      ↓
create refresh-token session
      ↓
set HttpOnly refresh cookie
      ↓
return access token + user
61. API Flow — Login

Document:

POST /login
      ↓
normalize email
      ↓
lookup user
      ↓
verify password
      ↓
verify user active
      ↓
create session
      ↓
update last_login_at
      ↓
set refresh cookie
      ↓
return access token + user
62. API Flow — Refresh

Document:

POST /refresh
      ↓
read refresh cookie
      ↓
hash token
      ↓
find database record
      ↓
validate active + expiration
      ↓
revoke current token
      ↓
create replacement
      ↓
issue new JWT
      ↓
set new refresh cookie
63. API Flow — Protected Request

Document:

Browser
   ↓
Authorization: Bearer JWT
   ↓
get_current_user
   ↓
verify token
   ↓
extract sub
   ↓
load user
   ↓
check status
   ↓
route handler
64. API Flow — Logout

Document:

POST /logout
      ↓
read refresh cookie
      ↓
revoke matching DB session
      ↓
expire cookie
      ↓
client clears access token
65. Avoid Authentication Enumeration

Where practical, authentication timing should not deliberately make nonexistent accounts trivially distinguishable from incorrect-password accounts.

At minimum:

same external error
same HTTP status
same response structure

Do not introduce premature complex side-channel defenses, but avoid obvious enumeration vulnerabilities.

66. Time Handling

Store timestamps as timezone-aware UTC values.

Use:

TIMESTAMPTZ

where appropriate.

Do not store naive local timestamps.

Relevant fields include:

created_at
updated_at
terms_accepted_at
last_login_at
email_verified_at
refresh_token.created_at
refresh_token.last_used_at
refresh_token.expires_at
refresh_token.revoked_at
67. Dependency Management

Pin/lock all newly introduced dependencies using the existing backend dependency workflow.

Do not remove:

uv.lock
package-lock.json

Run dependency security checks where already established.

Avoid adding a large authentication framework if the required implementation can remain clean with focused dependencies.

68. Docker Compatibility

All Milestone 2 functionality must work through the existing standard workflow:

cp .env.example .env
docker compose up --build

Do not require developers to install Python or Node locally.

Keep frontend and backend independently executable as established in Milestone 1.

69. Makefile

Extend existing Makefile commands only where useful.

Existing commands should continue working.

At minimum:

make build
make up
make down
make check
make backend-test
make frontend-test
make lint
make typecheck
make db-upgrade
make db-downgrade
make connectivity

Do not break Milestone 1 workflows.

70. Backward Compatibility

All existing Milestone 1 checks must continue to pass.

Specifically:

/health
/health/db
/health/redis
/docs
/openapi.json
frontend health page
Docker startup
database migrations
Redis health
lint
format
strict typing

The previous delivery reported all of these areas passing and all four Docker services healthy.

Milestone 2 must not regress them.

71. Definition of Done

Milestone 2 is complete only when ALL conditions below are satisfied.

Database
[ ] users table exists
[ ] refresh_tokens table exists
[ ] UUID keys implemented
[ ] unique normalized email enforced by database
[ ] refresh token indexes implemented
[ ] migration upgrade works
[ ] migration downgrade works
[ ] migration re-upgrade works
Security
[ ] passwords use Argon2id
[ ] raw passwords are never stored
[ ] JWT access tokens expire
[ ] JWT secrets come from configuration
[ ] refresh tokens are cryptographically random
[ ] raw refresh tokens are not stored in database
[ ] refresh tokens rotate
[ ] revoked refresh tokens fail
[ ] refresh cookie is HttpOnly
[ ] Secure cookie behavior is environment-aware
[ ] sensitive auth responses use no-store caching
Registration
[ ] registration endpoint works
[ ] email normalization works
[ ] duplicate registration is rejected
[ ] password policy is enforced
[ ] terms acceptance is required
[ ] successful signup creates authenticated session
Authentication
[ ] login works
[ ] invalid credentials are rejected safely
[ ] disabled users cannot login
[ ] refresh works
[ ] refresh rotation works
[ ] logout works
[ ] logout revokes session
Protected API
[ ] /users/me requires authentication
[ ] valid access token succeeds
[ ] expired token fails
[ ] invalid token fails
[ ] disabled user fails
[ ] reusable get_current_user dependency exists
Frontend
[ ] /signup works
[ ] /login works
[ ] /app is protected
[ ] confirm-password validation works
[ ] Terms checkbox works
[ ] successful signup redirects appropriately
[ ] successful login redirects to /app
[ ] browser refresh restores session
[ ] logout works
[ ] access token is not persisted to localStorage
[ ] refresh token is inaccessible to JavaScript
Architecture
[ ] no Organization model exists
[ ] no organization_id exists
[ ] user is documented as tenant boundary
[ ] repository layer exists
[ ] router/service/repository separation is maintained
[ ] future resource ownership convention uses current_user.id
Quality
[ ] backend tests pass
[ ] frontend tests pass
[ ] integration tests pass
[ ] Ruff passes
[ ] formatting passes
[ ] mypy strict passes
[ ] ESLint passes
[ ] TypeScript strict passes
[ ] production builds pass
[ ] no hard-coded secrets
Regression
[ ] all Milestone 1 functionality still passes
72. Required Verification Commands

Before declaring completion, execute the repository's real verification workflow.

At minimum:

docker compose build
docker compose up --build -d --wait

make check

make db-upgrade
make db-downgrade
make db-upgrade

Also verify production frontend/backend builds as supported by the existing repository.

Perform an actual authentication smoke test against the running application.

Example logical flow:

register unique user
      ↓
authenticated /users/me
      ↓
refresh token
      ↓
old refresh token rejected
      ↓
new access token works
      ↓
logout
      ↓
refresh rejected

Do not merely mock this verification.

73. Browser Verification

Verify in a real browser if the existing Milestone 1 verification tooling permits it.

Required user journey:

open /signup
      ↓
enter valid email
      ↓
enter password
      ↓
confirm password
      ↓
accept terms
      ↓
create account
      ↓
arrive at /app
      ↓
reload browser
      ↓
remain authenticated
      ↓
logout
      ↓
arrive at /login
      ↓
protected /app unavailable

Check for:

browser exceptions
failed API calls
cookie errors
CORS errors
redirect loops
74. Required Codex Delivery

When implementation is complete, create:

docs/verification-milestone-2.md

The document must contain:

implementation summary
architecture changes
database migration details
complete files created/modified
commands actually executed
backend test result
frontend test result
migration verification result
Docker verification result
browser verification result
security verification result
known limitations
Definition of Done checklist

Also update:

README.md

Do not claim a check passed unless it was actually executed successfully.

75. Known Deferred Features

At completion, explicitly document that these remain deferred:

email verification workflow
forgot/reset password
CAPTCHA
OAuth
MFA
projects
keywords
SERP tracking
background workers
billing
subscriptions
API keys
teams
organizations

This is intentional.

76. Future Milestone Compatibility

Milestone 2 must prepare cleanly for Milestone 3.

Milestone 3 is expected to introduce approximately:

User
  │
  ├── Project
  │      │
  │      └── Keywords
  │
  └── Project
         │
         └── Keywords

Expected future schema concept:

projects
├── id
├── user_id
├── name
├── domain
├── ...

Every project operation must eventually be scoped by:

current_user.id

Do not create project tables in Milestone 2.

77. Engineering Principles

Prioritize:

security
correctness
simplicity
maintainability
testability
explicit ownership
future scalability

Do not over-engineer.

In particular:

DO NOT introduce Organization abstraction
DO NOT introduce enterprise RBAC
DO NOT introduce a full identity provider
DO NOT introduce microservices
DO NOT introduce distributed session infrastructure
DO NOT implement unrelated SERP functionality

The objective is a secure and clean single-account SaaS authentication foundation.

78. Final Instruction to Codex

Implement Milestone 2 completely according to this specification.

Work directly on top of the existing Milestone 1 repository.

Before coding:

1. Read docs/milestone-1-spec.md.
2. Read README.md.
3. Read docs/verification.md.
4. Inspect the existing implementation.
5. Preserve working Milestone 1 architecture and conventions.

Do not assume the verification document is sufficient proof of implementation details. Inspect the actual source before modifying it.

Then implement Milestone 2 incrementally.

Recommended sequence:

1. Inspect current architecture
2. Add authentication configuration
3. Add User model
4. Add RefreshToken model
5. Add repositories
6. Add password security
7. Add token security
8. Create Alembic migration
9. Add auth service
10. Add authentication dependency
11. Add API schemas
12. Add register endpoint
13. Add login endpoint
14. Add refresh endpoint
15. Add logout endpoint
16. Add /users/me
17. Add backend tests
18. Add frontend auth API
19. Add auth state/provider
20. Add signup page
21. Add login page
22. Add protected /app page
23. Add frontend tests
24. Run migration checks
25. Run complete Milestone 1 regression suite
26. Run complete Milestone 2 test suite
27. Run real application authentication smoke test
28. Run browser verification
29. Update documentation
30. Produce verification-milestone-2.md

When an implementation detail is unspecified, choose the simplest production-sensible approach consistent with this specification.

Do not weaken a security requirement merely to simplify implementation.

Do not add features outside scope.

Before declaring Milestone 2 complete, actually execute:

Docker build
Docker startup
database migrations
backend tests
frontend tests
lint
format checks
Python strict type checking
TypeScript strict type checking
production builds
authentication API smoke test
browser authentication flow
Milestone 1 regression checks

Fix discovered issues before reporting completion.

Only report checks as successful if they were actually executed successfully.