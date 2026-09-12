from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.registry import (
    ProviderCapabilities,
    ProviderRegistration,
    ProviderRegistry,
)
from app.services.serp.router import ProviderRouter
from app.services.serp.serpapi import SerpApiProvider
from app.services.serp.serper import SerperProvider


def get_provider_router(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> ProviderRouter:
    enabled = set(settings.enabled_provider_names)
    registrations = [
        ProviderRegistration(
            provider=SerperProvider(
                api_key=(
                    settings.serper_api_key.get_secret_value()
                    if settings.serper_api_key
                    else None
                ),
                base_url=settings.serper_base_url,
                timeout_seconds=settings.serp_request_timeout_seconds,
            ),
            configured=bool(
                settings.serper_api_key and settings.serper_api_key.get_secret_value()
            ),
            enabled="serper" in enabled,
            capabilities=ProviderCapabilities(
                supported_search_engines=frozenset({"google"}),
                # Serper Search has no documented device request field.
                supported_devices=frozenset({"desktop"}),
            ),
            request_budget=settings.serper_request_budget,
        ),
        ProviderRegistration(
            provider=SerpApiProvider(
                api_key=(
                    settings.serpapi_api_key.get_secret_value()
                    if settings.serpapi_api_key
                    else None
                ),
                base_url=settings.serpapi_base_url,
                timeout_seconds=settings.serp_request_timeout_seconds,
            ),
            configured=bool(
                settings.serpapi_api_key and settings.serpapi_api_key.get_secret_value()
            ),
            enabled="serpapi" in enabled,
            capabilities=ProviderCapabilities(
                supported_search_engines=frozenset({"google"}),
                supported_devices=frozenset({"desktop", "mobile"}),
            ),
            request_budget=settings.serpapi_request_budget,
        ),
        ProviderRegistration(
            provider=FakeSerpProvider(delay_seconds=0.2),
            configured=True,
            enabled="fake" in enabled,
            capabilities=ProviderCapabilities(
                supported_search_engines=frozenset({"google"}),
                supported_devices=frozenset({"desktop", "mobile"}),
            ),
        ),
    ]
    return ProviderRouter(
        registry=ProviderRegistry(registrations),
        session_factory=session_factory,
        strategy=settings.effective_provider_strategy,
        priority=settings.provider_priority_names,
        fixed_provider=settings.effective_fixed_provider,
        max_fallbacks=settings.serp_max_provider_fallbacks,
    )
