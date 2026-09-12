# SERP SaaS — Milestone 4 Specification
## SERP Provider Abstraction, SerpApi Integration, Domain Matching & Ranking History
1. Objective

Implement the first real SERP tracking pipeline.

Milestone 4 must allow an authenticated user to manually run rank checks for Project Keywords and persist ranking history.

The primary execution pipeline is:

Project
+
Keyword
    ↓
SERP Provider abstraction
    ↓
SerpApi
    ↓
Normalized organic results
    ↓
Domain Matcher
    ↓
User's active Tracked Domains
    ↓
Matched Tracked Sites
    ↓
Rank Check + Ranking History

Milestone 4 is manually triggered.

Do NOT implement recurring scheduling, queues, workers, billing, or automated recurring checks yet.

2. Existing Foundation

Build on the current completed Milestone 3.1 repository.

The current architecture is:

Authenticated User
│
├── Projects
│    └── Keywords
│
└── Tracked Sites
     └── Domain Aliases

Project contains:

name
search_engine
country_code
language_code
device
location
status

Keyword contains only:

keyword
keyword_normalized
active

Tracked Sites and Domain Aliases belong directly to the user and are not Project-specific.

Do not reverse this architecture.

3. Core M4 Principle

M4 must distinguish clearly between:

Provider-specific data

and:

application/domain data

SerpApi must be an adapter behind a generic contract.

Incorrect:

RankingService
    ↓
direct SerpApi HTTP calls

Correct:

RankingService
    ↓
SerpProvider interface
    ↓
SerpApiProvider

Future:

SerpProvider
├── SerpApiProvider
├── DataForSeoProvider
├── SerperProvider
└── SearchApiProvider
4. Explicit Scope

M4 must implement:

generic SERP provider interface
SerpApi provider implementation

provider request/response normalization

manual Project rank check
manual single Keyword rank check

organic result extraction

hostname normalization
Tracked Domain matching

www equivalence
exact-host matching

rank check persistence
ranking history persistence

provider request status/error persistence

SERP configuration snapshot

provider metadata

ranking history APIs

latest ranking APIs

frontend manual Check Rankings action

frontend latest positions

frontend ranking history

provider configuration

fake provider for tests
mocked HTTP provider tests
optional explicit real SerpApi smoke test

security
migration
documentation
production builds
browser verification
5. Explicitly Out of Scope

Do NOT implement:

scheduled rank checking
cron
Celery
worker pools
distributed queues

automatic daily checks

billing
subscription usage enforcement

provider failover
provider load balancing

multiple production providers

competitor analytics dashboard

search volume
CPC
keyword difficulty

email reports
notifications

Google Search Console
Google Analytics

automatic 301 resolution
HTTP redirect crawling

Project ↔ Tracked Site mapping

AI Overview tracking
local pack tracking
paid ads ranking

pixel positions

These belong to later milestones.

6. Provider Choice

The first provider is:

SerpApi

SerpApi Google Search API accepts q as the query and supports location, gl, hl, and related localization parameters.

Current Project → SerpApi mapping:

Project.search_engine
→ engine

Keyword.keyword
→ q

Project.country_code
→ gl

Project.language_code
→ hl

Project.device
→ device

Project.location
→ location

For M4:

search_engine = google

maps to:

engine=google
7. SerpApi Free-Quota Awareness

SerpApi's current Free plan provides:

250 searches/month
50 searches/hour throughput

Therefore automated tests MUST NOT consume SerpApi quota by default.

Normal tests must use:

FakeSerpProvider
or
mocked SerpApi HTTP responses

Only an explicit manually-invoked smoke test may call the real provider.

8. Provider Interface

Create a provider abstraction conceptually equivalent to:

class SerpProvider(Protocol):
    async def search(
        self,
        request: SerpSearchRequest,
    ) -> SerpSearchResult:
        ...

Exact implementation may use ABC/Protocol according to repository conventions.

Core services must depend on this interface, not concrete SerpApi classes.

9. Internal Search Request

Define provider-independent:

SerpSearchRequest

Fields:

query

search_engine

country_code
language_code
device
location

result_limit

Optional future-ready:

request_context

but avoid speculative complexity.

10. Internal Search Result

Define:

SerpSearchResult

with at least:

provider
provider_request_id nullable

organic_results

requested_at
completed_at

raw_metadata optional

Do NOT expose raw SerpApi response throughout the application.

11. Internal Organic Result

Normalize every provider result into:

OrganicResult

Required fields:

position
title
url
hostname

Optional:

displayed_url
snippet

Keep the core model minimal.

12. SerpApi Organic Results

SerpApi exposes normal Google results under:

organic_results

and individual results can include:

position
title
link

among additional fields.

M4 should normalize:

organic_results[].position
→ OrganicResult.position

organic_results[].title
→ OrganicResult.title

organic_results[].link
→ OrganicResult.url

Hostname is derived by our code.

13. JSON Restrictor

SerpApi supports:

json_restrictor

to limit response fields, including limiting output to organic_results.

M4 may use this to reduce response payload.

However, do not depend on this behavior so tightly that provider parsing becomes fragile.

If used, document it.

14. Provider Configuration

Add settings equivalent to:

SERP_PROVIDER=serpapi

SERPAPI_API_KEY

SERPAPI_BASE_URL=https://serpapi.com/search

SERP_REQUEST_TIMEOUT_SECONDS

SERP_DEFAULT_RESULT_LIMIT

Recommended development:

SERP_DEFAULT_RESULT_LIMIT=10

The API key must never be committed.

15. Missing Provider Configuration

Application startup behavior should remain practical.

Recommended:

App may start without SERPAPI_API_KEY

but attempting a real rank check should return a clear service error:

SERP_PROVIDER_NOT_CONFIGURED

