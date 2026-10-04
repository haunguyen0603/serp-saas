#!/bin/sh
# Run from authenticated Cloud Shell after committing the CI files to GitHub.
set -eu
PROJECT=${GCP_PROJECT_ID:-serp-saas}
REGION=${GCP_LOCATION:-asia-southeast1}
REPOSITORY=${ARTIFACT_REPOSITORY:-serp-saas}
LOCK_BUCKET=${RELEASE_LOCK_BUCKET:-$PROJECT-ci-locks}
ACTION=${1:-plan}
case "$ACTION" in
  plan)
    printf 'Project: %s\nRegion: %s\nRepository: %s\nRelease locks: gs://%s\n' "$PROJECT" "$REGION" "$REPOSITORY" "$LOCK_BUCKET"
    printf 'Triggers: serp-web-main, serp-backend-main (push to main)\nSteps: prepare -> link GitHub in Developer Connect -> triggers\n'
    exit 0 ;;
  prepare|triggers) ;;
  *) printf 'Usage: %s [plan|prepare|triggers]\n' "$0" >&2; exit 2 ;;
esac
command -v gcloud >/dev/null 2>&1 || { printf 'Run in authenticated Cloud Shell.\n' >&2; exit 1; }
if test "$ACTION" = prepare; then
  # Fail before provisioning if the initial deployment is incomplete.
  for service in serp-web serp-api serp-worker; do
    gcloud run services describe "$service" --project="$PROJECT" --region="$REGION" \
      --format='value(metadata.name)' >/dev/null
  done
  gcloud run jobs describe serp-db-migrate --project="$PROJECT" --region="$REGION" \
    --format='value(metadata.name)' >/dev/null
  gcloud services enable cloudbuild.googleapis.com developerconnect.googleapis.com \
    run.googleapis.com artifactregistry.googleapis.com logging.googleapis.com \
    storage.googleapis.com cloudresourcemanager.googleapis.com --project="$PROJECT"
  accounts=$(gcloud iam service-accounts list --project="$PROJECT" --format='value(email)')
  buckets=$(gcloud storage buckets list --project="$PROJECT" --format='value(name)')
  if ! printf '%s\n' "$buckets" | grep -Eq "^(gs://)?$LOCK_BUCKET/?$"; then
    gcloud storage buckets create "gs://$LOCK_BUCKET" --project="$PROJECT" --location="$REGION" \
      --uniform-bucket-level-access --public-access-prevention
  fi
  for name in serp-ci-web serp-ci-backend; do
    identity="$name@$PROJECT.iam.gserviceaccount.com"
    member="serviceAccount:$identity"
    if ! printf '%s\n' "$accounts" | grep -Fxq "$identity"; then
      gcloud iam service-accounts create "$name" --project="$PROJECT" --display-name="$name"
    fi
    for role in roles/logging.logWriter roles/developerconnect.readTokenAccessor; do
      gcloud projects add-iam-policy-binding "$PROJECT" --member="$member" --role="$role" --condition=None
    done
    gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" --project="$PROJECT" \
      --location="$REGION" --member="$member" --role=roles/artifactregistry.writer --condition=None
    gcloud storage buckets add-iam-policy-binding "gs://$LOCK_BUCKET" \
      --member="$member" --role=roles/storage.objectUser
    if test "$name" = serp-ci-web; then services=serp-web; else services='serp-api serp-worker'; fi
    for service in $services; do
      runtime=$(gcloud run services describe "$service" --project="$PROJECT" --region="$REGION" \
        --format='value(spec.template.spec.serviceAccountName)')
      test -n "$runtime" || { printf 'No runtime identity on %s.\n' "$service" >&2; exit 1; }
      gcloud run services add-iam-policy-binding "$service" --project="$PROJECT" --region="$REGION" \
        --member="$member" --role=roles/run.developer --condition=None
      gcloud iam service-accounts add-iam-policy-binding "$runtime" --project="$PROJECT" \
        --member="$member" --role=roles/iam.serviceAccountUser --condition=None
    done
    if test "$name" = serp-ci-backend; then
      runtime=$(gcloud run jobs describe serp-db-migrate --project="$PROJECT" --region="$REGION" \
        --format='value(spec.template.spec.template.spec.serviceAccountName)')
      test -n "$runtime" || { printf 'No migration identity.\n' >&2; exit 1; }
      gcloud run jobs add-iam-policy-binding serp-db-migrate --project="$PROJECT" --region="$REGION" \
        --member="$member" --role=roles/run.developer --condition=None
      gcloud iam service-accounts add-iam-policy-binding "$runtime" --project="$PROJECT" \
        --member="$member" --role=roles/iam.serviceAccountUser --condition=None
    fi
  done
  printf 'CI identities ready. Link GitHub in Developer Connect in %s, then run triggers.\n' "$REGION"
