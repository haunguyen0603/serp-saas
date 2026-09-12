from dataclasses import dataclass

from app.services.serp.base import SerpProvider
from app.services.serp.types import SerpSearchRequest


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    supported_search_engines: frozenset[str]
    supported_devices: frozenset[str]
    supports_location: bool = True
    synchronous_search: bool = True

    def supports(self, request: SerpSearchRequest) -> bool:
        return (
            request.search_engine in self.supported_search_engines
            and request.device in self.supported_devices
            and (request.location is None or self.supports_location)
            and self.synchronous_search
        )


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    provider: SerpProvider
    configured: bool
    enabled: bool
    capabilities: ProviderCapabilities
    request_budget: int | None = None


class ProviderRegistry:
    def __init__(self, registrations: list[ProviderRegistration]) -> None:
        self._registrations = {
            registration.provider.name: registration for registration in registrations
        }
        if len(self._registrations) != len(registrations):
            raise ValueError("Provider names must be unique")

    def get(self, name: str) -> ProviderRegistration | None:
        return self._registrations.get(name)

    def eligible(
        self, names: tuple[str, ...], request: SerpSearchRequest
    ) -> list[ProviderRegistration]:
        return [
            registration
            for name in names
            if (registration := self.get(name)) is not None
            and registration.enabled
            and registration.configured
            and registration.capabilities.supports(request)
        ]
