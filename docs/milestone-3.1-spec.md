# SERP SaaS — Milestone 3.1 Specification
## Project Refactor + Tracked Sites & Domain Alias Registry
1. Objective

Refactor the current Milestone 3 Project/Keyword model before introducing SERP retrieval and ranking history.

The new conceptual architecture is:

Authenticated User
│
├── Projects
│    │
│    ├── Project A
│    │    ├── SERP environment
│    │    └── Keywords
│    │
│    └── Project B
│         ├── SERP environment
│         └── Keywords
│
└── Tracked Sites
     │
     ├── Site A
     │    ├── old-domain.com
     │    ├── redirected-domain.com
     │    └── current-domain.com
     │
     └── Site B
          └── another-domain.com

The core responsibilities are:

Project
=
Which SERP environment should be monitored?

Keyword
=
Which search queries should be executed?

Tracked Site
=
Which logical SEO websites/assets belong to the user?

Tracked Domain
=
Which current or historical domain aliases belong to a Tracked Site?

Future ranking behavior will conceptually be:

Project configuration
        +
Keyword
        ↓
SERP Provider
        ↓
Organic Results
        ↓
Domain Matcher
        ↓
User's Tracked Domains
        ↓
Tracked Sites
        ↓
Ranking History

SERP retrieval and ranking history are NOT part of Milestone 3.1.

2. Existing State

Build directly on the completed Milestone 3 implementation.

The current application already provides:

Authentication
User-level tenancy

Projects
Keywords

Project CRUD
Keyword CRUD
Bulk keyword creation

Cursor pagination
Search/filtering

Docker
PostgreSQL
Redis

Backend/frontend tests
Production builds
Browser verification

The current implementation scopes Project access using current_user.id and Keyword access through the exact user-owned Project.

Preserve that security architecture.

3. Critical New Domain Model

After Milestone 3.1 the model MUST be:

User
│
├── Project
│    ├── name
│    ├── search_engine
│    ├── country_code
│    ├── language_code
│    ├── device
│    ├── location
│    ├── status
│    │
│    └── Keywords
│         ├── keyword
│         ├── keyword_normalized
│         └── active
│
└── TrackedSite
     ├── name
     ├── status
     │
     └── TrackedDomains
          ├── domain
          ├── is_primary
          └── active
4. Project No Longer Represents a Website

Remove the conceptual relationship:

Project → domain

Project must no longer have a target domain.

A Project represents:

A collection of keywords monitored under one SERP environment.

Example:

Project:
Vietnam Desktop

Search engine: Google
Country: VN
Language: vi
Device: desktop
Location: Ho Chi Minh City

Keywords:
casino online
game bài
nhà cái uy tín

Do NOT require a domain when creating a Project.

5. Project Tracking Configuration

Rename the current Project fields:

default_search_engine
default_country_code
default_language_code
default_device
default_location

to:

search_engine
country_code
language_code
device
location

They are no longer defaults.

They are the definitive SERP environment for the Project.

6. Project Database Model

Final conceptual schema:

projects
──────────────────────────────
id
user_id

name

search_engine
country_code
language_code
device
location

status

created_at
updated_at

Recommended types:

id              UUID PRIMARY KEY
user_id         UUID NOT NULL FK users.id

name            VARCHAR(200) NOT NULL

search_engine   VARCHAR(32) NOT NULL
country_code    VARCHAR(2) NOT NULL
language_code   VARCHAR(16) NOT NULL
device          VARCHAR(16) NOT NULL
location        TEXT NULL

status          VARCHAR(16) NOT NULL

created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL

Remove Project:

domain

from the application model and public APIs.

7. Keyword Simplification

Keywords now inherit the Project SERP environment at runtime.

Do NOT store tracking configuration on Keyword.

Final Keyword model:

keywords
──────────────────────────────
id
project_id

keyword
keyword_normalized

active

created_at
updated_at

Remove:

search_engine
country_code
language_code
device
location
location_normalized

from Keyword.

8. New Keyword Uniqueness Rule

Keyword uniqueness becomes:

project_id
+
keyword_normalized

Create a PostgreSQL unique constraint/index equivalent to:

UNIQUE (project_id, keyword_normalized)

Example:

Project A

seo tool
SEO TOOL
 Seo   Tool

must resolve to one Keyword.

9. Project Configuration Controls All Keywords

If Project configuration changes:

country_code:
VN → TH

all Keywords in that Project use:

TH

for future SERP checks.

Do not copy configuration into Keyword rows.

