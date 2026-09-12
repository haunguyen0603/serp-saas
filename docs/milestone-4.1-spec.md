# SERP SaaS — Milestone 4.1 Specification
## Multi-Provider SERP Routing — SerpApi + Serper
1. Objective

Extend the existing Milestone 4 SERP architecture from one production provider to multiple production-capable providers.

Milestone 4.1 must add:

SerpApi
+
Serper
+
Provider routing
+
Provider fallback
+
Provider usage/budget tracking

without changing the end-user Project workflow.

The end user must NOT choose a SERP provider.

Conceptually:

End User
   ↓
Project + Keyword
   ↓
Rank Check Service
   ↓
Provider Router
   ↓
┌─────────────┬─────────────┐
│             │             │
Serper     SerpApi       Future
│             │
└──────┬──────┘
       ↓
Normalized SerpSearchResult
       ↓
Domain Matcher
       ↓
Ranking Persistence
2. Existing Foundation

Build directly on the completed Milestone 4 repository.

The current system already provides:

SerpProvider protocol
SerpApiProvider
FakeSerpProvider

normalized SerpSearchRequest
normalized SerpSearchResult
normalized OrganicResult

DomainMatcher

RankCheck
RankCheckResult
Ranking

ranking snapshots
provider field
provider_request_count

manual Keyword checks
manual Project checks

history
latest rankings

zero-credit fake testing

Milestone 4 verification confirms core execution is provider-independent and SerpApi-specific response types do not leak into ranking execution, persistence, or matching.

Do not redesign these working layers.

3. Core Architectural Rule

The end user never selects:

SerpApi
Serper
DataForSEO

The user selects only business configuration:

Search engine
Country
Language
Device
Location
Keywords

Provider selection is internal backend behavior.

Incorrect:

Create Project
├── Google
├── VN
├── Desktop
└── SERP Provider = Serper

Correct:

Create Project
├── Google
├── VN
└── Desktop

Backend:
ProviderRouter
→ chooses provider
4. Provider Architecture

Final conceptual provider layer:

SerpProvider
├── FakeSerpProvider
├── SerpApiProvider
└── SerperProvider

Add:

ProviderRegistry
ProviderRouter
ProviderSelectionPolicy

The Ranking Service must still depend only on:

SerpProvider
SerpSearchRequest
SerpSearchResult
OrganicResult
5. Explicit Scope

M4.1 must implement:

SerperProvider

multi-provider registry

provider routing

provider priority

provider availability checks

internal provider request budgets

usage accounting

safe fallback

provider attempt tracking

provider-specific config validation

Serper mocked adapter tests

routing tests

fallback tests

budget tests

zero-credit multi-provider smoke

optional real Serper smoke

optional real SerpApi smoke regression

documentation

regression verification
6. Explicitly Out of Scope

Do NOT implement:

scheduler
workers
queue
recurring rank checks

billing
subscription limits

dynamic provider pricing API

automatic purchasing credits

provider admin UI

user-selectable provider

Project-level provider selection

AI-based provider routing

provider result merging

run one Keyword through multiple providers simultaneously

consensus ranking

DataForSEO integration

automatic competitor analysis

M5 functionality
7. New Provider — Serper

Add:

SerperProvider

Serper currently provides real-time Google search results, supports query localization, and offers 2,500 trial queries.

The adapter must normalize Serper results into the existing provider-independent types.

Serper example response uses:

organic

with entries containing fields such as:

title
link
snippet
position

Map:

organic[].position
→ OrganicResult.position

organic[].title
→ OrganicResult.title

organic[].link
→ OrganicResult.url

Hostname is derived internally.

8. Serper Must Not Leak Into Core

Forbidden outside provider adapter/factory/registry code:

Serper response DTOs
raw `organic` assumptions
Serper-specific errors
Serper auth header logic
Serper URL structure

The Ranking Service must not contain:

if provider == "serper":
    ...

Provider-specific behavior belongs to the provider layer.

9. Provider Registry

Create a centralized registry conceptually equivalent to:

ProviderRegistry({
    "serpapi": SerpApiProvider(...),
    "serper": SerperProvider(...),
})

The registry determines:

configured providers
enabled providers
provider capabilities

Do not instantiate providers independently in route handlers.

10. Provider Router

Create:

ProviderRouter

