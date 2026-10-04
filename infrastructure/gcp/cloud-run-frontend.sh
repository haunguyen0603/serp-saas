#!/bin/sh
# Run explicitly from Cloud Shell after the API/worker deployment succeeds.
set -eu
repo_root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo_root"
PROJECT=${GCP_PROJECT_ID:-serp-saas}
REGION=${GCP_LOCATION:-asia-southeast1}
ACTION=${1:-plan}
case "$ACTION" in
  plan)
    printf 'Frontend: serp-web in %s / %s\n' "$PROJECT" "$REGION"
    printf 'Steps: export FRONTEND_IMAGE_TAG -> build -> deploy -> auth-origin -> verify\n'
    exit 0 ;;
  build|deploy|auth-origin|verify) ;;
  *) printf 'Usage: %s [plan|build|deploy|auth-origin|verify]\n' "$0" >&2; exit 2 ;;
esac
command -v gcloud >/dev/null 2>&1 || { printf 'Run in authenticated Cloud Shell.\n' >&2; exit 1; }
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
case "$PROJECT_NUMBER" in ''|*[!0-9]*) printf 'Could not read project number.\n' >&2; exit 1 ;; esac
SITE_URL=${FRONTEND_ORIGIN:-https://serp-web-$PROJECT_NUMBER.$REGION.run.app}
APP_URL=${FRONTEND_APP_ORIGIN:-$SITE_URL}
API_URL=${FRONTEND_API_URL:-}
if test -z "$API_URL"; then
  API_URL=$(gcloud run services describe serp-api --project="$PROJECT" --region="$REGION" --format='value(status.url)')
fi
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
case "$ACTION" in
  build|deploy)
    : "${FRONTEND_IMAGE_TAG:?Export FRONTEND_IMAGE_TAG before build and keep it for deploy.}"
    case "$FRONTEND_IMAGE_TAG" in
      ''|[.-]*|*[!a-zA-Z0-9_.-]*) printf 'Invalid frontend image tag.\n' >&2; exit 1 ;;
    esac
    test "${#FRONTEND_IMAGE_TAG}" -le 128 || { printf 'Frontend image tag is too long.\n' >&2; exit 1; }
    IMAGE="$REGION-docker.pkg.dev/$PROJECT/serp-saas/frontend:$FRONTEND_IMAGE_TAG"
    ;;
esac
case "$ACTION" in
  build)
    gcloud builds submit . --project="$PROJECT" \
      --config=infrastructure/gcp/cloudbuild-frontend.yaml \
      --substitutions="_REGION=$REGION,_IMAGE_TAG=$FRONTEND_IMAGE_TAG,_API_URL=$API_URL,_SITE_URL=$SITE_URL,_APP_URL=$APP_URL"
    printf 'Built frontend image: %s\nKeep FRONTEND_IMAGE_TAG for deploy.\n' "$IMAGE"
    ;;
  deploy)
    identity="serp-web@$PROJECT.iam.gserviceaccount.com"
    accounts=$(gcloud iam service-accounts list --project="$PROJECT" --format='value(email)')
    if ! printf '%s\n' "$accounts" | grep -Fxq "$identity"; then
      gcloud iam service-accounts create serp-web --project="$PROJECT" --display-name=serp-web
    fi
    gcloud run deploy serp-web --project="$PROJECT" --region="$REGION" --image="$IMAGE" \
      --execution-environment=gen2 --service-account="$identity" \
      --port=3000 --cpu=1 --memory=512Mi --concurrency=20 --timeout=300s \
      --min-instances=0 --max-instances=2 --ingress=all --allow-unauthenticated
    printf 'Website origin: %s\nApplication origin: %s\n' "$SITE_URL" "$APP_URL"
    ;;
  auth-origin)
    cors=$(python3 - "$SITE_URL" "$APP_URL" <<'PY'
import json
import sys
print(json.dumps(list(dict.fromkeys(sys.argv[1:])), separators=(",", ":")))
PY
    )
    # Partial update preserves existing secret bindings, SMTP and SERP settings.
    gcloud run services update serp-api --project="$PROJECT" --region="$REGION" \
      --update-env-vars="^|^AUTH_SITE_URL=$APP_URL|CORS_ORIGINS=$cors"
    python3 - "$repo_root/.env.cloud-run.yaml" "$APP_URL" "$cors" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.is_file():
    config = json.loads(path.read_text())
    config["AUTH_SITE_URL"] = sys.argv[2]
    config["CORS_ORIGINS"] = sys.argv[3]
    path.write_text(json.dumps(config, indent=2) + "\n")
PY
    ;;
  verify)
    gcloud run services describe serp-web --project="$PROJECT" --region="$REGION" \
      --format='yaml(status.url,status.conditions)'
    curl --fail --silent --show-error --output /dev/null "$SITE_URL/"
    curl --fail --silent --show-error --output /dev/null "$APP_URL/login"
    curl --fail --show-error "$API_URL/health/db"
    printf '\nWebsite: %s\nApplication: %s\nAPI: %s\nNext: test signup, verification, login/refresh, ranking and reports in a browser.\n' "$SITE_URL" "$APP_URL" "$API_URL"
    ;;
esac