This is intentional.

10. Historical Ranking Consideration

No ranking history exists yet.

When future Milestone 4 introduces ranking records, each rank check must snapshot the actual SERP configuration used at execution time.

Therefore changing:

country
language
device
location

later must not make historical ranking results ambiguous.

Do NOT implement ranking snapshot tables in M3.1.

Only document this requirement for M4.

11. Integrated Add Project Flow

Refactor Project creation so a user can create:

Project
+
one or many Keywords

in one operation.

Frontend Add Project form:

Project Name

Search Engine
Country
Language
Device
Location

Keywords
────────
keyword 1
keyword 2
keyword 3
...

No domain field.

12. New Create Project API

Use:

POST /api/v1/projects

Example request:

{
  "name": "Vietnam Desktop",
  "search_engine": "google",
  "country_code": "VN",
  "language_code": "vi",
  "device": "desktop",
  "location": "Ho Chi Minh City",
  "keywords": [
    "casino online",
    "game bài",
    "nhà cái uy tín"
  ]
}

The client must NOT send:

domain
user_id
owner_id
organization_id
default_search_engine
default_country_code
default_language_code
default_device
default_location

Strictly reject obsolete/privileged fields.

13. Project Creation Must Be Atomic

Create Project and initial Keywords in one logical transaction.

Conceptually:

validate
   ↓
normalize keyword input
   ↓
BEGIN
   ↓
create Project
   ↓
bulk insert Keywords
   ↓
COMMIT

Unexpected keyword persistence failure must rollback Project creation.

Do not leave an empty half-created Project because the initial Keyword operation failed.

14. Initial Keyword Requirement

New Project creation should require at least:

1 valid keyword

Maximum:

1000 submitted keywords

per create request.

Clean:

empty entries
duplicate normalized entries
leading/trailing whitespace
repeated whitespace

before insertion.

15. Create Project Result

Response should include Project and useful keyword counts.

Example:

{
  "project": {
    "id": "...",
    "name": "Vietnam Desktop",
    "search_engine": "google",
    "country_code": "VN",
    "language_code": "vi",
    "device": "desktop",
    "location": "Ho Chi Minh City",
    "status": "active"
  },
  "keywords": {
    "submitted": 4,
    "normalized_unique": 3,
    "created": 3,
    "skipped_empty": 1
  }
}

Exact shape may be improved, but keep it typed and documented.

16. Existing Keyword Creation APIs

Keep:

POST /api/v1/projects/{project_id}/keywords
POST /api/v1/projects/{project_id}/keywords/bulk

but simplify payloads.

Single:

{
  "keyword": "best seo tool"
}

Bulk:

{
  "keywords": [
    "seo tool",
    "rank tracker",
    "keyword checker"
  ]
}

Do NOT accept per-keyword:

search_engine
country_code
language_code
device
location
17. Keyword Update

Keyword PATCH may only modify:

keyword
active

Do not allow Keyword-level SERP configuration.

Recompute:

keyword_normalized

when keyword text changes.

Duplicate collision:

409 Conflict
18. Project Update

Project PATCH may modify:

name
search_engine
country_code
language_code
device
location
status

Changing SERP settings affects all Keywords for future checks.

Frontend must make this clear:

These tracking settings apply to every keyword in this project.
19. Tracked Site Concept

Introduce:

TrackedSite

A Tracked Site represents one logical SEO asset whose domain may change over time.

Example:

Tracked Site:
SEO Site A

Domains:
old-domain.com
redirect-domain.com
new-domain.com

These domains all represent the same logical SEO site.

20. Why Tracked Sites Exist

The design must explicitly support this use case:

old-domain.com
      ↓ 301
domain-b.com
      ↓ 301
domain-c.com

The user should NOT need to:

create another Project
re-enter Keywords
re-enter SERP configuration

Instead:

Tracked Site A
├── old-domain.com
├── domain-b.com
└── domain-c.com

Project and Keyword configuration remain untouched.

21. Tracked Site Database Model

Create:

tracked_sites

Recommended schema:

id
user_id

name
status

created_at
updated_at

Types:

id          UUID PRIMARY KEY
user_id     UUID NOT NULL

name        VARCHAR(200) NOT NULL
status      VARCHAR(16) NOT NULL

created_at  TIMESTAMPTZ NOT NULL
updated_at  TIMESTAMPTZ NOT NULL

Foreign key:

tracked_sites.user_id
→ users.id
ON DELETE CASCADE