Responsibilities:

receive SerpSearchRequest
determine eligible providers
apply routing policy
select provider
perform fallback when permitted
record attempts
return normalized result

It must NOT perform:

domain matching
ranking persistence
Project authorization
11. Initial Routing Strategy

Support at least:

fixed
priority

Recommended default for M4.1:

priority

Example:

SERP_PROVIDER_STRATEGY=priority
SERP_PROVIDER_PRIORITY=serper,serpapi

Meaning:

try Serper first
fallback to SerpApi only when policy permits
12. Why Serper First

For the user's current development environment:

Serper trial:
2500 queries

SerpApi free:
smaller free allowance

Therefore development configuration may prioritize:

serper
→ serpapi

Serper's current site advertises 2,500 free queries.

Do NOT hardcode 2500 in application business logic.

13. Provider Configuration

Add/update environment variables:

SERP_ENABLED_PROVIDERS=serper,serpapi
SERP_PROVIDER_STRATEGY=priority
SERP_PROVIDER_PRIORITY=serper,serpapi

SERPER_API_KEY=
SERPAPI_API_KEY=

SERP_REQUEST_TIMEOUT_SECONDS=10
SERP_DEFAULT_RESULT_LIMIT=10
SERP_MAX_CONCURRENT_REQUESTS=3
SERP_MANUAL_PROJECT_KEYWORD_LIMIT=25
14. Provider Internal Budgets

Add optional internal safety budgets:

SERPER_REQUEST_BUDGET=
SERPAPI_REQUEST_BUDGET=

Example development values:

SERPER_REQUEST_BUDGET=2500
SERPAPI_REQUEST_BUDGET=250

These values represent:

internal application budgets

They do NOT represent guaranteed provider plan limits.

Do not describe these as authoritative provider balances.

15. Budget Semantics

If configured:

budget = maximum requests this application is willing to send

If blank:

no internal request-budget limit

Budget tracking must not rely on provider pricing webpages at runtime.

16. Budget Persistence

Do NOT track provider usage only in process memory.

Usage must survive:

backend restart
Docker restart
multiple API requests

Add persisted provider usage accounting.

Recommended:

provider_usage

or equivalent.

17. Provider Usage Model

Recommended fields:

id

provider

period_type
period_key

request_count
success_count
failure_count
fallback_count

created_at
updated_at

For initial M4.1:

period_type = monthly
period_key = YYYY-MM

Example:

provider = serper
period_key = 2026-09
request_count = 143
18. Usage Scope

Provider usage is system-wide infrastructure accounting.

It does NOT belong to:

user_id
project_id
subscription

yet.

Per-user billing usage belongs to a later milestone.

19. Provider Attempt Tracking

Current RankCheck.provider stores the provider that produced the final result.

M4.1 must additionally preserve provider attempts when fallback occurs.

Example:

Serper
→ rate limited

SerpApi
→ success

History should show:

final provider = serpapi
provider attempts = 2
20. Provider Attempt Table

Recommended:

rank_check_provider_attempts

Fields:

id
rank_check_id

provider
attempt_number

status

started_at
completed_at

error_code nullable

provider_request_count

created_at

Do NOT store:

API key
secret-bearing URL
raw exception
21. Attempt Status

Support:

succeeded
failed

Optional:

skipped

only if useful.

22. Final Provider

Existing:

rank_checks.provider

must represent the provider whose response generated the persisted SERP results.

Example:

attempt 1 = serper failed
attempt 2 = serpapi succeeded

rank_checks.provider = serpapi
23. Provider Request Count

Existing:

provider_request_count

should represent total upstream provider requests consumed by the Rank Check.

Example:

Serper HTTP request = 1
fallback SerpApi HTTP request = 1

provider_request_count = 2

M4 already persists provider request count.

24. Fallback Policy

Fallback is allowed only for explicitly classified operational failures.

Recommended fallback errors:

SERP_PROVIDER_TIMEOUT
SERP_PROVIDER_UNAVAILABLE
SERP_PROVIDER_RATE_LIMITED
SERP_PROVIDER_QUOTA_EXHAUSTED

Potentially:

selected transient 5xx

after adapter-local retry policy is exhausted.

25. Do Not Fallback On

Do NOT fallback for:

SERP_PROVIDER_AUTH_ERROR

