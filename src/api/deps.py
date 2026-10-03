from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import decode_access_token
from src.models import User, UserRole, get_db

ACCESS_TOKEN_COOKIE = "access_token"


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(access_token) if access_token else None
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