Statuses:

active
archived
22. Tracked Domain Database Model

Create:

tracked_domains

Recommended schema:

id
user_id
tracked_site_id

domain

is_primary
active

created_at
updated_at

Recommended types:

id               UUID PRIMARY KEY

user_id          UUID NOT NULL
tracked_site_id  UUID NOT NULL

domain           VARCHAR(253) NOT NULL

is_primary       BOOLEAN NOT NULL
active           BOOLEAN NOT NULL

created_at       TIMESTAMPTZ NOT NULL
updated_at       TIMESTAMPTZ NOT NULL
23. Domain Ownership Constraint

Different users must be allowed to track the same domain.

Therefore this is valid:

User A → example.com
User B → example.com

But one user must not assign the same normalized domain to multiple Tracked Sites.

Database uniqueness:

UNIQUE (
    user_id,
    domain
)

where domain is already stored in normalized canonical hostname form.

24. Tracked Domain Tenant Integrity

Prefer enforcing at database level that:

tracked_domains.user_id

matches:

tracked_sites.user_id

A composite FK or equivalent robust constraint is acceptable.

Do not rely purely on frontend input.

25. Domain Normalization

Use the existing safe domain/IDNA normalization logic where possible.

Accept:

example.com
EXAMPLE.COM
https://example.com/
https://example.com/some-page

and extract/store canonical hostname:

example.com

At minimum:

lowercase
remove scheme
remove path
remove credentials
remove port
remove trailing dot
IDNA normalize

Reject malformed hostnames.

26. Do Not Collapse Subdomains

Do NOT automatically convert:

blog.example.com

into:

example.com

Store exact normalized hostname.

Do not strip arbitrary subdomains.

27. www Handling

Do not destroy the exact hostname information.

For M3.1:

www.example.com

and:

example.com

may remain distinct aliases.

Future M4 Domain Matcher may support www equivalence.

Do not implement SERP matching now.

28. Domain Alias Meaning

Every domain attached to a Tracked Site is an alias of that logical site.

Example:

TrackedSite #1

old.com
new.com
newer.com

Future ranking matching may treat any active alias as:

TrackedSite #1
29. Primary Domain

Each active Tracked Site must have exactly one:

is_primary = true

domain.

The primary domain represents the user's current canonical/preferred domain.

Historical aliases can remain:

active = true
is_primary = false

so future SERP matching can still recognize them.

30. Primary Domain Invariants

When a Site is created:

at least one domain required
exactly one primary domain required

When a different domain becomes primary:

BEGIN
unset old primary
set new primary
COMMIT

There must never be two primary aliases for one Site.

31. Primary Domain Cannot Be Inactive

Require:

is_primary = true
→ active = true

Do not allow deactivating the primary domain until another domain is promoted.

32. Primary Domain Deletion

Do not silently choose another domain.

If user attempts to delete the current primary while other aliases exist:

409 Conflict

Error:

PRIMARY_DOMAIN_REPLACEMENT_REQUIRED

User must first make another domain primary.

Do not allow deleting the only domain of an active Site.

33. Create Tracked Site API

Implement:

POST /api/v1/tracked-sites

Example:

{
  "name": "SEO Site A",
  "primary_domain": "new-domain.com",
  "aliases": [
    "old-domain.com",
    "redirect-domain.com"
  ]
}

Backend:

normalize domains
deduplicate
check user-level uniqueness
create site
create primary
create aliases

all within one transaction.

34. Create Tracked Site Response

Example conceptual response:

{
  "id": "...",
  "name": "SEO Site A",
  "status": "active",
  "primary_domain": "new-domain.com",
  "domains": [
    {
      "id": "...",
      "domain": "new-domain.com",
      "is_primary": true,
      "active": true
    },
    {
      "id": "...",
      "domain": "old-domain.com",
      "is_primary": false,
      "active": true
    }
  ]
}
35. Tracked Site APIs

Implement:

POST   /api/v1/tracked-sites
GET    /api/v1/tracked-sites
GET    /api/v1/tracked-sites/{site_id}
PATCH  /api/v1/tracked-sites/{site_id}
DELETE /api/v1/tracked-sites/{site_id}

All require authentication.

All repository operations must be scoped by:

current_user.id
36. Domain Alias APIs

Implement:

POST   /api/v1/tracked-sites/{site_id}/domains
PATCH  /api/v1/tracked-sites/{site_id}/domains/{domain_id}
DELETE /api/v1/tracked-sites/{site_id}/domains/{domain_id}