invalid request
unsupported search engine
unsupported parameter

provider parsing/schema bug

internal application bug

invalid Project configuration

These failures should surface instead of silently spending another provider's credits.

26. Why Auth Errors Must Not Fallback

Example:

SERPER_API_KEY is invalid

If system silently switches to SerpApi:

configuration defect remains hidden
+
SerpApi credits are consumed

Therefore:

AUTH_ERROR
→ fail Rank Check
27. Provider Adapter Retry vs Provider Fallback

Keep these concepts separate.

Adapter retry:

Serper request
→ transient network failure
→ retry Serper once

Provider fallback:

Serper exhausted allowed attempts
→ ProviderRouter chooses SerpApi

Do not accidentally produce unbounded retries.

28. Global Request Safety

Set maximum total provider attempts per Rank Check.

Recommended:

SERP_MAX_PROVIDER_FALLBACKS=1

Thus:

primary provider
+
maximum one fallback provider

No chains like:

provider1 → provider2 → provider3 → provider4

yet.

29. Provider Priority

Priority is backend configuration.

Example:

SERP_PROVIDER_PRIORITY=serper,serpapi

Changing it must NOT require:

database migration
frontend change
Project edit
30. Fixed Strategy

Support:

SERP_PROVIDER_STRATEGY=fixed
SERP_FIXED_PROVIDER=serper

This is useful for:

debugging
benchmarking
provider verification

It remains backend-only.

31. Priority Strategy

Example:

SERP_PROVIDER_STRATEGY=priority
SERP_PROVIDER_PRIORITY=serper,serpapi

Provider Router chooses the first provider that is:

enabled
configured
supports request
within internal budget
32. Provider Eligibility

A provider is eligible only when:

enabled
+
API credentials configured
+
supports search engine/configuration
+
budget available
33. No Eligible Provider

If no provider can serve a request:

SERP_NO_PROVIDER_AVAILABLE

Do not return:

SERPAPI_API_KEY missing

unless fixed strategy explicitly targets SerpApi.

34. Provider Capabilities

Introduce minimal capabilities metadata.

Example:

ProviderCapabilities
├── supported_search_engines
└── synchronous_search

For M4.1:

SerpApi → Google
Serper  → Google

Do not over-engineer a full capability platform.

35. Search Request Contract

Do NOT change the existing core:

SerpSearchRequest

unless Serper reveals a genuinely necessary generic field.

Existing conceptual fields remain:

query
search_engine
country_code
language_code
device
location
result_limit
36. Serper Search Mapping

Map internal fields to Serper's Google Search adapter according to the current Serper API contract.

At minimum map:

query
country
language
result count
location where supported

Serper advertises country/language localization and real-time results.

Do not guess unsupported parameters.

If current Serper docs/API behavior differs from SerpApi:

normalize in adapter

rather than changing Project semantics.

37. Device Handling

The existing Project supports:

desktop
mobile

Codex must verify Serper's current API semantics for device-specific Google results before implementation.

If Serper supports device:

map it

If Serper does NOT reliably support the required device mode:

Serper is not eligible for that request
→ router chooses another capable provider

Do NOT silently ignore Project.device.

This is critical.

38. Location Handling

Similarly:

Project.location

must not be silently dropped.

If Serper can map it safely:

use it

If not:

mark capability mismatch

and route to another provider.

Provider routing must preserve the user's requested SERP semantics.

39. Provider Semantic Compatibility

A cheaper provider must NOT be selected if doing so changes the search environment.

Correct:

request:
Google / VN / vi / mobile / Ho Chi Minh City

provider supports all required semantics
→ eligible

Incorrect:

provider supports only:
Google / VN / vi

system silently drops mobile/location

Cost optimization must never silently reduce accuracy.

40. Result Normalization

Serper response:

organic[]

must normalize into the exact same:

OrganicResult

used by SerpApi.

Core service must be unable to tell which provider produced it, except metadata.

41. Result Position

Use:

organic[].position

when positive and valid.

Do not derive rank from array order when provider supplies position.

42. Malformed Results

Skip individual organic rows lacking:

positive position
valid URL

as already done for SerpApi.

Do not fail the entire valid provider response because one row is malformed.

43. Empty Organic Results

A valid Serper response with:

organic = []

must behave the same as SerpApi:

