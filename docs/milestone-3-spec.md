# SERP SaaS — Milestone 3 Specification
## Project & Keyword Management
1. Objective

Implement Project and Keyword Management for the existing SERP SaaS application.

Milestone 3 is the first milestone that introduces actual SERP-tracking business entities.

The ownership hierarchy is:

Authenticated User
       │
       ├── Project
       │      │
       │      ├── Keyword
       │      ├── Keyword
       │      └── Keyword
       │
       └── Project
              │
              └── Keyword

The authenticated user remains the only tenant boundary.

The system must allow a user to:

Create projects
View their projects
Edit projects
Archive/activate projects
Delete projects

Add keywords
Bulk-add keywords
View keywords
Search/filter keywords
Edit keyword tracking configuration
Activate/pause keywords
Delete keywords

Milestone 3 does NOT perform SERP checks.

It manages only the data required for future SERP tracking.

2. Existing Foundation

Build on the existing Milestone 1 and Milestone 2 repository.

Do not redesign working architecture.

The application already has:

Next.js
TypeScript
App Router
TanStack Query

FastAPI
SQLAlchemy 2 async
Pydantic 2
Alembic
PostgreSQL
Redis

Authentication
Argon2id passwords
JWT access tokens
Refresh-token rotation
HttpOnly refresh cookie
get_current_user

Repository layer
Service layer
API router layer

Docker / Docker Compose
Pytest
Vitest
Ruff
mypy strict
ESLint
TypeScript strict

Milestone 2 verification reported 74 backend tests, 37 frontend tests, successful production builds, authentication smoke verification, browser verification and healthy Docker services.

All existing tests and behavior must remain working.

3. Critical Tenant Rule

The tenant remains:

tenant_id = current_user.id

Do NOT introduce:

Organization
Workspace
Membership
Team
Role
organization_id
workspace_id

Project ownership is:

projects.user_id

Keywords belong to a Project:

keywords.project_id

Keyword ownership is therefore:

Keyword
   ↓
Project
   ↓
User

Never trust a user_id supplied by the browser.

4. Mandatory Authorization Pattern

Every Project query must include the authenticated user.

Correct:

project = await project_repository.get_for_user(
    project_id=project_id,
    user_id=current_user.id,
)

Incorrect:

project = await project_repository.get(project_id)

followed by:

if project.user_id != current_user.id:
    ...

Avoid unrestricted resource retrieval.

Keyword access must similarly prove ownership through the parent project.

Conceptually:

SELECT keywords.*
FROM keywords
JOIN projects
  ON projects.id = keywords.project_id
WHERE keywords.id = :keyword_id
  AND projects.id = :project_id
  AND projects.user_id = :current_user_id;

User A must never be able to access User B's Project or Keyword.

5. Unauthorized Resource Disclosure

For user-owned resources, if a resource:

does not exist, or
exists but belongs to another user

return the same external response.

Recommended:

404 Not Found

Do NOT return:

403 = resource exists but is owned by another user
404 = resource does not exist

because that enables resource enumeration.

6. Explicit Scope

Milestone 3 must implement:

Project database model
Project repository
Project service
Project APIs

Keyword database model
Keyword repository
Keyword service
Keyword APIs

Project defaults for tracking configuration

Single keyword creation
Bulk keyword creation

Keyword normalization
Duplicate prevention

Project search/filter/pagination
Keyword search/filter/pagination

User-level authorization tests

Frontend project list
Frontend project creation
Frontend project editing
Frontend project detail

Frontend keyword table
Frontend single keyword creation
Frontend bulk keyword creation
Frontend keyword editing
Frontend active/pause controls
Frontend deletion

Database migration
API documentation
Architecture documentation
Tests
Browser verification
7. Explicitly Out of Scope

DO NOT implement:

SERP provider API calls
Google scraping
DataForSEO
Serper
SERPROBOT API integration

Rank checking
Ranking history
Ranking tables
SERP result tables

Celery
Workers
Schedulers
Queues
Background jobs

Billing
Subscriptions
Plan limits
Keyword quotas

Competitors
Search volume
CPC
SEO difficulty

Keyword groups
Tags
Folders

CSV file import
CSV export

Email notifications
Reports

Organization
Team
RBAC

Google Search Console integration
Google Analytics integration

These belong to later milestones.

8. Backend Architecture

Extend the existing backend with:

backend/app/
├── api/
│   └── v1/
│       ├── projects.py
│       └── keywords.py
│
├── models/
│   ├── project.py
│   └── keyword.py
│
├── repositories/
│   ├── project.py
│   └── keyword.py
│
├── schemas/
│   ├── project.py
│   └── keyword.py
│
├── services/
│   ├── projects.py
│   └── keywords.py
│
└── ...

Maintain:

Router
   ↓
Service
   ↓
Repository
   ↓
SQLAlchemy
   ↓
PostgreSQL

Do not put SQLAlchemy queries in API routers.

9. Project Model

Create:

projects

Required fields:

id
user_id

name
domain

default_search_engine
default_country_code
default_language_code
default_device
default_location

status

created_at
updated_at

Recommended database types:

id                      UUID PRIMARY KEY
user_id                 UUID NOT NULL FK users.id

