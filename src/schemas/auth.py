import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from src.models import UserRole


def _check_bcrypt_limit(value: str) -> str:
    # bcrypt ignores everything past 72 bytes
    if len(value.encode()) > 72:
        raise ValueError("password must be at most 72 bytes")
    return value


Email = Annotated[EmailStr, AfterValidator(str.lower)]
NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_check_bcrypt_limit)]
OtpCode = Annotated[str, Field(pattern=r"^\d{6}$")]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(CamelModel):
    email: Email
    password: str = Field(min_length=1)


class RegisterRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: Email
    password: NewPassword

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("fullName must not be blank")
        return value


class GoogleLoginRequest(CamelModel):
    id_token: str = Field(min_length=1)


class VerifyEmailRequest(CamelModel):
    otp: OtpCode


class ForgotPasswordRequest(CamelModel):
    email: Email


class _NewPasswordWithConfirmation(CamelModel):
    new_password: NewPassword
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.new_password != self.confirm_password:
            raise ValueError("confirmPassword does not match newPassword")
        return self


class ResetPasswordRequest(_NewPasswordWithConfirmation):
    email: Email
    otp: OtpCode


class ChangePasswordRequest(_NewPasswordWithConfirmation):
    current_password: str = Field(min_length=1)


class UpdateMeRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    # Both optional: omitted fields are left unchanged
    full_name: str | None = Field(default=None, max_length=255)
    email: Email | None = None

    @field_validator("full_name", "email")
    @classmethod
    def not_null(cls, value: str | None) -> str:
        # Only runs for fields the client sent; an explicit null is not a valid value
        if value is None:
            raise ValueError("must not be null")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("fullName must not be blank")
        return value


class MessageResponse(BaseModel):
    message: str


class UserResponse(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    email_verified_at: datetime | None
    avatar: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
