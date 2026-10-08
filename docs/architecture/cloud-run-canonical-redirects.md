# Permanent canonical redirects for the commercial domain

This rollout replaces the **apex website's DNS entry point** with a global
external Application Load Balancer. It adds `www` as a redirect alias. The
existing `serp-web` Cloud Run service in `asia-southeast1` remains the backend.
The existing `app.serpsaas.com` and `api.serpsaas.com` DNS/Domain Mappings, Cloud
Run ingress/IAM, image, application environment, authentication and cookies are
outside this Terraform state and are not changed.

Live baseline and limitations: [production investigation](../production-canonical-redirects.md).
Google's [serverless LB setup](https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless),
[URL map redirects](https://docs.cloud.google.com/load-balancing/docs/url-map-concepts)
and [DNS-authorized certificates](https://docs.cloud.google.com/certificate-manager/docs/deploy-google-managed-dns-auth)
describe the infrastructure used here.

## 1. Upload the infrastructure package

On the local workstation:

```sh
python3 infrastructure/gcp/package-cloudshell.py --canonical-guide
```

Upload `dist/serp-saas-canonical-redirects.tar.gz` using Cloud Shell's **More →
Upload**. This package contains no `.env`, application source, credentials,
Terraform state or plans. In Cloud Shell:

```sh
cd ~
tar -xzf serp-saas-canonical-redirects.tar.gz
cd ~/serp-saas-cloudshell
gcloud config set project serp-saas
terraform version
```

Use Terraform **1.7 or newer, below 2.0**; mock-provider tests require 1.7.
Cloud Shell may provide a `terraform` placeholder that only prints installation
instructions, sometimes with exit code zero. `command -v terraform` alone does
not establish that Terraform is installed. If `terraform version` shows those
instructions instead of a version, install the tested **1.13.5** binary in the
persistent home directory, following HashiCorp's
[binary installation option](https://developer.hashicorp.com/terraform/install):

```sh
(
  set -eu
  case "$(uname -m)" in
    x86_64) canonical_tf_arch=amd64 ;;
    aarch64|arm64) canonical_tf_arch=arm64 ;;
    *) echo 'Unsupported Cloud Shell architecture' >&2; exit 1 ;;
  esac
  canonical_tf_tmp="$(mktemp -d)"
  trap 'rm -rf "$canonical_tf_tmp"' EXIT
  cd "$canonical_tf_tmp"
  canonical_tf_zip="terraform_1.13.5_linux_${canonical_tf_arch}.zip"
  curl -fsSLO "https://releases.hashicorp.com/terraform/1.13.5/$canonical_tf_zip"
  curl -fsSLO 'https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_SHA256SUMS'
  awk -v archive="$canonical_tf_zip" '$2 == archive { print }' \
    terraform_1.13.5_SHA256SUMS > selected.sha256
  test -s selected.sha256
  sha256sum --check selected.sha256
  unzip -q "$canonical_tf_zip"
  mkdir -p "$HOME/.local/bin"
  install -m 0755 terraform "$HOME/.local/bin/terraform"
)
export PATH="$HOME/.local/bin:$PATH"
hash -r
terraform version -json
python3 infrastructure/gcp/canonical-redirects.py plan
```

`terraform version -json` must return a JSON object containing
`"terraform_version": "1.13.5"`. Re-export this PATH in each new Cloud Shell
session, or add the same `export PATH=...` line once to `~/.bashrc`. The binary
in `$HOME` persists across Cloud Shell sessions. The helper now rejects the
placeholder before fetching credentials or planning resources. If the old helper
failed with `JSONDecodeError` at `terraform show -json` and only installation
instructions appeared, its apply step had not been reached; install the binary
and rerun `prepare` in the same checkout, preserving any Terraform state.

The helper obtains a short-lived token from the authenticated Cloud Shell session
without printing or saving it. Operator permissions must allow enabling the two
APIs, managing Compute load balancing/static addresses/serverless NEGs and
Certificate Manager resources, and reading `serp-web` (for example, existing
project Owner). This rollout does not grant new IAM permissions.

The plan uses isolated names starting `serp-canonical-`. If an existing resource
has that name but is not in this state, stop and inspect it before importing it
or choosing another name. The helper rejects plans containing deletions or
replacements. It never treats an API permission error as an absent resource.

Terraform uses local state in `infrastructure/gcp/canonical-redirects/`. Keep the
same Cloud Shell home/checkout between phases and back up the state securely.
Do not include `.terraform/`, state or saved plans in Git or upload packages.
Never run `terraform destroy` as a rollback; the address has `prevent_destroy`.

## 2. Prepare DNS authorization and the static IP

```sh
python3 infrastructure/gcp/canonical-redirects.py prepare
terraform -chdir=infrastructure/gcp/canonical-redirects output certificate_dns_records
terraform -chdir=infrastructure/gcp/canonical-redirects output -raw load_balancer_ip
```

This creates the static IPv4 address, two `PER_PROJECT_RECORD` DNS
authorizations, a certificate covering `serpsaas.com` and `www.serpsaas.com`, and
its map/hostname entries. No forwarding rule or backend is created in this phase.
Production DNS still points at Domain Mapping.

On the first run there is no Terraform state yet. The helper reads current state
with `terraform show -json`, which supports that case, then proceeds to plan and
apply. A previous helper version incorrectly used `terraform state list` and
stopped with `No state file was found!` before planning. If you encounter that
error, upload the regenerated package from this workstation, extract it into the
**same checkout**, and rerun `prepare`. Extraction updates the helper/config/docs
but does not include or overwrite state files. Do not create an empty state file
or delete existing state. Genuine backend/state errors still stop the helper.

Public DNS on 2026-10-08 identifies `ns1.azdigi.com` and `ns2.azdigi.com` as the
authoritative nameservers. At AZDIGI, add **both CNAME records exactly as emitted**
in `certificate_dns_records`: use each `name`, `type` and `data`. If the UI appends
`.serpsaas.com` automatically, enter only the relative name; do not duplicate the
domain suffix. Keep these records for certificate renewal. Do not replace other
verification TXT/CNAME records.

The successful Cloud Shell `prepare` output for this rollout gives LB IP
**136.81.159.43** and the following authorization records. For a DNS UI that
automatically appends `.serpsaas.com`, enter these **relative** names with type
`CNAME` and TTL 300:

| Relative name | Target |
| --- | --- |
| `_acme-challenge_3gwysczgqi3z3sof` | `28faca74-b3ee-401b-b3fc-ce02f292d1cd.19.authorize.certificatemanager.goog.` |
| `_acme-challenge_3gwysczgqi3z3sof.www` | `2311a64e-a76e-471d-aa1c-bdd13109447c.7.authorize.certificatemanager.goog.` |

The full record names are respectively
`_acme-challenge_3gwysczgqi3z3sof.serpsaas.com.` and
`_acme-challenge_3gwysczgqi3z3sof.www.serpsaas.com.`. Treat the Terraform outputs
in the live Cloud Shell checkout as authoritative if resources are recreated.
Keep traffic A records at their existing values until certificate readiness,
LB deployment and preflight all pass. Adding these CNAMEs authorizes issuance;
it does not yet activate the permanent redirects.

Reduce the apex A record TTL to 300 in advance and allow the previous TTL to
expire before cutover. At baseline it points at `216.239.32.21`; record all current
values and TTLs in the DNS UI for rollback. `www` currently has no record; negative
DNS responses may also remain cached until their TTL expires.

Check certificate readiness after the CNAMEs propagate:

```sh
python3 infrastructure/gcp/canonical-redirects.py status
```

Continue only when the certificate and **both** certificate map entries are
`ACTIVE`. DNS authorization provisions the certificate without changing the
apex/www traffic records. If authorization fails, inspect the certificate's
`managed.authorizationAttemptInfo`, DNS CNAME values and any CAA restrictions.

If status shows `PROVISIONING` with both domains `AUTHORIZING` and the two CNAMEs
resolve to their exact expected targets, issuance is still pending. The helper's
`Certificate is not ACTIVE` message stops deployment until readiness; it does
not by itself indicate an invalid CNAME. Wait 5–10 minutes and rerun `status`;
this is a suggested recheck interval, not a guaranteed issuance deadline. Keep
the existing traffic A records while waiting. If an authorization changes to
`FAILED`, inspect its failure reason and
[Certificate Manager troubleshooting](https://docs.cloud.google.com/certificate-manager/docs/troubleshooting).

## 3. Create and test the load balancer before switching DNS

```sh
python3 infrastructure/gcp/canonical-redirects.py plan --phase=deploy
python3 infrastructure/gcp/canonical-redirects.py deploy
export CANONICAL_LB_IP="$(terraform -chdir=infrastructure/gcp/canonical-redirects output -raw load_balancer_ip)"
python3 infrastructure/gcp/canonical-redirects.py preflight \
  --ip "$CANONICAL_LB_IP" --output canonical-preflight.json
```

`deploy` refuses to apply until the certificate and map entries are ACTIVE and
the existing `serp-web` ingress permits load balancing. It creates a regional
serverless NEG and global backend, two URL maps, proxies and port 80/443
forwarding rules sharing the static IP. There are no Cloud Run updates, health
checks, CDN caching, IAP, header rewrites or changes to app routing.

The HTTP map uses `MOVED_PERMANENTLY_DEFAULT` (301), `https_redirect=true`,
`host_redirect=serpsaas.com`, `strip_query=false`, with no path/prefix replacement.
The HTTPS map redirects only `www` to apex with 301. Its `https_redirect=false`
retains the incoming HTTPS scheme; Google permits `https_redirect=true` only on
an HTTP target proxy. Apex HTTPS forwards to the existing backend preserving Host.

Preflight uses `curl --resolve` and `--noproxy '*'` to connect to the new IP while
preserving Host/SNI and verifying TLS. It checks HEAD and GET for all aliases,
root/pricing paths, ordinary/encoded/repeated queries, a Googlebot GET and final
canonical HTTPS 200. LB propagation can take time; rerun a failed preflight after
inspecting its recorded error. **Do not switch DNS until all checks pass.**

Observed on this deployment: the HTTP URL map generates raw Location
`https://serpsaas.com:443/<original-path>?<original-query>`. Port 443 is HTTPS's
default; the normalized URL is the same canonical destination under
[RFC 9110 §4.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.2.3).
The current verifier accepts only that default-port equivalence and retains the
raw header and final URL in its JSON evidence. It still requires 301, exact
path/query, correct apex host, valid TLS and final 200. Older helper packages
could falsely fail valid HTTP redirects solely because they included `:443`;
use the updated helper for future verification.

After deployment, use `plan --phase=deploy` or `deploy` for updates. Do not run
`prepare` again: it intentionally refuses to disable an existing LB. Direct
Terraform commands must keep `-var=enable_load_balancer=true` after phase 2.

## 4. Switch only the website's DNS records

At AZDIGI set:

| Name | Type | Value | TTL |
| --- | --- | --- | --- |
| `@` | A | `136.81.159.43` (this rollout's `CANONICAL_LB_IP`) | 300 |
| `www` | A | `136.81.159.43` (the same allocated IP) | 300 |

**Replace** all old apex A targets; do not add the LB IP alongside the Domain
Mapping IP. This configuration is IPv4 only. If apex/www AAAA or www CNAME records
have appeared since baseline, remove those conflicting traffic records so they
cannot route some users to the old entry point. Do not change app/api records,
nameservers, MX, TXT, or authorization CNAMEs. Keep the old Domain Mappings for
rollback. Do not restrict `serp-web` ingress: it also serves the existing app
Domain Mapping.

## 5. Verify production DNS and save actual after evidence

This rollout completed on 2026-10-08: both AZDIGI authoritative nameservers and
Google Public DNS point apex/www to `136.81.159.43`. Production verification
through Google Public DNS passed all 28 cases after targeted DNS-failure retries.
See the [measured report](../production-canonical-redirects.md) for raw headers,
retry evidence and the remaining effect of old resolver caches.

```sh
curl -I http://serpsaas.com/
curl -I http://serpsaas.com/pricing
curl -I http://www.serpsaas.com/
curl -I https://www.serpsaas.com/
curl -I 'http://serpsaas.com/pricing?utm_source=canonical-check&probe=1'
curl -IL --max-redirs 3 http://serpsaas.com/
curl -I https://serpsaas.com/
python3 infrastructure/gcp/canonical-redirects.py verify --output canonical-after.json
```

Expected: each alias's first response is **301** with Location pointing to
`https://serpsaas.com/<original-path>?<original-query>` (the HTTP map may include
equivalent default `:443`); apex HTTPS home and pricing are **200**, and HTTP home
finishes at normalized canonical `https://serpsaas.com/`. The helper
exits nonzero for 302, missing DNS, TLS failures, lost query or a failed final
destination, and records raw headers plus exact status/Location. Do not claim a
production pass from `preflight`: it bypasses production DNS.

If system DNS still returns the old Domain Mapping IP after AZDIGI has saved the
new records, inspect both authoritative nameservers and a public resolver. The
old apex TTL was 14440 seconds (about four hours); previously cached answers can
remain valid until expiry. Keep those failed system-resolver results as evidence.
To also check live production DNS through Google Public DNS without pinning the
website's IP, use the updated helper:

```sh
python3 infrastructure/gcp/canonical-redirects.py verify \
  --doh-url https://dns.google/dns-query --output canonical-after-public-dns.json
```

This uses [curl's DNS-over-HTTPS resolver](https://curl.se/docs/manpage.html#--doh-url),
keeps TLS verification enabled for the resolver and website, and records the
resolver and actual curl commands. It does not use `--resolve`. A public-resolver
pass establishes behavior through updated production records; it does not imply
every client cache has expired.

Check `https://app.serpsaas.com/login`, login/reload/logout, and API health through
the existing hostnames. The repository's existing `frontend/src/proxy.test.ts`
checks authentication routing; no application code is changed in this rollout.
Retain preflight/after JSON and update the investigation report with **measured**
after results. Only then request URL inspection again in Search Console. If its
historical HTTP 404 persists, compare the crawl timestamp with this deployment,
test a live fetch and inspect relevant request logs; today's 302 does not explain
the earlier 404 by itself.

Rollback if necessary: restore the saved apex A records, remove the new `www` A
record if it was absent before, leave certificate authorization records and LB
resources intact, and repeat HTTP/HTTPS checks after propagation. This restores
the observed 302 behavior; it does not satisfy the permanent-redirect requirement.
