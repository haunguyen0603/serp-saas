#!/bin/sh
# Called by repository triggers after tests/build/push, against existing services.
set -eu
component=${1:-}
case "$component" in
  frontend|backend) ;;
  *) printf 'Usage: %s [frontend|backend]\n' "$0" >&2; exit 2 ;;
esac
: "${GCP_PROJECT_ID:?}" "${GCP_LOCATION:?}" "${RELEASE_IMAGE:?}"
: "${RELEASE_BUILD_ID:?}" "${RELEASE_LOCK_BUCKET:?}"
if test "$component" = frontend; then
  : "${RELEASE_SITE_URL:?}" "${RELEASE_APP_URL:?}"
fi
lock_uri="gs://$RELEASE_LOCK_BUCKET/$component.lock"
lock_file=$(mktemp)
printf '%s\n' "$RELEASE_BUILD_ID" > "$lock_file"
# Atomic acquisition prevents concurrent migrations and interleaved API/worker updates.
if ! gcloud storage cp "$lock_file" "$lock_uri" --if-generation-match=0 --project="$GCP_PROJECT_ID"; then
  rm -f "$lock_file"
  printf 'Release lock unavailable: %s. Check active builds and bucket IAM; rerun the latest commit.\n' "$lock_uri" >&2
  exit 1
fi
rm -f "$lock_file"
generation=$(gcloud storage objects describe "$lock_uri" --project="$GCP_PROJECT_ID" --format='value(generation)')
case "$generation" in
  ''|*[!0-9]*) printf 'Could not read release lock generation; inspect %s.\n' "$lock_uri" >&2; exit 1 ;;
esac
cleanup() {
  result=$?
  trap - EXIT
  # Never delete a lock replaced by an operator or another build.
  if ! gcloud storage rm "$lock_uri" --if-generation-match="$generation" --project="$GCP_PROJECT_ID"; then
    printf 'Could not release lock %s; inspect it before another release.\n' "$lock_uri" >&2
    if test "$result" -eq 0; then result=1; fi
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if test "$component" = frontend; then
  # Partial image update preserves runtime configuration and IAM.
  gcloud run services update serp-web --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
    --image="$RELEASE_IMAGE" --quiet
  gcloud run services update-traffic serp-web --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
    --to-latest --quiet
  curl --fail --silent --show-error --retry 3 --max-time 30 --output /dev/null "$RELEASE_SITE_URL/"
  curl --fail --silent --show-error --retry 3 --max-time 30 --output /dev/null "$RELEASE_APP_URL/login"
else
  # Verify both services exist before running a migration; this is not bootstrap.
  for service in serp-api serp-worker; do
    gcloud run services describe "$service" --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
      --format='value(metadata.name)' >/dev/null
  done
  # Keep the migration job's existing Cloud SQL, identity and pinned secret version.
  gcloud run jobs update serp-db-migrate --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
    --image="$RELEASE_IMAGE" --quiet
  gcloud run jobs execute serp-db-migrate --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
    --wait --quiet
  for service in serp-worker serp-api; do
    gcloud run services update "$service" --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
      --image="$RELEASE_IMAGE" --quiet
    gcloud run services update-traffic "$service" --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
      --to-latest --quiet
  done
  api_url=$(gcloud run services describe serp-api --project="$GCP_PROJECT_ID" --region="$GCP_LOCATION" \
    --format='value(status.url)')
  curl --fail --silent --show-error --retry 3 --max-time 30 "$api_url/health/db"
fi
printf '\nReleased %s image %s (build %s).\n' "$component" "$RELEASE_IMAGE" "$RELEASE_BUILD_ID"