This allows ordinary M1–M3 development/tests without requiring a provider secret.

Production configuration may enforce stronger requirements later.

16. API Key Security

Never:

log API key
return API key in API response
include API key in frontend
store API key in localStorage
embed API key in Next.js public env

SerpApi calls occur from FastAPI backend only.

17. HTTP Client

Use an async HTTP client consistent with the Python stack.

Recommended:

httpx.AsyncClient

unless the repository already has another appropriate client.

Provider networking must support:

timeout
connection errors
non-2xx responses
malformed JSON
provider-declared errors
18. SerpApi Request Mapping

Conceptually:

params = {
    "engine": "google",
    "q": keyword.keyword,
    "gl": project.country_code.lower(),
    "hl": project.language_code,
    "device": project.device,
}

If Project location exists:

params["location"] = project.location

SerpApi recommends using gl alongside location for more consistent country-specific behavior.

Do that for configured location searches.

19. Search Result Depth

M4 default:

Top 10 organic results

The engine only evaluates results returned by the provider.

Do not claim:

"Not ranked anywhere"

if only Top 10 were checked.

Use semantics like:

not_found_within_depth

or:

not found in Top 10
20. Result Limit Storage

The actual checked depth must be persisted with every rank check.

Example:

result_limit = 10

Future:

10
20
50
100

Ranking history must remain interpretable if this changes.

21. Provider Result Ordering

Do not assume:

array index + 1 == rank

Use provider-provided:

position

when valid.

Ignore malformed organic entries without a usable:

position
url

but record provider parsing warnings appropriately.

22. Domain Normalization

Reuse/refactor the existing hostname normalization used by Tracked Domains.

SERP URL:

https://www.example.com/page?a=1

must yield:

www.example.com

Normalization must include:

lowercase
IDNA normalization
remove scheme
remove path
remove query
remove fragment
remove port
remove trailing dot

Do NOT resolve external redirects.

23. Domain Matching Semantics

M4 exact rule:

1. exact normalized hostname match
2. www equivalence fallback
3. no arbitrary subdomain collapsing

Examples:

Tracked:
example.com

SERP:
example.com
→ MATCH
Tracked:
example.com

SERP:
www.example.com
→ MATCH
Tracked:
www.example.com

SERP:
example.com
→ MATCH

but:

Tracked:
example.com

SERP:
blog.example.com
→ NO MATCH

and:

Tracked:
a.example.com

SERP:
b.example.com
→ NO MATCH
24. Why Not Collapse Arbitrary Subdomains

Do not automatically map:

shop.example.com
blog.example.com
app.example.com

to:

example.com

because separate subdomains may represent distinct SEO properties.

The user may explicitly add any subdomain as a Domain Alias.

25. Domain Matcher

Create a domain service equivalent to:

DomainMatcher

Inputs:

OrganicResult[]
TrackedDomain[]

Output:

MatchedOrganicResult[]

Conceptual result:

tracked_site_id
tracked_domain_id

position

result_url
result_hostname
title
26. Domain Registry Loading

Do NOT execute one database query for every organic result.

Incorrect:

for result in results:
    await tracked_domain_repo.find(result.hostname)

Correct:

load all active Tracked Domains for current user
        ↓
construct lookup maps
        ↓
match all organic results in memory

For normal M4 scale:

dict lookup ≈ O(1)
27. Domain Matching Map

Conceptually create:

exact_domains = {
    "example.com": domain_record,
    "blog.example.com": domain_record,
}

and optionally a separate normalized www equivalent map.

Do not make matching ambiguous.

28. Ambiguous www Collision

The data registry may legally contain:

example.com

and:

www.example.com

as different aliases.

If both exist and belong to different Sites for the same user, www equivalence becomes ambiguous.

M4 must handle this deterministically.

Recommended:

exact hostname match ALWAYS wins.

Only apply www equivalence if no exact match exists.

If fallback candidate is still ambiguous:

do not guess

record no match and emit sanitized warning/metric.

29. Active State Matching

Only match:

TrackedSite.status = active
AND
TrackedDomain.active = true

Archived Sites must not produce ranking matches.

Inactive aliases must not produce ranking matches.

30. Multiple Owned Sites in One SERP

A Keyword can match multiple user-owned Sites.

Example:

1 competitor.com
2 own-a.com
3 competitor2.com
4 own-b.com
8 own-c.com

Persist:

Site A → #2
Site B → #4
Site C → #8

Do NOT stop after the first user-owned result.

31. Multiple Results for Same Site

A Tracked Site may have multiple aliases or multiple URLs appearing in the same SERP.

Example:

#2 old-domain.com/page
#5 new-domain.com/page

both belong to:

Tracked Site A

For M4, persist the best organic position per Tracked Site per rank check as the primary ranking.

Optionally preserve all raw normalized organic results at check level if implemented efficiently.

At minimum:

Site A
position = 2
32. Ranking Identity

A ranking belongs conceptually to:

Rank Check
+
Tracked Site

not simply:

Keyword + domain

because Domain Aliases can change.

Logical SEO identity is:

TrackedSite
33. Rank Check Concept

Introduce:

rank_checks

One Rank Check represents one provider execution for one Keyword.

Relationship:

Project
  └── Keyword
       └── RankCheck
            └── Ranking[]
34. Rank Check Database Model

Create:

rank_checks

Recommended fields:

id
user_id
project_id
keyword_id

provider
status

query_snapshot
search_engine_snapshot
country_code_snapshot
language_code_snapshot
device_snapshot
location_snapshot

result_limit

provider_request_id nullable

requested_at
completed_at nullable

error_code nullable
error_message nullable

created_at
35. Why Snapshot Fields Are Mandatory

Project settings can later change:

VN / desktop
→
TH / mobile

