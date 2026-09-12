from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SerpSearchRequest:
    query: str
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None
    result_limit: int


@dataclass(frozen=True, slots=True)
class OrganicResult:
    position: int
    title: str
    url: str
    hostname: str
    displayed_url: str | None = None
    snippet: str | None = None


@dataclass(frozen=True, slots=True)
class SerpSearchResult:
    provider: str
    provider_request_id: str | None
    organic_results: tuple[OrganicResult, ...]
    requested_at: datetime
    completed_at: datetime
    raw_metadata: dict[str, object] = field(default_factory=dict)
    provider_request_count: int = 1