name                    VARCHAR(200) NOT NULL
domain                  VARCHAR(253) NOT NULL

default_search_engine   VARCHAR(32) NOT NULL
default_country_code    VARCHAR(2) NOT NULL
default_language_code   VARCHAR(16) NOT NULL
default_device          VARCHAR(16) NOT NULL
default_location        TEXT NULL

status                  VARCHAR(16) NOT NULL

created_at              TIMESTAMPTZ NOT NULL
updated_at              TIMESTAMPTZ NOT NULL

Use:

ON DELETE CASCADE

for:

projects.user_id → users.id

If a user is eventually deleted, owned projects can be deleted with the account.

User deletion itself remains out of scope.

10. Project Status

Support:

active
archived

New projects default to:

active

Archived projects remain visible when explicitly requested but should be visually distinguished.

Do not introduce additional workflow states.

11. Project Name

Validation:

required
trim whitespace
minimum 1 character after trim
maximum 200 characters

Duplicate project names for the same user are allowed.

Example:

Vietnam SEO
Thailand SEO
Client ABC
Main Website
12. Domain

Project domain represents the website whose ranking the user intends to track.

Examples:

example.com
www.example.com
blog.example.com

Store a normalized hostname.

Do not store:

https://example.com/
https://example.com/page

as the canonical database value.

The backend should accept reasonable user input such as:

example.com
www.example.com
https://example.com
https://example.com/

and normalize it to a hostname where safely possible.

Example:

Input:
https://www.Example.com/

Stored:
www.example.com

Reject URLs containing unsupported credentials or malformed hosts.

Do not attempt to reduce subdomains automatically.

For example:

blog.example.com

must remain:

blog.example.com

and must NOT automatically become:

example.com
13. Internationalized Domains

Handle internationalized hostnames safely using standard hostname/IDNA handling where practical.

Do not invent custom domain parsing.

If implementation complexity is excessive, punycode storage is acceptable as long as input/output behavior is documented and tested.

14. Project Tracking Defaults

Each Project contains default SERP tracking configuration.

Required:

default_search_engine
default_country_code
default_language_code
default_device
default_location

Example:

{
  "default_search_engine": "google",
  "default_country_code": "VN",
  "default_language_code": "vi",
  "default_device": "desktop",
  "default_location": null
}

These fields are defaults only.

They are copied into newly created Keywords.

15. Important Default Behavior

Changing Project defaults MUST NOT silently modify existing Keywords.

Example:

Project default country:
VN

Keyword A:
VN

User changes project default:
TH

Result:

Keyword A remains VN

Future Keyword B defaults to TH

Project defaults are creation convenience, not inherited runtime properties.

This prevents historical keyword tracking configuration from changing unexpectedly.

16. Search Engine

For Milestone 3, support:

google

only.

Represent it as a constrained string rather than a PostgreSQL native ENUM if doing so makes future extension simpler.

Future values may include:

bing

but do NOT implement Bing functionality yet.

Invalid values must be rejected.

17. Country Code

Use ISO-style two-character uppercase country codes.

Examples:

VN
TH
US
GB
AU
SG

Normalize:

vn → VN
th → TH

Validate format:

^[A-Z]{2}$

Milestone 3 does not need to maintain a complete database of supported SERP-provider countries.

Provider-specific availability will be handled later.

18. Language Code

Support normalized language identifiers.

Examples:

vi
en
th
en-US

Use a reasonable BCP-47-compatible validation format.

Normalize simple language codes to lowercase where appropriate.

Do not introduce a provider-specific language database yet.

19. Device

Support exactly:

desktop
mobile

New Project default may be:

desktop

unless the frontend explicitly selects otherwise.

Reject unsupported device values.

20. Location

default_location and Keyword location are optional.

Examples:

Bangkok
Ho Chi Minh City
New York, NY

For Milestone 3 this is a human-readable tracking setting only.

Do NOT:

geocode it
call Google Maps
resolve latitude/longitude
validate it against a SERP provider

That belongs to SERP Provider integration.

Normalize leading/trailing and repeated whitespace.

21. Keyword Model

Create:

keywords

Required fields:

id
project_id

keyword
keyword_normalized

search_engine
country_code
language_code
device

location
location_normalized

active

created_at
updated_at

Recommended types:

id                  UUID PRIMARY KEY
project_id          UUID NOT NULL FK projects.id

keyword             TEXT NOT NULL
keyword_normalized  TEXT NOT NULL

search_engine       VARCHAR(32) NOT NULL
country_code        VARCHAR(2) NOT NULL
language_code       VARCHAR(16) NOT NULL
device              VARCHAR(16) NOT NULL

location            TEXT NULL
location_normalized TEXT NOT NULL DEFAULT ''

active              BOOLEAN NOT NULL DEFAULT TRUE

created_at          TIMESTAMPTZ NOT NULL
updated_at          TIMESTAMPTZ NOT NULL

Use:

ON DELETE CASCADE

for:

keywords.project_id → projects.id
22. Why Tracking Settings Live on Keyword

Do NOT make future ranking execution depend dynamically on Project defaults.

Each Keyword must contain its complete tracking configuration.

Correct:

Keyword
├── text
├── search_engine
├── country
├── language
├── device
└── location

Incorrect:

Keyword
├── text
└── read tracking settings from Project every time

The Project settings are only defaults used when creating Keywords.

23. Keyword Validation

Keyword requirements:

required
non-empty after normalization
maximum 512 characters

Reject empty strings such as:

""
"   "
"\n"

Do not impose arbitrary SEO keyword length limits beyond a sensible database/application safety bound.

24. Keyword Normalization

Preserve a user-friendly canonical display string in:

keyword

Use an internal normalized representation:

keyword_normalized

for duplicate detection.

Normalization should include at least:

Unicode normalization
trim leading/trailing whitespace
collapse repeated whitespace
case-fold for duplicate comparison

Example:

"  Best   SEO Tool "
"best seo tool"
"BEST SEO TOOL"

should be considered the same keyword when all tracking configuration is also identical.

Do not modify the user's displayed text more aggressively than necessary.

25. Location Normalization

Use:

location_normalized

for duplicate detection.

Rules:

NULL location → ""
trim whitespace
collapse repeated whitespace
case-fold

Example:

"Bangkok"
" bangkok "
"BANGKOK"

must resolve to the same tracking location for duplicate detection.

Do not expose location_normalized publicly.

26. Keyword Duplicate Definition

A duplicate exists when all these values match:

project_id
keyword_normalized
search_engine
country_code
language_code
device
location_normalized

Example:

seo tool
Google
VN
vi
desktop
<no location>

cannot appear twice within the same Project.

However these are valid separate tracking configurations:

seo tool / VN / desktop
seo tool / VN / mobile
seo tool / TH / desktop
seo tool / VN / desktop / Ho Chi Minh City
27. Database-Level Duplicate Protection

Duplicate prevention MUST exist at PostgreSQL level, not only application level.

Create a composite unique constraint/index equivalent to:

project_id
keyword_normalized
search_engine
country_code
language_code
device
location_normalized

Handle concurrent insert races safely.

Do not return raw IntegrityError details to clients.

28. Indexes

Create appropriate indexes.

At minimum:

projects.user_id
projects(user_id, status)
projects(user_id, created_at)

keywords.project_id
keywords(project_id, active)
keywords(project_id, created_at)
keywords(project_id, keyword_normalized)

and the duplicate-protection unique composite index.

Do not add speculative excessive indexes.

Document index rationale.

29. Project APIs

Implement:

POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}

All routes require authentication.

30. Create Project

Request:

{
  "name": "My Website",
  "domain": "https://example.com/",
  "default_search_engine": "google",
  "default_country_code": "VN",
  "default_language_code": "vi",
  "default_device": "desktop",
  "default_location": null
}

Backend derives:

user_id = current_user.id

Client must not supply user_id.

Successful response:

201 Created

Example:

{
  "id": "...",
  "name": "My Website",
  "domain": "example.com",
  "default_search_engine": "google",
  "default_country_code": "VN",
  "default_language_code": "vi",
  "default_device": "desktop",
  "default_location": null,
  "status": "active",
  "created_at": "...",
  "updated_at": "..."
}

Do not expose user_id unless there is a clear frontend need.

It is unnecessary for normal API consumers.

31. List Projects

Implement:

GET /api/v1/projects

Support:

status
search
limit
cursor

Recommended defaults:

limit = 50
max limit = 200

Default:

status = active

Allow explicitly requesting:

active
archived
all

search may match:

project name
domain

Only return projects belonging to:

current_user.id
32. Pagination

Prefer stable cursor/keyset pagination rather than unbounded offset pagination.

Recommended ordering:

created_at DESC
id DESC

Response concept:

{
  "items": [],
  "next_cursor": "...",
  "has_more": false
}

Cursor format must be opaque to the client.

Do not expose raw SQL concepts through the cursor.

If existing repository conventions strongly favor another safe pagination design, document the deviation.

33. Get Project

Implement:

GET /api/v1/projects/{project_id}

Return only if:

project.user_id == current_user.id

Foreign user:

404

Unknown project:

404

Responses must be externally indistinguishable.

34. Update Project

Implement:

PATCH /api/v1/projects/{project_id}

Allow changing:

name
domain
default_search_engine
default_country_code
default_language_code
default_device
default_location
status

Do not allow:

id
user_id
created_at

Changing Project defaults does not update existing Keywords.

35. Archive Project

Archiving is performed by:

PATCH /api/v1/projects/{project_id}

with:

{
  "status": "archived"
}

Archived projects remain in the database.

Existing Keywords remain unchanged.

Future SERP scheduling will eventually skip archived projects, but scheduler behavior is out of scope now.

36. Delete Project

Implement:

DELETE /api/v1/projects/{project_id}

Deletion is a hard delete for Milestone 3.

Deleting a Project cascades deletion to its Keywords.

Return:

204 No Content

or a consistent documented success response.

The frontend must require an explicit confirmation action.

Do not implement recycle bin or restore.

37. Keyword APIs

Use project-scoped endpoints:

POST   /api/v1/projects/{project_id}/keywords
POST   /api/v1/projects/{project_id}/keywords/bulk