Keyword text can also change.

Historical Rank Check must still mean:

this result was generated for:
"casino online"
Google
VN
vi
desktop
Ho Chi Minh City

Therefore do NOT reconstruct old rank check context from current Project/Keyword values.

36. Rank Check Status

Support:

pending
running
succeeded
failed

For M4 manual synchronous execution, transitions may be:

pending
↓
running
↓
succeeded

or:

pending
↓
running
↓
failed

Even though execution is synchronous now, this state model prepares for M5 workers.

37. Ranking Table

Create:

rankings

Recommended fields:

id

rank_check_id
tracked_site_id
tracked_domain_id

position

result_url
result_hostname
title nullable

created_at
38. Ranking Uniqueness

For M4 primary ranking:

UNIQUE (
    rank_check_id,
    tracked_site_id
)

because only best position per Tracked Site is persisted as ranking.

39. Tracked Domain Reference

Persist both:

tracked_site_id
tracked_domain_id

because:

Tracked Site = logical identity

Tracked Domain = exact alias that appeared

Example:

Tracked Site:
SEO Site A

Current:
new.com

SERP matched:
old.com

Ranking must preserve:

tracked_site = Site A
matched_domain = old.com
40. Historical Deletion Policy

M3.1 currently permits hard deletion of Tracked Sites.

Once Ranking history exists, blindly cascading deletion would destroy history.

Therefore M4 must change deletion semantics.

Recommended:

Tracked Site DELETE
→ archive / soft delete behavior

or refuse hard deletion once history exists.

Preferred approach:

tracked_sites.deleted_at nullable
tracked_domains.deleted_at nullable

However avoid unnecessary redesign if a cleaner approach fits the existing model.

Core requirement:

Historical rankings must not be silently destroyed when the user removes a currently tracked Site or alias.

41. Ranking Historical Integrity

Ranking rows must remain interpretable even if:

Tracked Site renamed
Domain alias deactivated
Domain alias removed from active tracking
Project settings changed
Keyword renamed

Therefore Ranking should snapshot at least:

matched_domain_snapshot
tracked_site_name_snapshot

or maintain non-destructive foreign-key history.

I recommend explicit snapshots for:

tracked_site_name_snapshot
matched_domain_snapshot

in addition to IDs.

42. Provider Metadata

Do not create SerpApi-specific business columns.

Allowed generic fields:

provider
provider_request_id

Optional:

provider_metadata JSONB

but keep it small and sanitized.

Do NOT store:

api_key
request Authorization data
complete secret-bearing URL
43. Raw Provider Response

Do NOT persist full raw SerpApi JSON by default in M4.

Reasons:

database growth
provider coupling
unnecessary fields
privacy/noise

Persist normalized results and minimal metadata.

If raw result debugging is needed, logging must still avoid secrets and should be development-only.

44. Organic Result Persistence

For M4, there are two reasonable options:

A. persist only matched rankings
B. persist normalized Top N organic result snapshot

Choose B.

Reason: the user's original workflow is specifically based on extracting the Top 10 websites and mapping them against SEO domains.

Create:

rank_check_results

to preserve the normalized organic SERP snapshot.

45. Rank Check Result Table

Create:

rank_check_results

Recommended:

id
rank_check_id

position

title nullable
url
hostname

created_at

Unique:

UNIQUE(rank_check_id, position)

This table stores the provider-independent Top N organic results.

46. Why Preserve Top N

This enables future:

competitor detection
SERP comparison
domain movement
historical SERP inspection

without requiring the original SerpApi response.

It also matches the user's existing workflow:

keyword
→ top websites
→ map against SEO domain registry
47. Rank Check Transaction Strategy

Do NOT keep a database transaction open while waiting for external SerpApi HTTP.

Correct flow:

transaction A:
create RankCheck(status=pending/running)
commit

        ↓

external HTTP request

        ↓

transaction B:
store results
store rankings
mark succeeded
commit

On provider failure:

transaction B:
mark failed
store sanitized error
commit

This avoids holding DB locks during network latency.

48. Provider Failure Handling

Map errors into stable internal categories such as:

SERP_PROVIDER_NOT_CONFIGURED
SERP_PROVIDER_TIMEOUT
SERP_PROVIDER_UNAVAILABLE
SERP_PROVIDER_RATE_LIMITED
SERP_PROVIDER_AUTH_ERROR
SERP_PROVIDER_INVALID_RESPONSE
SERP_PROVIDER_ERROR

Do not expose raw upstream exceptions to users.

49. Provider HTTP Retry

M4 may perform a small bounded retry for clearly transient failures.

Recommended:

maximum 2 attempts total

Retry only appropriate cases such as:

connection reset
timeout
HTTP 5xx
possibly 429 with reasonable Retry-After

Do NOT retry:

invalid API key
invalid request
schema parsing error

Avoid consuming free credits unnecessarily.

50. No Automatic Provider Retries in Tests

Fake/mock tests should explicitly simulate retry conditions.

Real SerpApi smoke must not intentionally burn credits testing repeated failures.

51. Manual Single Keyword Check API

Implement:

POST /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks

Requirements:

authenticated
owned Project
owned Keyword
Project active
Keyword active
provider configured

Successful response may return:

201 Created

with full check summary.

52. Manual Project Check API

Implement:

POST /api/v1/projects/{project_id}/rank-checks

This checks all active Keywords in the Project.

For M4, synchronous sequential or bounded-concurrency execution is acceptable.

Do NOT introduce a worker queue yet.

53. Project Check Result

Return aggregate:

{
  "project_id": "...",
  "submitted_keywords": 10,
  "succeeded": 9,
  "failed": 1,
  "checks": [...]
}

Do not rollback successful Keyword checks merely because another keyword failed.

