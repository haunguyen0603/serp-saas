#!/bin/sh
# Operator phases for API/worker deployment; no phase runs at application startup.
set -eu
repo_root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo_root"
PROJECT=${GCP_PROJECT_ID:-serp-saas}
REGION=${GCP_LOCATION:-asia-southeast1}
ACTION=${1:-plan}
case "$ACTION" in
  plan)
    printf 'Project: %s\nRegion: %s\nServices: serp-api (public), serp-worker (IAM required)\n' "$PROJECT" "$REGION"
    printf 'Steps: prepare -> runtime secret versions -> config -> worker -> worker-iam -> api -> scheduler -> verify\n'
    exit 0 ;;
  prepare|config|worker|worker-iam|api|scheduler|verify) ;;
  *) printf 'Usage: %s [plan|prepare|config|worker|worker-iam|api|scheduler|verify]\n' "$0" >&2; exit 2 ;;
esac
command -v gcloud >/dev/null 2>&1 || { printf 'Run in authenticated Cloud Shell.\n' >&2; exit 1; }
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
case "$PROJECT_NUMBER" in ''|*[!0-9]*) printf 'Could not read project number.\n' >&2; exit 1 ;; esac
export GCP_PROJECT_ID="$PROJECT" GCP_LOCATION="$REGION" PROJECT_NUMBER
BUCKET="$PROJECT-reports-$PROJECT_NUMBER"
WORKER_URL="https://serp-worker-$PROJECT_NUMBER.$REGION.run.app"
API_URL="https://serp-api-$PROJECT_NUMBER.$REGION.run.app"
TASK_ACCOUNT="serp-task-invoker@$PROJECT.iam.gserviceaccount.com"
SCHEDULER_ACCOUNT="serp-scheduler-invoker@$PROJECT.iam.gserviceaccount.com"

case "$ACTION" in
  prepare)
    gcloud services enable run.googleapis.com sqladmin.googleapis.com \
      cloudtasks.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com \
      secretmanager.googleapis.com iam.googleapis.com --project="$PROJECT"
    accounts=$(gcloud iam service-accounts list --project="$PROJECT" --format='value(email)')
    for name in serp-api serp-worker serp-task-invoker serp-scheduler-invoker; do
      if ! printf '%s\n' "$accounts" | grep -Fxq "$name@$PROJECT.iam.gserviceaccount.com"; then
        gcloud iam service-accounts create "$name" --project="$PROJECT" --display-name="$name"
      fi
    done
    queues=$(gcloud tasks queues list --project="$PROJECT" --location="$REGION" --format='value(name.basename())')
    if ! printf '%s\n' "$queues" | grep -Fxq rank-checks; then
      gcloud tasks queues create rank-checks --project="$PROJECT" --location="$REGION"
    fi
    CLOUD_TASKS_QUEUE=rank-checks sh infrastructure/configure-rank-queue.sh
    buckets=$(gcloud storage buckets list --project="$PROJECT" --format='value(name)')
    if ! printf '%s\n' "$buckets" | grep -Eq "^(gs://)?$BUCKET/?$"; then
      gcloud storage buckets create "gs://$BUCKET" --project="$PROJECT" --location="$REGION" \
        --uniform-bucket-level-access --public-access-prevention
    fi
    gcloud storage buckets update "gs://$BUCKET" --uniform-bucket-level-access --public-access-prevention
    existing_secrets=$(gcloud secrets list --project="$PROJECT" --format='value(name.basename())')
    for name in serp-jwt-key serp-serper-key serp-serpapi-key serp-auth-smtp-password; do
      if ! printf '%s\n' "$existing_secrets" | grep -Fxq "$name"; then
        gcloud secrets create "$name" --project="$PROJECT" --replication-policy=automatic
      fi
    done
    for runtime in serp-api serp-worker; do
      identity="$runtime@$PROJECT.iam.gserviceaccount.com"
      gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$identity" \
        --role=roles/cloudsql.client --condition=None
      gcloud tasks queues add-iam-policy-binding rank-checks --project="$PROJECT" --location="$REGION" \
        --member="serviceAccount:$identity" --role=roles/cloudtasks.enqueuer
      gcloud iam service-accounts add-iam-policy-binding "$TASK_ACCOUNT" --project="$PROJECT" \
        --member="serviceAccount:$identity" --role=roles/iam.serviceAccountUser --condition=None
      gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
        --member="serviceAccount:$identity" --role=roles/storage.objectUser
      for name in serp-database-url serp-jwt-key serp-serper-key serp-serpapi-key serp-auth-smtp-password; do
        gcloud secrets add-iam-policy-binding "$name" --project="$PROJECT" \
          --member="serviceAccount:$identity" --role=roles/secretmanager.secretAccessor --condition=None
      done
    done
    printf 'Runtime infrastructure ready. Add JWT, Serper and actual SMTP password secret versions next.\n'
    printf 'Optional SerpAPI: add serp-serpapi-key and export SERPAPI_SECRET_VERSION to inject it during deployment.\n'
    ;;
  config)
    python3 infrastructure/gcp/create-cloud-run-config.py
    ;;
  worker|api)
    config_file="$repo_root/.env.cloud-run.yaml"
    test -f "$config_file" || { printf 'Run the config phase after obtaining real SMTP settings.\n' >&2; exit 1; }
    python3 - "$config_file" "$PROJECT" "$REGION" "$WORKER_URL" "$BUCKET" <<'PY'
import json
import sys

path, project, region, worker, bucket = sys.argv[1:]
with open(path) as stream:
    config = json.load(stream)
