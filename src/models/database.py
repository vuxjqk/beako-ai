import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker



def normalize_url(url: str) -> str:
    """Accept a connection string as hosts hand it out: Neon, Render and Heroku give
    postgres:// or postgresql:// (which SQLAlchemy maps to psycopg2, not installed here), and
    values copied from a .env file may keep their quotes."""
    url = url.strip().strip("\"'")
    # A whole .env line pasted as the value: DATABASE_URL_UNPOOLED="postgresql://..."
    name, sep, rest = url.partition("=")
    if sep and name.isidentifier() and "://" in rest:
        url = rest.strip().strip("\"'")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    if "://" not in url:
        # Say what is wrong without echoing a value that may hold a password
        shown = f"{len(url)} characters starting with {url[:12]!r}" if url else "empty"
        raise RuntimeError(f"DATABASE_URL must be a connection string such as postgresql://user:password@host/db; "
                           f"it is {shown}")
    return url


DATABASE_URL = normalize_url(os.environ["DATABASE_URL"])

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
