# SERP SaaS — Milestone 5 Specification
## Cloud Tasks + Cloud Run Worker + Scheduled Rank Checks

Target milestone: M5
Status: Specification
Prerequisite: Milestones M1, M2, M3, M3.1, M4, and M4.1 are complete.
Primary goal: Move rank-check execution out of synchronous API requests and into a durable asynchronous job architecture using Google Cloud Tasks and a Cloud Run Worker, while preserving the existing provider-routing and ranking pipeline.

1. Objective

Milestone 5 converts rank checks from synchronous request execution into durable background work.

Current conceptual flow:

Frontend
   ↓
FastAPI
   ↓
RankCheckExecutionService
   ↓
ProviderRouter
   ↓
Serper / SerpApi
   ↓
DomainMatcher
   ↓
RankCheck / Results / Rankings

M5 target flow:

Frontend
   ↓
FastAPI API
   ↓
Create Rank Check Batch
   ↓
Create Keyword Rank Check Jobs
   ↓
Task Queue Abstraction
   ↓
Cloud Tasks
   ↓
Cloud Run Worker
   ↓
Existing RankCheckExecutionService
   ↓
ProviderRouter
   ↓
Serper / SerpApi
   ↓
DomainMatcher
   ↓
RankCheck / Results / Rankings
   ↓
Batch Progress / History

The API request must return quickly after queueing work.

A Project with hundreds or thousands of Keywords must no longer require one long-running HTTP request.

2. Architectural Principles

M5 must follow these rules:

Do not rewrite the existing ranking engine.

Do not rewrite ProviderRouter.

Do not change DomainMatcher semantics.

Do not expose SERP provider selection to end users.

Cloud Tasks is infrastructure, not business logic.

Cloud Run Worker must be stateless.

PostgreSQL remains the source of truth for job state.

Queue delivery is at-least-once; execution must therefore be idempotent.

Task retries must never create duplicate ranking history.

Local development must not require paid GCP infrastructure.

Normal automated tests must not create real Cloud Tasks or consume SERP credits.

Scheduler, queue, and worker execution must be reusable outside HTTP request context.

M5 should minimize fixed cloud cost during development and staging.

3. Scope

M5 must implement:

Rank Check Batch model
Rank Check Job model
asynchronous Project rank checks
asynchronous single-Keyword rank checks
task queue abstraction
Google Cloud Tasks adapter
local deterministic queue adapter
Cloud Run Worker HTTP endpoint
worker authentication
worker idempotency
task retry policy
job retry accounting
batch progress
batch history
scheduled Project checks
schedule dispatcher
Cloud Scheduler-compatible dispatch endpoint
queue rate/concurrency configuration
job recovery
stale-job handling
frontend progress UI
frontend batch history UI
manual "Check now" through queue
structured worker logs
operational metrics/logging hooks
migration
tests
zero-cost local verification
optional real Cloud Tasks smoke
documentation

4. Explicitly Out of Scope

Do NOT implement in M5:

billing
subscriptions
paid plan enforcement
customer usage invoicing
DataForSEO integration
provider price synchronization
provider result merging
provider consensus
multi-page SERP collection
competitor entities
advanced ranking analytics
email notifications
Slack notifications
webhooks
Kubernetes
GKE
Memorystore requirement
Pub/Sub event fan-out
distributed workflow engine
Celery requirement
Redis production queue requirement
machine-learning provider routing
full admin dashboard
production autoscaling optimization beyond safe defaults

5. Existing M4.1 Components to Reuse

The current implementation already provides:

SerpProvider abstraction
SerperProvider
SerpApiProvider
FakeSerpProvider

ProviderRegistry
ProviderSelectionPolicy
ProviderRouter

provider budgets
provider usage accounting
provider fallback
provider attempt history

RankCheck
RankCheckResult
Ranking

DomainMatcher

Project
Keyword
TrackedSite
TrackedDomain

manual rank check APIs
ranking history
latest rankings
frontend ranking detail/history

M5 must execute the existing provider-independent rank-check service from the worker.

The worker must not implement separate SERP parsing, matching, or persistence logic.

6. Cloud Architecture

Production / staging target:

                    ┌─────────────────────┐
                    │      Frontend       │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Cloud Run API       │
                    │ FastAPI             │
                    └─────────┬───────────┘
                              │
                    create batch/jobs
                              │
                              ▼
                    ┌─────────────────────┐
                    │ PostgreSQL          │
                    │ Cloud SQL           │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Cloud Tasks         │
                    └─────────┬───────────┘
                              │ authenticated HTTP
                              ▼
                    ┌─────────────────────┐
                    │ Cloud Run Worker    │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ ProviderRouter      │
                    ├─────────────────────┤
                    │ Serper / SerpApi    │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ DomainMatcher       │
                    │ Ranking persistence │
                    └─────────────────────┘

Scheduled execution:

Cloud Scheduler
      ↓
Schedule Dispatcher endpoint
      ↓
Find due Project schedules
      ↓
Create Batch + Jobs
      ↓
Cloud Tasks
      ↓
Cloud Run Worker

7. Cost-Conscious Design

M5 must avoid infrastructure that creates unnecessary fixed cost.

Preferred:

Cloud Run
Cloud Tasks
Cloud Scheduler
Cloud SQL
Secret Manager
Artifact Registry

Avoid requiring:

Memorystore
Compute Engine workers running 24/7
GKE
always-on queue servers

Cloud Run services should support scale-to-zero where practical.

Development must work entirely with local Docker and fake/local queue implementations.

8. Queue Abstraction

Create a provider-independent task queue interface.

Conceptually:

class RankCheckTaskQueue(Protocol):
    async def enqueue_rank_check_job(
        self,
        job_id: UUID,
        *,
        schedule_time: datetime | None = None,
    ) -> TaskEnqueueResult:
        ...

Implement:

LocalTaskQueue
CloudTasksRankCheckQueue

Business services must depend on RankCheckTaskQueue, not Google SDK types.

Forbidden in Project/RankCheck business services:

from google.cloud import tasks_v2

Google-specific code belongs only in the Cloud Tasks adapter.

9. Local Queue Strategy

Local development must not require GCP.

Provide a deterministic local queue adapter.

Acceptable implementations:

in-process deterministic fake queue for tests
+
local worker-trigger helper / development dispatcher

Redis may remain available in Docker for existing infrastructure, but M5 must not require Redis as the production queue.

Do not build two independent business pipelines.

Both local and Cloud Tasks adapters must deliver the same worker job contract.

10. Rank Check Batch

Introduce:

RankCheckBatch

A Batch represents one user action or one scheduled Project execution.

Examples:

User clicks "Check Rankings" for Project
→ 1 batch

Project scheduled daily execution
→ 1 batch

User checks one Keyword
→ 1 batch containing one job

11. Rank Check Batch Model

Recommended table:

rank_check_batches

Fields:

id UUID PK

user_id UUID NOT NULL
project_id UUID NOT NULL

trigger_type
status