Create request:

{
  "domain": "new-domain.com",
  "make_primary": false
}
37. Promote Domain to Primary

Support:

PATCH /api/v1/tracked-sites/{site_id}/domains/{domain_id}

Example:

{
  "is_primary": true
}

Must transactionally:

unset current primary
activate target if necessary
set target primary
38. Domain Activation

Allow:

active = true
active = false

Future M4 should only match:

active Tracked Sites
+
active Tracked Domains

No matching is implemented now.

39. Tracked Site Archive

Allow:

status = archived

Archived Site remains stored.

Future M4 should ignore archived Sites.

Do not delete aliases merely because a Site is archived.

40. Delete Tracked Site

Hard delete is acceptable in M3.1 because ranking history does not exist yet.

Deleting the Site may cascade its aliases.

Frontend must require explicit confirmation.

Future milestones may change this to soft deletion once ranking history exists.

41. No Project ↔ Tracked Site Relation Yet

Do NOT add:

project_tracked_sites

in M3.1.

Current rule:

All active Tracked Sites belonging to the user are eligible for future matching against all of that user's Projects.

Conceptually:

User's Project SERP
       ↓
all active user Tracked Domains

This intentionally keeps setup simple.

42. Future Scalability

If users later manage many unrelated sites, a future many-to-many table may be introduced:

project_tracked_sites

Do not implement it now.

43. Project Migration

Create a new Alembic revision such as:

0004_project_refactor_tracked_sites

Do NOT rewrite:

0001_foundation
0002_authentication
0003_projects_keywords
44. Existing Project Domain Migration

Before dropping projects.domain, preserve existing domains in the new registry.

For every distinct:

(user_id, normalized project domain)

create one:

TrackedSite

with one primary TrackedDomain.

Because the old system contains no alias relationship information, do NOT attempt to infer which different domains are 301 aliases of the same site.

Recommended generated Site name:

normalized domain

Example:

projects.domain = example.com

becomes:

TrackedSite
name = "example.com"

TrackedDomain
domain = "example.com"
primary = true
45. Duplicate Existing Domains

If the same user's domain appears in multiple Projects:

User A

Project 1 → example.com
Project 2 → example.com

migration creates:

one TrackedSite
one TrackedDomain

not duplicates.

46. Existing Keyword Configuration Migration

Current Milestone 3 allows Keyword-level configuration overrides.

The new schema does not.

The migration MUST preserve semantic tracking configurations rather than blindly deleting them.

For each existing Project, group Keywords by:

search_engine
country_code
language_code
device
normalized location
47. Configuration Group Migration

If all Keywords use the same Project/default configuration:

keep one Project
move no Keywords
rename Project configuration columns

Simple case.

48. Existing Override Case

Example existing data:

Project A default:
VN / vi / desktop

Keywords:
A → VN / vi / desktop
B → VN / vi / desktop
C → TH / en / mobile
D → TH / en / mobile

New schema must become:

Project A
VN / vi / desktop
├── A
└── B

Project A — TH/en/mobile
TH / en / mobile
├── C
└── D

Do not discard configuration differences.

49. Choosing the Original Project Group

For an existing Project:

If a Keyword group matches the old Project defaults, keep that group in the original Project.
Otherwise, if Keywords exist, keep the largest configuration group in the original Project.
Ties must be resolved deterministically.
Create additional Projects for other configuration groups.
Preserve the same user_id and status.
50. Derived Project Naming

Use a deterministic readable suffix.

Example:

Original:
Client SEO

Derived:
Client SEO — TH/en/mobile

If location is material:

Client SEO — TH/en/mobile/Bangkok

Respect Project name maximum length.

Duplicate Project names remain allowed.

51. Empty Existing Projects

If an existing Project has zero Keywords:

keep the Project

and convert its old default settings to the new Project-level configuration.

Do not delete it automatically.

52. Remove Old Keyword Configuration

Only after configuration groups are safely migrated:

remove Keyword fields:

search_engine
country_code
language_code
device
location
location_normalized

Replace existing unique constraint with:

UNIQUE(project_id, keyword_normalized)
53. Migration Safety

This is a semantic model transformation.

Do NOT implement a fake or misleading downgrade that cannot restore the original Project-domain/Keyword-override relationships.

The current project is not production-deployed; Milestone 3 verification confirms production hosting/orchestration has not been deployed.

Therefore a forward semantic migration is acceptable for this development stage.

Document clearly if revision 0004 is intentionally irreversible.

