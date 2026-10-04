"""Limit password guesses per account.

After LOGIN_MAX_FAILURES failed logins for one email (since its last successful login) within
LOGIN_LOCK_MINUTES, further logins for that email are refused with 429 until the oldest of
those failures is that old, even with the right password. Unknown emails are limited the same
way, so the response does not reveal which emails have accounts.

Limits are per email, not per IP: behind the Next.js proxy the client can set X-Forwarded-For
itself, and without it every user shares the proxy's address. Per-IP limits belong in the
reverse proxy of a deployment.
"""

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.models import LoginAttempt


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        super().__init__("too many failed logins")
        self.retry_after = retry_after


def _lock_key(email: str) -> int:
    """A 64-bit advisory lock id for this email."""
    return int.from_bytes(hashlib.sha256(f"login:{email}".encode()).digest()[:8], "big", signed=True)


def check(db: Session, email: str) -> None:
    """Take the per-email lock for this login (held until commit/rollback, so parallel guesses
    for one account are counted one at a time) and raise TooManyAttempts when it is locked."""
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _lock_key(email)})
    row = db.execute(text(f"""
        SELECT count(*) AS failures,
               ceil(extract(epoch FROM min(created_at) + interval '{config.LOGIN_LOCK_MINUTES} minutes' - now()))::int
                   AS frees_in
        FROM login_attempts
        WHERE email = :e AND NOT success
          AND created_at > now() - interval '{config.LOGIN_LOCK_MINUTES} minutes'
          AND created_at > coalesce((SELECT max(created_at) FROM login_attempts WHERE email = :e AND success),
                                    '-infinity')
    """), {"e": email}).one()
    if row.failures >= config.LOGIN_MAX_FAILURES:
        raise TooManyAttempts(max(1, row.frees_in or 1))


def record(db: Session, email: str, success: bool, ip: str | None) -> None:
    """Store the outcome and commit (which also releases the lock taken by check())."""
    db.add(LoginAttempt(email=email, success=success, ip=ip))
    db.commit()
