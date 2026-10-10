from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from pydantic_core import PydanticCustomError

from app.repositories.user import normalize_email


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value: Any) -> Any:
        return normalize_email(value) if isinstance(value, str) else value


class NewPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    new_password: SecretStr

    @field_validator("new_password", mode="before")
    @classmethod
    def password_policy(cls, value: Any) -> Any:
        if isinstance(value, str) and not 10 <= len(value) <= 128:
            raise PydanticCustomError(
                "PASSWORD_POLICY_VIOLATION",
                "Password must contain 10 to 128 characters.",
            )
        return value


class ResetPasswordRequest(NewPasswordRequest):
    token: SecretStr = Field(min_length=64, max_length=128)


class ChangePasswordRequest(NewPasswordRequest):
    current_password: SecretStr = Field(min_length=1, max_length=128)
