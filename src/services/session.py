"""Auth cookies and refresh-token bookkeeping shared by the auth endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.api.deps import ACCESS_TOKEN_COOKIE
from src.core import config
from src.core.security import create_access_token, generate_refresh_token, hash_refresh_token
from src.models import RefreshToken, User

REFRESH_TOKEN_COOKIE = "refresh_token"
# The browser only sends the refresh token to /auth/* endpoints
REFRESH_TOKEN_PATH = "/auth"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": config.COOKIE_SECURE, "samesite": "lax"}
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        **common,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_TOKEN_PATH,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    common = {"httponly": True, "secure": config.COOKIE_SECURE, "samesite": "lax"}
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path=REFRESH_TOKEN_PATH, **common)


def issue_tokens(db: Session, response: Response, user: User) -> None:
    """Start a new session: store a refresh token, commit, and set both cookies."""
    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    set_auth_cookies(response, create_access_token(user.id), refresh_token)


def revoke_all_refresh_tokens(db: Session, user_id: uuid.UUID) -> None:
    """Sign the user out everywhere. Does not commit."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
