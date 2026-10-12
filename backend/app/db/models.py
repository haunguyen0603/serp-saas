"""Import future ORM models here so Alembic discovers their metadata."""

from app.db.base import Base
from app.models.email_verification import EmailVerificationToken
from app.models.keyword import Keyword
from app.models.keyword_organization import (
    KeywordGroup,
    KeywordTag,
    KeywordTagAssignment,
)
from app.models.password_reset import PasswordResetToken
from app.models.payment import PaymentEvent, PaymentOrder
from app.models.project import Project
from app.models.project_competitor_site import ProjectCompetitorSite
from app.models.provider_usage import ProviderUsage
from app.models.rank_check import RankCheck
from app.models.rank_check_provider_attempt import RankCheckProviderAttempt
from app.models.rank_check_result import RankCheckResult
from app.models.rank_job import ProjectRankSchedule, RankCheckBatch, RankCheckJob
from app.models.ranking import Ranking
from app.models.refresh_token import RefreshToken
from app.models.report import GeneratedReport, ReportDeliveryAttempt, ReportSchedule
from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite
from app.models.user import User

__all__ = [
    "Base",
    "PaymentEvent",
    "PaymentOrder",
    "Plan",
    "PlanChange",
    "Subscription",
    "UsagePeriod",
    "UsageReservation",
    "UsageEvent",
    "BillingAuditEvent",
    "RankCheckBatch",
    "RankCheckJob",
    "GeneratedReport",
    "ReportDeliveryAttempt",
    "ReportSchedule",
    "ProjectRankSchedule",
    "User",
    "RefreshToken",
    "EmailVerificationToken",
    "PasswordResetToken",
    "Project",
    "ProjectCompetitorSite",
    "Keyword",
    "KeywordGroup",
    "KeywordTag",
    "KeywordTagAssignment",
    "ProviderUsage",
    "RankCheck",
    "RankCheckResult",
    "Ranking",
    "RankCheckProviderAttempt",
    "TrackedSite",
    "TrackedDomain",
]

from app.models.billing import (
    BillingAuditEvent,
    Plan,
    PlanChange,
    Subscription,
    UsageEvent,
    UsagePeriod,
    UsageReservation,
)
