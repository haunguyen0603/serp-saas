# Cloud Tasks / Cloud Run deployment preparation

For the project's Cloud SQL PostgreSQL 16 instance and the initial database-only
migration job, follow [Cloud SQL initialization](cloud-sql-deployment.md) first.
After migration succeeds, follow the [API/worker deployment runbook](cloud-run-deployment.md).

M5 does not deploy GCP resources automatically. Local acceptance is zero-cost with
Docker, LocalTaskQueue and FakeSerpProvider. Cloud Tasks is the only production queue.

Use the backend production image for both services. API command: `python -m app`.
Worker command: `uvicorn app.worker_main:app --host 0.0.0.0 --port 8080`.
Deploy the worker with IAM authentication required, concurrency 1, min instances 0,
max instances 2 and timeout 300 seconds. Configure WORKER_DB_POOL_SIZE=2 and
WORKER_DB_MAX_OVERFLOW=0. A worker uses PostgreSQL directly and needs no Redis queue.

Configure TASK_QUEUE_PROVIDER=cloud_tasks, GCP_PROJECT_ID, GCP_LOCATION,
CLOUD_TASKS_QUEUE, CLOUD_TASKS_WORKER_URL (HTTPS service origin),
CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL, and SCHEDULER_SERVICE_ACCOUNT_EMAIL. Production
rejects local queues and incomplete OIDC configuration. The worker verifies Google
ID tokens and authorizes the specific caller email for each internal route, in addition
to Cloud Run IAM. Token audiences equal the worker service origin (`https://SERVICE.run.app`, no
trailing slash). Use the standard Authorization bearer header; do not substitute
X-Serverless-Authorization for the application-level signature check. See
[Cloud Run service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## IAM and provisioning

- API runtime: Cloud Tasks Enqueuer scoped to the queue and Service Account User
  (`iam.serviceAccounts.actAs`) on the dedicated task invocation account.
- Task invocation identity: Cloud Run Invoker on Worker only.
- Scheduler invocation identity: Cloud Run Invoker on Worker only. Scheduler calls
  the dispatch endpoint on this same private worker; the public user API has no
  dispatcher route.
- Worker runtime: Cloud Tasks Enqueuer for recovery, actAs on task identity, database
  access, and Secret Accessor only on its required secrets.
- Cloud Tasks service agent retains its required service-agent role. Do not grant
  Owner/Editor to any of these identities.

Create the queue once, then apply the environment-driven settings:

```sh
gcloud tasks queues create "${CLOUD_TASKS_QUEUE:-rank-checks}" \
  --project="$GCP_PROJECT_ID" --location="$GCP_LOCATION"
sh infrastructure/configure-rank-queue.sh
```

Use GCP environment variables from `.env.example`.
The script applies configurable dispatch rate/concurrency and bounded retry policy.
It is an explicit operator action, never application startup behavior.

Create one authenticated Scheduler HTTP job:

```sh
gcloud scheduler jobs create http rank-schedule-dispatch \
  --project="$GCP_PROJECT_ID" --location="$GCP_LOCATION" \
  --schedule='*/5 * * * *' --time-zone=UTC --http-method=POST \
  --uri="$CLOUD_TASKS_WORKER_URL/internal/schedules/dispatch" \
  --oidc-service-account-email="$SCHEDULER_SERVICE_ACCOUNT_EMAIL" \
  --oidc-token-audience="$CLOUD_TASKS_WORKER_URL"
```

Set queue defaults: max attempts 5, min backoff 30s, max backoff 300s, max retry duration
3600s. Cloud Tasks considers both attempt and duration thresholds when terminating
retries; 3600s is not an unconditional queue lifetime. See
[queue retry semantics](https://docs.cloud.google.com/tasks/docs/configuring-queues).
Application max claims independently enforces five attempts; early duplicates
and backoff rejections do not increase it. Scale safely instead of increasing dispatch
and provider concurrency together. Keep API and worker pool budgets below Cloud SQL's
connection limit. Set an Artifact Registry cleanup policy and use a small staging DB.

Use workload identity / runtime service accounts; no downloaded private keys in `.env`.
Signup verification also requires production SMTP configuration and an HTTPS
`AUTH_SITE_URL` matching the frontend origin. See [email verification](email-verification.md)
for auth mail settings, TLS, verification gates and local Mailpit acceptance.
Provide DATABASE_URL, JWT and SERP keys using Secret Manager. The existing asyncpg URL
configuration remains compatible with Cloud Run → Cloud SQL private/proxy connectivity.
No GCP or provider credentials belong in NEXT_PUBLIC variables. Configure all services
in compatible nearby regions; business code has no hardcoded region.

## Optional real smoke

`RUN_REAL_CLOUD_TASKS_SMOKE=true CLOUD_TASKS_SMOKE_JOB_ID=<dedicated pending Job UUID>
make cloud-tasks-smoke` submits one task and waits up to 60 seconds for success. The
worker environment determines provider cost: prefer a controlled non-production fake
worker. Do not enable real smoke in normal checks. Missing configuration is skipped.
Normal `make cloud-tasks-contract-smoke` uses a mocked SDK client with no credentials.

References: [Google authenticated HTTP tasks](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks),
[Cloud Tasks creation and OIDC](https://docs.cloud.google.com/tasks/docs/create-tasks).

## Environment reference

| Variable | Local/default | Cloud requirement |
| --- | --- | --- |
| TASK_QUEUE_PROVIDER | local | cloud_tasks in production |
| GCP_PROJECT_ID / GCP_LOCATION | empty | Required, deployment-specific |
| CLOUD_TASKS_QUEUE | rank-checks | Existing queue |
| CLOUD_TASKS_WORKER_URL | empty | HTTPS Cloud Run service origin |
| CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL | empty | Dedicated task caller |
| SCHEDULER_SERVICE_ACCOUNT_EMAIL | empty | Dedicated dispatcher caller |
| RANK_CHECK_BATCH_MAX_KEYWORDS | 5000 | Safety ceiling, not billing |
| RANK_CHECK_JOB_MAX_ATTEMPTS | 5 | Application claim limit |
| RANK_CHECK_JOB_LEASE_SECONDS | 300 | Align with worker timeout |
| TASK_DISPATCH_MAX_PER_SECOND | 2 | Apply using queue configuration script |
| TASK_MAX_CONCURRENT_DISPATCHES | 2 | Apply using queue configuration script |
| TASK_MIN_BACKOFF_SECONDS / TASK_MAX_BACKOFF_SECONDS | 30 / 300 | Queue and application backoff |
| TASK_MAX_RETRY_DURATION_SECONDS | 3600 | Queue setting and recovery age budget |
| WORKER_DB_POOL_SIZE / WORKER_DB_MAX_OVERFLOW | 2 / 0 | Worker HTTP engine pool |

Cloud Run min/max instances and request concurrency are deployment flags, not
application environment variables. Local Compose worker is the development loop;
production must use the HTTP worker command instead. Compose is intentionally for
local queue verification; supply GCP environment variables directly to Cloud Run.

## Recovery procedure

1. Inspect owner-scoped batch/job APIs and safe structured job events. Check queue
   delivery errors and database health; do not log tokens or raw provider responses.
2. Run `make recover-rank-jobs` locally (or `python -m scripts.rank_jobs` in the
   configured backend environment). Local recovery uses the normal worker pipeline.
3. For cloud pending jobs, recovery re-enqueues using the same deterministic name.
   It sends at most 100 jobs per pass with at most ten concurrent enqueue calls.
   Run additional passes for large backlogs. The periodic dispatcher also does this.
4. Cloud redelivery reclaims expired execution leases subject to the attempt limit.
   Recovery closes abandoned jobs once their last state update is older than retry
   duration plus lease headroom. It preserves any already-succeeded RankCheck.
5. Terminal `TASK_DELIVERY_EXHAUSTED` jobs require a new manual batch after correcting
   the infrastructure issue. Do not reset terminal rows or rotate deterministic
   names blindly: Cloud Tasks may retain a deduplication tombstone.

With default chunks, large cloud batches may need several dispatcher passes before
all jobs enqueue. This is a bounded staging tradeoff; tune dispatcher cadence and
recovery passes before increasing queue/provider throughput. Local loop drains every
two seconds. No automatic operational or ranking history deletion is implemented.