GET    /api/v1/projects/{project_id}/keywords
GET    /api/v1/projects/{project_id}/keywords/{keyword_id}

PATCH  /api/v1/projects/{project_id}/keywords/{keyword_id}
DELETE /api/v1/projects/{project_id}/keywords/{keyword_id}

All require authentication and project ownership.

Avoid creating an unrestricted global route such as:

GET /api/v1/keywords/{keyword_id}

unless ownership is still enforced through an equally strong repository query.

Project-scoped routes are preferred.

38. Create Single Keyword

Request may contain only:

{
  "keyword": "best seo tool"
}

In this case copy Project defaults.

Resulting Keyword:

search_engine = project.default_search_engine
country_code = project.default_country_code
language_code = project.default_language_code
device = project.default_device
location = project.default_location
39. Keyword Configuration Override

Allow optional explicit override at creation:

{
  "keyword": "best seo tool",
  "search_engine": "google",
  "country_code": "TH",
  "language_code": "en",
  "device": "mobile",
  "location": "Bangkok"
}

Missing configuration fields use Project defaults.

Do not partially resolve configuration dynamically later.

Persist the final resolved configuration to the Keyword row.

40. Single Keyword Duplicate

If the complete tracking configuration already exists:

409 Conflict

Use a stable error code such as:

KEYWORD_ALREADY_EXISTS

Do not silently create a duplicate.

41. Bulk Keyword Creation

Implement:

POST /api/v1/projects/{project_id}/keywords/bulk

Primary use case:

User pastes hundreds of keywords

Request:

{
  "keywords": [
    "seo tool",
    "rank tracker",
    "keyword tracker"
  ],
  "search_engine": "google",
  "country_code": "VN",
  "language_code": "vi",
  "device": "desktop",
  "location": null
}

Tracking configuration fields are optional.

When omitted, use Project defaults.

42. Bulk Limits

Maximum:

1000 keyword entries per HTTP request

This is not a subscription quota.

It is only an API request safety limit.

Requests over the limit must be rejected with a clear validation error.

Future plan limits are out of scope.

43. Bulk Input Cleanup

Before insertion:

trim entries
remove empty entries
normalize keywords
deduplicate repeated input entries

Example input:

seo tool
SEO TOOL
 seo   tool
rank tracker

should resolve to two normalized candidate keywords:

seo tool
rank tracker

assuming the same tracking configuration.

44. Bulk Existing Duplicate Behavior

Bulk create should NOT fail the entire operation merely because some keywords already exist.

Instead:

insert new unique keywords
skip existing duplicates
report results

Example response:

{
  "submitted": 5,
  "normalized_unique": 4,
  "created": 3,
  "skipped_duplicates": 1,
  "skipped_empty": 1
}

Include created entities or IDs where reasonable.

Do not leak another user's records.

45. Bulk Transaction and Race Safety

Bulk creation must remain correct under concurrent requests.

Database uniqueness is the final authority.

Handle conflict races gracefully.

Avoid:

SELECT every keyword
then INSERT one-by-one blindly

if a more efficient set-oriented approach is reasonable.

Do not prematurely optimize beyond maintainable SQLAlchemy/PostgreSQL code.

46. List Keywords

Implement:

GET /api/v1/projects/{project_id}/keywords

Support:

search
active
search_engine
country_code
language_code
device
location
limit
cursor

Default:

all active states OR active=true

Choose one behavior and document it consistently.

I recommend:

active=true

by default for normal user workflow.

Allow:

active=true
active=false
active=all

or equivalent documented filter semantics.

47. Keyword Search

search should perform a case-insensitive keyword-text search within the authenticated user's Project.

Do not search globally across other users.

For Milestone 3, PostgreSQL ILIKE or equivalent is acceptable.

Do not add Elasticsearch/OpenSearch.

48. Get Keyword

Implement:

GET /api/v1/projects/{project_id}/keywords/{keyword_id}

The repository query must enforce:

project_id
+
keyword_id
+
project.user_id = current_user.id

Do not separately trust that a keyword belongs to the project from URL parameters.

49. Update Keyword

Implement:

PATCH /api/v1/projects/{project_id}/keywords/{keyword_id}

Allow:

keyword
search_engine
country_code
language_code
device
location
active

Recompute normalization fields when:

keyword
location

changes.

Re-run duplicate validation after configuration changes.

If an update would collide with another Keyword tracking configuration:

409 Conflict
50. Active vs Paused Keyword

Use:

active = true
active = false

Semantics:

true  = eligible for future SERP tracking
false = paused

No scheduler exists yet.

Milestone 3 only persists the state.

Do not delete a Keyword merely because it is paused.

51. Delete Keyword

Implement:

DELETE /api/v1/projects/{project_id}/keywords/{keyword_id}

Hard delete for Milestone 3.

Use a consistent response:

204 No Content

Frontend must request confirmation.

52. API Error Codes

Add consistent codes such as:

PROJECT_NOT_FOUND
INVALID_PROJECT_DOMAIN
INVALID_PROJECT_STATUS

KEYWORD_NOT_FOUND
KEYWORD_ALREADY_EXISTS
INVALID_SEARCH_ENGINE
INVALID_COUNTRY_CODE
INVALID_LANGUAGE_CODE
INVALID_DEVICE
BULK_KEYWORD_LIMIT_EXCEEDED

