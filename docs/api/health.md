# Infrastructure API

Swagger UI: `http://localhost:8000/docs`.
OpenAPI schema: `http://localhost:8000/openapi.json`.
The API root redirects to Swagger UI.

| Endpoint | Check | Success |
| --- | --- | --- |
| `GET /health` | API process is serving HTTP | `200 {"status":"ok"}` |
| `GET /health/db` | PostgreSQL executes `SELECT 1` | `200 {"status":"ok"}` |
| `GET /health/redis` | Redis responds to `PING` | `200 {"status":"ok"}` |

Dependency failures return HTTP 503, with `DATABASE_UNAVAILABLE` or
`REDIS_UNAVAILABLE` in the error code. The API does not disclose connection details.

```json
{
  "error": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "The database dependency is unavailable."
  }
}
```

Unknown routes return 404 `NOT_FOUND`, invalid input returns 422 `VALIDATION_ERROR`,
and unexpected failures return 500 `INTERNAL_SERVER_ERROR`, using the same envelope.
The `/api/v1` router is mounted but intentionally has no business endpoints.
