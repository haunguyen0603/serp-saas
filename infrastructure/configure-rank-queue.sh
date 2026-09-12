#!/bin/sh
# Explicit operator command; never invoked by API startup or automated tests.
set -eu
: "${GCP_PROJECT_ID:?required}" "${GCP_LOCATION:?required}"
gcloud tasks queues update "${CLOUD_TASKS_QUEUE:-rank-checks}" \
  --project="$GCP_PROJECT_ID" --location="$GCP_LOCATION" \
  --max-dispatches-per-second="${TASK_DISPATCH_MAX_PER_SECOND:-2}" \
  --max-concurrent-dispatches="${TASK_MAX_CONCURRENT_DISPATCHES:-2}" \
  --max-attempts="${RANK_CHECK_JOB_MAX_ATTEMPTS:-5}" \
  --min-backoff="${TASK_MIN_BACKOFF_SECONDS:-30}s" \
  --max-backoff="${TASK_MAX_BACKOFF_SECONDS:-300}s" \
  --max-retry-duration="${TASK_MAX_RETRY_DURATION_SECONDS:-3600}s"
