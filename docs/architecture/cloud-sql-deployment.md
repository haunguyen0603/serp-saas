# Cloud SQL initialization for Serp SaaS

This runbook prepares the existing **empty** PostgreSQL 16 instance and runs
Alembic migrations from a Cloud Run job. API/worker deployment follows afterward;
creating the schema does not make the website public.

## Deployment values

| Setting                               | Value                                               |
| ------------------------------------- | --------------------------------------------------- |
| Project                               | `serp-saas`                                         |
| Region                                | `asia-southeast1` (Singapore)                       |
| Cloud SQL connection name             | `serp-saas:asia-southeast1:serp-saas`               |
| Public IP, provided by operator       | `136.85.36.202`                                     |
| Database                              | `serp_saas`                                         |
| PostgreSQL user                       | `serp_app`                                          |
| Proposed Artifact Registry repository | `serp-saas`                                         |
| Proposed migration service account    | `serp-migrations@serp-saas.iam.gserviceaccount.com` |
| Proposed database URL secret          | `serp-database-url`                                 |
| Proposed migration job                | `serp-db-migrate`                                   |

Resource names below are proposed names; the instance/database/user above were
provided by the operator. Their cloud state has not yet been checked from this
workspace, which has no `gcloud` installation. No cloud resource query or
deployment has been executed here.

## Connection

Use Cloud Run's Cloud SQL connection and its Unix socket:

```text
postgresql+asyncpg://serp_app:URL_ENCODED_PASSWORD@/serp_saas?host=/cloudsql/serp-saas:asia-southeast1:serp-saas&ssl=disable
```

