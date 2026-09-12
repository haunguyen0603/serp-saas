"""One-request, explicitly opt-in real SerpApi smoke test."""

import asyncio
import json
import os

from app.core.config import get_settings
from app.services.serp.serpapi import SerpApiProvider
from app.services.serp.types import SerpSearchRequest


async def run() -> None:
    settings = get_settings()
    enabled = os.getenv("RUN_REAL_SERP_SMOKE", "").lower() == "true"
    key = (
        settings.serpapi_api_key.get_secret_value() if settings.serpapi_api_key else ""
    )
    if not enabled or not key:
        reason = (
            "RUN_REAL_SERP_SMOKE is not true"
            if not enabled
            else "SERPAPI_API_KEY is not configured"
        )
        print(json.dumps({"real_serpapi_smoke": "skipped", "reason": reason}))
        return
    provider = SerpApiProvider(
        api_key=key,
        base_url=settings.serpapi_base_url,
        timeout_seconds=settings.serp_request_timeout_seconds,
        max_attempts=1,
    )
    result = await provider.search(
        SerpSearchRequest(
            query="OpenAI",
            search_engine="google",
            country_code="US",
            language_code="en",
            device="desktop",
            location=None,
            result_limit=1,
        )
    )
    assert result.provider == "serpapi"
    assert all(
        item.position >= 1 and item.url and item.hostname
        for item in result.organic_results
    )
    print(
        json.dumps(
            {
                "real_serpapi_smoke": "passed",
                "requests": result.provider_request_count,
                "organic_results": len(result.organic_results),
                "provider_request_id_present": result.provider_request_id is not None,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
