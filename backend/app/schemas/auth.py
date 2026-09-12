from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    SecretStr,
    StrictBool,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app.repositories.user import normalize_email
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: EmailStr
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value: Any) -> Any:
        return normalize_email(value) if isinstance(value, str) else value

    @field_validator("password", mode="before")
    @classmethod
    def password_policy(cls, value: Any) -> Any:
        if isinstance(value, str) and not 10 <= len(value) <= 128:
            raise PydanticCustomError(
                "PASSWORD_POLICY_VIOLATION",
                "Password must contain 10 to 128 characters.",
            )
        return value


class RegisterRequest(LoginRequest):
    accept_terms: StrictBool

    @field_validator("accept_terms")
    @classmethod
    def terms_required(cls, value: bool) -> bool:
        if not value:
            raise PydanticCustomError(
                "TERMS_NOT_ACCEPTED", "You must accept the Terms of Service."
            )
        return value


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class SessionRequest(BaseModel):
    """An optional empty JSON body; refresh credentials come only from the cookie."""

    model_config = ConfigDict(extra="forbid")