`ssl=disable` applies to the same-container Unix socket. Cloud SQL Auth Proxy
encrypts the connection to Cloud SQL. This setup uses built-in PostgreSQL
username/password authentication plus IAM permission to establish the connection;
it does not enable IAM database authentication. The application does not dial
`136.85.36.202:5432` directly. Authorized networks are not needed for the proxy
connection. Keep the instance's public IP enabled for this connection path.
See [Cloud Run connections](https://docs.cloud.google.com/sql/docs/postgres/connect-run)
and [Cloud SQL Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/sql-proxy).

The API's settings now accept this socket URL as well as the existing local TCP
URL. Alembic loads database-only settings, so the migration job needs only
`DATABASE_URL`; it does not require SMTP, Redis, SERP keys, JWT or Cloud Tasks
configuration. API/worker production validation remains in force.

## 1. Open an authenticated Cloud Shell checkout

Use Google Cloud Shell, or install/authenticate `gcloud` on your computer. Obtain
a checkout containing this change and run commands from the repository root.
No downloaded service-account key is needed.

Cloud Shell starts in its own home directory (`~`). Files on your Mac are not
automatically present there. If the script reports `No such file or directory`,
transfer the current source first and change into its directory.

On your **local computer**, generate the upload bundle from the current working
tree (including the uncommitted deployment files):

```sh
python3 infrastructure/gcp/package-cloudshell.py
```

This creates `dist/serp-saas-cloudshell.tar.gz`, excluding local `.env` secrets,
credentials/key files, Git metadata, caches and installed dependencies. In Cloud
Shell, choose **More (⋮) → Upload** and upload that archive into the home directory.
See [Google's file transfer instructions](https://docs.cloud.google.com/shell/docs/uploading-and-downloading-files).

Then run these commands in **Cloud Shell**:

```sh
cd ~
tar -xzf serp-saas-cloudshell.tar.gz
cd serp-saas-cloudshell
ls infrastructure/gcp/cloudsql-migration.sh
```

Run all subsequent commands from `~/serp-saas-cloudshell`. If you already have a
checkout with these exact changes, change into that checkout instead. Cloning the
remote repository alone will not include deployment files that are still
uncommitted on your local computer. No local database dump is needed for this
empty Cloud SQL database.

```sh
gcloud auth list
sh infrastructure/gcp/cloudsql-migration.sh plan
sh infrastructure/gcp/cloudsql-migration.sh check
```

The check should show PostgreSQL 16, a running instance, the supplied connection
name, database `serp_saas`, and user `serp_app`. Confirm the instance server CA
configuration is supported by Cloud Run's second generation execution environment.
Cloud Run jobs use that environment.

The operator needs permission to enable APIs, create the proposed repository,
service account and secret, grant IAM bindings, submit builds, and deploy/execute
Cloud Run jobs. Deploying the job also needs Service Account User on the migration
identity. These are operator permissions, separate from the job's runtime grants.

## 2. Prepare IAM and the empty Secret Manager resource

```sh
sh infrastructure/gcp/cloudsql-migration.sh prepare
```

This enables Cloud SQL Admin, Cloud Run, Artifact Registry, Cloud Build and Secret
Manager APIs. It creates missing proposed resources and grants the migration
identity Cloud SQL Client on the project plus Secret Accessor only on
`serp-database-url`. It does not change the instance/database/user or their
passwords, and does not execute a migration.

The service account's IAM role does not grant PostgreSQL schema permissions.
If `serp_app` does not already have them, connect to **database `serp_saas`** in
Cloud SQL Studio as an administrator and run:

```sql
GRANT CONNECT ON DATABASE serp_saas TO serp_app;
GRANT USAGE, CREATE ON SCHEMA public TO serp_app;
```

For this initially empty database, tables created by migrations are owned by
`serp_app`. Future upgrades require ownership of those tables. This initial setup
uses the same database user for migration and runtime; the GCP migration identity
has separate IAM grants.

## 3. Add the database URL secret version

```sh
python3 infrastructure/gcp/create-database-secret.py
```

Enter the **existing password of `serp_app`** at the hidden prompt. The helper
percent-encodes special characters, creates the socket URL, and sends it directly
to Secret Manager through stdin. It prints only the created version's resource
name. The password/URL are not put into command arguments, stdout or a temporary
file. Running this command again creates a new version; it does not reset the
database user's password.

Set the numeric version from the result, for example:

```sh
export DATABASE_SECRET_VERSION=1
```

Use the actual created version, not necessarily `1`. Migration deploys pin that
version rather than using `latest`.

## 4. Build the production backend image

First grant the **build execution identity** its build permissions. It is a
different account from `serp-migrations`; granting permissions to the migration
identity does not authorize Cloud Build to read source or publish images.

```sh
sh infrastructure/gcp/cloudsql-migration.sh build-access
```

This looks up Google's selected default build service account and grants
`roles/cloudbuild.builds.builder` on this project. That purpose-specific role
includes source-object reads, Artifact Registry publishing and build log writes.
The operator needs permission to modify project IAM for this step. See
[Google's default build identity and role documentation](https://docs.cloud.google.com/build/docs/cloud-build-service-account).

Then run the build:

```sh
export BACKEND_IMAGE_TAG="cloudsql-$(date -u +%Y%m%d-%H%M%S)"
sh infrastructure/gcp/cloudsql-migration.sh build
```

Keep `BACKEND_IMAGE_TAG` for the next step. Cloud Build builds the production
target of `infrastructure/docker/backend.Dockerfile` on Google Cloud, avoiding
Apple Silicon/Cloud Run architecture differences, then publishes the image to
`asia-southeast1-docker.pkg.dev/serp-saas/serp-saas/backend:$BACKEND_IMAGE_TAG`.
`.gcloudignore` excludes local `.env` files from the source upload and
`.dockerignore` excludes them from the image. See
[Cloud Build source exclusions](https://docs.cloud.google.com/sdk/gcloud/reference/topic/gcloudignore).

The build config uses `CLOUD_LOGGING_ONLY`, avoiding a Google-owned default GCS log
bucket for the Compute Engine build identity. See
[Cloud Build service accounts and logging](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts).
The `build` command itself does not grant IAM roles; use `build-access` first.

### Recover an existing Cloud Shell checkout from source-upload error 403

The observed error names build identity
`833917440392-compute@developer.gserviceaccount.com` and missing
`storage.objects.get` on `gs://serp-saas_cloudbuild/source/...`. Source upload
completed, but the build identity could not read the uploaded object. No migration
was run by this failed build.

If the Cloud Shell checkout predates the new `build-access` action, run this
equivalent IAM command directly:

```sh
gcloud projects add-iam-policy-binding serp-saas \
  --member='serviceAccount:833917440392-compute@developer.gserviceaccount.com' \
  --role=roles/cloudbuild.builds.builder \
  --condition=None
```

Also add the logging options to the older build YAML if it does not have them:

```sh
if ! grep -q '^options:' infrastructure/gcp/cloudbuild-backend.yaml; then
  cat >> infrastructure/gcp/cloudbuild-backend.yaml <<'YAML'
options:
  logging: CLOUD_LOGGING_ONLY
YAML
fi
```

Then retry `sh infrastructure/gcp/cloudsql-migration.sh build` with the existing
`BACKEND_IMAGE_TAG`. If permission still fails immediately after a successful IAM
update, allow IAM propagation and retry. Wait for build success before executing
`migrate`. Keep `DATABASE_SECRET_VERSION=1`; the source-read error does not require
another database secret version or a database password change.

## 5. Execute the migration once

```sh
sh infrastructure/gcp/cloudsql-migration.sh migrate
```

This deploys the migration job with the built image, Cloud SQL connection,
dedicated identity and pinned database secret. It runs one task, parallelism one,
automatic retries zero, with command:

```sh
alembic upgrade head && alembic current
```

It waits for execution to finish. Do not launch another migration execution while
one is running. The expected current revision in this checkout is
`0013_email_verification`. Migrations create all tables and seed the Plans catalog;
no local users, rankings or refresh sessions are imported.

Inspect execution status/logs in Cloud Run → Jobs → `serp-db-migrate`, and optionally
verify in Cloud SQL Studio while connected to `serp_saas`:

```sql
SELECT version_num FROM alembic_version;
SELECT COUNT(*) FROM plans;
SELECT COUNT(*) FROM users;
```

The users count should be zero for the initial empty database. Re-running a
successful `upgrade head` is normally a no-op. For a failed migration, inspect its
logs and current revision before retrying. No downgrade or reset is part of this
runbook. For later releases with data, take/verify a backup before upgrading.

## 6. Deploy API and worker afterward

Continue with the [step-by-step API/worker Cloud Run runbook](cloud-run-deployment.md)
once the migration succeeds. It reuses the migration image and prepares runtime
IAM, secrets, configuration, Cloud Tasks, reports storage and Scheduler.

Attach the same Cloud SQL connection to **both** runtime services and grant their
own identities Cloud SQL Client and access to the database secret. Use second
generation Cloud Run services. The API needs `BACKEND_PORT=8080` with Cloud Run
`--port=8080`; `python -m app` currently reads `BACKEND_PORT`, not Cloud Run's `PORT`.
The worker uses `uvicorn app.worker_main:app --host 0.0.0.0 --port 8080`, with IAM
authentication required.

The existing production checks also require:

- `APP_ENV=production`, `DEBUG=false`, a random JWT secret, Secure cookies and
  explicit frontend HTTPS origin/CORS settings. Custom frontend/API subdomains
  under one site are preferable; separate `run.app` origins need cross-site cookie
  settings and may be affected by browser third-party cookie restrictions.
- Real enabled SERP provider credentials.
- Cloud Tasks queue, private worker URL and task/Scheduler invocation identities.
- A private GCS bucket for reports (`REPORT_STORAGE_PROVIDER=gcs`).
- Real TLS SMTP for signup verification and an HTTPS `AUTH_SITE_URL`.
- `REDIS_URL` remains a required setting. Provide a reachable Redis endpoint if
  using Redis health checks; ranking tasks themselves use PostgreSQL/Cloud Tasks.

Use [Cloud Tasks / Cloud Run deployment](cloud-tasks-deployment.md) and
[email verification](email-verification.md) for those settings. They are not
required to initialize the database with the migration job above.

After runtime deployment, check `/health/db` and the real signup/verification
workflow. Bound API/worker maximum instances and connection pool sizes to fit the
Cloud SQL connection budget. The database must be ready before routing public
traffic to the application.

## Local validation of this change

The database configuration regression tests check the actual SQLAlchemy/asyncpg
socket arguments, passwords containing URL-reserved characters, and redaction.
The fresh-database integration test runs all migrations with unrelated production
configuration intentionally incomplete, proving migrations depend only on the
database URL. All 271 backend tests pass, as do Ruff and mypy (141 source files).
The deployment commands and secret helper were also checked with mocked `gcloud`
calls, including pinned secret versions and hidden/encoded passwords.
The production backend image builds successfully and `alembic current` runs
against the local development database with only `DATABASE_URL`, returning
`0013_email_verification (head)`.
GCP resource creation, cloud connectivity and cloud migration
execution must still be verified in the authenticated environment.
