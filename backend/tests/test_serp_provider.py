from datetime import UTC, datetime

import httpx
import pytest

from app.services.serp import OrganicResult, SerpProviderError, SerpSearchRequest
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.serpapi import SerpApiProvider


def request() -> SerpSearchRequest:
    return SerpSearchRequest(
        query="rank tracker",
        search_engine="google",
        country_code="VN",
        language_code="vi",
        device="mobile",
        location="Ho Chi Minh City",
        result_limit=10,
    )


@pytest.mark.asyncio
async def test_serpapi_maps_request_and_normalizes_organic_results() -> None:
    seen: httpx.Request | None = None

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen = http_request
        return httpx.Response(
            200,
            json={
                "search_metadata": {"id": "provider-request"},
                "organic_results": [
                    {
                        "position": 2,
                        "title": "Owned",
                        "link": "https://WWW.Example.com./path?q=1",
                        "displayed_link": "example.com",
                        "snippet": "Result summary",
                    },
                    {"position": 0, "link": "https://invalid.example"},
                    {"position": 3},
                    {"position": 12, "link": "https://deep.example/page"},
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SerpApiProvider(
            api_key="provider-secret",
            base_url="https://serpapi.test/search",
            timeout_seconds=1,
            client=client,
            retry_delay_seconds=0,
        )
        result = await provider.search(request())
    assert seen is not None
    assert dict(seen.url.params) == {
        "api_key": "provider-secret",
        "engine": "google",
        "q": "rank tracker",
        "gl": "vn",
        "hl": "vi",
        "device": "mobile",
        "num": "10",
        "location": "Ho Chi Minh City",
    }
    assert result.provider == "serpapi"
    assert result.provider_request_id == "provider-request"
    assert result.provider_request_count == 1
    assert result.organic_results == (
        OrganicResult(
            position=2,
            title="Owned",
            url="https://WWW.Example.com./path?q=1",
            hostname="www.example.com",
            displayed_url="example.com",
            snippet="Result summary",
        ),
    )
    assert result.raw_metadata == {
        "organic_results_received": 4,
        "parsing_warnings": 3,
    }


@pytest.mark.asyncio
async def test_fake_provider_is_deterministic_and_network_free() -> None:
    provider = FakeSerpProvider()
    fixture = [OrganicResult(1, "Title", "https://site.example", "site.example")]
    provider.add_result("rank tracker", fixture)
    result = await provider.search(request())
    assert result.organic_results == tuple(fixture)
    assert provider.requests == [request()]
    assert result.requested_at <= result.completed_at <= datetime.now(UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "SERP_PROVIDER_AUTH_ERROR"),
        (403, "SERP_PROVIDER_AUTH_ERROR"),
        (429, "SERP_PROVIDER_RATE_LIMITED"),
        (500, "SERP_PROVIDER_UNAVAILABLE"),
        (400, "SERP_PROVIDER_INVALID_REQUEST"),
    ],
)
async def test_serpapi_maps_http_failures(status: int, code: str) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status))
    ) as client:
        provider = SerpApiProvider(
            api_key="secret",
            base_url="https://serpapi.test/search",
            timeout_seconds=1,
            client=client,
            retry_delay_seconds=0,
        )
        with pytest.raises(SerpProviderError) as failure:
            await provider.search(request())
    assert failure.value.code == code
    assert "secret" not in failure.value.safe_message
    assert failure.value.request_count == (2 if status in {429, 500} else 1)


@pytest.mark.asyncio
async def test_serpapi_maps_timeout_invalid_json_and_provider_error_safely() -> None:
    attempts = 0

    def timeout_handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("secret upstream timeout", request=http_request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(timeout_handler)
    ) as client:
        provider = SerpApiProvider(
            api_key="secret",
            base_url="https://serpapi.test/search",
            timeout_seconds=1,
            client=client,
            retry_delay_seconds=0,
        )
        with pytest.raises(SerpProviderError) as timeout:
            await provider.search(request())
    assert timeout.value.code == "SERP_PROVIDER_TIMEOUT" and attempts == 2
    for body, expected in [
        (b"not-json", "SERP_PROVIDER_INVALID_RESPONSE"),
        (b'{"error":"Invalid API key secret-value"}', "SERP_PROVIDER_AUTH_ERROR"),
    ]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _, response_body=body: httpx.Response(200, content=response_body)
            )
        ) as client:
            provider = SerpApiProvider(
                api_key="secret",
                base_url="https://serpapi.test/search",
                timeout_seconds=1,
                client=client,
            )
            with pytest.raises(SerpProviderError) as failure:
                await provider.search(request())
        assert failure.value.code == expected
        assert "secret-value" not in failure.value.safe_message


@pytest.mark.asyncio
async def test_missing_key_never_makes_http_request() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SerpApiProvider(
            api_key=None,
            base_url="https://serpapi.test/search",
            timeout_seconds=1,
            client=client,
        )
        with pytest.raises(SerpProviderError, match="not configured") as failure:
            await provider.search(request())
    assert failure.value.code == "SERP_PROVIDER_NOT_CONFIGURED"
    assert calls == 0
