# Projects API

All `/api/v1/projects` endpoints require a bearer access token and derive ownership
from it. POST atomically creates a Project plus initial Keywords:

```json
{"name":"Vietnam Desktop","search_engine":"google","country_code":"VN","language_code":"vi","device":"desktop","location":"Ho Chi Minh City","keywords":["casino online","game bài"]}
```

One to 1000 inputs are required; empty and duplicate normalized lines are cleaned.
The typed response contains `project` (including `keyword_count`) and `keywords`
counts. `domain`, ownership fields, and obsolete `default_*` fields are rejected.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/projects` | Atomic Project and initial Keyword creation; 201 |
| GET | `/projects` | Owner-scoped, paginated list |
| GET | `/projects/{project_id}` | Owner-scoped detail |
| PATCH | `/projects/{project_id}` | Update environment or status |
| DELETE | `/projects/{project_id}` | Delete only when no Rank Check history exists; otherwise `HISTORY_EXISTS`; 204 |

PATCH supports `name`, `search_engine`, `country_code`, `language_code`, `device`,
`location`, and `status`. List filters are `status`, name `search`, `limit` (1–200),
and opaque `cursor`. Foreign and missing Projects return `PROJECT_NOT_FOUND`.