requested_keyword_count
queued_keyword_count
running_keyword_count
succeeded_keyword_count
failed_keyword_count
cancelled_keyword_count

requested_at
started_at nullable
completed_at nullable

schedule_id nullable

created_at
updated_at

Optional:

requested_by_user_id

if useful, but the existing tenant model remains User-only.

12. Batch Trigger Types

Support:

manual_project
manual_keyword
scheduled

Do not infer trigger type from UI.

Persist it explicitly.

13. Batch Status

Support:

pending
queued
running
completed
completed_with_errors
failed
cancelled

Recommended semantics:

pending
→ DB row exists but job creation not complete

queued
→ all intended jobs successfully created/enqueued

running
→ at least one job has started

completed
→ all jobs terminal and none failed

completed_with_errors
→ all jobs terminal and at least one failed

failed
→ batch-level failure prevented execution

cancelled
→ batch intentionally cancelled

14. Rank Check Job

Introduce:

RankCheckJob

One job represents execution for one Keyword.

Recommended table:

rank_check_jobs

Fields:

id UUID PK

batch_id UUID NOT NULL
user_id UUID NOT NULL
project_id UUID NOT NULL
keyword_id UUID NOT NULL

status

attempt_count
max_attempts

queued_at nullable
started_at nullable
completed_at nullable

next_retry_at nullable

rank_check_id nullable

last_error_code nullable

task_name nullable

created_at
updated_at

15. Job Status

Support:

pending
queued
running
succeeded
failed
cancelled

Optional:

retry_scheduled

only if it materially improves clarity.

Keep the state machine small and explicit.

16. Batch / Job Snapshot Policy

Jobs must preserve enough identity to execute safely.

However, search-environment snapshots should continue to be persisted on RankCheck using the existing M4 execution path.

Do not duplicate every RankCheck snapshot field onto RankCheckJob unless needed.

The worker should resolve the current Project/Keyword and then call the existing snapshot-aware RankCheck execution flow.

If a Project or Keyword becomes inactive after queueing but before execution, behavior must be explicitly defined.

Recommended:

manual queued job
→ execute using current entity if still valid

archived Project / inactive Keyword before worker starts
→ fail/skip safely with stable code

Do not silently execute archived business entities.

17. Idempotency

Cloud Tasks uses at-least-once delivery semantics.

Therefore worker execution MUST be idempotent.

The same job_id may be delivered multiple times.

Correct behavior:

delivery #1
→ job claims execution
→ succeeds

delivery #2
→ sees job already succeeded
→ returns success without creating another RankCheck

18. Job Claiming

Worker must atomically claim a Job.

Use PostgreSQL transaction and row locking.

Conceptually:

SELECT job FOR UPDATE

if status == succeeded:
    return ALREADY_COMPLETED

if status == running and lease still valid:
    return ALREADY_RUNNING

if status in queued/pending/eligible retry:
    mark running
    increment attempt_count
    set started_at / execution lease

Avoid race-prone check-then-update logic outside a transaction.

19. Worker Execution Lease

Add an execution lease concept to recover from worker crashes.

Recommended fields:

lease_expires_at
worker_execution_id

When claiming:

lease_expires_at = now + configured lease duration

If worker dies after claiming:

job remains running

A later delivery or recovery process may reclaim it only after the lease expires.

20. Worker Execution ID

Generate a unique execution ID per claim.

Example:

worker_execution_id = UUID

Structured logs should include:

job_id
batch_id
worker_execution_id
rank_check_id
provider

when available.

21. RankCheck Idempotency

There must be at most one successful logical RankCheck execution per Job.

Recommended:

rank_check_jobs.rank_check_id

links the job to its created RankCheck.

Use a DB uniqueness constraint where appropriate to prevent duplicate linkage.

Do not allow repeated task deliveries to create multiple RankCheck histories for the same Job.

22. Worker Endpoint

Add internal endpoint, for example:

POST /internal/tasks/rank-check

Request body:

{
  "job_id": "UUID"
}

The worker endpoint must not accept:

user_id
project_id
keyword_id
provider
search parameters
budget values

from the task body.

The database Job record is the source of truth.

This minimizes tampering and payload drift.

23. Worker Service Separation

Preferred deployment:

API Cloud Run service
Worker Cloud Run service

They may share the same source repository/image initially, but use different commands/configuration.

Example:

API:
uvicorn app.main:app

Worker:
uvicorn app.worker_main:app

The worker service should expose only necessary internal endpoints plus health endpoints.

24. Worker Authentication

Cloud Tasks → Cloud Run Worker calls must be authenticated.

Use a dedicated Google service account.

Preferred mechanism:

Cloud Tasks HTTP target
+
OIDC token
+
Cloud Run IAM authentication

Do not protect the worker with a shared secret query string.

Do not make the worker public merely for convenience.

25. Service Accounts

Use separate service identities where practical:

serp-api-service
serp-worker-service
serp-task-enqueuer
serp-scheduler-invoker

At minimum:

API service account
Worker service account
Cloud Tasks invocation identity

Apply least privilege.

26. Cloud Tasks Queue

Recommended initial queue:

rank-checks

Do not create one queue per User or Project.

One queue is sufficient initially.

Future workload classes may justify multiple queues.

27. Cloud Tasks Configuration

Make these environment-driven:

TASK_QUEUE_PROVIDER=cloud_tasks

GCP_PROJECT_ID=
GCP_LOCATION=
CLOUD_TASKS_QUEUE=rank-checks
CLOUD_TASKS_WORKER_URL=

CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=

TASK_DISPATCH_MAX_PER_SECOND=
TASK_MAX_CONCURRENT_DISPATCHES=

Do not hardcode project, region, or URL.

28. Queue Rate Control

Cloud Tasks queue rate/concurrency must protect:

SERP provider quotas
Cloud SQL connections
Worker concurrency
cost

Initial development/staging defaults should be conservative.

For example:

max dispatches per second = low single digits
max concurrent dispatches = low single digits

Exact defaults should be documented and configurable.

Do not assume higher throughput is always better.

29. Interaction with M4.1 Provider Concurrency

M4.1 already controls provider routing and budgets.

M5 introduces task-level concurrency.

These controls are distinct:

Cloud Tasks dispatch concurrency
→ number of jobs entering workers

ProviderRouter
→ provider choice/fallback/budget per job

Do not multiply concurrency accidentally.

30. Worker Cloud Run Concurrency

Cloud Run worker concurrency must be explicitly configured.

For initial staging:

low concurrency

is preferred to simplify DB/provider pressure.

Do not rely solely on Cloud Run default concurrency.

Document the chosen value.

31. DB Connection Pool Safety

Worker autoscaling can create many instances.

Therefore DB pool sizes must be conservative.

Add worker-specific configuration if needed:

WORKER_DB_POOL_SIZE=
WORKER_DB_MAX_OVERFLOW=

Total potential DB connections must be considered:

API instances
+
Worker instances × per-instance pool

Do not allow Cloud Run autoscaling to overwhelm Cloud SQL.

32. Manual Single Keyword Check

