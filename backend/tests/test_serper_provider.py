import httpx
import pytest

from app.services.serp import OrganicResult, SerpProviderError, SerpSearchRequest
from app.services.serp.serper import SerperProvider


def request() -> SerpSearchRequest:
    return SerpSearchRequest(
        query="rank tracker",
        search_engine="google",
        country_code="VN",
        language_code="vi",
        device="desktop",
        location="Ho Chi Minh City",
        result_limit=10,
    )


@pytest.mark.asyncio
async def test_serper_maps_request_and_normalizes_response() -> None:
    seen: httpx.Request | None = None

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen = http_request
        return httpx.Response(
            200,
            headers={"x-request-id": "serper-request"},
            json={
                "organic": [
                    {
                        "position": 2,
                        "title": "Owned",
                        "link": "https://WWW.Example.com./rank",
                        "snippet": "Summary",
                    },
                    {"position": 0, "link": "https://invalid.example"},
                    {"position": 2, "link": "https://duplicate.example"},
                    {"position": 12, "link": "https://deep.example"},
                    {"position": 3},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SerperProvider(
            api_key="provider-secret",
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=client,
        )
        result = await provider.search(request())

    assert seen is not None
    assert seen.method == "POST"
    assert seen.headers["x-api-key"] == "provider-secret"
    assert seen.headers["content-type"].startswith("application/json")
    assert seen.url == httpx.URL("https://google.serper.test/search")
    assert __import__("json").loads(seen.content) == {
        "q": "rank tracker",
        "gl": "vn",
        "hl": "vi",
        "num": 10,
        "location": "Ho Chi Minh City",
    }
    assert result.provider == "serper"
    assert result.provider_request_id == "serper-request"
    assert result.organic_results == (
        OrganicResult(
            position=2,
            title="Owned",
            url="https://WWW.Example.com./rank",
            hostname="www.example.com",
            snippet="Summary",
        ),
    )
    assert result.raw_metadata == {
        "organic_results_received": 5,
        "parsing_warnings": 4,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "body", "code", "attempts"),
    [
        (401, "", "SERP_PROVIDER_AUTH_ERROR", 1),
        (403, "", "SERP_PROVIDER_AUTH_ERROR", 1),
        (400, "", "SERP_PROVIDER_INVALID_REQUEST", 1),
        (429, "rate limited", "SERP_PROVIDER_RATE_LIMITED", 2),
        (429, "quota exhausted", "SERP_PROVIDER_QUOTA_EXHAUSTED", 1),
        (500, "", "SERP_PROVIDER_UNAVAILABLE", 2),
    ],
)
async def test_serper_maps_http_failures(
    status: int, body: str, code: str, attempts: int
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, text=body))
    ) as client:
        provider = SerperProvider(
            api_key="secret",
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=client,
            retry_delay_seconds=0,
        )
        with pytest.raises(SerpProviderError) as failure:
            await provider.search(request())
    assert failure.value.code == code
    assert failure.value.provider == "serper"
    assert failure.value.request_count == attempts
    assert "secret" not in failure.value.safe_message


@pytest.mark.asyncio
async def test_serper_timeout_invalid_json_and_missing_key_are_safe() -> None:
    calls = 0

    def timeout(http_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("secret detail", request=http_request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        provider = SerperProvider(
            api_key="secret",
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=client,
            retry_delay_seconds=0,
        )
        with pytest.raises(SerpProviderError) as failure:
            await provider.search(request())
    assert failure.value.code == "SERP_PROVIDER_TIMEOUT"
    assert failure.value.request_count == calls == 2

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"bad"))
    ) as client:
        provider = SerperProvider(
            api_key="secret",
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=client,
        )
        with pytest.raises(SerpProviderError) as failure:
            await provider.search(request())
    assert failure.value.code == "SERP_PROVIDER_INVALID_RESPONSE"

    missing = SerperProvider(
        api_key=None,
        base_url="https://google.serper.test/search",
        timeout_seconds=1,
    )
    with pytest.raises(SerpProviderError) as failure:
        await missing.search(request())
    assert failure.value.code == "SERP_PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_serper_accepts_empty_organic_results() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"organic": []})
        )
    ) as client:
        provider = SerperProvider(
            api_key="secret",
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=client,
        )
        result = await provider.search(request())
    assert result.organic_results == ()
    assert result.raw_metadata["organic_results_received"] == 0