expected = {
    "GCP_PROJECT_ID": project,
    "GCP_LOCATION": region,
    "CLOUD_TASKS_WORKER_URL": worker,
    "REPORT_STORAGE_BUCKET": bucket,
    "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL": f"serp-task-invoker@{project}.iam.gserviceaccount.com",
    "SCHEDULER_SERVICE_ACCOUNT_EMAIL": f"serp-scheduler-invoker@{project}.iam.gserviceaccount.com",
}
if any(config.get(key) != value for key, value in expected.items()):
    sys.exit("Runtime profile does not match this deployment. Run config again.")
if not all(isinstance(value, str) for value in config.values()):
    sys.exit("Cloud Run environment values must all be strings.")
PY
    image=${BACKEND_IMAGE:-}
    if test -z "$image"; then
      image=$(gcloud run jobs describe serp-db-migrate --project="$PROJECT" --region="$REGION" \
        --format='value(spec.template.spec.template.spec.containers[0].image)')
    fi
    test -n "$image" || { printf 'Set BACKEND_IMAGE to the production image used by the successful migration.\n' >&2; exit 1; }
    db_version=${DATABASE_SECRET_VERSION:-1}
    jwt_version=${JWT_SECRET_VERSION:-1}
    serper_version=${SERPER_SECRET_VERSION:-1}
    serpapi_version=${SERPAPI_SECRET_VERSION:-}
    smtp_version=${SMTP_SECRET_VERSION:-1}
    set -- "serp-database-url:$db_version" "serp-jwt-key:$jwt_version" \
      "serp-serper-key:$serper_version" "serp-auth-smtp-password:$smtp_version"
    if test -n "$serpapi_version"; then
      set -- "$@" "serp-serpapi-key:$serpapi_version"
    fi
    for entry in "$@"; do
      name=${entry%:*}; version=${entry##*:}
      case "$version" in ''|*[!0-9]*) printf 'Secret versions must be numeric.\n' >&2; exit 1 ;; esac
      state=$(gcloud secrets versions describe "$version" --secret="$name" --project="$PROJECT" --format='value(state)')
      test "$state" = ENABLED || { printf 'Secret version %s is not enabled.\n' "$entry" >&2; exit 1; }
    done
    secret_flags="DATABASE_URL=serp-database-url:$db_version,JWT_SECRET_KEY=serp-jwt-key:$jwt_version,SERPER_API_KEY=serp-serper-key:$serper_version,AUTH_SMTP_PASSWORD=serp-auth-smtp-password:$smtp_version"
    if test -n "$serpapi_version"; then
      secret_flags="$secret_flags,SERPAPI_API_KEY=serp-serpapi-key:$serpapi_version"
    fi
    if test "$ACTION" = worker; then
      gcloud run deploy serp-worker --project="$PROJECT" --region="$REGION" --image="$image" \
        --execution-environment=gen2 --service-account="serp-worker@$PROJECT.iam.gserviceaccount.com" \
        --set-cloudsql-instances="$PROJECT:$REGION:serp-saas" \
        --env-vars-file="$config_file" --set-secrets="$secret_flags" \
        --command=uvicorn --args=app.worker_main:app,--host,0.0.0.0,--port,8080 \
        --port=8080 --cpu=1 --memory=512Mi --concurrency=1 --timeout=300s \
        --min-instances=0 --max-instances=2 --ingress=all --no-allow-unauthenticated
    else
      gcloud run deploy serp-api --project="$PROJECT" --region="$REGION" --image="$image" \
        --execution-environment=gen2 --service-account="serp-api@$PROJECT.iam.gserviceaccount.com" \
        --set-cloudsql-instances="$PROJECT:$REGION:serp-saas" \
        --env-vars-file="$config_file" --set-secrets="$secret_flags" \
        --command=python --args=-m,app --port=8080 --cpu=1 --memory=512Mi \
        --concurrency=8 --timeout=300s --min-instances=0 --max-instances=2 \
        --no-cpu-throttling --ingress=all --allow-unauthenticated
    fi
    ;;
  worker-iam)
    for identity in "$TASK_ACCOUNT" "$SCHEDULER_ACCOUNT"; do
      gcloud run services add-iam-policy-binding serp-worker --project="$PROJECT" --region="$REGION" \
        --member="serviceAccount:$identity" --role=roles/run.invoker --condition=None
    done
    ;;
  scheduler)
    jobs=$(gcloud scheduler jobs list --project="$PROJECT" --location="$REGION" --format='value(name.basename())')
    verb=create
    if printf '%s\n' "$jobs" | grep -Fxq rank-schedule-dispatch; then verb=update; fi
    gcloud scheduler jobs "$verb" http rank-schedule-dispatch --project="$PROJECT" --location="$REGION" \
      --schedule='*/5 * * * *' --time-zone=UTC --http-method=POST \
      --uri="$WORKER_URL/internal/schedules/dispatch" --oidc-service-account-email="$SCHEDULER_ACCOUNT" \
      --oidc-token-audience="$WORKER_URL" --attempt-deadline=300s
    ;;
  verify)
    for name in serp-worker serp-api; do
      gcloud run services describe "$name" --project="$PROJECT" --region="$REGION" \
        --format='yaml(status.url,status.conditions)'
    done
    curl --fail --show-error "$API_URL/health"
    curl --fail --show-error "$API_URL/health/db"
    status=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$WORKER_URL/health")
    case "$status" in 401|403) printf '\nWorker blocks anonymous access (%s).\n' "$status" ;; \
      *) printf '\nUnexpected anonymous worker status: %s\n' "$status" >&2; exit 1 ;; esac
    printf 'API: %s\nWorker: %s\n' "$API_URL" "$WORKER_URL"
    ;;
esac