Existing user action:

Check now

must become asynchronous.

Flow:

POST keyword rank-check request
→ create Batch
→ create one Job
→ enqueue Job
→ return 202

Suggested response:

{
  "batch_id": "...",
  "job_id": "...",
  "status": "queued"
}

Do not block until SERP provider completion.

33. Manual Project Check

Existing:

Check Rankings

becomes:

POST Project check
→ validate Project / active Keywords
→ create Batch
→ create one Job per Keyword
→ enqueue jobs
→ return Batch ID

The HTTP request should not execute provider calls.

34. Large Project Support

M5 should remove the M4 synchronous execution limitation as a product constraint.

Do not require the whole Project to have <= 25 Keywords just because the request is synchronous.

However, protect abuse with a separate configurable enqueue limit.

Example:

RANK_CHECK_BATCH_MAX_KEYWORDS=5000

The exact default may be conservative.

This is a system-safety limit, not billing.

35. Batch Creation Transaction

Batch/job creation must be atomic in the database.

Recommended flow:

Transaction A:

validate Project ownership
resolve selected active Keywords
create Batch
create Job rows
commit

Then enqueue tasks.

Because queue creation is external I/O, do not hold the DB transaction open while making Cloud Tasks API calls.

36. DB + Queue Consistency

DB and Cloud Tasks cannot share one transaction.

Therefore M5 must explicitly handle partial enqueue failures.

Recommended outbox-like approach:

1. Persist Batch + Jobs as pending
2. Enqueue each pending Job
3. Mark each Job queued only after enqueue succeeds
4. Background/explicit recovery can enqueue remaining pending Jobs

Do not mark a Job queued before Cloud Tasks confirms task creation.

37. Task Naming and Deduplication

Use deterministic Cloud Task names when possible.

Example derived from:

job_id

This helps prevent duplicate enqueue on recovery.

Conceptually:

rank-check-job-{job_uuid}

If Cloud Tasks reports task already exists:

treat as already enqueued

after verifying state.

Do not generate random names for repeated enqueue attempts of the same Job.

38. Enqueue Recovery

Provide a recovery mechanism for Jobs stuck in:

pending

because API process died between DB commit and task creation.

Options:

internal recovery endpoint
scheduled dispatcher
startup-safe maintenance command

Recommended:

schedule dispatcher also re-enqueues stale pending jobs

with deterministic task naming.

39. Worker Success

Successful worker flow:

claim Job
↓
execute existing RankCheck service
↓
persist RankCheck/Results/Rankings
↓
set Job succeeded + rank_check_id
↓
update Batch counters/status
↓
return HTTP 2xx

40. Worker Failure

Failure must distinguish:

retryable job failure
terminal job failure

Do not simply return 500 for every business error.

41. Retry Layers

M5 now has three possible retry layers:

1. Provider adapter retry
2. ProviderRouter fallback
3. Job/task retry

They must remain conceptually separate.

Example:

Serper transient HTTP failure
→ adapter retries Serper

still fails rate limit
→ ProviderRouter may fallback to SerpApi

both unavailable
→ Rank Check execution returns retryable infrastructure failure

Cloud Tasks may retry Job later

Avoid exponential request explosions.

42. Retryable Job Errors

Recommended retryable categories:

temporary database connectivity
temporary provider unavailability after router fallback
temporary network failure
Cloud dependency temporary failure

Do not retry indefinitely.

43. Non-Retryable Job Errors

Examples:

Project archived
Keyword inactive/deleted
invalid Project configuration
authentication/configuration defect
unsupported search semantics with no eligible provider
business validation failure

These should mark Job failed terminally.

44. Cloud Tasks Retry Policy

Configure queue retry settings.

Environment/documentation should define:

max attempts
minimum backoff
maximum backoff
maximum retry duration

Cloud Tasks retry count and application Job attempt_count must be reconcilable.

Do not create an unbounded retry queue.

45. HTTP Status Contract for Cloud Tasks

Worker endpoint should return:

2xx
→ task considered successfully handled

retryable infrastructure failure
→ non-2xx chosen intentionally to trigger Cloud Tasks retry

terminal application failure
→ persist Job failed and return 2xx

This distinction is critical.

A terminal business failure must not cause Cloud Tasks to retry forever.

46. Batch Progress Counters

Batch counters must remain accurate under concurrent worker completion.

Use atomic updates or derive from Jobs.

Recommended source of truth:

rank_check_jobs

Batch counters may be cached/denormalized for fast API reads, but must be transactionally maintained.

Avoid race-prone read-modify-write.

47. Batch Completion

After every Job terminal transition, evaluate Batch state.

Examples:

100 jobs
100 succeeded
→ completed

100 jobs
97 succeeded
3 failed
→ completed_with_errors

Batch terminal transition must happen once.

48. Batch Progress API

Add:

GET /api/v1/projects/{project_id}/rank-check-batches/{batch_id}

Return:

{
  "id": "...",
  "status": "running",
  "requested_keyword_count": 500,
  "queued_keyword_count": 500,
  "running_keyword_count": 8,
  "succeeded_keyword_count": 311,
  "failed_keyword_count": 2,
  "cancelled_keyword_count": 0,
  "progress_percent": 62.6,
  "requested_at": "...",
  "started_at": "...",
  "completed_at": null
}

progress_percent may be derived.

49. Batch History API

Add cursor-paginated endpoint:

GET /api/v1/projects/{project_id}/rank-check-batches

Support filters such as:

status
trigger_type

only if useful.

Do not implement overly complex filtering.

50. Batch Job Detail API

Optional but recommended:

GET /api/v1/projects/{project_id}/rank-check-batches/{batch_id}/jobs

Cursor paginated.

Return per Keyword:

keyword
status
attempt_count
rank_check_id
last_error_code
started_at
completed_at

51. Cancellation

M5 should support best-effort cancellation.

Endpoint:

POST /api/v1/projects/{project_id}/rank-check-batches/{batch_id}/cancel

Semantics:

pending/queued Jobs
→ mark cancelled

running Jobs
→ may finish safely

future task deliveries
→ worker sees cancelled and returns 2xx without execution

Do not require deleting Cloud Tasks individually for correctness.

Database state remains authoritative.

52. Schedule Model

Introduce Project schedules.

Recommended table:

project_rank_schedules

Fields:

id UUID PK

user_id UUID NOT NULL
project_id UUID NOT NULL

enabled boolean

frequency
timezone

next_run_at
last_enqueued_at nullable

created_at
updated_at

53. Initial Schedule Frequencies

Support only simple frequencies initially:

daily
weekly

Optionally:

every_3_days

if easy.

Do not expose arbitrary cron expressions to normal end users in M5.

54. Schedule Time

Allow user to choose a local execution time.

Example:

Daily at 07:00
Timezone: Asia/Ho_Chi_Minh

Persist timezone explicitly.

Do not assume server UTC is the user's timezone.

Store next_run_at as UTC.

55. Schedule Dispatcher

Create an internal dispatcher service/function:

dispatch_due_schedules(now)