Verification must at minimum prove:

fresh base → head
0003 fixture → 0004
data preservation
no schema drift

If Codex can implement a genuinely lossless downgrade, it may do so.

Do not fabricate one merely to satisfy a test.

54. Migration Fixture Test

Create a realistic pre-M3.1 fixture containing:

two users

multiple Projects

duplicate Project domains

Keyword defaults

Keyword configuration overrides

same Keyword text under different tracking configurations

Upgrade it through 0004.

Verify:

Tracked Sites correctly created
duplicate domains deduplicated per user

Projects correctly split
Keywords remain present

Project SERP configurations preserved

Keyword configurations represented by Project placement

new uniqueness rules hold

This migration test is mandatory.

55. Project List Refactor

Remove domain from Project list.

Display:

Project Name
Search Engine
Country
Language
Device
Location
Keyword Count
Status

Do not display target domain.

56. Add Project Page

Refactor:

/app/projects/new

into an integrated form.

Suggested UI:

Create Project
────────────────────────

Project Name
[ Vietnam Desktop ]

Search Engine
[ Google ]

Country
[ Vietnam ]

Language
[ Vietnamese ]

Device
[ Desktop ]

Location
[ Ho Chi Minh City ]


Keywords
────────────────────────

One keyword per line:

┌────────────────────────────┐
│ casino online              │
│ game bài                   │
│ nhà cái uy tín             │
│ casino trực tuyến          │
└────────────────────────────┘

4 keywords

[ Create Project ]
57. Add Project UX Requirements

Support:

keyword count
duplicate cleanup
empty-line cleanup
validation messages
loading state
backend failure
successful creation

After successful creation:

redirect to Project detail
58. Project Detail Refactor

Project header displays:

name
SERP environment
status

Example:

Vietnam Desktop

Google
Vietnam
Vietnamese
Desktop
Ho Chi Minh City

No Project domain.

59. Keyword Table Refactor

Keyword table only needs:

Keyword
Status
Created
Actions

Optionally:

Updated

Remove:

Search engine
Country
Language
Device
Location

from every Keyword row because they are Project-level values.

60. Keyword Add UI

Single Add Keyword:

Keyword
[                        ]

[ Add Keyword ]

No advanced configuration.

Bulk Add:

one keyword per line

No country/language/device/location inputs.

61. Project Setting UI

Editing SERP environment must display a warning:

These settings apply to every keyword in this project
and will be used for future rank checks.

No Keyword override UI.

62. Tracked Sites Frontend

Add navigation:

Projects
Tracked Sites
Account

Route:

/app/tracked-sites
63. Tracked Site List UI

Display:

Site Name
Primary Domain
Domain Alias Count
Status

Actions:

Open
Archive / Reactivate
Delete

Provide:

Add Tracked Site
64. Add Tracked Site UI

Example:

Add Tracked Site
────────────────────────

Site Name
[ SEO Site A ]

Primary Domain
[ new-domain.com ]

Previous / Alias Domains
┌─────────────────────────┐
│ old-domain.com          │
│ second-domain.com       │
└─────────────────────────┘

[ Create Site ]

Aliases are optional.

Primary domain is required.

65. Tracked Site Detail

Example:

SEO Site A

Primary:
new-domain.com


Domain aliases
────────────────────────

new-domain.com
PRIMARY
ACTIVE

old-domain.com
ACTIVE

older-domain.com
ACTIVE


[ Add Domain ]

Allow:

make primary
activate
deactivate
delete

subject to invariants.

66. 301 User Flow

The frontend must support this workflow without touching Project:

SEO Site A

old-domain.com
      ↓ 301
new-domain.com

User:

opens Tracked Site
↓
adds new-domain.com
↓
makes new-domain.com primary

Result:

old-domain.com
active alias

new-domain.com
active primary

No Project or Keyword modification occurs.

67. Tracked Site Tenant Security

Every query must be user-scoped.

Correct concept:

site = await tracked_site_repository.get_for_user(
    site_id=site_id,
    user_id=current_user.id,
)

Domain operations must verify:

site
+
domain
+
current_user.id
68. Cross-User Domain Rules

User A cannot:

read
modify
move
delete

User B's Tracked Sites or domains.

Foreign and nonexistent IDs should be externally indistinguishable:

404
69. Same Domain Different Users

Explicitly test:

User A
→ example.com

User B
→ example.com

Both must succeed.

70. Same Domain Same User

Explicitly test:

User A
Site A → example.com