Continue using the existing error envelope:

{
  "error": {
    "code": "...",
    "message": "..."
  }
}
53. No User Identifier in Write APIs

The following must be rejected or ignored according to strict request-schema behavior:

{
  "user_id": "...",
  "owner_id": "...",
  "organization_id": "..."
}

Prefer strict Pydantic schemas that reject unexpected privileged fields.

Do not allow ownership assignment from frontend input.

54. Database Migration

Create:

0003_projects_keywords

or equivalent next revision.

Do not modify:

0001_foundation
0002_authentication

Migration creates:

projects
keywords
constraints
foreign keys
indexes

Verify:

upgrade head
downgrade -1
upgrade head
alembic check

No schema drift may remain.

55. Migration Downgrade

Downgrading Milestone 3 must remove only Milestone 3 schema objects.

It must NOT remove:

users
refresh_tokens
Milestone 1 baseline

Test this explicitly.

56. Frontend Routes

Add:

/app/projects
/app/projects/new
/app/projects/[projectId]

Optionally:

/app/projects/[projectId]/settings

if useful, but do not unnecessarily fragment the UX.

All require authentication.

57. Authenticated App Navigation

Update /app to provide navigation into Projects.

Example:

SERP SaaS

Projects
Account
Logout

Do not create the full analytics dashboard yet.

58. Project List Page

Implement:

/app/projects

Display:

Project name
Domain
Default country
Default language
Default device
Status
Created date

Provide:

Create Project
Search
Active / Archived filter
Open project

Handle:

loading
empty state
API failure
pagination
59. Empty Project State

For a new user:

No projects yet.

Create your first project to start organizing keywords.

[ Create Project ]

Keep UI original.

Do not copy SERPROBOT branding or proprietary visual assets.

60. Create Project Page

Implement:

/app/projects/new

Fields:

Project name
Domain

Search engine
Country
Language
Device
Location (optional)

Create Project

Defaults should make creating the first Project straightforward.

Do not require company information.

61. Project Detail Page

Implement:

/app/projects/[projectId]

Display project header:

Project name
Domain
Status

Provide access to:

Keywords
Project Settings

The primary content in Milestone 3 is the Keyword table.

62. Keyword Table

Display at minimum:

Keyword
Search engine
Country
Language
Device
Location
Active/Paused
Created
Actions

Provide:

Search
Filters
Pagination
Add keyword
Bulk add

Do not display ranking columns yet.

No fake ranking data.

63. Add Single Keyword UI

Provide form/modal.

Fields:

Keyword

Use project defaults

Optionally allow:

Advanced tracking settings

where user can override:

country
language
device
location

Search engine is currently Google.

Avoid making the basic flow unnecessarily complicated.

64. Bulk Add UI

Provide a textarea.

Example:

seo tool
rank tracker
keyword checker
google position tracker

One keyword per line.

Provide common configuration:

Country
Language
Device
Location

Default these fields from Project.

Maximum:

1000 lines/request

Display result:

97 keywords added
3 duplicates skipped

Do not implement file upload in this milestone.

65. Keyword Editing UI

Allow editing:

keyword text
country
language
device
location
active state

Show duplicate conflicts clearly.

Do not expose:

keyword_normalized
location_normalized
project_id
user_id

as editable fields.

66. Pause/Resume UI

Allow changing:

Active
Paused

without deleting the Keyword.

A simple toggle or action menu is acceptable.

Make the state visually clear.

67. Delete UX

Project deletion must explicitly warn:

Deleting this project will also delete its keywords.

Keyword deletion must also require explicit confirmation.

Do not rely on accidental single-click destructive actions.

68. Frontend API Layer

Extend the existing typed API layer.

Add functions equivalent to:

createProject()
listProjects()
getProject()
updateProject()
deleteProject()

createKeyword()
bulkCreateKeywords()
listKeywords()
getKeyword()
updateKeyword()
deleteKeyword()

All protected requests must reuse the existing authenticated request/session mechanism.

Do not duplicate token refresh logic.

69. TanStack Query

Use TanStack Query for server-state management where appropriate.

Create stable query keys.

Example concept:

["projects"]
["project", projectId]
["project", projectId, "keywords", filters]

After mutations:

invalidate/refetch only relevant queries

Avoid unnecessary full application reloads.

70. API Type Safety

Create frontend TypeScript types for:

Project
ProjectCreate
ProjectUpdate
ProjectListResponse

Keyword
KeywordCreate
KeywordBulkCreate
KeywordBulkResult
KeywordUpdate
KeywordListResponse

Do not use any for API entities.

Maintain strict TypeScript.

71. Backend Repository Requirements

Project repository should expose focused operations such as:

create_for_user(...)
get_for_user(...)
list_for_user(...)
update_for_user(...)
delete_for_user(...)

Keyword repository should expose operations equivalent to:

create_for_project(...)
bulk_create_for_project(...)
get_for_user_project(...)
list_for_user_project(...)
update_for_user_project(...)
delete_for_user_project(...)

Exact names may vary.

Every read/write path must preserve ownership isolation.

