import asyncio
from datetime import UTC, datetime

from app.services.serp.base import RequestPermit, SerpProviderError
from app.services.serp.types import OrganicResult, SerpSearchRequest, SerpSearchResult


class FakeSerpProvider:
    def __init__(self, *, delay_seconds: float = 0, name: str = "fake") -> None:
        self._responses: dict[str, tuple[OrganicResult, ...] | SerpProviderError] = {}
        self.delay_seconds = delay_seconds
        self._name = name
        self.requests: list[SerpSearchRequest] = []

    @property
    def name(self) -> str:
        return self._name

    def add_result(self, query: str, organic_results: list[OrganicResult]) -> None:
        self._responses[query] = tuple(organic_results)

    def add_error(self, query: str, error: SerpProviderError) -> None:
        self._responses[query] = error

    async def search(
        self, request: SerpSearchRequest, request_permit: RequestPermit | None = None
    ) -> SerpSearchResult:
        if request_permit is not None:
            await request_permit()
        self.requests.append(request)
        requested_at = datetime.now(UTC)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        fixture = self._responses.get(request.query)
        if isinstance(fixture, SerpProviderError):
            raise fixture
        results = fixture if fixture is not None else self._default_results()
        return SerpSearchResult(
            provider=self.name,
            provider_request_id=f"fake-{len(self.requests)}",
            organic_results=results[: request.result_limit],
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            raw_metadata={"fixture": True},
            provider_request_count=1,
        )

    @staticmethod
    def _default_results() -> tuple[OrganicResult, ...]:
        return (
            OrganicResult(
                1, "Competitor", "https://competitor.example/page", "competitor.example"
            ),
            OrganicResult(
                2,
                "Tracked result",
                "https://tracked.example/ranking",
                "tracked.example",
            ),
            OrganicResult(
                4,
                "Secondary result",
                "https://www.secondary.example/page",
                "www.secondary.example",
            ),
        )