External provider work is naturally multi-operation.

54. Bounded Concurrency

Do not issue hundreds of provider calls simultaneously.

For manual Project checks, introduce configurable small concurrency, e.g.:

SERP_MAX_CONCURRENT_REQUESTS=3

This protects:

provider quota
rate limits
local resources

No distributed rate limiter yet.

55. Free-Plan Safety

Because the development provider has limited quota, include a per-request safety limit.

For manual Project check:

max 25 keywords per invocation

for M4 development, unless explicitly configured higher.

If a Project has more:

reject with clear message

or allow selecting a subset.

Do NOT silently burn 500 provider searches.

56. Better API for Keyword Subset

Recommended Project check request:

{
  "keyword_ids": null
}

Meaning all active keywords subject to safety cap.

Or:

{
  "keyword_ids": [
    "...",
    "..."
  ]
}

to manually check selected Keywords.

Validate all selected keywords belong to the Project.

57. Provider Usage Accounting Foundation

Add lightweight persisted accounting per Rank Check:

provider
provider_request_count

For SerpApi M4:

1 successful provider request ≈ 1 search

Do NOT implement billing/quota enforcement yet.

This field prepares M7 usage accounting.

58. Current SerpApi Quota Display

Do NOT hardcode:

250 free searches

into business logic.

Pricing can change.

Documentation may mention current provider free allowance, but the application must not assume it.

59. Rank History API

Implement:

GET /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks

Support:

limit
cursor
status

Newest first.

60. Rank Check Detail API

Implement:

GET /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}

Return:

check metadata
configuration snapshot
normalized organic results
matched rankings
61. Latest Ranking API

Implement an efficient endpoint such as:

GET /api/v1/projects/{project_id}/rankings/latest

Return latest successful results for active Keywords.

Conceptually:

{
  "items": [
    {
      "keyword_id": "...",
      "keyword": "casino online",
      "checked_at": "...",
      "rankings": [
        {
          "tracked_site_id": "...",
          "tracked_site_name": "Site A",
          "domain": "new-domain.com",
          "position": 3,
          "url": "https://new-domain.com/page"
        }
      ]
    }
  ]
}
62. Not Found Within Checked Depth

If no tracked domain is present in Top N:

rankings = []

and check still:

status = succeeded

This is NOT a provider failure.

Frontend should display:

Not found in Top 10

not:

Error
63. Multiple Sites Display

If multiple Tracked Sites rank for a Keyword:

Site A #2
Site B #5
Site C #8

show all.

Do not collapse to one "project rank".

64. Project With No Tracked Sites

Rank check may still run and save Top N SERP results.

Result:

rankings = []

This is valid.

Frontend may show:

No tracked sites matched this SERP.

Do not block Project checking just because registry is empty.

65. Project Status

Archived Project:

manual rank check forbidden

Return stable business error such as:

PROJECT_NOT_ACTIVE
66. Keyword Status

Paused Keyword:

single manual rank check forbidden

Project-wide checks skip inactive Keywords.

Document behavior consistently.

67. Rank Check Idempotency / Duplicate Clicks

Users may double-click "Check Rankings".

M4 should prevent accidental immediate duplicate execution where practical.

Recommended API support:

Idempotency-Key

for manual rank-check creation.

If implementing full generic idempotency is excessive, frontend button locking plus backend "currently running" check for same Keyword is acceptable.

At minimum, prevent obvious duplicate concurrent checks for the same:

user
keyword
68. Running Check Constraint

Do not permit multiple simultaneous running checks for the same Keyword.

Database or service coordination should enforce:

one pending/running RankCheck per keyword

where practical.

Future M5 may formalize distributed job uniqueness.

69. Ranking Indexes

At minimum:

rank_checks(keyword_id, created_at)
rank_checks(project_id, created_at)
rank_checks(user_id, created_at)
rank_checks(status)

rank_check_results(rank_check_id, position)

rankings(rank_check_id)
rankings(tracked_site_id, created_at)

Avoid speculative excessive indexing.

70. User Ownership on Rank Data

Rank checks must be user-scoped.

Even though ownership can be derived:

RankCheck → Keyword → Project → User

store:

rank_checks.user_id

for efficient security filtering and future worker operations.

Database and service invariants must prevent mismatch.

71. Tenant Security

Never trust:

user_id
project_id from body
tracked_site_id supplied as ranking ownership

All ownership derives from:

Bearer token
→ current_user.id

Provider results decide which user's Tracked Sites match only after loading that user's registry.

72. Cross-Tenant Domain Matching Test

Explicitly test:

User A tracked:
example.com

User B tracked:
competitor.com

User A Rank Check SERP includes:

competitor.com

This must NOT generate a Ranking for User B's site.

Only User A's domain registry may participate.

73. Domain Alias Matching Test

Tracked Site:

primary:
new.com

alias:
old.com

SERP:

old.com

Expected:

Tracked Site = same Site
matched domain = old.com
position = ...
74. Primary Domain Is Not Required for Match

Do NOT only match:

is_primary = true

All:

active aliases

of active Sites are matchable.

Primary is UI/business metadata, not ranking eligibility.

75. Inactive Alias Test

If:

old.com active=false

SERP result:

old.com

must NOT match.

76. Archived Site Test

If Site:

status=archived

none of its aliases match.

77. Exact Host vs WWW Test

Test:

Tracked:
example.com

SERP:
www.example.com
→ match

and reverse.

Also test:

Tracked:
example.com

SERP:
blog.example.com
→ no match
78. Position Selection Test

If same Site appears:

#2 old.com
#7 new.com

Expected Ranking:

position = 2
matched_domain = old.com

Rank Check Results still preserve both organic rows.

79. Provider Parsing Tests

Mock SerpApi responses for:

