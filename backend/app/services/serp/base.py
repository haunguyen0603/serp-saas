from collections.abc import Awaitable, Callable
from typing import Protocol

from app.services.serp.types import SerpSearchRequest, SerpSearchResult

RequestPermit = Callable[[], Awaitable[None]]


class SerpProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def search(
        self, request: SerpSearchRequest, request_permit: RequestPermit | None = None
    ) -> SerpSearchResult: ...


class SerpProviderError(Exception):
    def __init__(
        self,
        code: str,
        safe_message: str,
        *,
        request_count: int = 0,
        provider: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = safe_message
        self.request_count = request_count
        self.provider = provider
        super().__init__(safe_message)


class ProviderBudgetReservationError(Exception):
    """Raised immediately before HTTP when the persisted budget cannot be reserved."""