Responsibilities:

find enabled schedules with next_run_at <= now
lock schedules safely
create scheduled Batch + Jobs
advance next_run_at
enqueue Jobs

Must be safe if invoked more than once.

56. Cloud Scheduler

Use Cloud Scheduler only to invoke the dispatcher periodically.

Recommended:

one Cloud Scheduler job
→ every 5 minutes
→ POST internal schedule dispatcher endpoint

Do NOT create one Cloud Scheduler job per Project.

This controls cloud cost and operational complexity.

57. Scheduler Authentication

Cloud Scheduler → API/dispatcher must use authenticated invocation.

Prefer:

OIDC service account
+
Cloud Run IAM

No public unauthenticated scheduler endpoint.

58. Dispatcher Concurrency

Two dispatcher invocations may overlap.

Use PostgreSQL locking such as:

SELECT ... FOR UPDATE SKIP LOCKED

or equivalent.

A due schedule must generate at most one Batch per due occurrence.

59. Schedule Catch-Up

Define what happens after downtime.

Recommended:

do not create one batch for every missed historical interval

Instead:

if schedule is overdue
→ create one catch-up batch
→ compute next future run

This prevents massive accidental queue bursts.

60. Scheduled Project State

If Project is archived:

skip schedule
disable or advance safely

If no active Keywords:

do not create useless provider calls

Persist a safe operational reason if needed.

61. Frontend Project Controls

Project detail should provide:

Check Rankings
Schedule
Latest Batch status
Progress
Recent Batch history

No provider selector.

62. Manual Check UX

When user clicks:

Check Rankings

UI should receive a queued Batch response immediately.

Show:

Queued
0 / 500 completed

then poll/refetch progress.

Do not keep the original HTTP request open.

63. Progress Refresh

For M5, polling is sufficient.

Recommended:

TanStack Query refetch interval

while Batch is non-terminal.

Do NOT add WebSockets or SSE unless necessary.

Stop polling after terminal state.

64. Single Keyword UX

Check now becomes:

Queued
Running
Completed
Failed

When completed:

refresh latest ranking/history

65. Batch History UI

Project page should display recent batches:

Date
Trigger
Status
Keywords
Succeeded
Failed
Duration

Clicking a batch may show Job details.

66. Error UX

Normal users should see business-safe messages.

Examples:

Some keyword checks could not be completed.
Ranking providers are temporarily unavailable.
Project is archived.

Do not expose:

Cloud Tasks queue name
service account email
GCP project ID
provider API key
raw stack trace

67. Worker Health Endpoints

Worker service should expose:

/health
/health/db

Redis health is not required for worker correctness.

Do not expose internal worker task execution endpoints publicly without IAM.

68. Structured Logging

Add structured events:

rank_check_batch_created
rank_check_job_created
rank_check_job_enqueued
rank_check_job_claimed
rank_check_job_succeeded
rank_check_job_failed
rank_check_job_retry
rank_check_job_cancelled

rank_check_batch_completed

rank_schedule_due
rank_schedule_dispatched

cloud_task_enqueue_failed
cloud_task_already_exists

Useful fields:

user_id
project_id
keyword_id
batch_id
job_id
rank_check_id
trigger_type
attempt_count
duration_ms
safe_error_code

Never log secrets or raw provider payloads.

69. Metrics

M5 should expose or log enough data to derive:

queued jobs
running jobs
job success rate
job failure rate
average job duration
batch duration
retry count
provider requests per batch

Full monitoring dashboards are not required yet.

70. Database Migration

Create next migration, expected:

0007_async_rank_check_jobs

unless current head differs.

Do not modify previous migrations.

71. Migration Creates

At minimum:

rank_check_batches
rank_check_jobs
project_rank_schedules

Add required indexes/constraints/FKs.

72. Recommended Batch Constraints

Examples:

requested_keyword_count >= 0
queued_keyword_count >= 0
running_keyword_count >= 0
succeeded_keyword_count >= 0
failed_keyword_count >= 0
cancelled_keyword_count >= 0

Counts must never exceed requested count.

Application logic must enforce valid status transitions.

73. Recommended Job Constraints

Examples:

attempt_count >= 0
max_attempts > 0

Unique relationship:

job.id

must be sufficient to identify one logical execution.

Consider:

UNIQUE(rank_check_id)

when non-null, if compatible with existing history.

74. Tenant Isolation

Every Batch, Job, and Schedule lookup must remain owner-scoped.

Never trust task request user IDs.

Worker receives only:

job_id

Then loads:

job
→ user_id
→ project_id
→ keyword_id

from DB.

Internal worker authorization is infrastructure-level, but tenant consistency still must be enforced in repository/service logic.

75. History Deletion Protection

Existing RankCheck history protection remains.

New Job/Batch references must not enable silent deletion of:

Project
Keyword
RankCheck history
Tracked Site history

Define FKs carefully.

Recommended:

historical Batch/Job rows should remain readable

Do not cascade-delete ranking history because a schedule is deleted.

76. Schedule Deletion

Deleting a schedule must not delete:

historical Batches
Jobs
RankChecks
Rankings

Scheduled Batch may keep:

schedule_id nullable / SET NULL

plus trigger snapshot if useful.

77. Queue Adapter Errors

Normalize queue errors into generic internal errors.

Examples:

TASK_QUEUE_UNAVAILABLE
TASK_ENQUEUE_FAILED
TASK_ALREADY_EXISTS

Do not leak Google exception classes through business services.

78. Cloud Tasks Payload

Keep payload minimal:

{
  "job_id": "..."
}

Optional:

schema_version

if useful.

Do not place keyword text or SERP settings in task payload.

79. Task Payload Versioning

Recommended:

{
  "version": 1,
  "job_id": "..."
}

Worker rejects unsupported versions safely.

This allows future evolution without ambiguous payloads.

80. Cloud Tasks Task Name

Recommended deterministic name:

projects/{project}/locations/{location}/queues/{queue}/tasks/rank-check-{job_id}

Implementation must sanitize/format according to Cloud Tasks requirements.

81. Cloud Tasks Scheduling

Normal manual jobs:

enqueue immediately

Retry/backoff is primarily handled by Cloud Tasks.

Do not use per-keyword scheduled Cloud Tasks months in advance for recurring schedules.

Recurring scheduling belongs to the Schedule Dispatcher.

82. Worker Timeout

Cloud Run request timeout and application timeout must be configured with headroom above:

provider timeout
provider adapter retries
provider fallback
DB writes

But do not allow extremely long task requests.

One Job = one Keyword keeps execution bounded.

83. One Job = One Keyword

This is a critical M5 rule.

Do NOT create:

one Cloud Task = 500 Keywords

Use:

one Cloud Task = one Keyword Job

Benefits:

independent retries
bounded runtime
accurate progress
failure isolation
better concurrency control

84. Provider Request Accounting

M4.1 remains authoritative for:

provider usage
provider attempts
provider fallback
provider_request_count

M5 Batch/Job metrics may aggregate these but must not implement duplicate provider accounting.