normal organic results

organic_results missing

empty organic_results

malformed one result

provider error payload

invalid JSON

timeout

429

500

No real API quota required.

80. Fake Provider

Implement:

FakeSerpProvider

for service tests.

It should accept deterministic response fixtures.

Example:

fake.add_result(
    query="casino online",
    organic_results=[...],
)

Avoid network use.

81. Provider Factory

Create provider resolution centrally.

Concept:

get_serp_provider(settings) -> SerpProvider

Do not instantiate SerpApi client independently in services/routes.

82. Provider Structure

Recommended:

backend/app/services/serp/
├── base.py
├── types.py
├── factory.py
├── serpapi.py
└── fake.py

M1 already reserved a SERP service area; reuse existing conventions rather than duplicate architecture.

83. Ranking Service Structure

Add:

backend/app/services/rank_checks.py
backend/app/services/domain_matching.py

Repositories:

rank_check.py
rank_check_result.py
ranking.py

Models/schemas accordingly.

84. API Layer

Add approximately:

backend/app/api/v1/rank_checks.py
backend/app/api/v1/rankings.py

Do not put provider parsing or domain matching inside route handlers.

85. New Migration

Create:

0005_rank_tracking

or appropriate next revision.

Do NOT modify:

0001
0002
0003
0004
86. Migration Creates

At minimum:

rank_checks
rank_check_results
rankings

and any necessary historical-preservation adjustments for Tracked Site deletion.

87. Historical Foreign-Key Strategy

Avoid cascades that would destroy rankings.

For ranking-related FKs, choose deliberate semantics.

Recommended:

rankings.tracked_site_id
→ RESTRICT or nullable historical FK

rankings.tracked_domain_id
→ RESTRICT or nullable historical FK

because snapshots preserve display meaning.

Do not use:

ON DELETE CASCADE

from Tracked Site to ranking history.

88. Tracked Site Delete Refactor

Because history now exists:

DELETE /tracked-sites/{id}

should no longer physically delete ranking-bearing history.

Preferred behavior:

soft delete / archive

If the existing endpoint's semantics change, document clearly and adapt frontend wording.

Example:

Remove from tracking

rather than:

Permanently delete history
89. Rank Check History Retention

Deleting a Project or Keyword also creates historical integrity concerns.

M3.1 currently permits hard deletes.

Once M4 data exists, do NOT allow silent cascading history destruction.

Recommended policy for M4:

Project with Rank Checks:
cannot hard delete

Keyword with Rank Checks:
cannot hard delete

Instead:

archive Project
pause Keyword

Return:

HISTORY_EXISTS

if destructive deletion is requested.

Projects/Keywords with no ranking history may still hard delete.

This is simpler than introducing full soft-delete semantics everywhere in M4.

90. Provider Request Timing

Record:

requested_at
completed_at

This allows future latency measurement.

Optional derived:

duration_ms

need not be persisted if easily computed.

91. Check Timestamps

Use timezone-aware UTC timestamps.

All historical SERP data must use:

TIMESTAMPTZ
92. Frontend Project Detail

Add a primary action:

Check Rankings

on Project detail.

If Project contains more than the configured manual cap, show clear message and selection workflow.

93. Keyword Table M4 Columns

Extend the current table with real data only:

Keyword
Status
Last checked
Tracked rankings
Actions

Example:

casino online
Active
11 Sep 2026 10:30
Site A #3
Site B #8

No fake values.

94. Keyword Check Action

Each Keyword row may expose:

Check now

Disable while that Keyword has a running request.

95. Latest Ranking Display

If no check has ever occurred:

Never checked

If check succeeded with no tracked matches:

Not found in Top 10

If failed:

Check failed

These states must be distinct.

96. Ranking History UI

On Project/Keyword detail provide history showing:

Check time
SERP environment snapshot
Provider
Result depth
Matched Sites
Positions
Status

A simple table is sufficient.

No charts required yet.

97. Rank Check Detail UI

Allow viewing:

Top 10 Organic Results

Example:

#1 competitor.com
#2 own-old-domain.com   ← Site A
#3 competitor2.com
#4 own-site-b.com      ← Site B
...

This is especially useful for verifying domain matching correctness.

98. Tracked Site Labeling

Matched organic results should show:

Tracked
Site name

but unmatched domains are simply normal organic results.

Do not automatically create competitors as database records in M4.

99. Project Environment Display

Every check detail must show snapshot:

Google
VN
vi
Desktop
Ho Chi Minh City

not current Project config only.

100. Frontend Error Handling

User-friendly messages:

Provider is not configured.

SERP provider timed out.

Provider quota/rate limit reached.

This keyword is paused.

This project is archived.

A rank check is already running.

Do not expose upstream error JSON.

101. API Response Security

Do not return:

SERPAPI_API_KEY
full provider request URL containing api_key
internal stack trace
provider secrets
102. Logging

Structured logging events:

rank_check_started
rank_check_succeeded
rank_check_failed
serp_provider_request
serp_provider_error
domain_matches_found

Allowed metadata:

user_id
project_id
keyword_id
rank_check_id
provider
result_count
match_count
duration

Avoid logging full bulk histories unnecessarily.

Never log API keys.

103. Metrics Foundation

No monitoring platform required, but structure logs so later metrics can derive:

SERP requests
success rate
failure rate
latency
matches per request
provider errors
104. OpenAPI

Document:

manual rank-check endpoint
project check endpoint
history endpoints
latest rankings endpoint

Include:

401
404
409
422
502/503-style provider failures

according to existing error conventions.

105. Error Codes

Add stable errors such as:

SERP_PROVIDER_NOT_CONFIGURED
SERP_PROVIDER_TIMEOUT
SERP_PROVIDER_UNAVAILABLE
SERP_PROVIDER_RATE_LIMITED
SERP_PROVIDER_AUTH_ERROR
SERP_PROVIDER_INVALID_RESPONSE

