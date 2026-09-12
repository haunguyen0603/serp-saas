from dataclasses import dataclass
from uuid import UUID

from app.services.serp.types import OrganicResult


@dataclass(frozen=True, slots=True)
class MatchableDomain:
    tracked_site_id: UUID
    tracked_domain_id: UUID
    tracked_site_name: str
    domain: str


@dataclass(frozen=True, slots=True)
class MatchedOrganicResult:
    tracked_site_id: UUID
    tracked_domain_id: UUID
    tracked_site_name: str
    matched_domain: str
    position: int
    result_url: str
    result_hostname: str
    title: str


class DomainMatcher:
    def match(
        self,
        organic_results: tuple[OrganicResult, ...],
        domains: list[MatchableDomain],
    ) -> list[MatchedOrganicResult]:
        exact = {domain.domain: domain for domain in domains}
        best: dict[UUID, MatchedOrganicResult] = {}
        for result in organic_results:
            domain = exact.get(result.hostname)
            if domain is None:
                equivalent = (
                    result.hostname[4:]
                    if result.hostname.startswith("www.")
                    else f"www.{result.hostname}"
                )
                domain = exact.get(equivalent)
            if domain is None:
                continue
            match = MatchedOrganicResult(
                tracked_site_id=domain.tracked_site_id,
                tracked_domain_id=domain.tracked_domain_id,
                tracked_site_name=domain.tracked_site_name,
                matched_domain=domain.domain,
                position=result.position,
                result_url=result.url,
                result_hostname=result.hostname,
                title=result.title,
            )
            current = best.get(domain.tracked_site_id)
            if current is None or match.position < current.position:
                best[domain.tracked_site_id] = match
        return sorted(
            best.values(), key=lambda value: (value.position, value.tracked_site_id)
        )