RankCheck = succeeded
results = 0
rankings = 0
44. Provider Error Normalization

Serper-specific upstream errors must map to existing generic codes where possible:

SERP_PROVIDER_TIMEOUT
SERP_PROVIDER_UNAVAILABLE
SERP_PROVIDER_RATE_LIMITED
SERP_PROVIDER_AUTH_ERROR
SERP_PROVIDER_INVALID_RESPONSE
SERP_PROVIDER_ERROR

Add:

SERP_PROVIDER_QUOTA_EXHAUSTED

if needed and reliably distinguishable.

45. Rate Limit vs Quota

Do not assume they are identical.

Conceptually:

rate limited
= try later

quota exhausted
= provider budget/account unavailable until replenished

Both may permit fallback, but should remain distinct internally.

46. Serper Credentials

Add:

SERPER_API_KEY=

Never:

NEXT_PUBLIC_SERPER_API_KEY

Never send the key to frontend.

47. Serper Secret Logging

Tests must verify the Serper key cannot appear in:

logs
stored provider errors
API responses
provider attempt error fields
48. Provider Router Integration

Current flow:

RankCheckService
→ SerpProvider

Refactor minimally into:

RankCheckService
→ ProviderRouter
→ selected SerpProvider

Everything after normalized provider result remains unchanged:

DomainMatcher
Persistence
History
Frontend
49. No Domain Matcher Changes

Do NOT modify existing matching semantics:

exact hostname first
www fallback second
no arbitrary subdomain collapsing

active Sites only
active aliases only

best position per Site

M4 verification confirms these rules already work.

50. No Ranking Schema Semantics Change

Existing:

rank_checks
rank_check_results
rankings

remain authoritative.

M4.1 adds provider routing metadata, not a second ranking model.

51. Provider History

Rank Check Detail should return:

final_provider
provider_request_count
provider_attempts

Example:

{
  "provider": "serpapi",
  "provider_request_count": 2,
  "provider_attempts": [
    {
      "provider": "serper",
      "status": "failed",
      "error_code": "SERP_PROVIDER_RATE_LIMITED"
    },
    {
      "provider": "serpapi",
      "status": "succeeded"
    }
  ]
}
52. Frontend Provider Display

Do NOT add a provider selector.

Rank Check Detail may optionally display:

Data source: SerpApi

or:

Data source: Serper

If fallback happened, optional:

2 provider attempts

Do not expose infrastructure complexity prominently in Project creation.

53. Provider Usage API

Provider usage should remain internal/admin-level for now.

Do NOT expose it to normal end users unless useful for debugging.

An internal endpoint is optional.

No admin UI required.

54. Budget Exhaustion

When internal budget is reached:

provider becomes ineligible

Priority strategy automatically considers the next provider.

Example:

Serper internal budget reached
        ↓
SerpApi selected
55. Budget Race Safety

Concurrent Rank Checks must not exceed configured budgets because of race conditions.

Use:

transaction
row lock
atomic counter

or equivalent.

Do not use:

if usage < budget:
    usage += 1

without concurrency control.

56. When Usage Is Counted

Count an upstream attempt when the application actually sends the provider request.

Do not count:

provider selection
validation failure before HTTP
budget rejection
57. Success/Failure Counters

Provider usage should track at least:

request_count
success_count
failure_count

Fallback count is optional but recommended.

58. Provider Credits Are Not Billing

Do not interpret:

request_count

as exact financial charge.

Providers may have different billing semantics.

M4.1 usage is operational accounting only.

59. Migration

Create:

0006_multi_provider_routing

or the next correct revision.

Do NOT modify migrations:

0001
0002
0003
0004
0005
60. Migration Creates

At minimum, if using proposed schema:

provider_usage
rank_check_provider_attempts

plus indexes/constraints.

61. Migration Preservation

Verify:

existing RankChecks remain valid
existing provider=serpapi data remains valid
existing rankings remain unchanged
existing history remains unchanged

No historical rewrite is necessary.

62. Historical Compatibility

Existing M4 rank checks:

provider = serpapi

must continue rendering.

They may have:

provider_attempts = []

or equivalent because attempt history did not exist yet.

Do not fabricate historical attempts.

63. Provider Attempt FK

Use:

rank_check_provider_attempts.rank_check_id

with history-safe behavior.