72. Avoid N+1 Queries

Do not introduce avoidable N+1 queries.

For example, listing 100 Keywords must not perform:

1 keyword query
+
100 project ownership queries

Ownership should be enforced efficiently through joins/subqueries or prevalidated scoped Project access.

Tests should verify query behavior where practical.

73. Service Layer

Project service handles:

domain normalization
validation
business rules
ownership-aware repository calls

Keyword service handles:

keyword normalization
location normalization
Project-default resolution
duplicate behavior
bulk cleanup
bulk creation
business rules

Do not put these responsibilities into React components or route functions.

74. Transaction Boundaries

Use transactions deliberately.

Project creation:

single transaction

Bulk Keyword insertion:

single logical transaction

Keyword update:

single transaction

Handle uniqueness conflicts cleanly.

Do not leave partial state after failed operations unless partial-success behavior is explicitly part of the bulk contract.

75. Bulk Atomicity

For valid normalized candidates:

new keywords should be inserted consistently
existing duplicates should be skipped intentionally
unexpected database failure should roll back the operation

Do not silently return partial success after an unexpected infrastructure/database failure.

76. Concurrency

Test concurrent duplicate creation.

Example:

Request A → "seo tool"
Request B → "SEO TOOL"

for the same Project/configuration.

Expected final state:

one Keyword row

The database constraint is the final authority.

77. Project Ownership Tests

Create at least two users:

User A
User B

Verify:

A can create A's project
A can read A's project
A can update A's project
A can delete A's project

B cannot read A's project
B cannot update A's project
B cannot delete A's project

Foreign-resource results should use the same external behavior as nonexistent resources.

78. Keyword Ownership Tests

Verify:

User A
  └── Project A
       └── Keyword A

User B
  └── Project B

User B must not be able to access Keyword A by:

guessing keyword_id
guessing project_id
mixing Project B ID + Keyword A ID
supplying user_id
supplying ownership headers
79. Cross-Project Security Test

Within the same user:

Project A
  └── Keyword A

Project B

Calling:

/projects/B/keywords/A

must fail.

The URL's project_id and Keyword's actual parent must both be enforced.

80. Project Tests

At minimum test:

create
read
list
update
archive
reactivate
delete

domain normalization
invalid domains

search
status filter
pagination

different users can use same domain
duplicate project names allowed

defaults persist correctly
changing defaults does not update existing keywords
81. Keyword Tests

At minimum test:

single create using project defaults
single create with overrides

keyword normalization
location normalization

duplicate rejection
different device allowed
different country allowed
different location allowed

edit
pause
resume
delete

search
filters
pagination

bulk creation
bulk input deduplication
existing duplicates skipped
bulk limit enforcement
concurrent duplicate protection
82. Database Tests

Verify:

Project FK
Keyword FK

Project → Keyword cascade deletion
User → Project cascade behavior

unique keyword tracking configuration constraint
required fields
indexes
timezone-aware timestamps

Do not rely solely on service tests.

83. Authorization Security Tests

Explicitly test that the following cannot change ownership:

user_id query parameter
user_id request body
X-User-ID header
owner_id
organization_id

The only authorization identity is:

validated access token
→ current_user.id

Milestone 2 already established this tenant rule; Milestone 3 must preserve it.

84. Authentication Regression

All existing authentication behavior must remain valid:

signup
login
refresh
refresh rotation
logout
/users/me
browser session restoration
disabled-user rejection

Do not modify authentication architecture unless required to fix a proven defect.

85. Logging

Continue structured logging.

Useful events include:

project_created
project_updated
project_archived
project_deleted

keyword_created
keyword_bulk_created
keyword_updated
keyword_deleted

Never log:

Authorization header
cookies
tokens
passwords
secrets

Avoid logging entire large bulk keyword payloads.

Log counts rather than 1000-keyword request bodies.

86. Performance Baseline

Milestone 3 should comfortably support a Project containing:

10,000+ Keywords

without loading all records into memory for a normal list page.

Therefore:

pagination is mandatory
database filtering is mandatory
database search is mandatory

Do not:

keywords = await get_all_keywords()
filtered = [x for x in keywords if ...]

for API listing.

Filtering/pagination must occur in PostgreSQL.

87. API Request Limits

Bulk input maximum:

1000 keywords/request

Keyword list maximum response:

200 rows/request

Project list maximum response:

200 rows/request

Enforce limits server-side.

88. Time Handling

Continue using timezone-aware UTC timestamps.

Use:

TIMESTAMPTZ

for:

created_at
updated_at

Do not store naive local timestamps.

89. OpenAPI

Document all new endpoints.

Swagger must correctly show:

Bearer authentication requirement
request schemas
response schemas
pagination parameters
filter parameters
error responses

Do not expose internal normalization fields unless intentionally part of response schemas.

90. Documentation

Create:

docs/api/projects.md
docs/api/keywords.md
docs/architecture/project-keyword-model.md

or equivalent.

Document:

User → Project → Keyword ownership

Project defaults

Keyword resolved tracking settings

Duplicate definition

Bulk creation behavior

Pagination

Tenant security

Hard-delete behavior
91. README

Update README with:

