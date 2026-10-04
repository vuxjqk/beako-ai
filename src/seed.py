"""Accounts for a new database.

    python -m src.seed                         development: admin/expert/user with password 12345678
    python -m src.seed admin EMAIL [FULL NAME] production: one admin with a random password,
                                               printed once (change it after signing in)
"""

import secrets
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from src.core.security import hash_password
from src.models import SessionLocal, User, UserRole

DEFAULT_PASSWORD = "12345678"

SEED_USERS = [
    {"full_name": "Admin", "email": "admin@beako.com", "role": UserRole.ADMIN},
    {"full_name": "Expert", "email": "expert@beako.com", "role": UserRole.EXPERT},
    {"full_name": "User", "email": "user@beako.com", "role": UserRole.USER},
]


def seed() -> None:
    with SessionLocal() as db:
        existing = set(db.scalars(select(User.email)))
        for data in SEED_USERS:
            if data["email"] in existing:
                print(f"skip    {data['email']} (already exists)")
                continue
            db.add(
                User(
                    **data,
                    email_verified_at=datetime.now(timezone.utc),
                    password_hash=hash_password(DEFAULT_PASSWORD),
                )
            )
            print(f"create  {data['email']}")
        db.commit()


def create_admin(email: str, full_name: str = "Admin") -> None:
    email = email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit(f"{email} already exists")
        password = secrets.token_urlsafe(12)
        db.add(User(full_name=full_name, email=email, role=UserRole.ADMIN, password_hash=hash_password(password),
                    email_verified_at=datetime.now(timezone.utc)))
        db.commit()
    print(f"created admin {email}")
    print(f"password: {password}")
    print("(shown only now; change it in Settings after signing in)")


if __name__ == "__main__":
    if sys.argv[1:2] == ["admin"] and len(sys.argv) >= 3:
        create_admin(sys.argv[2], " ".join(sys.argv[3:]) or "Admin")
    elif len(sys.argv) == 1:
        seed()
    else:
        raise SystemExit(__doc__)