Deleting attempt records must not affect RankCheck result history.

Prefer:

ON DELETE CASCADE from RankCheck

only if RankCheck itself remains protected by existing history semantics.

64. Usage Indexes

Recommended:

UNIQUE(provider, period_type, period_key)

INDEX(provider, period_key)

Do not over-index.

65. Provider Attempt Indexes

At minimum:

(rank_check_id, attempt_number)
(provider, created_at)
66. Provider Router Logging

Add structured events such as:

serp_provider_selected
serp_provider_fallback
serp_provider_budget_exhausted
serp_provider_no_eligible_provider

Allowed:

rank_check_id
provider
attempt
error_code

Never log:

API keys
query text unless existing policy explicitly allows
provider request body
raw provider response
67. Provider Selection Tests

Test:

Serper configured
SerpApi configured
priority = serper,serpapi

→ Serper selected
68. Missing Primary Provider Test
Serper enabled
but API key missing

SerpApi configured

→ SerpApi selected

for priority strategy.

69. Fixed Strategy Missing Key
fixed = serper
SERPER_API_KEY missing

Expected:

SERP_PROVIDER_NOT_CONFIGURED

Do not silently choose SerpApi in fixed mode.

70. Budget Routing Test
Serper budget exhausted
SerpApi budget available

→ SerpApi selected
71. All Budgets Exhausted

Expected:

SERP_NO_PROVIDER_AVAILABLE

and Rank Check fails safely.

72. Fallback Test — Timeout
Serper
→ timeout after permitted retry

SerpApi
→ success

Expected:

RankCheck succeeded
provider = serpapi
provider attempts include Serper failure + SerpApi success
provider_request_count reflects real upstream calls
73. Fallback Test — Rate Limit
Serper → rate limited
SerpApi → success

must fallback.

74. No Fallback — Auth
Serper → invalid API key

Expected:

RankCheck failed
SerpApi NOT called
75. No Fallback — Invalid Response

If malformed provider response indicates an adapter/provider-contract defect:

do not automatically spend backup credits

unless explicitly classified transient.

76. Provider Semantic Eligibility Test

If Serper cannot fulfill one requested dimension, e.g. a required device/location mode:

Serper → ineligible
SerpApi → selected

No request should be sent to Serper.

77. Provider Consistency Test

Feed logically equivalent mocked SerpApi and Serper responses.

Expected normalized results:

same OrganicResult shape
same DomainMatcher behavior
same Ranking persistence
78. Provider Independence Test

Run complete ranking pipeline using:

FakeSerpProvider
SerpApiProvider mock
SerperProvider mock

Core ranking service must produce equivalent domain behavior without provider-specific branches.

79. Existing Fake Provider

Keep:

FakeSerpProvider

as the default deterministic test provider.

Do not replace normal tests with Serper network calls.

80. Zero-Credit Test Requirement

These commands must consume:

0 SerpApi credits
0 Serper credits

by default:

pytest
make check
frontend tests
ranking smoke
browser verification
81. Optional Real Serper Smoke

Create:

make serper-smoke

guarded by:

RUN_REAL_SERPER_SMOKE=true
SERPER_API_KEY

One request only by default.

82. Real Serper Smoke Assertions

Do not assert exact rank.

Assert:

request succeeds
response normalizes
organic result positions parse
URLs parse
hostname normalization works
API key does not leak
83. Real SerpApi Regression

Keep:

make serpapi-smoke

as existing optional smoke.

Do not require both provider smokes for ordinary make check.

84. Multi-Provider Routing Smoke

Create a deterministic zero-credit smoke.

Example:

primary fake provider A
→ simulated rate limit

fallback fake provider B
→ success

Verify:

routing
attempt history
request accounting
final provider
ranking persistence
85. Real UI Behavior

No Project/Create UI change.

Existing:

Check Rankings
Check now

must route automatically through backend provider selection.

86. Frontend Rank Detail

Optionally add:

Provider: Serper

to check detail.

If fallback:

Provider: SerpApi
Attempts: 2

No provider controls.

87. Provider Failure UX

If no provider available:

Ranking provider is temporarily unavailable.

Do NOT show:

Serper budget is 2500 and exhausted

to normal end users.

Infrastructure details stay internal.

88. API Contract

Existing rank-check endpoints remain unchanged from the user's perspective.

