# SERP provider architecture

Core ranking code consumes only `SerpSearchRequest`, `SerpSearchResult`, and
`OrganicResult`. `SerpApiProvider`, `SerperProvider`, and `FakeSerpProvider`
implement the same `SerpProvider` protocol. Provider response fields, auth headers,
URLs, and parsing rules remain inside their adapters.

SerpApi maps search engine → `engine`, query → `q`, country → `gl`, language →
`hl`, device → `device`, location → `location`, and depth → `num`. Serper maps the
same generic query, country, language, depth, and location semantics to its JSON
Search request. The verified Serper synchronous Search contract has no device
parameter, so Serper is eligible only for desktop checks; mobile checks route to a
provider that supports mobile. No Project setting is silently omitted.

Both real adapters keep positive organic positions through the requested depth,
normalize URL hostnames, discard malformed/duplicate-position rows, and retain only
bounded metadata counts plus an optional request ID. Timeout, availability,
rate-limit, quota, credential, invalid-request, and invalid-response failures map to
generic sanitized codes. Each adapter performs at most two HTTP attempts for its
own transient retry policy.

`FakeSerpProvider` is deterministic and performs no HTTP. Automated tests, ordinary
smokes, and browser verification use fake or mocked adapters and consume no real
provider credits. Production rejects a configuration where fake is enabled. Real
smokes are separately guarded and make at most one request:

```bash
RUN_REAL_SERPER_SMOKE=true make serper-smoke
RUN_REAL_SERP_SMOKE=true make serpapi-smoke
```

Provider keys exist only in backend settings. They are never placed in
`NEXT_PUBLIC_*`, API payloads, stored errors, or structured logs.
