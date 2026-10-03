import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.core.security import hash_password
from src.models import OtpPurpose, User, UserRole, get_db
from src.schemas.admin import (
    AdminCreateUserRequest,
    AdminSetActiveRequest,
    AdminUpdateUserRequest,
    Page,
)
from src.schemas.auth import UserResponse
from src.services.otp import invalidate_otps
from src.services.session import revoke_all_refresh_tokens

router = APIRouter(
    prefix="/admin/users",
    tags=["admin: users"],
    dependencies=[Depends(require_admin)],
)

# Admins and soft-deleted accounts are invisible to these endpoints
_MANAGEABLE = (User.role != UserRole.ADMIN, User.deleted_at.is_(None))


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "User not found")


def _email_taken() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")


def _get_manageable_user(db: Session, user_id: uuid.UUID) -> User:
    # An admin's id gets exactly the same 404 as a nonexistent one, so admin ids can't be probed
    user = db.scalar(select(User).where(User.id == user_id, *_MANAGEABLE))
    if user is None:
        raise _not_found()
    return user


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=Page[UserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    search: str | None = Query(None, max_length=255, description="Matches full name or email"),
    db: Session = Depends(get_db),
) -> Page[UserResponse]:
    filters = list(_MANAGEABLE)
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        filters.append(
            or_(
                User.full_name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )

    total = db.scalar(select(func.count()).select_from(User).where(*filters))
    users = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[UserResponse](
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(body: AdminCreateUserRequest, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise _email_taken()

    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole(body.role),
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent sign-up for the same email
        db.rollback()
        raise _email_taken()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    return _get_manageable_user(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: AdminUpdateUserRequest,
    db: Session = Depends(get_db),
) -> User:
    user = _get_manageable_user(db, user_id)
    changes = body.model_dump(exclude_unset=True)

    if "full_name" in changes:
        user.full_name = changes["full_name"]
    if "role" in changes:
        user.role = UserRole(changes["role"])

    new_email = changes.get("email")
    if new_email is not None and new_email != user.email:
        if db.scalar(select(User.id).where(User.email == new_email)) is not None:
            raise _email_taken()
        user.email = new_email
        # The linked Google account belongs to the old address
        user.google_id = None
        # OTPs already mailed to the old address must not act on the new one
        invalidate_otps(db, user.id, OtpPurpose.EMAIL_VERIFICATION, OtpPurpose.PASSWORD_RESET)

    if "password" in changes:
        user.password_hash = hash_password(changes["password"])
        invalidate_otps(db, user.id, OtpPurpose.PASSWORD_RESET)
        # Sessions opened with the old password shouldn't survive an admin reset
        revoke_all_refresh_tokens(db, user.id)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _email_taken()
    db.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_user_active(
    user_id: uuid.UUID,
    body: AdminSetActiveRequest,
    db: Session = Depends(get_db),
) -> User:
    user = _get_manageable_user(db, user_id)
    user.is_active = body.is_active
    if not body.is_active:
        # Access tokens are rejected on the next request because get_current_user
        # checks is_active; revoking refresh tokens ends the sessions for good
        revoke_all_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)
    return user