else
  : "${GIT_REPOSITORY_LINK:?Copy the full Developer Connect gitRepositoryLinks resource name.}"
  # A connection/trigger may be in another region than the deployed services.
  # Validate each resource segment so a clone URL cannot be appended as a link ID.
  BUILD_REGION=$(python3 - "$GIT_REPOSITORY_LINK" <<'PY'
import re
import sys

match = re.fullmatch(
    r"projects/([A-Za-z0-9_-]+)/locations/([a-z0-9-]+)/"
    r"connections/([A-Za-z0-9_-]+)/gitRepositoryLinks/([A-Za-z0-9_-]+)",
    sys.argv[1],
)
if not match:
    sys.exit(
        "GIT_REPOSITORY_LINK must be a complete Developer Connect resource name "
        "returned by --format='value(name)', not a GitHub/clone/proxy URL."
    )
print(match.group(2))
PY
  )
  SITE_URL=${FRONTEND_ORIGIN:-https://serp-web-833917440392.asia-southeast1.run.app}
  APP_URL=${FRONTEND_APP_ORIGIN:-$SITE_URL}
  API_URL=${FRONTEND_API_URL:-https://serp-api-833917440392.asia-southeast1.run.app}
  python3 - "$SITE_URL" "$APP_URL" "$API_URL" <<'PY'
import sys
from urllib.parse import urlsplit

for origin in sys.argv[1:]:
    url = urlsplit(origin)
    if (
        url.scheme != "https" or not url.hostname or url.path or url.query
        or url.fragment or url.username or url.password
        or any(char in origin for char in ",|\r\n")
    ):
        sys.exit("Frontend/API URLs must be HTTPS origins without a trailing slash.")
PY
  printf 'Trigger/build region: %s\nCloud Run/Artifact Registry region: %s\n' "$BUILD_REGION" "$REGION"
  existing=$(gcloud builds triggers list --project="$PROJECT" --region="$BUILD_REGION" --format='value(name)')
  for component in frontend backend; do
    if test "$component" = frontend; then
      name=serp-web-main
      account=serp-ci-web
      included='frontend/**,infrastructure/docker/frontend.Dockerfile,infrastructure/gcp/cloudbuild-frontend-cd.yaml,infrastructure/gcp/cloud-run-release.sh,.dockerignore'
      substitutions="_REGION=$REGION,_REPOSITORY=$REPOSITORY,_LOCK_BUCKET=$LOCK_BUCKET,_SITE_URL=$SITE_URL,_APP_URL=$APP_URL,_API_URL=$API_URL"
      service=serp-web
    else
      name=serp-backend-main
      account=serp-ci-backend
      included='backend/**,infrastructure/docker/backend.Dockerfile,infrastructure/gcp/cloudbuild-backend-cd.yaml,infrastructure/gcp/cloud-run-release.sh,.dockerignore'
      substitutions="_REGION=$REGION,_REPOSITORY=$REPOSITORY,_LOCK_BUCKET=$LOCK_BUCKET"
      service=serp-api
    fi
    if printf '%s\n' "$existing" | grep -Fxq "$name"; then
      set -- update developer-connect "$name" "--update-substitutions=$substitutions"
    else
      set -- create developer-connect "--name=$name" "--substitutions=$substitutions"
    fi
    trigger_id=$(gcloud alpha builds triggers "$@" --project="$PROJECT" --region="$BUILD_REGION" \
      --git-repository-link="$GIT_REPOSITORY_LINK" --branch-pattern='^main$' \
      --build-config="infrastructure/gcp/cloudbuild-$component-cd.yaml" \
      --included-files="$included" \
      --service-account="projects/$PROJECT/serviceAccounts/$account@$PROJECT.iam.gserviceaccount.com" \
      --format='value(id)')
    test -n "$trigger_id" || { printf 'No trigger ID returned.\n' >&2; exit 1; }
    gcloud run services update "$service" --project="$PROJECT" --region="$REGION" \
      --update-labels="gcb-trigger-id=$trigger_id" --quiet
    if test "$component" = backend; then
      gcloud run services update serp-worker --project="$PROJECT" --region="$REGION" \
        --update-labels="gcb-trigger-id=$trigger_id" --quiet
    fi
  done
  printf 'Triggers configured. Run each once in Cloud Build, then verify build and release logs.\n'
fi