Do NOT add:

{
  "provider": "serper"
}

to normal Rank Check request bodies.

Strict schemas must reject provider selection from user requests.

89. Security Rule

Explicitly test rejection of:

{
  "provider": "serpapi"
}

or:

{
  "provider": "serper"
}

from end-user rank-check payloads.

Provider routing cannot be influenced by user input.

90. Tenant Isolation

Provider usage infrastructure is global, but Rank Checks remain tenant-isolated.

Provider Router must never affect:

user ownership
Tracked Domain matching
Rank Check authorization
91. Concurrency

Existing one-running-check-per-Keyword behavior remains.

Provider fallback must not bypass that constraint.

M4 verification confirms duplicate concurrent checks are already prevented.

92. Project Check Concurrency

Existing:

SERP_MAX_CONCURRENT_REQUESTS=3

continues to apply to Keyword checks.

Do not interpret this as:

3 requests per provider × 2 providers

Fallback remains part of each Keyword's execution.

93. Request Timeout

Existing:

SERP_REQUEST_TIMEOUT_SECONDS=10

may be shared by both providers initially.

Provider-specific overrides may be added only if demonstrated necessary.

94. Default Result Limit

Keep:

SERP_DEFAULT_RESULT_LIMIT=10

No multi-page result collection in M4.1.

One selected provider result remains the source for one Rank Check.

95. Result Comparison

Do NOT compare SerpApi and Serper results inside a normal Rank Check.

Incorrect:

call both
choose better position

Correct:

select one provider
call it
fallback only on operational failure
96. Benchmark Utility

An optional developer-only comparison script may be created:

compare-providers

but it must be:

opt-in
clearly credit-consuming
not part of normal tests

Not required for M4.1 Definition of Done.

97. Documentation

Create/update:

docs/architecture/serp-provider.md
docs/architecture/provider-routing.md

docs/api/rank-checks.md

README.md

Document:

provider abstraction
Serper adapter
priority routing
fixed routing
eligibility
budgets
fallback rules
attempt history
secret handling
98. .env.example

Update with empty credentials:

SERP_ENABLED_PROVIDERS=serper,serpapi
SERP_PROVIDER_STRATEGY=priority
SERP_PROVIDER_PRIORITY=serper,serpapi

SERPER_API_KEY=
SERPAPI_API_KEY=

SERPER_REQUEST_BUDGET=
SERPAPI_REQUEST_BUDGET=

SERP_MAX_PROVIDER_FALLBACKS=1

Do not place real credentials in .env.example.

99. README Real Provider Setup

Document:

Serper key goes in .env
SerpApi key goes in .env

never NEXT_PUBLIC_*

Include opt-in smoke commands.

100. Expected Backend Additions

Approximately:

backend/app/services/serp/
├── base.py
├── types.py
├── factory.py
├── registry.py
├── router.py
├── fake.py
├── serpapi.py
└── serper.py

Additional:

models/provider_usage.py
models/rank_check_provider_attempt.py

repositories/provider_usage.py
repositories/rank_check_provider_attempt.py

Adapt names to current conventions.

101. New Migration

Create:

0006_multi_provider_routing

or next valid revision.

102. Migration Verification

Verify:

base → head

0005 → 0006

0006 → 0005 → 0006

if migration is losslessly reversible.

Also:

alembic check

must report no drift.

103. Existing History Regression

Create existing M4 fixture:

RankCheck provider=serpapi
Rankings
RankCheckResults

Upgrade.

Verify:

all historical records unchanged
provider remains serpapi
attempt list empty/legacy-safe
104. Backend Tests

At minimum add:

Serper request mapping

Serper response normalization

Serper empty organic results

Serper malformed row handling

Serper timeout

Serper 429

Serper auth failure

Serper 5xx

Serper invalid JSON

Provider registry

priority selection

fixed selection

missing credentials

budget exhaustion

budget concurrency

fallback timeout

fallback rate limit

no fallback auth

no fallback invalid contract

attempt persistence

provider request counting

provider history response

provider-input rejection

provider independence
105. Frontend Tests

At minimum:

ranking history renders Serper provider

ranking detail renders provider metadata

fallback attempt summary renders if exposed

Project/Create forms contain no provider selector

Rank Check API sends no provider field
106. Security Tests

Explicitly verify:

SERPER_API_KEY never logged

SERPER_API_KEY never returned

provider request headers not logged

provider request bodies not logged if they contain sensitive data

user cannot choose provider

user cannot manipulate provider budget
107. Zero-Credit API Smoke

Extend/create:

make ranking-smoke

to cover:

provider A selected
provider A fallback
provider B succeeds

attempt persistence
final provider
ranking persistence

with fake providers only.

108. Optional Real Serper Smoke

Required status in verification:

PASSED

if actually executed,

or:

SKIPPED — SERPER_API_KEY not configured

Do not pretend.

Since the user has already obtained Serper trial credits, running one real Serper request is recommended after zero-credit checks pass.

109. Browser Verification

Existing browser ranking journey must remain deterministic and zero-credit.

It should use backend fake routing.

Add assertions that:

no provider selector appears
rank check still succeeds
provider metadata can render
110. Production Behavior

Production must reject:

only fake provider enabled

as M4 already does for fake production configuration.

At least one real configured provider must be usable.

111. Provider Health

Do NOT call providers periodically just to determine health.

Provider availability is inferred from:

configuration
budgets
recent execution failures

No provider-health polling in M4.1.

112. No Circuit Breaker Yet

A full distributed circuit breaker belongs later.

M4.1 may use simple per-request fallback.

Do not add unnecessary Redis-based failure state yet.

113. M5 Compatibility

ProviderRouter must be injectable/reusable so future worker can call:

RankCheckService
→ ProviderRouter

without HTTP context.

No logic may depend on:

FastAPI Request object
browser session
frontend
114. Definition of Done — Serper Adapter
[ ] SerperProvider exists

[ ] It implements SerpProvider

[ ] It maps supported Project settings correctly

[ ] It normalizes Serper organic results

[ ] malformed rows are handled safely

[ ] timeout/error mapping works

[ ] API key remains backend-only

[ ] Serper-specific types do not leak into Ranking Service
115. Definition of Done — Routing
[ ] ProviderRegistry exists

[ ] ProviderRouter exists

[ ] fixed strategy works

[ ] priority strategy works

[ ] provider priority is configurable

[ ] missing configuration removes provider eligibility

[ ] capability incompatibility removes provider eligibility

[ ] no eligible provider returns stable error

[ ] end user cannot choose provider
116. Definition of Done — Budgeting
[ ] optional internal budgets work

[ ] usage persists across restarts

[ ] concurrent budget checks are race-safe

[ ] request count tracks actual upstream attempts

[ ] successful/failed usage counters work

[ ] budget exhaustion can route to another provider

[ ] provider pricing/free allowances are not hard-coded
117. Definition of Done — Fallback
[ ] timeout fallback works

[ ] unavailable fallback works

[ ] rate-limit fallback works

[ ] quota-exhausted fallback works if identifiable

[ ] auth errors do not fallback

[ ] invalid requests do not fallback

[ ] provider parsing defects do not silently fallback

[ ] maximum fallback count is enforced
118. Definition of Done — Attempt History
[ ] every actual provider attempt can be persisted

[ ] provider name stored

[ ] attempt status stored

[ ] safe error code stored

[ ] timestamps stored

[ ] final successful provider remains on RankCheck

[ ] provider_request_count reflects total upstream calls

[ ] old M4 RankChecks remain readable
119. Definition of Done — Existing Ranking Behavior
[ ] exact-host matching unchanged

[ ] www fallback unchanged

[ ] arbitrary subdomains still do not collapse

[ ] active aliases work

[ ] archived Sites ignored

[ ] best position per Site retained

[ ] Top N result persistence unchanged

[ ] snapshots unchanged

[ ] latest rankings unchanged

[ ] history remains intact
120. Definition of Done — Frontend
[ ] no provider selector appears in Project UI

[ ] no provider selector appears in Check Rankings UI

[ ] rank checks still work normally

[ ] provider may be displayed as informational metadata

[ ] fallback metadata renders safely if exposed

[ ] frontend never receives provider API keys
121. Definition of Done — Quality
[ ] backend tests pass

[ ] frontend tests pass

[ ] Serper adapter tests pass

[ ] provider routing tests pass

[ ] budget/concurrency tests pass

[ ] fallback tests pass

[ ] migration tests pass

[ ] zero-credit ranking smoke passes

