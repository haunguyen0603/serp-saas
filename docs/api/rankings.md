# Rankings API

`GET /api/v1/projects/{project_id}/rankings/latest` requires authentication and
returns one row for each active Keyword in the user-owned Project. Foreign and
missing Projects return the same `PROJECT_NOT_FOUND` 404.

Each row contains the current Keyword ID/text and its latest Rank Check summary, or
`latest_check: null` for Never Checked. A succeeded check with no matches represents
Not Found in Top N. Failed and running checks retain their status. A successful
check may contain multiple Site rankings; each Site appears once at its best organic
position.

The query uses a PostgreSQL window function to select one latest check per Keyword,
then loads normalized results and rankings in set-oriented queries. It does not load
complete history or issue a query per Keyword.

Ranking rows expose immutable display snapshots (`tracked_site_name`,
`matched_domain`, position, result URL/hostname, and title). Current Site and domain
IDs may become null after a history-safe deletion, while those snapshots remain.