85. Internal Budgets

Existing:

SERPER_REQUEST_BUDGET=
SERPAPI_REQUEST_BUDGET=

continue to work.

If provider budget is exhausted during a Job:

ProviderRouter
→ choose next eligible provider

if policy permits.

If no provider is available:

Job failure classification determines retryability

Be careful: static monthly budget exhaustion should usually be terminal until budget period changes, not aggressively retried every few seconds.

86. No-Provider Retry Policy

Differentiate:

temporary provider unavailable
→ retryable

all configured monthly budgets exhausted
→ not immediately retryable

Avoid wasting Cloud Tasks attempts when the next retry cannot possibly succeed.

87. Batch Creation Limit

Add configurable protection:

RANK_CHECK_BATCH_MAX_KEYWORDS=5000

or a conservative project-specific default.

This prevents accidental queue floods.

Not a subscription limit.

88. Enqueue Rate Protection

When creating thousands of Jobs, API should not necessarily make thousands of Cloud Tasks API calls serially before responding.

Implement bounded enqueue concurrency or staged enqueue recovery.

The API must remain responsive.

Possible strategy:

persist all Jobs
enqueue bounded chunks
mark Batch queued once all are accepted
recovery dispatcher handles remainder if needed

Keep implementation understandable.

89. Batch Creation API Response

Return 202 Accepted.

Example:

{
  "batch_id": "...",
  "status": "pending",
  "requested_keyword_count": 1000
}

Frontend follows progress API.

90. Existing API Compatibility

Existing endpoints may retain their route names but change response semantics from synchronous result to asynchronous Batch.

If this would create ambiguous breaking behavior, introduce clearly named batch endpoints and migrate frontend.

Document all API changes.

91. Suggested APIs

Manual Project batch:

POST /api/v1/projects/{project_id}/rank-check-batches

Body optional:

{
  "keyword_ids": ["..."]
}

Manual Keyword:

POST /api/v1/projects/{project_id}/keywords/{keyword_id}/rank-check-batches

Batch detail:

GET /api/v1/projects/{project_id}/rank-check-batches/{batch_id}

Batch list:

GET /api/v1/projects/{project_id}/rank-check-batches

Batch jobs:

GET /api/v1/projects/{project_id}/rank-check-batches/{batch_id}/jobs

Cancel:

POST /api/v1/projects/{project_id}/rank-check-batches/{batch_id}/cancel

92. Schedule APIs

Suggested:

GET    /api/v1/projects/{project_id}/rank-schedule
PUT    /api/v1/projects/{project_id}/rank-schedule
DELETE /api/v1/projects/{project_id}/rank-schedule

Initial schedule model can allow one active schedule per Project.

This keeps M5 simple.

93. Schedule PUT Example

{
  "enabled": true,
  "frequency": "daily",
  "local_time": "07:00",
  "timezone": "Asia/Ho_Chi_Minh"
}

Response includes:

next_run_at

94. Schedule Validation

Validate:

IANA timezone
valid local time
supported frequency
Project active

Do not accept raw unvalidated cron from user.

95. Cloud Scheduler Internal Endpoint

Example:

POST /internal/schedules/dispatch

No user-controlled request fields required.

It computes due schedules from DB.

Protected by Cloud Run IAM / OIDC.

96. Task Queue Dependency Injection

Application wiring should choose queue adapter using environment.

Example:

TASK_QUEUE_PROVIDER=local

or:

TASK_QUEUE_PROVIDER=cloud_tasks

Production must reject unsafe local queue configuration.

97. Production Configuration Guard

Production should fail startup or health validation if:

TASK_QUEUE_PROVIDER=local

unless explicitly allowed for a controlled environment.

Similarly, worker/task authentication configuration must be present.

98. Local Development Configuration

Example:

TASK_QUEUE_PROVIDER=local

RANK_CHECK_BATCH_MAX_KEYWORDS=5000
RANK_CHECK_JOB_MAX_ATTEMPTS=5
RANK_CHECK_JOB_LEASE_SECONDS=300

No GCP credentials required for normal local development.

99. GCP Configuration Example

Example only:

TASK_QUEUE_PROVIDER=cloud_tasks

GCP_PROJECT_ID=
GCP_LOCATION=
CLOUD_TASKS_QUEUE=rank-checks
CLOUD_TASKS_WORKER_URL=
CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=

RANK_CHECK_BATCH_MAX_KEYWORDS=5000
RANK_CHECK_JOB_MAX_ATTEMPTS=5
RANK_CHECK_JOB_LEASE_SECONDS=300

Do not put service-account private keys into .env for Cloud Run production.

Use workload/service identity.

100. Docker Compose

Add local worker service if useful:

backend
worker
frontend
postgres
redis

However, local queue execution must stay deterministic and easy to verify.

Redis can remain for existing health/infrastructure work, but M5 business correctness must not depend on Redis queue semantics.

101. Worker Docker Image

Prefer reusing the backend image with different startup command.

Example:

same application image
different service command

Avoid duplicate dependency stacks.

102. Cloud Run API Service

API responsibilities:

auth
Project/Keyword management
Batch creation
Schedule CRUD
Batch/history reads
Cloud Task enqueue

It must not execute SERP calls for normal M5 rank-check requests.

103. Cloud Run Worker Service

Worker responsibilities:

authenticated task receipt
Job claim
existing RankCheck execution
Job finalization
Batch progress update

No normal end-user routes.

104. Schedule Dispatcher Placement

Dispatcher may run inside the API service behind an internal endpoint.

No separate always-on scheduler service is required.

Cloud Scheduler invokes it periodically.

105. Testing Strategy

Normal test suite must consume:

0 Cloud Tasks operations
0 Cloud Scheduler calls
0 Serper credits
0 SerpApi credits

Use:

Fake/LocalTaskQueue
Mock Cloud Tasks client
FakeSerpProvider
httpx mocks

106. Batch Unit Tests

Test:

single Keyword batch
Project batch
selected Keyword subset
zero active Keywords
archived Project
inactive Keyword
batch size limit
tenant isolation
counter transitions
terminal batch status

107. Queue Tests

Test:

local queue enqueue
Cloud Tasks request construction
deterministic task name
OIDC configuration
task payload version
already-exists handling
enqueue failure
recovery enqueue
no Google type leakage

No real Cloud Tasks calls.

108. Worker Idempotency Tests

Critical tests:

same task delivered twice
→ one RankCheck only

two workers race same Job
→ one claim succeeds

worker crashes after claim
→ lease expires
→ Job reclaim works

already succeeded Job
→ returns success without provider call

cancelled Job delivery
→ no provider call

109. Retry Tests

Test:

retryable infrastructure failure
→ worker returns retry-triggering status

terminal business failure
→ Job failed + worker returns 2xx

provider adapter retries
→ no accidental duplicate Job attempt semantics

provider fallback
→ remains within one Job attempt

max Job attempts
→ Job terminally failed

110. Batch Concurrency Tests

Run many Jobs concurrently.

Verify:

counters exact
no negative counters
no double completion
batch terminal transition exactly once

111. Schedule Tests

Test:

daily next_run_at
weekly next_run_at
timezone handling
DST-safe behavior where applicable
due schedule dispatch
not-due schedule skipped
duplicate dispatcher overlap
catch-up behavior
archived Project
no active Keywords
disabled schedule

112. Migration Tests

Verify:

base → head
0006 → new M5 head
head → previous revision → head
alembic check

Existing M4/M4.1 history fixture must remain intact.

113. Frontend Tests

At minimum:

Check Rankings returns queued batch
single Keyword Check now queues
batch progress renders
completed batch refreshes rankings
failed jobs display safely
batch history renders
schedule CRUD works
no provider selector appears
no GCP infrastructure details shown
polling stops after terminal batch

114. Browser Verification

Create/update deterministic browser flow:

login
create Project + Keywords
create Tracked Site
click Check Rankings
observe queued/running
local fake worker executes jobs
observe completed
verify latest rankings
verify batch history
configure schedule
verify schedule UI

Use fake/local queue and fake provider.

Zero external credits.

115. Local End-to-End Worker Smoke

Add:

make async-ranking-smoke

Flow:

create Batch
enqueue Jobs in local adapter
execute worker contract
persist RankChecks
verify Batch complete
verify Rankings

Zero GCP usage.

116. Cloud Tasks Mock Smoke

Add:

make cloud-tasks-contract-smoke

Use mock client.

Verify:

correct task name
correct target URL
correct OIDC config
correct payload

No real GCP call.

117. Optional Real Cloud Tasks Smoke

Add opt-in:

RUN_REAL_CLOUD_TASKS_SMOKE=true make cloud-tasks-smoke

Requirements:

configured GCP project
queue exists
worker endpoint configured
explicit opt-in
minimum number of tasks

Do not run during make check.

118. Real Cloud Tasks Smoke Behavior

Prefer one task only.

Use a dedicated smoke Job and fake/no-credit provider mode if possible.

Goal:

Cloud Tasks
→ authenticated Cloud Run/local reachable worker
→ Job claimed
→ persisted success

Do not unnecessarily consume SERP credits.

119. Optional Real Scheduled Smoke

Not required for M5 acceptance.

If implemented:

explicit opt-in only

Avoid waiting for long cron intervals during verification.

Direct dispatcher invocation is sufficient for normal verification.

120. Security Tests

Verify:

worker endpoint rejects unauthenticated production calls
task body cannot override user/project/keyword/provider
Cloud Tasks service account config not exposed to frontend
no service-account secret logged
no provider secrets logged
cross-user Batch lookup rejected
cross-user Job lookup rejected
schedule ownership enforced
internal dispatcher not exposed as normal user endpoint

121. Secret Handling

Production secrets:

SERPER_API_KEY
SERPAPI_API_KEY
DATABASE_URL or DB credentials
JWT/refresh secrets

should be compatible with Secret Manager.

Do not expose:

NEXT_PUBLIC_SERPER_API_KEY
NEXT_PUBLIC_SERPAPI_API_KEY

122. Cloud Run IAM

Document required IAM roles, but keep them minimal.

Examples conceptually:

API service:
Cloud Tasks enqueuer

Cloud Tasks invocation service account:
Cloud Run invoker on Worker

Cloud Scheduler invocation service account:
Cloud Run invoker on dispatcher/API

Do not grant Owner/Editor broadly.

123. Cloud SQL Connectivity

M5 architecture must remain compatible with Cloud Run → Cloud SQL.

Do not hardwire localhost DB assumptions into worker.

Use existing SQLAlchemy configuration.

124. Region Strategy

Recommend placing:

Cloud Run API
Cloud Run Worker
Cloud Tasks queue
Cloud Scheduler
Cloud SQL

in compatible/nearby regions where possible.

Do not encode one region into business code.

Region belongs in deployment configuration.

125. Cost Guardrails

Document development/staging guardrails:

Cloud Run min instances = 0 where practical
low worker concurrency initially
bounded Cloud Tasks dispatch
one Scheduler job for dispatcher
no Memorystore requirement
no always-on VM worker
small Cloud SQL instance for staging
artifact cleanup policy

126. Cloud Tasks Cost Safety

Avoid accidental task storms.

Protections:

RANK_CHECK_BATCH_MAX_KEYWORDS
deterministic task naming
enqueue recovery
queue rate limits
batch deduplication where applicable
schedule overlap protection

127. Manual Batch Deduplication

Prevent accidental double-click creating duplicate large batches.

Recommended:

optional idempotency key

for manual batch creation.

At minimum, frontend disables duplicate submission while request is pending.

Better:

Idempotency-Key header

persisted for a short logical window.

If implemented, scope by:

user + project + endpoint + key

128. Scheduled Batch Deduplication

This is mandatory.

One schedule occurrence must create at most one Batch.

Recommended unique identity:

schedule_id + scheduled_for

with unique constraint.

129. RankCheck Existing Running Constraint

M4/M4.1 may already prevent concurrent execution for the same Keyword.

M5 must reconcile this with queued Jobs.

Recommended:

prevent two running Jobs for same Keyword

but queued future/scheduled Jobs need careful behavior.

Do not simply remove existing safety constraints.

130. Overlapping Scheduled Checks

If previous scheduled Job for a Keyword is still running when next schedule occurs:

Recommended initial behavior:

skip duplicate execution for that Keyword

or mark the new Job failed/skipped with:

RANK_CHECK_ALREADY_RUNNING

Do not run concurrent provider checks for the same Keyword.

Document chosen behavior.

131. Schedule Frequency vs Execution Duration

If a Batch takes longer than the schedule interval:

do not create unlimited overlapping batches

Daily/weekly initial schedules make this unlikely, but protection is still required.

132. Cleanup / Retention

Do not implement aggressive history deletion in M5.

However, document that:

Batch/Job operational rows may require retention policy later

Ranking history remains product data.

No automatic deletion required yet.

133. API Pagination

Batch history and Job lists must use cursor pagination consistent with existing project APIs.

Avoid offset pagination for large histories.

134. Query Performance

Avoid N+1 queries for:

batch list
job list
progress

Use aggregate queries or denormalized counters.

Add only necessary indexes.

135. Suggested Indexes

Batch:

(user_id, project_id, requested_at DESC)
(project_id, status)

Job:

(batch_id, status)
(keyword_id, status)
(status, lease_expires_at)

Schedule:

(enabled, next_run_at)
(user_id, project_id)

Use exact naming consistent with repository conventions.

136. Schedule Uniqueness

Initial model should enforce:

one schedule per Project

for simplicity.

Unique:

(user_id, project_id)

137. Worker Repository Boundaries

Create repository/service separation consistent with earlier milestones.

Likely:

repositories/rank_check_batch.py
repositories/rank_check_job.py
repositories/project_rank_schedule.py

services/rank_check_batches.py
services/rank_check_jobs.py
services/rank_schedules.py
services/task_queue/

