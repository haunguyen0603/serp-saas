"""One-request, explicitly opt-in real Serper smoke test."""

import asyncio
import json
import os

from app.core.config import get_settings
from app.services.serp.serper import SerperProvider
from app.services.serp.types import SerpSearchRequest


async def run() -> None:
    settings = get_settings()
    enabled = os.getenv("RUN_REAL_SERPER_SMOKE", "").lower() == "true"
    key = settings.serper_api_key.get_secret_value() if settings.serper_api_key else ""
    if not enabled or not key:
        reason = (
            "RUN_REAL_SERPER_SMOKE is not true"
            if not enabled
            else "SERPER_API_KEY is not configured"
        )
        print(json.dumps({"real_serper_smoke": "skipped", "reason": reason}))
        return
    provider = SerperProvider(
        api_key=key,
        base_url=settings.serper_base_url,
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
    assert result.provider == "serper"
    assert all(item.position >= 1 and item.url for item in result.organic_results)
    print(
        json.dumps(
            {
                "real_serper_smoke": "passed",
                "requests": result.provider_request_count,
                "organic_results": len(result.organic_results),
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
