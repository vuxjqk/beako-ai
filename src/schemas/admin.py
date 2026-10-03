from typing import Annotated, Generic, Literal, TypeVar

from pydantic import ConfigDict, Field, StringConstraints, field_validator

from src.schemas.auth import CamelModel, Email, NewPassword

FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
# Admins can't create or promote other admins through the API
ManagedRole = Literal["user", "expert"]

T = TypeVar("T")


class AdminCreateUserRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    full_name: FullName
    email: Email
    password: NewPassword
    role: ManagedRole = "user"


class AdminUpdateUserRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    # All optional: omitted fields are left unchanged
    full_name: FullName | None = None
    email: Email | None = None
    password: NewPassword | None = None
    role: ManagedRole | None = None

    @field_validator("full_name", "email", "password", "role")
    @classmethod
    def not_null(cls, value: str | None) -> str:
        # Only runs for fields the client sent; an explicit null is not a valid value
        if value is None:
            raise ValueError("must not be null")
        return value


class AdminSetActiveRequest(CamelModel):
    is_active: bool


class Page(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
