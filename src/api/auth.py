from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.core.email import send_otp_email
from src.core.google import GoogleTokenError, verify_google_id_token
from src.core.security import hash_password, hash_refresh_token, verify_password
from src.models import OtpPurpose, RefreshToken, User, get_db
from src.schemas.auth import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from src.services import login_limit
from src.services.otp import OtpCooldownError, consume_otp, issue_otp
from src.services.session import (
    REFRESH_TOKEN_COOKIE,
    clear_auth_cookies,
    issue_tokens,
    revoke_all_refresh_tokens,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    """Too many wrong passwords for one email answer 429 with Retry-After (see login_limit)."""
    try:
        login_limit.check(db, body.email)
    except login_limit.TooManyAttempts as e:
        db.rollback()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many failed logins; try again later or reset your password",
                            headers={"Retry-After": str(e.retry_after)})
    user = db.scalar(select(User).where(User.email == body.email))
    password_ok = verify_password(body.password, user.password_hash if user else None)
    ok = user is not None and password_ok and user.deleted_at is None
    # The browser's address as the proxy reports it; for the audit trail only
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else None)
    login_limit.record(db, body.email, ok, ip[:64] if ip else None)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    issue_tokens(db, response, user)
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> User:
    email_taken = HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise email_taken

    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # Lost a race with a concurrent registration for the same email
        db.rollback()
        raise email_taken

    issue_tokens(db, response, user)
    db.refresh(user)
    return user


@router.post("/google", response_model=UserResponse)
def google_login(body: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    try:
        profile = verify_google_id_token(body.id_token)
    except GoogleTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google token")

    user = db.scalar(select(User).where(User.google_id == profile.sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == profile.email))
        if user is not None and user.google_id is not None:
            # Email belongs to an account already linked to a different Google account
            raise HTTPException(status.HTTP_409_CONFLICT, "Email is linked to another Google account")

    if user is not None and (user.deleted_at is not None or not user.is_active):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            full_name=profile.name or profile.email.split("@")[0],
            email=profile.email,
            google_id=profile.sub,
            avatar=profile.picture,
            email_verified_at=now,
        )
        db.add(user)
    else:
        if user.google_id is None:
            if user.email_verified_at is None:
                # Whoever registered this email never proved owning it; drop their
                # password so they can't keep access to the real owner's account
                user.password_hash = None
            user.google_id = profile.sub
        if user.email_verified_at is None:
            user.email_verified_at = now
        if user.avatar is None:
            user.avatar = profile.picture

    try:
        db.flush()
    except IntegrityError:
        # Lost a race with a concurrent sign-up for the same email/Google account
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Account was just created, please retry")

    issue_tokens(db, response, user)
    db.refresh(user)
    return user


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
    db: Session = Depends(get_db),
) -> Response:
    stored = None
    if refresh_token is not None:
        stored = db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
            .with_for_update()
        )

    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at <= now
        or stored.user.deleted_at is not None
        or not stored.user.is_active
    ):
        error = JSONResponse(
            {"detail": "Invalid or expired refresh token"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        clear_auth_cookies(error)
        return error

    # Rotate: the presented refresh token can't be used again
    stored.revoked_at = now
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    issue_tokens(db, response, stored.user)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
    db: Session = Depends(get_db),
) -> Response:
    if refresh_token is not None:
        stored = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
        )
        if stored is not None:
            stored.revoked_at = datetime.now(timezone.utc)
            db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post(
    "/email/verification/send",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def send_email_verification(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if user.email_verified_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already verified")
    try:
        code = issue_otp(db, user, OtpPurpose.EMAIL_VERIFICATION)
    except OtpCooldownError as e:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Please wait {e.retry_after}s before requesting a new OTP",
            headers={"Retry-After": str(e.retry_after)},
        )

    background_tasks.add_task(send_otp_email, user.email, user.full_name, code, "xác thực email")
    return MessageResponse(message="Verification OTP has been sent to your email")


@router.post("/email/verification/verify", response_model=UserResponse)
def verify_email(
    body: VerifyEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.email_verified_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already verified")
    if not consume_otp(db, user, OtpPurpose.EMAIL_VERIFICATION, body.otp):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OTP")

    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    return user


FORGOT_PASSWORD_MESSAGE = "If the email is registered, a password reset OTP has been sent"


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    # Every branch returns the same response, and the email is sent in the
    # background so response time doesn't reveal whether the account exists.
    user = db.scalar(
        select(User).where(
            User.email == body.email,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    if user is not None:
        try:
            code = issue_otp(db, user, OtpPurpose.PASSWORD_RESET)
        except OtpCooldownError:
            pass
        else:
            background_tasks.add_task(
                send_otp_email, user.email, user.full_name, code, "đặt lại mật khẩu"
            )
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OTP")
    user = db.scalar(
        select(User).where(
            User.email == body.email,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    if user is None or not consume_otp(db, user, OtpPurpose.PASSWORD_RESET, body.otp):
        raise invalid

    user.password_hash = hash_password(body.new_password)
    # Sign out every session that was opened with the old password
    revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return MessageResponse(message="Password has been reset")
