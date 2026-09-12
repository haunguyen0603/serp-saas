# Rank-check batches and schedules

All user endpoints require the existing bearer token and enforce Project ownership.
M5 retires synchronous POST `/projects/{project_id}/rank-checks` and POST
`/projects/{project_id}/keywords/{keyword_id}/rank-checks`. Existing GET ranking,
RankCheck detail, and history endpoints remain unchanged. Clients must migrate to:

| Method | `/api/v1` path | Result |
| --- | --- | --- |
| POST | `/projects/{project_id}/rank-check-batches` | 202 BatchAccepted |
| POST | `/projects/{project_id}/keywords/{keyword_id}/rank-check-batches` | 202 BatchAccepted |
| GET | `/projects/{project_id}/rank-check-batches` | Cursor-paginated history |
| GET | `/projects/{project_id}/rank-check-batches/{batch_id}` | Progress and counters |
| GET | `/projects/{project_id}/rank-check-batches/{batch_id}/jobs` | Cursor-paginated job details |
| POST | `/projects/{project_id}/rank-check-batches/{batch_id}/cancel` | Updated progress |
| GET | `/projects/{project_id}/rank-schedule` | Schedule or null |
| PUT | `/projects/{project_id}/rank-schedule` | Upserted schedule |
| DELETE | `/projects/{project_id}/rank-schedule` | 204; history retained |

Project POST accepts `{}` or `{"keyword_ids":["UUID"]}`. Single-keyword POST accepts
`{}` only. Unknown fields are rejected, including provider, owner, budget and search
settings. Empty selection, no active Keywords, archived Project or inactive selection
returns a safe validation error. POST performs no provider calls.

```json
{"batch_id":"UUID","job_id":"UUID or null","status":"queued","requested_keyword_count":1}
```

The initial status may be `pending` for a large batch or temporary queue outage.
Poll detail every two seconds until `completed`, `completed_with_errors`, `failed`
or `cancelled`, then refresh ranking history/latest. Batch lists and Job lists accept
`limit` (1–200, default 50) and opaque `cursor`. Progress is terminal jobs / requested
jobs. Cancelled jobs count toward completion. The frontend disables duplicate submits
while enqueue requests are pending; no manual idempotency header is implemented.

```json
{"enabled":true,"frequency":"weekly","weekday":0,"local_time":"07:00","timezone":"Asia/Ho_Chi_Minh"}
```

Schedule responses include ID, UTC next_run_at and last_enqueued_at. Daily schedules
ignore weekday. Disabled schedules retain settings; DELETE removes only the schedule.

The separate private worker accepts POST `/internal/tasks/rank-check` with
`{"version":1,"job_id":"UUID"}` and POST `/internal/schedules/dispatch` with no
business input. It exposes `/health` and `/health/db`, no user routes or public OpenAPI.
Only service OIDC identities may call internal endpoints in cloud mode.