Project functionality
Keyword functionality
new routes
new migration
bulk keyword workflow
test commands

Preserve Milestone 1 and Milestone 2 documentation.

92. Migration Verification

Execute:

make db-upgrade
make db-downgrade
make db-upgrade

Then:

docker compose exec -T backend alembic check

Expected:

No new upgrade operations detected.

Do not declare Milestone 3 complete with schema drift.

93. Production Builds

Both must continue to build.

Backend production image:

PASS

Frontend production build:

PASS

New frontend routes must build successfully:

/app/projects
/app/projects/new
/app/projects/[projectId]
94. API Smoke Test

Create or extend an executable smoke test.

Required logical flow:

register User A
register User B

User A
  ↓
create Project A
  ↓
add Keyword A
  ↓
bulk-add Keywords
  ↓
list Keywords
  ↓
update Keyword
  ↓
pause Keyword

User B
  ↓
attempt Project A access
  ↓
404

User B
  ↓
attempt Keyword A access
  ↓
404

User A
  ↓
delete Keyword
  ↓
delete Project

Smoke test must operate against the real running API/PostgreSQL stack.

95. Browser Verification

Perform real-browser verification if the existing verification environment supports it.

Required journey:

Login
  ↓
Projects
  ↓
Create Project
  ↓
Open Project
  ↓
Add Keyword
  ↓
Bulk add Keywords
  ↓
Search/filter
  ↓
Edit Keyword
  ↓
Pause Keyword
  ↓
Reload browser
  ↓
state still correct
  ↓
Delete Keyword
  ↓
Delete Project

Verify:

no browser exceptions
no unexpected network failures
no CORS errors
no authentication loops
96. UI Scope

UI should be functional and clean.

Do not spend excessive Milestone 3 effort on:

animations
marketing graphics
advanced charts
pixel-perfect SERPROBOT cloning
complex design system work

Business functionality and security are higher priority.

97. No Fake SERP Data

Do NOT show:

Position
Rank change
Top 10
Search volume
Visibility
Ranking chart

using fake/generated values.

These fields do not exist until later milestones.

The Keyword table should only display real Milestone 3 data.

98. Existing Milestone Regression

All Milestone 1 and Milestone 2 checks must continue passing.

At minimum:

health endpoints
PostgreSQL health
Redis health
OpenAPI
authentication
refresh rotation
logout
protected routes
frontend authentication restoration
Docker workflow
migrations
lint
formatting
strict typing
production builds

Milestone 2's final report states these were all working before Milestone 3 begins.

99. Definition of Done — Database
[ ] projects table exists
[ ] keywords table exists
[ ] UUID IDs are used
[ ] projects.user_id FK exists
[ ] keywords.project_id FK exists
[ ] cascade behavior is correct
[ ] tracking-configuration uniqueness is DB-enforced
[ ] required indexes exist
[ ] all timestamps are timezone-aware
[ ] migration upgrade works
[ ] migration downgrade works
[ ] migration re-upgrade works
[ ] alembic check reports no drift
100. Definition of Done — Tenant Security
[ ] User is still the only tenant boundary
[ ] No Organization model exists
[ ] No organization_id exists

[ ] All Project queries are user-scoped
[ ] All Keyword queries are ownership-scoped through Project

[ ] Cross-user Project access fails
[ ] Cross-user Keyword access fails
[ ] Cross-project Keyword access fails

[ ] Client-provided user_id cannot influence authorization
[ ] Foreign and nonexistent resources are externally indistinguishable
101. Definition of Done — Projects
[ ] Create Project works
[ ] List Projects works
[ ] Get Project works
[ ] Update Project works
[ ] Archive Project works
[ ] Reactivate Project works
[ ] Delete Project works

[ ] Domain normalization works
[ ] Search works
[ ] Status filter works
[ ] Pagination works

[ ] Project defaults work
[ ] Updating defaults does not modify existing Keywords
102. Definition of Done — Keywords
[ ] Single Keyword creation works
[ ] Project defaults are copied at creation
[ ] Per-keyword override works

[ ] Keyword normalization works
[ ] Location normalization works

[ ] Duplicate protection works
[ ] Concurrent duplicate protection works

[ ] Bulk creation works
[ ] Bulk input deduplication works
[ ] Existing duplicate skipping works
[ ] 1000-keyword request limit works

[ ] List works
[ ] Search works
[ ] Filters work
[ ] Pagination works

[ ] Get works
[ ] Update works
[ ] Pause works
[ ] Resume works
[ ] Delete works
103. Definition of Done — Frontend
[ ] Projects navigation exists

[ ] Project list renders
[ ] Project empty state works
[ ] Project creation works
[ ] Project editing works
[ ] Project archive/reactivation works
[ ] Project deletion confirmation works

[ ] Project detail renders

[ ] Keyword table renders
[ ] Single keyword addition works
[ ] Bulk keyword textarea works
[ ] Bulk result counts are displayed

[ ] Keyword search works
[ ] Keyword filtering works
[ ] Pagination works

[ ] Keyword edit works
[ ] Pause/resume works
[ ] Keyword deletion confirmation works

