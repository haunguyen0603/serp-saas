# Production canonical redirect investigation — 2026-10-08

Status: **Production DNS cutover confirmed; all 28 canonical checks passed through
Google Public DNS after targeted DNS-failure retries**, completed at
**2026-10-08 08:33 UTC (15:33 Vietnam time)**.
Both authoritative AZDIGI nameservers and Google Public DNS now return
**136.81.159.43**, TTL **300**, for apex and www. Neither hostname has a conflicting
AAAA or CNAME record:
[dns-and-auth-after-cutover.json](verification-artifacts/production-canonical-redirects/dns-and-auth-after-cutover.json).

The certificate and both map entries are ACTIVE according to the supplied
[Cloud Shell status output](verification-artifacts/production-canonical-redirects/certificate-active-output.json).
The supplied [HTTPS frontend configuration](verification-artifacts/production-canonical-redirects/https-frontend-output.json)
confirms the certificate map, URL map and EXTERNAL_MANAGED port-443 forwarding
rule at that IP. The live LB preflight passed **28/28** checks:
[preflight-after-deploy.json](verification-artifacts/production-canonical-redirects/preflight-after-deploy.json).

A system-resolver check immediately after the save still connected apex to old
IP **216.239.32.21**, returning 302, and could not resolve www:
[production-after-system-dns-cache.json](verification-artifacts/production-canonical-redirects/production-after-system-dns-cache.json).
The old apex TTL was **14440 seconds** (about four hours). That cached-path
failure is retained separately; it must not be presented as a production pass
or confused with the updated authoritative DNS. The production verifier now
supports an explicit public DNS-over-HTTPS resolver, without pinning the website
IP and with TLS verification enabled. Final results are recorded in
[production-after.json](verification-artifacts/production-canonical-redirects/production-after.json).

GCP changes were applied by the operator in authenticated Cloud Shell; DNS was
saved at AZDIGI. No GCP or DNS mutation was performed from this workstation.
The [rollout runbook](architecture/cloud-run-canonical-redirects.md) records
preparation, deployment, DNS cutover, verification and rollback steps.

## Measured baseline

Captured raw curl output: [before.json](verification-artifacts/production-canonical-redirects/before.json).
Public resolver answers: [dns-before.json](verification-artifacts/production-canonical-redirects/dns-before.json).
GET/Googlebot and app/API baseline:
[http-get-and-app-before.json](verification-artifacts/production-canonical-redirects/http-get-and-app-before.json).
The new verifier also ran against current production and correctly failed the
301 requirement: [verification-before.json](verification-artifacts/production-canonical-redirects/verification-before.json).

| Request | Before status | Before Location | After DNS cutover, Google Public DNS status / raw Location |
| --- | --- | --- | --- |
| `http://serpsaas.com/` | 302 | `https://serpsaas.com/` | 301 / `https://serpsaas.com:443/` |
| `http://serpsaas.com/pricing` | 302 | `https://serpsaas.com/pricing` | 301 / `https://serpsaas.com:443/pricing` |
| `http://serpsaas.com/pricing?utm_source=canonical-check&probe=1` | 302 | `https://serpsaas.com/pricing?utm_source=canonical-check&probe=1` | 301 / `https://serpsaas.com:443/pricing?utm_source=canonical-check&probe=1` |
| `http://www.serpsaas.com/` | No HTTP response; curl exit 6 (DNS) | None | 301 / `https://serpsaas.com:443/` |
| `https://www.serpsaas.com/` | No HTTP response; curl exit 6 (DNS) | None | 301 / `https://serpsaas.com/` |
| `https://serpsaas.com/` | 200 | None | 200 / None |
| `https://serpsaas.com/pricing` | 200 | None | 200 / None |

The after column above contains measured responses through updated production
DNS using Google Public DNS-over-HTTPS, without `--resolve`. HTTP home follows
**301 → 200**, raw final
URL `https://serpsaas.com:443/`, normalized canonical destination
`https://serpsaas.com/`. The port-80 map includes explicit `:443` in Location;
HTTPS-www redirects omit it. Both identify the same HTTPS origin/resource under
[RFC 9110 §4.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.2.3).
The verifier now accepts only this exact default-port equivalence and keeps raw
Location/final URL alongside normalized values. It does not normalize path/query,
accept other hosts or ports, or suppress TLS/status failures. System DNS cache
results are retained separately, as described above.

Anonymous live routing probes through the new LB keep apex `/login` and `/app`
at their existing **307** redirects to the corresponding `app.serpsaas.com` path,
including query string. The existing app login is **200**, app root **307** to
`/app`, and API `/health/db` **200**:
[auth-routing-after-lb.json](verification-artifacts/production-canonical-redirects/auth-routing-after-lb.json).
After the DNS save, app login still returns 200, app root 307 to `/app`, API health
200, and apex login 307 with its query preserved:
[dns-and-auth-after-cutover.json](verification-artifacts/production-canonical-redirects/dns-and-auth-after-cutover.json).
These checks establish routing/availability, not a full authenticated browser
session. No app/API DNS or application runtime configuration was changed.