Do not put SQLAlchemy queries directly in route handlers.

138. Suggested Task Queue Package

Conceptually:

backend/app/services/task_queue/
├── base.py
├── types.py
├── factory.py
├── local.py
└── cloud_tasks.py

Adapt to current repository style.

139. Suggested Worker Package

Conceptually:

backend/app/services/workers/
├── rank_check_worker.py
└── job_claim.py

Do not over-fragment if existing service organization suggests a simpler layout.

140. Worker Route Separation

Internal routes should be clearly separated:

/internal/tasks/*
/internal/schedules/*

Do not mix with /api/v1 user endpoints.

141. OpenAPI Exposure

Consider excluding internal worker/scheduler endpoints from public OpenAPI schema in production.

Not mandatory if architecture makes this awkward, but preferred.

142. Request Authentication Context

Normal user APIs:

current_user.id

Internal worker:

IAM-authenticated service request
+
DB Job ownership

Never fake a normal end-user session inside worker.

143. Worker RankCheck Execution Contract

Refactor existing RankCheck execution into an application service callable as:

execute_rank_check(
    *,
    user_id,
    project_id,
    keyword_id,
)

or preferably a strongly typed command.

It must not require FastAPI Request.

The API and worker should share the same business service.

144. Transaction Boundaries

Recommended worker transactions:

Transaction A:
claim Job

provider I/O outside DB transaction

Transaction B:
existing RankCheck success/failure persistence
finalize Job
update Batch

Do not hold DB locks while waiting on SERP provider HTTP.

145. Failure Durability

If provider execution fails:

existing RankCheck failure history
+
Job failure/retry state

must be durable.

Avoid losing the reason because Cloud Tasks retries the HTTP request.

146. RankCheck Creation Timing

Preferred:

worker claims Job
→ creates/executes RankCheck using existing service

not during Batch creation.

This avoids creating thousands of pending RankChecks that may never execute.

If current M4 architecture strongly favors pre-creation, Codex may adapt, but must preserve idempotency and explain the decision.

147. Stale Running Job Recovery

Provide logic for:

status=running
lease_expires_at < now

Such Jobs are eligible for safe reclaim if:

attempt_count < max_attempts

Otherwise:

mark failed

148. Stale Batch Recovery

Batch status must eventually reflect terminal Jobs.

Provide maintenance/reconciliation logic that can recompute a stale Batch from Jobs.

This can run from dispatcher/recovery command.

149. Recovery Command

Add developer/admin command such as:

make recover-rank-jobs

or a backend script.

It may:

re-enqueue pending Jobs
reconcile stale running Jobs
recompute Batch status

Must be safe/idempotent.

150. Definition of Done — Batch / Job Models

[ ] RankCheckBatch exists
[ ] RankCheckJob exists
[ ] ProjectRankSchedule exists
[ ] migrations created
[ ] tenant ownership enforced
[ ] indexes/constraints added
[ ] existing ranking history preserved

151. Definition of Done — Async Execution

[ ] Project checks no longer execute SERP calls inside user HTTP request
[ ] single Keyword Check now is asynchronous
[ ] one Job represents one Keyword
[ ] API returns Batch/Job identity quickly
[ ] worker executes existing RankCheck service
[ ] Ranking persistence remains unchanged

152. Definition of Done — Cloud Tasks

[ ] task queue abstraction exists
[ ] local adapter exists
[ ] Cloud Tasks adapter exists
[ ] deterministic task names used
[ ] payload contains only version + job_id
[ ] OIDC worker invocation supported
[ ] queue settings are configuration-driven
[ ] business logic contains no Google SDK dependency

153. Definition of Done — Worker

[ ] Cloud Run-compatible worker exists
[ ] worker endpoint is internal
[ ] worker is stateless
[ ] atomic Job claiming works
[ ] execution lease works
[ ] duplicate delivery is idempotent
[ ] only one RankCheck is created per Job
[ ] terminal Jobs return success without duplicate execution

154. Definition of Done — Retry

[ ] provider retry remains separate
[ ] provider fallback remains separate
[ ] task/job retry exists
[ ] retryable vs terminal errors are classified
[ ] Cloud Tasks retry behavior is intentional
[ ] max attempts enforced
[ ] static budget exhaustion does not create rapid useless retries

155. Definition of Done — Progress

[ ] Batch counters are concurrency-safe
[ ] Batch status transitions are correct
[ ] progress API exists
[ ] Batch history exists
[ ] Job detail list exists or equivalent diagnostic path
[ ] Project UI shows queued/running/completed states
[ ] polling stops after terminal state

156. Definition of Done — Scheduler

[ ] Project schedule CRUD exists
[ ] one schedule per Project
[ ] daily supported
[ ] weekly supported
[ ] IANA timezone persisted
[ ] next_run_at stored in UTC
[ ] due-schedule dispatcher exists
[ ] duplicate dispatcher calls are safe
[ ] one Cloud Scheduler job can dispatch all due Projects
[ ] one schedule occurrence creates at most one Batch
[ ] catch-up does not create an unbounded backlog

157. Definition of Done — Cancellation / Recovery

[ ] Batch cancellation is best-effort and safe
[ ] cancelled queued Jobs do not execute
[ ] running Jobs may complete safely
[ ] stale running Jobs can recover
[ ] pending Jobs can be re-enqueued
[ ] Batch state can be reconciled

158. Definition of Done — Security

[ ] worker production invocation requires authenticated service identity
[ ] scheduler dispatcher invocation requires authenticated service identity
[ ] task payload cannot override ownership or provider
[ ] tenant isolation remains intact
[ ] no GCP credentials reach frontend
[ ] no SERP keys reach frontend
[ ] secrets do not appear in logs
[ ] least-privilege IAM documented

159. Definition of Done — Cost Safety

[ ] M5 does not require Memorystore
[ ] M5 does not require always-on VM workers
[ ] Cloud Run architecture supports scale-to-zero where practical
[ ] one Cloud Scheduler job can serve all Projects
[ ] queue rate limits configurable
[ ] batch size safety limit exists
[ ] task duplication protection exists
[ ] local development requires no paid GCP service

160. Definition of Done — Testing

[ ] full backend tests pass
[ ] full frontend tests pass
[ ] queue adapter tests pass
[ ] worker idempotency tests pass
[ ] concurrency tests pass
[ ] retry tests pass
[ ] scheduler tests pass
[ ] migration tests pass
[ ] tenant isolation tests pass
[ ] browser verification passes
[ ] local async ranking smoke passes
[ ] Cloud Tasks contract smoke passes
[ ] normal tests consume 0 real Cloud Tasks operations
[ ] normal tests consume 0 real SERP credits

161. Definition of Done — Quality

[ ] Ruff passes
[ ] Ruff format passes
[ ] mypy strict passes
[ ] ESLint passes
[ ] Prettier passes
[ ] TypeScript strict passes
[ ] npm audit acceptable
[ ] backend production image builds
[ ] worker production image/command builds
[ ] frontend production build passes
[ ] Alembic schema drift check passes
[ ] Docker services healthy

162. Definition of Done — Regression

[ ] M1 health/foundation regression passes
[ ] M2 authentication regression passes
[ ] M3 Project/Keyword regression passes
[ ] M3.1 Tracked Sites/Aliases regression passes
[ ] M4 Ranking Engine regression passes
[ ] M4.1 Multi-provider routing regression passes
[ ] DomainMatcher behavior unchanged
[ ] provider budgets/fallback unchanged
[ ] ranking history/latest behavior unchanged

163. Optional Real GCP Verification

Optional only:

[ ] one real Cloud Tasks enqueue/delivery
[ ] authenticated worker invocation
[ ] task reaches terminal Job state

If not configured:

SKIPPED — real GCP Cloud Tasks environment not configured

This must not block local M5 acceptance.

164. Required Verification Commands

Adapt exact commands to repository Makefile, but include at minimum:

docker compose build
docker compose up -d --build --wait

make check

make auth-smoke
make business-smoke
make tracked-site-smoke
make ranking-smoke
make provider-routing-smoke

make async-ranking-smoke
make cloud-tasks-contract-smoke

Also run:

migration upgrade
migration downgrade/re-upgrade where safe
alembic check

browser auth verification
browser Project verification
browser ranking verification
browser async Batch/schedule verification

backend production build
worker production build/command verification
frontend production build

docker compose ps

165. Optional Real Cloud Tasks Command

Recommended:

RUN_REAL_CLOUD_TASKS_SMOKE=true make cloud-tasks-smoke

It must:

be explicit opt-in
use minimal task count
not leak credentials
not be part of make check
prefer fake SERP execution

166. Verification Report

Create:

docs/verification-milestone-5.md

Include:

implementation summary

old synchronous architecture
new asynchronous architecture

Batch model
Job model
Schedule model

queue abstraction
Cloud Tasks adapter
local adapter

worker claim/idempotency design
execution lease
retry classification

Cloud Tasks retry configuration
Cloud Run worker configuration

scheduler dispatcher

API changes
frontend changes

migration details
files created/modified

exact commands executed
exact test counts/results

migration round-trip
schema drift

local async smoke
Cloud Tasks contract smoke
browser verification

security
IAM design

cost guardrails

optional real Cloud Tasks status

M1–M4.1 regression status

known limitations

full Definition of Done checklist

Do not claim a command passed unless it was actually executed.

167. Expected Known Limitations After M5

Document honestly:

Cloud Tasks is the only production queue adapter
no Pub/Sub event architecture
no Redis production queue
no Memorystore requirement

scheduler supports only simple frequencies
no arbitrary user cron

no billing
no plan-based rank-check quotas

no email/Slack notifications

no analytics dashboard beyond current ranking views
no competitor analysis

no multi-page SERP collection

provider budgets remain static backend configuration

no automatic provider balance synchronization

no advanced autoscaling optimizer

no distributed tracing requirement yet

168. Final M5 Architecture

User
 │
 │ Check Rankings / Check now
 ▼
Frontend
 │
 ▼
FastAPI API — Cloud Run
 │
 ├── create RankCheckBatch
 ├── create RankCheckJobs
 └── enqueue
       │
       ▼
   Cloud Tasks
       │
       ▼
Cloud Run Worker
       │
       ▼
existing RankCheckExecutionService
       │
       ▼
ProviderRouter
 ┌─────┴────────┐
 ▼              ▼
Serper        SerpApi
 └─────┬────────┘
       ▼
SerpSearchResult
       ▼
DomainMatcher
       ▼
RankCheck / Results / Rankings
       ▼
Job + Batch completion
       ▼
Frontend progress/history

Scheduled path:

Cloud Scheduler
      │
      ▼
Schedule Dispatcher
      │
      ▼
Due Project schedules
      │
      ▼
RankCheckBatch + Jobs
      │
      ▼
Cloud Tasks

169. Roadmap Position

After M5:

M1    Foundation                              ✅
M2    Authentication                          ✅
M3    Projects + Keywords                     ✅
M3.1  Tracked Sites + Domain Aliases          ✅
M4    SERP Provider + Ranking Engine           ✅
M4.1  Multi-provider Routing                   ✅
M5    Cloud Tasks + Cloud Run Worker           ← current
M6    Ranking Dashboard + Analytics
M7    Billing + Usage Limits
M8    Production Cloud Deployment

M5 should prepare deployment architecture for GCP, but it does not require full production deployment to complete the milestone.

170. Final Instruction to Codex

Implement this specification against the CURRENT M4.1 repository.

The current repository and completed migrations are the source of truth.

Before changing code, inspect:

M1–M4.1 specifications
M1–M4.1 verification reports
README
current source
current migrations
current tests
current Docker configuration
current RankCheck execution service
current ProviderRouter
current provider usage/budget implementation
current frontend ranking flow

Critical rules:

1. Do not rewrite the M4/M4.1 ranking engine.

2. A user HTTP request must not wait for SERP provider execution.

3. One RankCheckJob represents one Keyword.

4. PostgreSQL is the source of truth for Batch/Job state.

5. Cloud Tasks delivery is at-least-once; worker execution must be idempotent.

6. The same Job must never create duplicate RankCheck history.

7. Cloud Tasks is behind an application queue abstraction.

8. Local development and automated tests must not require GCP.

9. Normal tests must consume zero Cloud Tasks operations and zero SERP credits.

10. Cloud Run Worker is stateless and receives only a job identifier.

11. Worker request payload must not accept user ownership, provider, keyword, or SERP settings from the task caller.

12. Worker loads the authoritative Job from PostgreSQL.

13. Use authenticated Cloud Tasks → Cloud Run invocation.

14. Do not make the production worker publicly callable.

15. Keep provider retry, ProviderRouter fallback, and task/job retry as separate layers.

16. Do not add Redis/Memorystore as a production requirement.

17. Do not create one Cloud Scheduler job per Project.

18. Use one dispatcher schedule to find all due Project schedules.

19. Scheduled execution must be duplicate-safe.

20. Preserve tenant isolation, DomainMatcher behavior, provider budgets, provider fallback, ranking snapshots, and ranking history.

21. Do not add billing, DataForSEO, Pub/Sub, GKE, competitor analysis, or M6 functionality.

22. Keep cloud-cost defaults conservative.

Before completion:

run full backend tests
run full frontend tests

run queue adapter tests
run worker idempotency tests
run concurrency tests
run retry tests
run schedule tests

run migration tests
run alembic check

run all existing M1–M4.1 smoke tests
run local async ranking smoke
run Cloud Tasks contract smoke

run browser verification

run lint
run formatting
run strict typing

build API production image
verify Worker production command/image
build frontend production bundle

verify all Docker services healthy
verify M1–M4.1 regressions

Create:

docs/verification-milestone-5.md

Do not claim a check passed unless it was actually executed.

If a real GCP Cloud Tasks environment is unavailable, report the real smoke as truthfully skipped. The mandatory M5 implementation and verification must remain possible with local/mock infrastructure.