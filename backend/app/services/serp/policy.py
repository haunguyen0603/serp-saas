from app.services.serp.base import SerpProviderError
from app.services.serp.registry import ProviderRegistration, ProviderRegistry
from app.services.serp.types import SerpSearchRequest


class ProviderSelectionPolicy:
    def __init__(
        self,
        *,
        strategy: str,
        priority: tuple[str, ...],
        fixed_provider: str | None,
    ) -> None:
        self.strategy = strategy
        self.priority = priority
        self.fixed_provider = fixed_provider

    def candidates(
        self, registry: ProviderRegistry, request: SerpSearchRequest
    ) -> list[ProviderRegistration]:
        if self.strategy == "fixed":
            if self.fixed_provider is None:
                return []
            registration = registry.get(self.fixed_provider)
            if registration is None or not registration.enabled:
                return []
            if not registration.configured:
                raise SerpProviderError(
                    "SERP_PROVIDER_NOT_CONFIGURED",
                    "The configured SERP provider is not available.",
                    provider=self.fixed_provider,
                )
            if not registration.capabilities.supports(request):
                raise SerpProviderError(
                    "SERP_PROVIDER_UNSUPPORTED_CONFIGURATION",
                    "The configured SERP provider cannot preserve "
                    "this search configuration.",
                    provider=self.fixed_provider,
                )
            return [registration]
        return registry.eligible(self.priority, request)