RANK_CHECK_ALREADY_RUNNING
RANK_CHECK_NOT_FOUND

PROJECT_NOT_ACTIVE
KEYWORD_NOT_ACTIVE

RANK_CHECK_LIMIT_EXCEEDED

HISTORY_EXISTS
106. HTTP Status Guidance

Suggested:

201
Rank check created/completed

400
business-invalid request

401
authentication

404
owned resource absent/foreign

409
already running
history prevents destructive action

422
schema validation

502
upstream provider invalid/failure

503
provider unavailable/not configured if consistent with app conventions

Use existing error architecture.

107. Real SerpApi Smoke Test

Create an explicit opt-in script:

scripts/smoke_serpapi.py

or equivalent.

It must NOT run automatically in:

make check
pytest
frontend tests
browser tests

unless explicitly enabled.

108. Smoke Environment Flag

Real provider smoke requires:

SERPAPI_API_KEY
RUN_REAL_SERP_SMOKE=true

Without flag:

skip

Do not fail normal development test suite.

109. Real Smoke Credit Budget

Real smoke should use:

1 keyword
1 request

unless there is a compelling reason otherwise.

Do not spend dozens of searches validating M4.

110. Real Smoke Query

Use a stable harmless test query.

Do not assert exact search position because live SERPs vary.

Assert:

HTTP/provider succeeds
normalized result parses
organic positions are valid
URLs parse
provider metadata available
111. Automated Service Test

Use fake provider to test complete pipeline:

Project
+
Keyword
+
Tracked Sites
+
Fake SERP
        ↓
RankCheck
RankCheckResults
Rankings

No network.

112. Full Pipeline Fixture

Example:

User A

Project:
Google
VN
vi
desktop

Keyword:
"casino online"

Tracked Site A:
new-a.com
old-a.com

Tracked Site B:
site-b.com

Fake provider:

1 competitor.com
2 old-a.com/page
3 competitor2.com
5 site-b.com/page
7 new-a.com/other

Expected:

RankCheckResults:
all five normalized rows

Ranking:
Site A = #2, matched alias old-a.com

Ranking:
Site B = #5

Do not create a second Ranking for Site A at #7.

113. No-Match Test

Fake SERP:

10 competitor domains

Expected:

RankCheck status = succeeded
RankCheckResults = 10
Rankings = 0
114. Empty Organic Results

If provider returns valid response with no organic results:

RankCheck = succeeded
RankCheckResults = 0
Rankings = 0

unless provider explicitly indicates an error.

115. Provider Error Test

Provider exception:

timeout

Expected:

RankCheck = failed
error_code = SERP_PROVIDER_TIMEOUT
no rankings

Do not leave check:

running
116. Persistence Atomicity

Success persistence:

rank_check_results
+
rankings
+
rank_check succeeded

must be one transaction.

If ranking persistence fails:

rollback normalized results/rankings
mark check failed in a subsequent safe transaction

Avoid partially succeeded checks.

117. Concurrency Test

Two simultaneous requests for same Keyword.

Expected:

one executes
one receives RANK_CHECK_ALREADY_RUNNING

No duplicate provider consumption where coordination can prevent it.

118. User Isolation Tests

At minimum:

User A cannot read User B rank checks

User A cannot run checks for User B Project

User A cannot query User B latest rankings

User B Tracked Domains never participate in User A matching
119. Project Setting Snapshot Test

Run check:

VN desktop

then modify Project:

TH mobile

Historical check must still return:

VN desktop
120. Keyword Snapshot Test

Run:

keyword = "seo tool"

then rename:

"best seo tool"

Historical check retains:

query_snapshot = "seo tool"
121. Alias History Test

Run SERP matching:

old.com

then later:

deactivate old.com
promote new.com

Historical Ranking still shows:

matched_domain_snapshot = old.com
122. Result URL Preservation

Persist exact provider result URL.

Example:

https://old.com/page/article

Do not store hostname only.

This helps later diagnose which ranking page appeared.

123. Ranking Positions

Use positive integer:

position >= 1

Reject malformed zero/negative positions from provider normalization.

124. Pagination

Rank history must use stable cursor pagination.

Recommended:

created_at DESC
id DESC

Limit:

default 50
max 200
125. Latest Ranking Query Performance

Do not fetch complete historical history and filter in Python.

Latest ranking endpoint must use PostgreSQL efficiently.

Possible approaches:

DISTINCT ON
window function
latest successful rank check subquery

Choose maintainable PostgreSQL/SQLAlchemy implementation.

126. Avoid N+1

Fetching latest ranks for 100 Keywords must not issue hundreds of database queries.

Use set-oriented queries.

127. Manual Project Check Execution

Since M4 has no worker:

HTTP request
→ perform checks
→ return result

This is acceptable only for a small manually bounded number of keywords.

Document that asynchronous background execution moves to M5.

128. Request Timeout Implication

Because Project checks call external providers synchronously, keep manual cap low.

Do NOT attempt:

1000 keywords

inside one M4 HTTP request.

That is M5 territory.

129. M5 Compatibility

Design Rank Check status and services so M5 can change:

HTTP
→ direct execution

to:

HTTP
→ queue job
→ worker

without changing ranking schema.

130. Provider Independence Test

Create a test with:

FakeSerpProvider

that runs the entire Rank Check service without importing SerpApi adapter code.

This proves core business layer is provider-independent.

131. No SerpApi Types Outside Adapter

Forbidden outside SerpApi adapter:

SerpApi-specific response model
SerpApi-specific error classes
raw organic_results dict assumptions

Services receive normalized internal types only.