User A
Site B → example.com

Second operation must fail:

409 Conflict

Stable error:

DOMAIN_ALREADY_TRACKED
71. Relevant Error Codes

Add stable errors such as:

TRACKED_SITE_NOT_FOUND
TRACKED_DOMAIN_NOT_FOUND

DOMAIN_ALREADY_TRACKED
INVALID_DOMAIN

PRIMARY_DOMAIN_REQUIRED
PRIMARY_DOMAIN_REPLACEMENT_REQUIRED
PRIMARY_DOMAIN_MUST_BE_ACTIVE

PROJECT_NOT_FOUND
KEYWORD_NOT_FOUND
KEYWORD_ALREADY_EXISTS

PROJECT_REQUIRES_KEYWORDS
PROJECT_KEYWORD_LIMIT_EXCEEDED

Continue using existing error envelope.

72. Repository Architecture

Maintain:

Router
 ↓
Service
 ↓
Repository
 ↓
SQLAlchemy/PostgreSQL

Add:

tracked_site repository
tracked_domain repository

Do not put direct SQLAlchemy queries in route handlers.

73. Backend Structure

Expected additions/refactors approximately:

backend/app/
├── models/
│   ├── tracked_site.py
│   └── tracked_domain.py
│
├── repositories/
│   ├── tracked_site.py
│   └── tracked_domain.py
│
├── schemas/
│   ├── tracked_site.py
│   └── tracked_domain.py
│
├── services/
│   ├── tracked_sites.py
│   └── domain_normalization.py
│
└── api/v1/
    └── tracked_sites.py

Refactor existing Project and Keyword layers rather than duplicating them.

74. Future M4 Contract

M3.1 must prepare for this future call:

serp = provider.search(
    query=keyword.keyword,
    search_engine=project.search_engine,
    country=project.country_code,
    language=project.language_code,
    device=project.device,
    location=project.location,
)

Then:

SERP result domains
      ↓
Tracked Domain Registry
      ↓
Tracked Site

Do NOT implement this code yet.

75. No Redirect Resolution

M3.1 does NOT perform:

HTTP HEAD
HTTP GET
follow 301
follow 302
resolve final URL

The user explicitly manages aliases.

This prevents unnecessary external network requests.

76. No SERP Provider

Do NOT call:

SerpApi
SERPROBOT
DataForSEO
Google
Bing

No external SERP requests belong in this milestone.

77. No Ranking Tables

Do NOT create:

rankings
rank_checks
serp_results
positions
competitors

These belong to M4.

78. Tracked Site API Smoke Test

Create a real-stack smoke flow:

register User A
register User B

User A:
create Site A
  primary = new.com
  alias = old.com

add second alias
promote second alias

verify old aliases retained

attempt duplicate domain in Site B
→ conflict

User B:
track same domain
→ allowed

User B:
attempt Site A access
→ 404
79. Project Refactor API Smoke Test

Real stack:

create Project with:
  SERP settings
  3 Keywords

verify Project created
verify 3 Keywords created

verify Project response has no domain

verify Keyword response has no:
  country
  language
  device
  location

bulk-add Keywords

update Project country:
VN → TH

verify Keywords unchanged
verify Project now TH

edit/pause/delete Keyword
80. Browser Verification

Required real-browser journey:

Login

Tracked Sites
↓
Create Site
↓
Add old/current domains
↓
Promote new primary

Projects
↓
Create Project
↓
enter SERP settings
↓
paste multiple Keywords
↓
Create
↓
open Project
↓
verify Keyword list
↓
edit Project SERP setting
↓
verify Keywords remain
↓
add Keyword
↓
pause Keyword
↓
reload
↓
state remains correct

Check:

browser exceptions = 0
unexpected network failures = 0
CORS errors = 0
auth loops = 0
81. Backend Tests

At minimum cover:

new Project schema
integrated Project + Keyword creation
transaction rollback
Project requires keyword
1000 keyword limit

Project setting update

simplified Keyword CRUD
simplified Keyword uniqueness

Tracked Site CRUD
Tracked Domain CRUD

domain normalization
IDNA
duplicate domains

primary domain invariants
primary switching

archive/reactivate Site

tenant isolation

same domain across different users

migration data transformation
migration configuration splitting
migration domain deduplication
82. Frontend Tests

At minimum:

Add Project integrated form

keyword textarea cleanup
keyword count
Project API payload

Project detail environment

Keyword table without per-keyword settings

Tracked Site list