At baseline, following HTTP home gave **302 → 200**, final URL exactly
`https://serpsaas.com/`. Googlebot HEAD and GET both return 302. App login returns
200, app root returns 307 to `https://app.serpsaas.com/app`, and API `/health/db`
returns 200. These anonymous probes establish routing/availability, not a full
authenticated browser-session test. The baseline curl
`--ipv6` connection used an IPv4-mapped address, so it does not establish native
IPv6 coverage. The public DNS baseline has no apex AAAA record.

## Root cause and limits

The previous entry point was Cloud Run Domain Mapping (`Server: Google Frontend`),
with apex A `216.239.32.21`. Its HTTP entry point emits a **temporary 302** before
the request can reach Next.js, so application middleware cannot replace that
response with 301. The [Domain Mapping API specification](https://docs.cloud.google.com/run/docs/reference/rest/v1/namespaces.domainmappings)
exposes route/certificate/override settings, but no redirect-status setting.
This is the identified cause of the **permanent canonical redirect requirement
failing at baseline**. At baseline, `www` had no traffic records; authoritative nameservers are
`ns1.azdigi.com` / `ns2.azdigi.com`.

The reported Search Console HTTP **404 was not reproduced in baseline or after
checks**. Its historical root cause remains unconfirmed without the crawl
timestamp and corresponding request logs. The measured correction is replacing
temporary redirects and missing www DNS with permanent redirects through the LB.

## Infrastructure/configuration fix

[Terraform configuration](../infrastructure/gcp/canonical-redirects/main.tf)
creates an isolated global external Application Load Balancer, static IPv4,
serverless NEG for existing `serp-web`, and a DNS-authorized certificate for apex
and `www`. The first phase provisions certificates without traffic changes; the
second requires ACTIVE certificate/map entries via the
[deployment helper](../infrastructure/gcp/canonical-redirects.py).

The port 80 URL map permanently redirects all paths to HTTPS apex with **301**;
HTTPS `www` also redirects to apex with **301**. Both maps preserve path and query.
Apex HTTPS passes to the existing service without a host rewrite or CDN caching.
Only apex/www A records move to the new address. Existing app/API DNS, Cloud Run
Domain Mappings, ingress, IAM, frontend/backend code and runtime settings remain
as they are, preserving the authenticated application routing.

## Validation and rollout checks

Local validation completed successfully with Terraform 1.13.5 and Google
provider 7.46.1: configuration validation, formatting, **2 Terraform mock-plan
tests**, **21 Python helper tests**, Ruff checks and **21 existing frontend proxy
tests** (Node 22.22.0). These checks do not deploy or verify a live load balancer.

Cloud Shell follow-up: the initial `prepare` encountered a Terraform placeholder
that printed installation guidance with a successful exit code. The old helper
attempted to parse that text as plan JSON and raised `JSONDecodeError` before
apply. The helper now validates `terraform version -json` and rejects missing,
placeholder or unsupported CLIs before retrieving credentials or planning. The
runbook includes checksum-verified binary installation in the persistent home
directory. The placeholder failure was reproduced locally, and the installed
Terraform 1.13.5 binary passed the new version check; the operator subsequently completed deployment.

After installing Terraform, Cloud Shell successfully initialized provider 7.46.1
but the old helper stopped at `terraform state list`: no state exists before a
first apply. This was a helper bug, reproduced with the actual Terraform 1.13.5
CLI. The helper now reads current state using `terraform show -json`; a first-run
state without resources is accepted, existing LB resources remain protected,
and backend/JSON errors are not ignored. The screenshot's failure occurred before
plan/apply. The corrected prepare flow is checked locally with an actual Terraform
CLI and a built-in local resource, without any GCP calls or production changes.

Run the Terraform mock-provider plans with `terraform test` in the configuration
directory; they check certificate staging, HTTP/HTTPS-www 301 maps, path/query
preservation and the original frontend backend. Python verifier/guard tests cover
temporary redirects, proxy response headers, lost queries, DNS failures, TLS
preflight routing, inactive certificates and refusing destructive plans. The
existing frontend proxy tests check app-domain authentication routing.

The helper's `preflight` checks the new IP with original Host/SNI before cutover;
`verify` checks production DNS afterward. Raw after statuses, Location headers,
final URL, connection IP and commands are retained in `production-after.json`.
The initial public-resolver run received correct responses for 26/28 checks;
two other requests failed during DNS resolution before an HTTP connection.
Those failures are retained in
[production-after-first-public-dns.json](verification-artifacts/production-canonical-redirects/production-after-first-public-dns.json)
and only those two checks were rerun. The final artifact records retry indices
and completion time, including one additional retry for GET www/pricing.
All **28/28** final results pass and connect to **136.81.159.43**, including valid
TLS, HEAD/GET, original and encoded/repeated queries, Googlebot, and the final
canonical destination. No HTTP 404 was observed. This does not imply every client
DNS cache has expired or establish the cause of the historical Search Console 404.