132. Frontend Does Not Know Provider Credentials

Frontend may display:

Provider: SerpApi

from API response.

It never receives:

API key
provider config secrets
133. Provider Display Name

Core stores:

provider = "serpapi"

UI maps to:

SerpApi

Avoid provider-specific branding throughout unrelated components.

134. Migration Verification

Run:

base → head
0004 → 0005

and:

alembic check

Since M4 changes deletion/history semantics, add fixture tests for existing M3.1 data.

135. Migration Fixture

Start at 0004 with:

users
projects
keywords
tracked_sites
tracked_domains

Upgrade to 0005.

Verify:

all M3.1 data remains

rank tables exist

history-safe constraints exist

no Project/Keyword/Tracked Site data lost
136. API Smoke

Create M4 business smoke using Fake/controlled provider or mock endpoint so it costs zero SerpApi credits.

Flow:

register User

create Tracked Sites + aliases

create Project + Keywords

run fake/manual rank check

verify Top N stored

verify matched rankings

verify best Site position

verify no-match state

verify history endpoint

change Project settings

verify old snapshot unchanged
137. Optional Real Provider Smoke

Separate command such as:

make serpapi-smoke

Must clearly warn:

Consumes SerpApi search quota.

One request only by default.

138. Browser Verification

Use fake/mocked backend provider mode for deterministic browser verification.

Required journey:

Login
↓
Tracked Sites
↓
Project
↓
Check Rankings
↓
see running/loading state
↓
see latest positions
↓
open Keyword history
↓
open rank-check detail
↓
see Top N organic results
↓
see owned domains highlighted
↓
reload
↓
history persists

No real SerpApi call is required for browser test.

139. Provider Test Mode

Support test/dev dependency injection.

Do NOT add an insecure frontend switch like:

?provider=fake

Provider selection must remain backend-controlled.

140. Documentation

Create/update:

docs/api/rank-checks.md
docs/api/rankings.md

docs/architecture/serp-provider.md
docs/architecture/ranking-engine.md
docs/architecture/domain-matching.md

Document:

provider abstraction
SerpApi mapping
domain matching semantics
www behavior
snapshot strategy
Top N semantics
failure handling
history retention
141. README

Update README with:

SERP provider configuration

SerpApi key setup

manual rank checking

fake provider testing

real provider smoke command

warning about provider credits

new ranking history routes

Do not print example real API keys.

142. Production Configuration

Production must require secure provider configuration before real Rank Checks are usable.

Do not build provider API key into Docker image.

Inject through runtime environment/secret manager later.

143. Security Tests

Explicitly test log sanitization for:

SERPAPI_API_KEY

full provider URL with api_key

provider error content containing secrets

No secrets may reach:

logs
client response
stored error_message
144. Result Content Safety

Provider titles/snippets/URLs are untrusted external data.

Frontend must render text safely through normal React escaping.

Do not use:

dangerouslySetInnerHTML

for provider result content.

145. Database Size Awareness

Top 10:

10 RankCheckResult rows
per Keyword check

is acceptable for M4.

Do not store huge arbitrary provider payloads.

Later retention/partitioning strategy belongs to scaling work.

146. Definition of Done — Provider Layer
[ ] Generic SerpProvider interface exists

[ ] SerpApiProvider implements it

[ ] Core rank service does not depend on SerpApi types

[ ] Project → provider parameter mapping works

[ ] Provider timeout/error mapping works

[ ] API key remains backend-only

[ ] Fake provider exists

[ ] Normal automated tests consume zero real provider credits
147. Definition of Done — Domain Matching
[ ] Active user Tracked Domains are loaded efficiently

[ ] Exact hostname matching works

[ ] www equivalence works

[ ] Arbitrary subdomain matching does not occur

[ ] Exact match wins over www fallback

[ ] Archived Sites do not match

[ ] Inactive aliases do not match

[ ] Multiple Sites can match one SERP

[ ] Multiple aliases for same Site collapse to best position

[ ] Cross-user domains never match
148. Definition of Done — Rank Checks
[ ] Single Keyword manual check works

[ ] Project multi-Keyword manual check works

[ ] Project check has safe request limit

[ ] RankCheck status lifecycle works

[ ] Provider failures result in failed checks

[ ] Valid zero-match SERP still succeeds

[ ] Duplicate concurrent checks are prevented

[ ] provider request count is stored

[ ] result depth is stored
149. Definition of Done — Historical Data
[ ] Rank Check stores query snapshot

[ ] search engine snapshot stored

[ ] country snapshot stored

[ ] language snapshot stored

[ ] device snapshot stored

[ ] location snapshot stored

[ ] provider stored

[ ] result depth stored

[ ] Top N normalized organic results stored

[ ] matched Site ranking stored

[ ] exact matched alias/domain preserved

[ ] result URL preserved

[ ] historical data remains meaningful after Project changes

[ ] historical data remains meaningful after Keyword rename

[ ] historical data remains meaningful after domain alias changes
150. Definition of Done — APIs
[ ] manual single Keyword check endpoint works

[ ] manual Project check endpoint works

[ ] Keyword history endpoint works

[ ] Rank Check detail works

[ ] latest rankings endpoint works

[ ] cursor pagination works

[ ] tenant isolation works

[ ] OpenAPI documents contracts
151. Definition of Done — Frontend
[ ] Check Rankings action exists

[ ] Keyword Check Now works

[ ] loading/running state works

[ ] latest positions display

[ ] multiple Tracked Sites display

[ ] Never Checked state works

[ ] Not Found in Top N state works

[ ] Failed state works

[ ] history renders

[ ] check detail renders

[ ] Top N organic results render

[ ] matched Sites are identified

[ ] no fake ranking data is shown

