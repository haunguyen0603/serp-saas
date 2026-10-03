from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    token: SecretStr

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: SecretStr) -> SecretStr:
        if not 32 <= len(value.get_secret_value()) <= 256:
            raise ValueError("Invalid verification token")
        return value


class VerificationStatus(BaseModel):
    verified: bool
    delivery_status: Literal["not_requested", "pending", "sent", "failed", "verified"]
    retry_after_seconds: int
    expires_at: datetime | None = None


class VerifiedEmailResponse(BaseModel):
    status: Literal["verified"] = "verified"
    user_id: UUID
