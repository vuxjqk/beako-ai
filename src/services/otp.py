import hashlib
import hmac
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core import config
from src.models import OtpCode, OtpPurpose, User


class OtpCooldownError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Retry after {retry_after}s")
        self.retry_after = retry_after


def _hash_code(user_id: uuid.UUID, purpose: OtpPurpose, code: str) -> str:
    # Keyed hash: a 6-digit code is trivially brute-forced from a plain SHA-256
    message = f"{user_id}:{purpose.value}:{code}".encode()
    return hmac.new(config.JWT_SECRET.encode(), message, hashlib.sha256).hexdigest()


def issue_otp(db: Session, user: User, purpose: OtpPurpose) -> str:
    """Create a new OTP for the user, replacing any previous unused ones.

    Raises OtpCooldownError if one was issued too recently. Commits the session.
    """
    # Serialize concurrent requests for the same user so the cooldown holds
    db.execute(select(User.id).where(User.id == user.id).with_for_update())

    now = datetime.now(timezone.utc)
    last_created = db.scalar(
        select(OtpCode.created_at)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    if last_created is not None:
        elapsed = (now - last_created).total_seconds()
        if elapsed < config.OTP_RESEND_COOLDOWN_SECONDS:
            db.rollback()
            raise OtpCooldownError(math.ceil(config.OTP_RESEND_COOLDOWN_SECONDS - elapsed))

    db.execute(
        delete(OtpCode).where(
            OtpCode.user_id == user.id,
            OtpCode.purpose == purpose,
            OtpCode.used_at.is_(None),
        )
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        OtpCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=_hash_code(user.id, purpose, code),
            expires_at=now + timedelta(minutes=config.OTP_EXPIRE_MINUTES),
            created_at=now,
        )
    )
    db.commit()
    return code


def invalidate_otps(db: Session, user_id: uuid.UUID, *purposes: OtpPurpose) -> None:
    """Drop the user's unused OTPs (e.g. ones mailed to an old address). Does not commit."""
    db.execute(
        delete(OtpCode).where(
            OtpCode.user_id == user_id,
            OtpCode.purpose.in_(purposes),
            OtpCode.used_at.is_(None),
        )
    )


def consume_otp(db: Session, user: User, purpose: OtpPurpose, code: str) -> bool:
    """Check the code against the user's active OTP and mark it used on success.

    On success the caller must commit (together with its own changes) so the OTP
    is consumed atomically. A wrong code is counted and committed immediately.
    """
    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.user_id == user.id,
            OtpCode.purpose == purpose,
            OtpCode.used_at.is_(None),
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if otp is None or otp.expires_at <= now or otp.attempts >= config.OTP_MAX_ATTEMPTS:
        return False

    if not hmac.compare_digest(otp.code_hash, _hash_code(user.id, purpose, code)):
        otp.attempts += 1
        db.commit()
        return False

    otp.used_at = now
    return True
