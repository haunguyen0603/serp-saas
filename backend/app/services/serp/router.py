import logging
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.rank_check_provider_attempt import ProviderAttemptStatus
from app.repositories.provider_usage import ProviderUsageRepository
from app.repositories.rank_check_provider_attempt import (
    RankCheckProviderAttemptRepository,
)
from app.services.serp.base import (
    ProviderBudgetReservationError,
    SerpProviderError,
)
from app.services.serp.policy import ProviderSelectionPolicy
from app.services.serp.registry import ProviderRegistration, ProviderRegistry
from app.services.serp.types import SerpSearchRequest, SerpSearchResult

logger = logging.getLogger(__name__)

_SAFE_FALLBACK_CODES = {
    "SERP_PROVIDER_TIMEOUT",
    "SERP_PROVIDER_UNAVAILABLE",
    "SERP_PROVIDER_RATE_LIMITED",
    "SERP_PROVIDER_QUOTA_EXHAUSTED",
}


class ProviderRouter:
    name = "unselected"

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        strategy: str,
        priority: tuple[str, ...],
        fixed_provider: str | None,
        max_fallbacks: int,
    ) -> None:
        self.registry = registry
        self.session_factory = session_factory
        self.strategy = strategy
        self.priority = priority
        self.fixed_provider = fixed_provider
        self.max_fallbacks = max_fallbacks
        self.selection_policy = ProviderSelectionPolicy(
            strategy=strategy,
            priority=priority,
            fixed_provider=fixed_provider,
        )

    async def search(
        self, request: SerpSearchRequest, rank_check_id: UUID
    ) -> SerpSearchResult:
        registrations = self.selection_policy.candidates(self.registry, request)
        if not registrations:
            raise self._no_provider_error()

        total_requests = 0
        attempt_number = 0
        last_error: SerpProviderError | None = None
        for registration in registrations:
            if attempt_number >= 1 + self.max_fallbacks:
                break
            if not await self._within_budget(registration):
                self._log_budget(rank_check_id, registration.provider.name)
                continue

            started_at = datetime.now(UTC)
            reserved = 0

            async def reserve(
                current: ProviderRegistration = registration,
            ) -> None:
                nonlocal reserved
                if not await self._reserve(current):
                    raise ProviderBudgetReservationError
                reserved += 1

            logger.info(
                "serp_provider_selected",
                extra={
                    "rank_check_id": str(rank_check_id),
                    "provider": registration.provider.name,
                    "attempt": attempt_number + 1,
                },
            )
            try:
                result = await registration.provider.search(request, reserve)
            except ProviderBudgetReservationError:
                if reserved:
                    attempt_number += 1
                    total_requests += reserved
                    await self._record_failure(
                        rank_check_id,
                        registration.provider.name,
                        attempt_number,
                        started_at,
                        "SERP_PROVIDER_BUDGET_EXHAUSTED",
                        reserved,
                        fallback=True,
                    )
                self._log_budget(rank_check_id, registration.provider.name)
                continue
            except SerpProviderError as error:
                actual_requests = reserved
                if actual_requests:
                    attempt_number += 1
                    total_requests += actual_requests
                    can_fallback = (
                        error.code in _SAFE_FALLBACK_CODES
                        and attempt_number <= self.max_fallbacks
                    )
                    await self._record_failure(
                        rank_check_id,
                        registration.provider.name,
                        attempt_number,
                        started_at,
                        error.code,
                        actual_requests,
                        fallback=can_fallback,
                    )
                    if can_fallback:
                        logger.warning(
                            "serp_provider_fallback",
                            extra={
                                "rank_check_id": str(rank_check_id),
                                "provider": registration.provider.name,
                                "attempt": attempt_number,
                                "error_code": error.code,
                            },
                        )
                        last_error = SerpProviderError(
                            error.code,
                            error.safe_message,
                            request_count=total_requests,
                            provider=registration.provider.name,
                        )
                        continue
                raise SerpProviderError(
                    error.code,
                    error.safe_message,
                    request_count=total_requests,
                    provider=registration.provider.name,
                ) from None

            actual_requests = reserved
            attempt_number += 1
            total_requests += actual_requests
            await self._record_success(
                rank_check_id,
                registration.provider.name,
                attempt_number,
                started_at,
                result.completed_at,
                actual_requests,
            )
            return replace(result, provider_request_count=total_requests)

        logger.warning(
            "serp_provider_no_eligible_provider",
            extra={"rank_check_id": str(rank_check_id)},
        )
        if last_error is not None:
            raise SerpProviderError(
                last_error.code,
                last_error.safe_message,
                request_count=total_requests,
                provider=last_error.provider,
            ) from None
        raise self._no_provider_error(total_requests)

    async def _within_budget(self, registration: ProviderRegistration) -> bool:
        if registration.request_budget is None:
            return True
        async with self.session_factory() as session:
            usage = await ProviderUsageRepository(session).current(
                registration.provider.name
            )
            return usage is None or usage.request_count < registration.request_budget

    async def _reserve(self, registration: ProviderRegistration) -> bool:
        async with self.session_factory() as session:
            async with session.begin():
                return await ProviderUsageRepository(session).reserve_request(
                    registration.provider.name, registration.request_budget
                )

    async def _record_success(
        self,
        rank_check_id: UUID,
        provider: str,
        attempt_number: int,
        started_at: datetime,
        completed_at: datetime,
        request_count: int,
    ) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                await RankCheckProviderAttemptRepository(session).create(
                    rank_check_id=rank_check_id,
                    provider=provider,
                    attempt_number=attempt_number,
                    status=ProviderAttemptStatus.SUCCEEDED,
                    started_at=started_at,
                    completed_at=completed_at,
                    provider_request_count=request_count,
                )
                await ProviderUsageRepository(session).record_outcome(
                    provider,
                    successes=1,
                    failures=max(0, request_count - 1),
                )

    async def _record_failure(
        self,
        rank_check_id: UUID,
        provider: str,
        attempt_number: int,
        started_at: datetime,
        error_code: str,
        request_count: int,
        *,
        fallback: bool,
    ) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                await RankCheckProviderAttemptRepository(session).create(
                    rank_check_id=rank_check_id,
                    provider=provider,
                    attempt_number=attempt_number,
                    status=ProviderAttemptStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    provider_request_count=request_count,
                    error_code=error_code,
                )
                await ProviderUsageRepository(session).record_outcome(
                    provider,
                    failures=request_count,
                    fallbacks=int(fallback),
                )

    @staticmethod
    def _log_budget(rank_check_id: UUID, provider: str) -> None:
        logger.warning(
            "serp_provider_budget_exhausted",
            extra={"rank_check_id": str(rank_check_id), "provider": provider},
        )

    def _no_provider_error(self, request_count: int = 0) -> SerpProviderError:
        code = (
            "SERP_PROVIDER_NOT_CONFIGURED"
            if self.strategy == "fixed"
            else "SERP_NO_PROVIDER_AVAILABLE"
        )
        return SerpProviderError(
            code,
            "The ranking provider is temporarily unavailable.",
            request_count=request_count,
            provider=self.fixed_provider if self.strategy == "fixed" else None,
        )
