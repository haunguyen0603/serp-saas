# Tracked Sites API

All endpoints require authentication and scope Site and Domain queries by the
current User. Ownership fields are rejected.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/tracked-sites` | Create Site, required primary, optional aliases; 201 |
| GET | `/tracked-sites` | Status/search/cursor list |
| GET | `/tracked-sites/{site_id}` | Site with all aliases |
| PATCH | `/tracked-sites/{site_id}` | Rename or archive/reactivate |
| DELETE | `/tracked-sites/{site_id}` | Delete Site and aliases; 204 |
| POST | `/tracked-sites/{site_id}/domains` | Add domain, optionally primary; 201 |
| PATCH | `/tracked-sites/{site_id}/domains/{domain_id}` | Activate/deactivate/promote |
| DELETE | `/tracked-sites/{site_id}/domains/{domain_id}` | Delete allowed alias; 204 |

Create Site accepts `name`, `primary_domain`, and `aliases`. Add Domain accepts
`domain` and `make_primary`. Domain PATCH accepts `active` and `is_primary`.
Normalized duplicate domains for the user return `DOMAIN_ALREADY_TRACKED`. Primary
domains cannot be inactive; deleting/demoting a primary with other aliases returns
`PRIMARY_DOMAIN_REPLACEMENT_REQUIRED`, and an active Site cannot lose its only
primary. Foreign and missing IDs are externally indistinguishable 404 responses.
