# Keywords API

Keyword endpoints are nested under `/api/v1/projects/{project_id}/keywords` and
enforce ownership through the exact user-owned Project. A Keyword contains only
`keyword`, `active`, IDs, and timestamps in its response.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/projects/{project_id}/keywords` | Add `{ "keyword": "..." }`; 201 |
| POST | `/projects/{project_id}/keywords/bulk` | Add `{ "keywords": [...] }`; 201 |
| GET | `/projects/{project_id}/keywords` | Search/state-filtered paginated list |
| GET | `/projects/{project_id}/keywords/{keyword_id}` | Owner-scoped detail |
| PATCH | `/projects/{project_id}/keywords/{keyword_id}` | Change `keyword` and/or `active` |
| DELETE | `/projects/{project_id}/keywords/{keyword_id}` | Hard delete; 204 |

Per-Keyword search engine, country, language, device, and location inputs are
rejected. Uniqueness is normalized query text within one Project. Collisions return
`KEYWORD_ALREADY_EXISTS`. Bulk input is limited to 1000 and reports submitted,
normalized, created, duplicate, and empty counts. List filters are `search`,
`active`, `limit`, and opaque `cursor`.