[ ] reload preserves history
152. Definition of Done — Data Integrity
[ ] ranking history is not cascade-deleted accidentally

[ ] Project/Keyword destructive behavior is history-safe

[ ] Tracked Site/Domain destructive behavior is history-safe

[ ] migration from 0004 preserves M3.1 data

[ ] schema drift = none

[ ] timestamps timezone-aware
153. Definition of Done — Quality
[ ] Backend tests pass

[ ] Frontend tests pass

[ ] Provider adapter tests pass

[ ] Fake-provider pipeline tests pass

[ ] Domain matcher tests pass

[ ] Ranking persistence tests pass

[ ] Snapshot tests pass

[ ] Tenant tests pass

[ ] Migration tests pass

[ ] API smoke passes

[ ] Browser verification passes

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

[ ] Docker services healthy
154. SerpApi Real Smoke Definition of Done

This is separate from normal automated checks.

If:

SERPAPI_API_KEY

is available and real provider verification is explicitly requested:

[ ] one real SerpApi request succeeds

[ ] response normalizes correctly

[ ] organic positions parse

[ ] URLs/hostnames parse

[ ] no API key leaks

[ ] exact credit-consuming command is documented

If key is unavailable:

SKIPPED — SERPAPI_API_KEY not configured

must be reported truthfully.

Do not mark it passed.

155. Required Verification Commands

Use repository-standard workflow.

At minimum:

docker compose build
docker compose up --build -d --wait

make check

make auth-smoke
make business-smoke
make tracked-site-smoke

Add:

make ranking-smoke

or equivalent zero-credit deterministic smoke.

Also execute:

migration verification
alembic check

backend production build
frontend production build

browser verification

docker compose ps
156. Real Provider Command

Add a separate command, for example:

RUN_REAL_SERP_SMOKE=true make serpapi-smoke

This command:

must not run from make check
must not run automatically
must clearly consume external quota
157. Expected Backend Structure

Approximately:

backend/app/
├── api/v1/
│   ├── rank_checks.py
│   └── rankings.py
│
├── models/
│   ├── rank_check.py
│   ├── rank_check_result.py
│   └── ranking.py
│
├── repositories/
│   ├── rank_check.py
│   ├── rank_check_result.py
│   └── ranking.py
│
├── schemas/
│   ├── rank_check.py
│   └── ranking.py
│
└── services/
    ├── rank_checks.py
    ├── domain_matching.py
    └── serp/
        ├── base.py
        ├── types.py
        ├── factory.py
        ├── serpapi.py
        └── fake.py

Adapt names to current repository conventions.

158. Expected Frontend Structure

Approximately:

frontend/src/features/rankings/
├── api.ts
├── types.ts
├── ranking-summary.tsx
├── rank-check-history.tsx
├── rank-check-detail.tsx
└── tests...

Reuse current auth and Project query infrastructure.

159. Required Delivery

Create:

docs/verification-milestone-4.md

Include:

implementation summary

architecture

provider abstraction

SerpApi adapter behavior

Project → SerpApi parameter mapping

domain matching rules

database schema

ranking snapshot strategy

history-preservation changes

API changes

frontend changes

files modified
files created

commands actually executed

backend test results
frontend test results

provider adapter tests

domain matcher tests

migration results
schema-drift result

zero-credit ranking smoke result

browser result

production build results

security verification

M1–M3.1 regressions

real SerpApi smoke:
passed / failed / skipped
with exact reason

known limitations

full Definition of Done checklist
160. Known Limitations Expected After M4

Document that M4 intentionally still has:

manual checking only

no scheduler
no workers
no queue

single production provider

Top 10 default depth

no automatic provider failover

no competitor entity

no redirect resolver

no billing/quota enforcement

no charts

no automated daily checks
161. Final Architectural Rule

The complete M4 model should now conceptually become:

User
│
├── Projects
│    │
│    └── Keywords
│          │
│          └── Rank Checks
│                 │
│                 ├── Organic SERP Results
│                 │
│                 └── Rankings
│                        ↓
│                   Tracked Sites
│
└── Tracked Sites
     └── Domain Aliases

Execution:

Project SERP environment
        +
Keyword
        ↓
SerpProvider
        ↓
SerpApiProvider
        ↓
normalized Top N results
        ↓
DomainMatcher
        ↓
TrackedSite matches
        ↓
Ranking History
162. Final Instruction to Codex

Implement Milestone 4 completely according to:

docs/milestone-4-spec.md

Work on top of the CURRENT Milestone 3.1 repository.

Before making changes, inspect:

Milestone 1 specification
Milestone 2 specification
Milestone 3 specification
Milestone 3.1 specification

all verification reports

README

current source
current migrations
current tests

The repository is the source of truth.

Critical architecture rules:

1. User remains the only tenant boundary.

2. Project defines one SERP environment.

3. Keyword remains query-only.

4. Tracked Sites remain user-global.

5. Rank checking must use SerpProvider abstraction.

6. SerpApi is only the first provider adapter.

7. Core Ranking Service must not depend on SerpApi response types.

8. Normal automated tests must consume zero SerpApi credits.

9. Domain matching:
   exact hostname first
   then www equivalence
   never arbitrary subdomain collapsing.

10. Match all active aliases of active Tracked Sites.

11. If the same Site appears multiple times in one SERP,
    persist the best position.

12. Persist normalized Top N organic results.

13. Persist ranking history with configuration snapshots.

14. Do not destroy history through careless cascading deletes.

15. Real SerpApi smoke is explicit/opt-in only.

16. Do not implement workers, scheduler, recurring checks,
    billing, provider failover, or M5 functionality.

Run all required verification before completion.

Create:

docs/verification-milestone-4.md

Do not claim any test, build, browser flow, migration, or real SerpApi verification succeeded unless it actually ran successfully.