[ ] Browser reload preserves authenticated session
104. Definition of Done — Quality
[ ] Backend tests pass
[ ] Frontend tests pass
[ ] Database integration tests pass
[ ] Ownership security tests pass
[ ] API smoke passes
[ ] Real-browser verification passes

[ ] Ruff passes
[ ] Ruff formatting passes
[ ] mypy strict passes

[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes

[ ] npm audit remains acceptable
[ ] production frontend build passes
[ ] production backend build passes

[ ] Milestone 1 regression passes
[ ] Milestone 2 regression passes
105. Required Verification Commands

Before completion, run the repository's actual workflow.

At minimum:

docker compose build
docker compose up --build -d --wait

make check

make db-upgrade
make db-downgrade
make db-upgrade

docker compose exec -T backend alembic check
docker compose ps

Also execute:

Project/Keyword API smoke test
real browser Project/Keyword flow
backend production build
frontend production build

Use the existing repository tooling where possible.

106. Required Codex Delivery

Create:

docs/verification-milestone-3.md

It must include:

Implementation summary

Architecture changes

Database schema/migration details

Normalization rules

Duplicate rules

Tenant isolation implementation

Bulk keyword implementation

Files created
Files modified

Commands actually executed

Backend test result
Frontend test result

Migration result
Schema-drift result

Docker result
Production build result

API smoke result
Browser verification result

Security test coverage

Milestone 1 regression
Milestone 2 regression

Known limitations

Full Definition of Done checklist

Do not claim successful checks that were not actually run.

107. Deferred Features

Explicitly document that these remain deferred:

SERP retrieval
Ranking history
Rank checks
SERP providers
Google scraping

Queue
Workers
Scheduler

Keyword scheduling frequency

Billing
Subscriptions
Usage limits

Competitors
Tags/groups

CSV import/export

Notifications
Reports
Search volume

Email verification
Password reset
OAuth
MFA

Organizations
Teams
Roles
Permissions
108. Future Milestone Compatibility

Milestone 3 must prepare cleanly for Milestone 4:

SERP Provider + Ranking Engine

Future conceptual flow:

User
 ↓
Project
 ↓
Keyword
 ↓
SERP Check
 ↓
Ranking

Every Keyword already contains the complete request configuration needed by the future provider:

keyword
search_engine
country_code
language_code
device
location

Therefore Milestone 4 should not need to reinterpret Project defaults.

109. Important Future Ranking Rule

Do not create ranking tables now.

However, document this future principle:

When ranking history is introduced, a ranking record should preserve enough context to understand what tracking configuration produced the result.

This matters if the user later changes:

country
language
device
location

on an existing Keyword.

Do not prematurely solve this by introducing additional Milestone 4 tables now.

110. Implementation Order

Recommended Codex sequence:

1. Read Milestone 1–3 specifications
2. Read README
3. Read verification reports
4. Inspect actual current source

5. Design Project model/schema
6. Design Keyword model/schema
7. Add normalization utilities
8. Add migration

9. Add Project repository
10. Add Project service
11. Add Project schemas
12. Add Project routes

13. Add Keyword repository
14. Add Keyword service
15. Add Keyword schemas
16. Add Keyword routes

17. Implement bulk create
18. Implement filters/pagination

19. Add repository tests
20. Add service tests
21. Add API tests
22. Add tenant-isolation tests
23. Add concurrency tests

24. Implement frontend Project API
25. Implement Project pages

26. Implement Keyword API client
27. Implement Keyword table
28. Implement single-add UI
29. Implement bulk-add UI
30. Implement edit/pause/delete UI

31. Add frontend tests

32. Run migration cycle
33. Run schema-drift check

34. Run all M1/M2/M3 tests
35. Run lint/type checks

36. Run API smoke test
37. Run browser verification

38. Build production frontend/backend

39. Update README/docs
40. Create verification-milestone-3.md
111. Final Instruction to Codex

Implement Milestone 3 completely according to:

docs/milestone-3-spec.md

Work directly on the existing Milestone 2 repository.

Before changing code, inspect:

docs/milestone-1-spec.md
docs/milestone-2-spec.md
docs/verification.md
docs/verification-milestone-2.md
README.md
existing source code
existing migrations
existing tests

The actual repository is the source of truth.

Do not rewrite correct Milestone 1 or Milestone 2 functionality unnecessarily.

The critical architecture rule remains:

Tenant = authenticated user

Project ownership:

projects.user_id = current_user.id

Keyword ownership:

keyword → project → current_user.id

Never trust a client-supplied user identifier.

Do not introduce:

Organization
Workspace
Membership
Team
Role
organization_id

Do not implement Milestone 4 functionality.

Specifically, do NOT:

call SERP providers
scrape Google
retrieve rankings
create fake rankings
schedule checks
create workers
create ranking history

Before declaring completion:

run all tests
run migration upgrade/downgrade/upgrade
run alembic check
run lint
run formatting checks
run mypy strict
run TypeScript strict
run production builds
run Project/Keyword API smoke
run real-browser Project/Keyword verification
run Milestone 1 regression
run Milestone 2 regression
verify Docker services are healthy

Fix actual failures before completion.

Create:

docs/verification-milestone-3.md

Only report a verification as successful if it was actually executed successfully.