create Tracked Site
domain alias list
add domain
promote primary
activate/deactivate
duplicate error

301 workflow

auth regression
83. Regression Requirements

All still-valid Milestone 1–3 behavior must continue to pass.

Expected intentional changes from M3:

Project domain removed
Project default_* renamed

Keyword SERP settings removed

Add Project now requires initial Keywords

Keyword advanced tracking overrides removed

Tests expecting old behavior must be deliberately updated, not blindly preserved.

84. Migration Verification

Because M3.1 is a semantic refactor, verification must include:

fresh database:
base → head

realistic M3 fixture:
0003 → 0004

alembic check

model ↔ migration agreement

Do not report migration success solely from an empty database.

85. Production Builds

Verify:

backend production image
frontend production build

New frontend route(s):

/app/tracked-sites

and any Tracked Site detail/new routes must build successfully.

86. Documentation

Create/update:

docs/architecture/project-keyword-model.md
docs/architecture/tracked-sites.md

docs/api/projects.md
docs/api/keywords.md
docs/api/tracked-sites.md

Document clearly:

Project = SERP environment

Keyword = query only

Tracked Site = logical SEO site

Tracked Domain = domain alias

Tracked Sites are global per user

No Project ↔ Site mapping yet
87. README

Update README to explain:

integrated Add Project flow

new Project data model

simplified Keyword model

Tracked Sites

domain alias / 301 workflow

new APIs

migration behavior

Do not remove useful authentication/foundation documentation.

88. Definition of Done — Project Refactor
[ ] Project no longer has domain
[ ] default_* fields renamed
[ ] Project owns complete SERP environment
[ ] Project creation accepts initial Keywords
[ ] Project + Keywords creation is transactional
[ ] At least one Keyword required
[ ] 1000-input safety limit works

[ ] Existing separate Keyword add still works
[ ] Existing bulk Keyword add still works

[ ] Project configuration update applies conceptually to all Keywords
89. Definition of Done — Keyword Refactor
[ ] Keyword contains query-level data only

[ ] Keyword no longer stores:
    search engine
    country
    language
    device
    location

[ ] Unique constraint is:
    project_id + keyword_normalized

[ ] Keyword PATCH only supports:
    keyword
    active

[ ] Old per-Keyword override API input is rejected
90. Definition of Done — Tracked Sites
[ ] tracked_sites exists
[ ] tracked_domains exists

[ ] Tracked Site belongs to user
[ ] Domain alias belongs to Site and user

[ ] Same domain can exist for different users
[ ] Same domain cannot exist twice for one user

[ ] Site requires primary domain
[ ] Exactly one primary exists
[ ] Primary is always active

[ ] Alias can be added
[ ] Alias can be disabled
[ ] Alias can be reactivated
[ ] Alias can become primary

[ ] Primary deletion invariant works

[ ] Site archive/reactivate works
[ ] Site deletion works
91. Definition of Done — Migration
[ ] Existing Project domains preserved as Tracked Sites

[ ] Same-user duplicate domains deduplicated

[ ] Existing Keyword configuration overrides preserved
    by deterministic Project splitting

[ ] No Keyword is silently lost

[ ] No SERP configuration is silently lost

[ ] Old Keyword configuration columns removed

[ ] Project domain removed

[ ] fresh base → head works

[ ] realistic 0003 → 0004 fixture works

[ ] alembic check reports no schema drift
92. Definition of Done — Tenant Security
[ ] User remains only tenant boundary

[ ] Project queries remain user-scoped

[ ] Keyword queries remain user-scoped through Project

[ ] Tracked Site queries are user-scoped

[ ] Tracked Domain queries are user-scoped

[ ] Foreign IDs return same external behavior as missing IDs

[ ] user_id / owner_id / organization_id cannot override ownership

[ ] No Organization or Workspace model introduced
93. Definition of Done — Frontend
[ ] Add Project has no domain field

[ ] Add Project accepts multiple Keywords

[ ] Project list has no domain

[ ] Project detail shows SERP environment

[ ] Keyword table has no duplicated SERP configuration columns

[ ] Keyword Add/Bulk Add is simplified


[ ] Tracked Sites navigation exists

[ ] Tracked Site list works

[ ] Site creation works

[ ] Domain alias management works

[ ] Primary-domain switching works

[ ] 301 workflow works without modifying Project

[ ] Reload preserves saved state
94. Definition of Done — Quality
[ ] Backend tests pass
[ ] Frontend tests pass

[ ] Migration fixture tests pass
[ ] Tenant isolation tests pass

