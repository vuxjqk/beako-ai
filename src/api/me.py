from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.core import config
from src.core.security import hash_password, verify_password
from src.models import OtpPurpose, User, get_db
from src.schemas.auth import (
    ChangePasswordRequest,
    MessageResponse,
    UpdateMeRequest,
    UserResponse,
)
from src.services import storage
from src.services.otp import invalidate_otps
from src.services.session import clear_auth_cookies, issue_tokens, revoke_all_refresh_tokens

router = APIRouter(prefix="/auth/me", tags=["me"])


@router.get("", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("", response_model=UserResponse)
def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    changes = body.model_dump(exclude_unset=True)
    email_taken = HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    if "full_name" in changes:
        user.full_name = changes["full_name"]

    new_email = changes.get("email")
    if new_email is not None and new_email != user.email:
        if db.scalar(select(User.id).where(User.email == new_email)) is not None:
            raise email_taken
        user.email = new_email
        # The new address is unproven, and the Google account was tied to the old one
        user.email_verified_at = None
        user.google_id = None
        # OTPs already mailed to the old address must not verify/reset the new one
        invalidate_otps(db, user.id, OtpPurpose.EMAIL_VERIFICATION, OtpPurpose.PASSWORD_RESET)

    try:
        db.commit()
    except IntegrityError:
        # Lost a race with another account taking the same email
        db.rollback()
        raise email_taken
    return user


@router.patch("/password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if user.password_hash is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Account has no password yet; use forgot-password to set one",
        )
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "New password must be different from the current one"
        )

    user.password_hash = hash_password(body.new_password)
    invalidate_otps(db, user.id, OtpPurpose.PASSWORD_RESET)
    # Sign out every other session, then give this one fresh tokens
    revoke_all_refresh_tokens(db, user.id)
    issue_tokens(db, response, user)
    return MessageResponse(message="Password has been changed")


@router.put("/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    data = file.file.read(config.AVATAR_MAX_BYTES + 1)
    if len(data) > config.AVATAR_MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Avatar must be at most {config.AVATAR_MAX_BYTES // (1024 * 1024)} MB",
        )
    try:
        new_url = storage.save_avatar(data)
    except storage.InvalidImageError as e:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(e))

    old_url = user.avatar
    user.avatar = new_url
    try:
        db.commit()
    except Exception:
        storage.delete_avatar(new_url)
        raise
    # Only remove the old file once the DB no longer points to it
    storage.delete_avatar(old_url)
    return user


@router.delete("/avatar", response_model=UserResponse)
def delete_avatar(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    old_url = user.avatar
    user.avatar = None
    db.commit()
    storage.delete_avatar(old_url)
    return user


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    # Soft delete only: the row (and avatar file) is kept
    user.deleted_at = datetime.now(timezone.utc)
    revoke_all_refresh_tokens(db, user.id)
    db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response
