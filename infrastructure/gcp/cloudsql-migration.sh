#!/bin/sh
# Explicit operator actions; never run by application startup.
set -eu

PROJECT=${GCP_PROJECT_ID:-serp-saas}
REGION=${GCP_LOCATION:-asia-southeast1}
INSTANCE=${CLOUD_SQL_INSTANCE:-serp-saas}
CONNECTION="$PROJECT:$REGION:$INSTANCE"
REPOSITORY=${ARTIFACT_REPOSITORY:-serp-saas}
MIGRATION_ACCOUNT=${MIGRATION_SERVICE_ACCOUNT:-serp-migrations}
IDENTITY="$MIGRATION_ACCOUNT@$PROJECT.iam.gserviceaccount.com"
DATABASE_SECRET=${DATABASE_SECRET_NAME:-serp-database-url}
JOB=${MIGRATION_JOB_NAME:-serp-db-migrate}
ACTION=${1:-plan}

case "$ACTION" in
  plan)
    printf 'Project: %s\nRegion: %s\nCloud SQL: %s\nMigration identity: %s\nDatabase secret: %s\nJob: %s\n' \
      "$PROJECT" "$REGION" "$CONNECTION" "$IDENTITY" "$DATABASE_SECRET" "$JOB"
    printf '\nSteps: check -> prepare -> create-database-secret.py -> build-access -> build -> migrate\n'
    exit 0
    ;;
  check|prepare|build-access|build|migrate) ;;
  *) printf 'Usage: sh infrastructure/gcp/cloudsql-migration.sh [plan|check|prepare|build-access|build|migrate]\n' >&2; exit 2 ;;
esac

command -v gcloud >/dev/null 2>&1 || {
  printf 'gcloud is required. Run these commands from an authenticated Google Cloud Shell checkout.\n' >&2
  exit 1
}

case "$ACTION" in
  check)
    gcloud sql instances describe "$INSTANCE" --project="$PROJECT" \
      --format='table(name,databaseVersion,state,region,connectionName,ipAddresses.ipAddress)'
    gcloud sql databases describe serp_saas --instance="$INSTANCE" --project="$PROJECT"
    gcloud sql users list --instance="$INSTANCE" --project="$PROJECT" --format='table(name,type)'
    ;;
  prepare)
    gcloud services enable sqladmin.googleapis.com run.googleapis.com \
      artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com \
      --project="$PROJECT"
    # Lists must succeed before creating resources; a failed lookup is not absence.
    repositories=$(gcloud artifacts repositories list --project="$PROJECT" \
      --location="$REGION" --format='value(name.basename())')
    if ! printf '%s\n' "$repositories" | grep -Fxq "$REPOSITORY"; then
      gcloud artifacts repositories create "$REPOSITORY" --project="$PROJECT" \
        --location="$REGION" --repository-format=docker
    fi
    accounts=$(gcloud iam service-accounts list --project="$PROJECT" --format='value(email)')
    if ! printf '%s\n' "$accounts" | grep -Fxq "$IDENTITY"; then
      gcloud iam service-accounts create "$MIGRATION_ACCOUNT" --project="$PROJECT" \
        --display-name='Serp SaaS database migrations'
    fi
    gcloud projects add-iam-policy-binding "$PROJECT" \
      --member="serviceAccount:$IDENTITY" --role=roles/cloudsql.client --condition=None
    secrets=$(gcloud secrets list --project="$PROJECT" --format='value(name.basename())')
    if ! printf '%s\n' "$secrets" | grep -Fxq "$DATABASE_SECRET"; then
      gcloud secrets create "$DATABASE_SECRET" --project="$PROJECT" --replication-policy=automatic
    fi
    gcloud secrets add-iam-policy-binding "$DATABASE_SECRET" --project="$PROJECT" \
      --member="serviceAccount:$IDENTITY" --role=roles/secretmanager.secretAccessor --condition=None
    printf 'Infrastructure prepared. Add the database secret version with create-database-secret.py.\n'
    ;;
  build-access)
    # IAM for the build execution identity is separate from migration IAM.
    # Google may select the Compute Engine or legacy Cloud Build identity.
    build_account=$(gcloud builds get-default-service-account --project="$PROJECT" \
      --region="$REGION" --format='value(serviceAccountEmail)')
    build_account=${build_account##*/}
    case "$build_account" in
      *@*.gserviceaccount.com) ;;
      *) printf 'No default build service account was returned. Check Cloud Build service account settings.\n' >&2; exit 1 ;;
    esac
    gcloud projects add-iam-policy-binding "$PROJECT" \
      --member="serviceAccount:$build_account" --role=roles/cloudbuild.builds.builder --condition=None
    printf 'Build access configured for %s.\n' "$build_account"
    ;;
  build)
    : "${BACKEND_IMAGE_TAG:?Set a unique BACKEND_IMAGE_TAG for this release}"
    gcloud builds submit . --project="$PROJECT" --region="$REGION" \
      --config=infrastructure/gcp/cloudbuild-backend.yaml \
      --substitutions="_REGION=$REGION,_REPOSITORY=$REPOSITORY,_IMAGE_TAG=$BACKEND_IMAGE_TAG"
    printf 'Image: %s-docker.pkg.dev/%s/%s/backend:%s\n' "$REGION" "$PROJECT" "$REPOSITORY" "$BACKEND_IMAGE_TAG"
    ;;
  migrate)
    : "${BACKEND_IMAGE_TAG:?Set the BACKEND_IMAGE_TAG built for this release}"
    : "${DATABASE_SECRET_VERSION:?Set the numeric database secret version}"
    case "$DATABASE_SECRET_VERSION" in
      ''|*[!0-9]*) printf 'DATABASE_SECRET_VERSION must be a numeric version.\n' >&2; exit 2 ;;
    esac
    # A single task with no retry prevents concurrent/automatic migration attempts.
    # Migrations load DatabaseSettings, so runtime SMTP/queue secrets are not needed.
    gcloud run jobs deploy "$JOB" --project="$PROJECT" --region="$REGION" \
      --image="$REGION-docker.pkg.dev/$PROJECT/$REPOSITORY/backend:$BACKEND_IMAGE_TAG" \
      --service-account="$IDENTITY" --set-cloudsql-instances="$CONNECTION" \
      --set-secrets="DATABASE_URL=$DATABASE_SECRET:$DATABASE_SECRET_VERSION" \
      --tasks=1 --parallelism=1 --max-retries=0 --task-timeout=600s \
      --cpu=1 --memory=512Mi --command=sh \
      --args='-c,alembic upgrade head && alembic current'
    gcloud run jobs execute "$JOB" --project="$PROJECT" --region="$REGION" --wait
    printf 'Migration completed. Check logs for the current Alembic revision.\n'
    ;;
esac
