# Rank Check API

All routes require a bearer access token. Ownership always comes from the token;
foreign Project, Keyword, and Rank Check IDs use the same 404 responses as missing
IDs. Request models reject extra fields, including `user_id` and provider settings.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks` | Run one active Keyword check; `{}` body; 201 |
| POST | `/api/v1/projects/{project_id}/rank-checks` | Run active Project Keywords; optional `keyword_ids`; 201 |
| GET | `/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks` | Cursor-paginated history |
| GET | `/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}` | Check, rankings, and normalized organic results |

The Project request accepts either `{}` to check all active Keywords or
`{"keyword_ids":["uuid"]}` for an explicit active subset. IDs are deduplicated.
The default Project cap is 25 and concurrency is bounded by configuration. An
archived Project, paused Keyword, over-limit request, or already-running Keyword
returns a stable application error.

History accepts `status=pending|running|succeeded|failed|all`, `limit=1..200`
(default 50), and an opaque `cursor`. Ordering is stable by `created_at DESC, id
DESC`. Each summary includes the stored query/environment snapshot, provider,
depth, request count, status/error, result count, and matched Site rankings. Detail
also includes ordered normalized organic results. New checks include ordered
`provider_attempts`; legacy Milestone 4 history returns an empty list. The existing
`provider` field is the final successful data source and `provider_request_count`
is the total number of upstream requests across retries and fallback.

A valid provider response with no owned-domain match is a successful check with an
empty `rankings` array. Provider failures create a durable failed check and return a
sanitized 502/503 error for a single check. Project checks report per-Keyword
success/failure outcomes so one failure does not erase other completed checks.

Documented errors include 401, 404, 409, 422, and provider 502/503 responses.
Provider credentials, raw upstream errors, and full provider request URLs are never
returned.

Priority routing returns `SERP_NO_PROVIDER_AVAILABLE` when no enabled, configured,
capable provider has budget. Fixed routing returns
`SERP_PROVIDER_NOT_CONFIGURED` for a missing fixed provider. Both are sanitized 503
responses. Clients cannot submit `provider`, provider credentials, or request
budgets; strict request validation rejects those fields.
