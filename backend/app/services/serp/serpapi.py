import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from app.services.normalization import normalize_domain
from app.services.serp.base import RequestPermit, SerpProviderError
from app.services.serp.types import OrganicResult, SerpSearchRequest, SerpSearchResult


class SerpApiProvider:
    name = "serpapi"

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
        retry_delay_seconds: float = 0.1,
        max_attempts: int = 2,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._client = client
        self._retry_delay = retry_delay_seconds
        self._max_attempts = max_attempts

    async def search(
        self, request: SerpSearchRequest, request_permit: RequestPermit | None = None
    ) -> SerpSearchResult:
        if not self._api_key:
            raise SerpProviderError(
                "SERP_PROVIDER_NOT_CONFIGURED",
                "The SERP provider is not configured.",
                provider=self.name,
            )
        params = self._params(request)
        requested_at = datetime.now(UTC)
        attempts = 0
        while attempts < self._max_attempts:
            if request_permit is not None:
                await request_permit()
            attempts += 1
            try:
                response = await self._get(params)
            except httpx.TimeoutException:
                if attempts < self._max_attempts:
                    await asyncio.sleep(self._retry_delay)
                    continue
                raise SerpProviderError(
                    "SERP_PROVIDER_TIMEOUT",
                    "The SERP provider timed out.",
                    request_count=attempts,
                ) from None
            except httpx.RequestError:
                if attempts < self._max_attempts:
                    await asyncio.sleep(self._retry_delay)
                    continue
                raise SerpProviderError(
                    "SERP_PROVIDER_UNAVAILABLE",
                    "The SERP provider is unavailable.",
                    request_count=attempts,
                ) from None
            if response.status_code == 429:
                if self._quota_exhausted(response):
                    raise self._error(
                        "SERP_PROVIDER_QUOTA_EXHAUSTED",
                        "The SERP provider quota is exhausted.",
                        attempts,
                    )
                if attempts < self._max_attempts:
                    await asyncio.sleep(self._retry_delay)
                    continue
                raise self._error(
                    "SERP_PROVIDER_RATE_LIMITED",
                    "The SERP provider rate limit was reached.",
                    attempts,
                )
            if response.status_code in {401, 403}:
                raise self._error(
                    "SERP_PROVIDER_AUTH_ERROR",
                    "The SERP provider rejected its credentials.",
                    attempts,
                )
            if response.status_code >= 500:
                if attempts < self._max_attempts:
                    await asyncio.sleep(self._retry_delay)
                    continue
                raise SerpProviderError(
                    "SERP_PROVIDER_UNAVAILABLE",
                    "The SERP provider is unavailable.",
                    request_count=attempts,
                )
            if response.status_code >= 400:
                raise self._error(
                    "SERP_PROVIDER_INVALID_REQUEST",
                    "The SERP provider rejected the search request.",
                    attempts,
                )
            return self._parse(response, request, requested_at, attempts)
        raise AssertionError("Provider retry loop exhausted")

    def _params(self, request: SerpSearchRequest) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "api_key": cast(str, self._api_key),
            "engine": request.search_engine,
            "q": request.query,
            "gl": request.country_code.lower(),
            "hl": request.language_code,
            "device": request.device,
            "num": request.result_limit,
        }
        if request.location:
            params["location"] = request.location
        return params

    async def _get(self, params: dict[str, str | int]) -> httpx.Response:
        if self._client is not None:
            return await self._client.get(
                self._base_url, params=params, timeout=self._timeout
            )
        async with httpx.AsyncClient() as client:
            return await client.get(
                self._base_url, params=params, timeout=self._timeout
            )

    def _parse(
        self,
        response: httpx.Response,
        request: SerpSearchRequest,
        requested_at: datetime,
        attempts: int,
    ) -> SerpSearchResult:
        try:
            payload = response.json()
        except ValueError:
            raise SerpProviderError(
                "SERP_PROVIDER_INVALID_RESPONSE",
                "The SERP provider returned an invalid response.",
                request_count=attempts,
            ) from None
        if not isinstance(payload, dict):
            raise SerpProviderError(
                "SERP_PROVIDER_INVALID_RESPONSE",
                "The SERP provider returned an invalid response.",
                request_count=attempts,
            )
        if payload.get("error"):
            message = str(payload["error"]).lower()
            code = (
                "SERP_PROVIDER_AUTH_ERROR"
                if "api key" in message or "account" in message
                else "SERP_PROVIDER_ERROR"
            )
            safe = (
                "The SERP provider rejected its credentials."
                if code == "SERP_PROVIDER_AUTH_ERROR"
                else "The SERP provider could not complete the search."
            )
            raise SerpProviderError(code, safe, request_count=attempts)
        rows = payload.get("organic_results", [])
        if not isinstance(rows, list):
            raise SerpProviderError(
                "SERP_PROVIDER_INVALID_RESPONSE",
                "The SERP provider returned an invalid response.",
                request_count=attempts,
            )
        parsed: list[OrganicResult] = []
        positions: set[int] = set()
        warnings = 0
        for raw in rows:
            result = self._organic(raw)
            if (
                result is None
                or result.position > request.result_limit
                or result.position in positions
            ):
                warnings += 1
                continue
            positions.add(result.position)
            parsed.append(result)
        parsed.sort(key=lambda value: value.position)
        metadata = payload.get("search_metadata")
        request_id = None
        if isinstance(metadata, dict):
            candidate = metadata.get("id") or metadata.get("search_id")
            if isinstance(candidate, str):
                request_id = candidate[:255]
        return SerpSearchResult(
            provider=self.name,
            provider_request_id=request_id,
            organic_results=tuple(parsed[: request.result_limit]),
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
            raw_metadata={
                "organic_results_received": len(rows),
                "parsing_warnings": warnings,
            },
            provider_request_count=attempts,
        )

    @staticmethod
    def _organic(raw: Any) -> OrganicResult | None:
        if not isinstance(raw, dict):
            return None
        position = raw.get("position")
        url = raw.get("link")
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            return None
        if not isinstance(url, str) or not url:
            return None
        try:
            hostname = normalize_domain(url)
        except Exception:
            return None
        title = raw.get("title")
        displayed = raw.get("displayed_link")
        snippet = raw.get("snippet")
        return OrganicResult(
            position=position,
            title=title if isinstance(title, str) else "",
            url=url,
            hostname=hostname,
            displayed_url=displayed if isinstance(displayed, str) else None,
            snippet=snippet if isinstance(snippet, str) else None,
        )

    @staticmethod
    def _quota_exhausted(response: httpx.Response) -> bool:
        text = response.text.lower()
        return any(marker in text for marker in ("quota", "credit", "insufficient"))

    def _error(self, code: str, message: str, attempts: int) -> SerpProviderError:
        return SerpProviderError(
            code,
            message,
            request_count=attempts,
            provider=self.name,
        )