[ ] Project/Keyword smoke passes
[ ] Tracked Site smoke passes

[ ] Browser verification passes

[ ] Ruff passes
[ ] Ruff formatting passes
[ ] mypy strict passes

[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes

[ ] npm audit remains acceptable

[ ] backend production build passes
[ ] frontend production build passes

[ ] Milestone 1 regression passes
[ ] Milestone 2 regression passes
[ ] all still-valid Milestone 3 behavior passes

[ ] Docker services healthy
95. Explicitly Out of Scope

Do NOT implement:

SERP Provider
SerpApi integration
Google search calls

SERP scraping

Rank Checks
Ranking History
SERP result storage

Domain Matcher
Competitor detection

301 HTTP resolver

Workers
Queues
Scheduler

Billing
Subscription
Usage quotas

Project ↔ Tracked Site mapping

CSV import/export

Notifications
Reports
Analytics
96. Expected M4 Architecture

After M3.1, M4 should be able to operate with:

Project
├── Google
├── VN
├── vi
├── desktop
└── Ho Chi Minh City

Keyword
└── "casino online"

        ↓

SERP Provider

        ↓

Top organic results

        ↓

Domain Matcher

        ↓

User's active Tracked Domains

        ↓

Tracked Sites

        ↓

Rankings

Do not implement this pipeline now.

97. Required Verification Commands

Run existing repository workflows plus new checks.

At minimum:

docker compose build
docker compose up --build -d --wait

make check

make auth-smoke
make business-smoke

Add an appropriate:

tracked-site smoke

command or extend business smoke.

Also run:

fresh migration verification
M3 → M3.1 fixture migration
alembic check
backend production build
frontend production build
browser verification
docker compose ps

Do not claim checks that were not executed.

98. Required Delivery

Create:

docs/verification-milestone-3.1.md

Include:

implementation summary

architecture changes

old vs new data model

migration strategy

existing Project-domain migration

Keyword configuration-group migration

Tracked Site schema

Tracked Domain schema

API changes

frontend changes

files created
files modified

commands actually executed

backend test result
frontend test result

migration-fixture result
schema-drift result

security verification

API smoke results
browser verification

M1 regression
M2 regression
M3 regression/adaptations

known limitations

full Definition of Done checklist
99. Important Codex Instruction About Existing M3 Tests

Do NOT preserve outdated Milestone 3 tests merely for the sake of keeping them green.

Tests based on these old assumptions must be intentionally rewritten:

Project owns domain

Project settings are merely defaults

Keyword owns country/language/device/location

Keyword can override Project settings

Those behaviors are intentionally removed.

Preserve tests for:

authentication
tenant isolation
normalization
bulk processing
pagination
CRUD
security
Docker
migration consistency

where they remain valid.

100. Final Instruction to Codex

Implement Milestone 3.1 completely according to:

docs/milestone-3.1-spec.md

Work directly on the CURRENT Milestone 3 repository.

Before changing code, read:

docs/milestone-1-spec.md
docs/milestone-2-spec.md
docs/milestone-3-spec.md

docs/verification.md
docs/verification-milestone-2.md
docs/verification-milestone-3.md

README.md

current source
current migrations
current tests

The repository is the source of truth.

Do NOT restart the project.

Refactor the current implementation.

Critical architecture changes:

1. Project no longer owns a domain.

2. Project owns one SERP environment.

3. Keyword is only a query belonging to Project.

4. Keyword has no tracking configuration override.

5. Add Project creates Project + Keywords together.

6. Tracked Sites are user-global SEO assets.

7. Tracked Sites may have multiple current/historical domain aliases.

8. Domain changes/301s must not require Project recreation.

9. No Project ↔ Tracked Site mapping exists yet.

10. SERP/ranking functionality remains out of scope.

Preserve:

user-level tenancy
auth architecture
repository/service/router separation
security conventions
Docker workflow
strict typing
testing discipline

Before declaring completion:

verify data migration
verify Keyword configuration preservation
verify existing Project domains migrate to Tracked Sites

run complete backend tests
run complete frontend tests

run lint/format
run strict Python typing
run strict TypeScript typing

run schema-drift check

run auth regression
run business regression
run Tracked Site smoke

run real browser verification

build production frontend
build production backend

verify final Docker service health

Fix actual failures before completion.

Create:

docs/verification-milestone-3.1.md

Do not claim Milestone 3.1 complete unless every applicable Definition of Done item has actually been verified.