[ ] browser verification passes

[ ] Ruff passes

[ ] Ruff formatting passes

[ ] mypy strict passes

[ ] ESLint passes

[ ] Prettier passes

[ ] TypeScript strict passes

[ ] npm audit acceptable

[ ] backend production build passes

[ ] frontend production build passes

[ ] M1 regression passes

[ ] M2 regression passes

[ ] M3/M3.1 regression passes

[ ] M4 regression passes

[ ] Docker services healthy
122. Optional Real Provider Verification

Serper:

[ ] one real Serper query verified

If not configured:

SKIPPED — SERPER_API_KEY not configured

SerpApi regression:

[ ] one real SerpApi query verified

if explicitly desired.

Neither should run from normal automated tests.

123. Required Commands

At minimum run:

docker compose build
docker compose up --build -d --wait

make check

make auth-smoke
make business-smoke
make tracked-site-smoke
make ranking-smoke

Add:

make provider-routing-smoke

or equivalent zero-credit deterministic command.

Also:

migration upgrade/downgrade/re-upgrade
alembic check

backend production build
frontend production build

browser verification

docker compose ps
124. Real Serper Command

Recommended:

RUN_REAL_SERPER_SMOKE=true make serper-smoke

Must:

consume one query by default
not run automatically
not expose API key
125. Verification Report

Create:

docs/verification-milestone-4.1.md

Include:

implementation summary

old vs new provider architecture

Serper adapter mapping

provider routing

routing strategies

provider eligibility

budgeting semantics

fallback policy

attempt history

migration details

files created/modified

exact commands executed

backend tests

frontend tests

routing tests

budget/concurrency tests

zero-credit smoke

browser verification

production builds

schema drift

security

real Serper smoke status

real SerpApi smoke status

M1–M4 regressions

known limitations

full Definition of Done checklist
126. Known Limitations Expected After M4.1

Document:

manual Rank Checks only

no scheduler
no queue
no workers

two production adapters only

no automatic cost-price synchronization

budgets are internal configuration

no provider UI for users

no dynamic provider performance scoring

no distributed circuit breaker

no DataForSEO

no provider result consensus/merging

no multi-page SERP collection
127. Final Architecture

After M4.1:

User
│
├── Projects
│    └── Keywords
│          ↓
│      RankCheckService
│          ↓
│      ProviderRouter
│       ┌──┴──────────────┐
│       ↓                 ↓
│    Serper            SerpApi
│       └──────┬──────────┘
│              ↓
│      SerpSearchResult
│              ↓
│       DomainMatcher
│              ↓
│      Ranking History
│
└── Tracked Sites
     └── Domain Aliases
128. Final Instruction to Codex

Implement:

docs/milestone-4.1-spec.md

against the CURRENT Milestone 4 repository.

Before changes, inspect:

all M1–M4 specs
all verification reports
README
current source
0001–0005 migrations
current tests
current SERP provider code
current Rank Check code

The repository is the source of truth.

Critical rules:

1. End users must NOT select a SERP provider.

2. Provider selection is backend infrastructure.

3. Preserve the existing SerpProvider abstraction.

4. Add Serper as a second adapter.

5. Add ProviderRegistry + ProviderRouter.

6. Support backend fixed and priority routing.

7. Never silently degrade Project search semantics just to use a cheaper provider.

8. If a provider cannot honor required search settings, it is ineligible.

9. Allow fallback only for explicitly safe operational failures.

10. Do not fallback on authentication/configuration/schema defects.

11. Normal automated tests consume zero real credits.

12. Persist provider usage and provider attempts.

13. Preserve final provider and total request count on RankCheck.

14. Do not change DomainMatcher semantics.

15. Do not change ranking/history semantics.

16. Do not add a provider selector to frontend.

17. Do not implement workers, scheduling, queue, billing, DataForSEO, or M5 functionality.

Before completion:

run all backend tests
run all frontend tests

run routing tests
run fallback tests
run budget/concurrency tests

run migration tests
run alembic check

run all existing smoke tests
run zero-credit provider-routing smoke

run browser verification

run lint
run formatting
run strict typing

build production backend
build production frontend

verify M1–M4 regressions
verify Docker services healthy

Create:

docs/verification-milestone-4.1.md

Do not claim a check passed unless it was actually executed.