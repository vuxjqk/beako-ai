"""Shared test setup.

The tests run against a real PostgreSQL (with pgvector), because the guardrails rely on it:
advisory locks, JSONB and day boundaries in a time zone. DATABASE_URL must name a database
ending in "_test"; every table the tests touch is emptied after each test.

LLM calls and retrieval are replaced by fakes (see `fake_answer`), which still report token
use to the request meter, so limits and cost accounting are exercised for real.

Local run (inside the backend container):
    docker compose exec db createdb -U <user> beako_test        # once
    docker compose exec -e DATABASE_URL=postgresql+psycopg://<user>:<password>@db:5432/beako_test \\
        backend sh -c "pip install -q -r requirements-dev.txt && pytest"
"""

import os
import uuid
from collections.abc import Callable

import pytest

# Settings the app requires at import; CI and local runs may override them
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789abcdef")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_FROM", "Beako Test <test@example.com>")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
    raise pytest.UsageError(
        "DATABASE_URL must point to a database whose name ends in '_test' (tests empty its tables)"
    )

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.core import config  # noqa: E402
from src.core.security import create_access_token, hash_password  # noqa: E402
from src.main import app  # noqa: E402
from src.models import SessionLocal, User, UserRole  # noqa: E402
from src.services import llm  # noqa: E402
from src.services.qa import Answer  # noqa: E402

# Tables a test may write to; the book tables are left alone
TABLES = ["login_attempts", "qa_requests", "qa_messages", "qa_conversations", "refresh_tokens", "otp_codes",
          "users"]
PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with SessionLocal() as db:
        db.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.commit()


@pytest.fixture(autouse=True)
def default_limits(monkeypatch):
    """Known limits for every test, whatever the environment says; tests lower them as needed."""
    for name, value in {
        "QA_USER_PER_MINUTE": 100, "QA_USER_PER_DAY": 1000, "QA_USER_DAILY_TOKENS": 10_000_000,
        "QA_USER_MAX_CONCURRENT": 1, "QA_DAILY_BUDGET_USD": 1000.0, "QA_DEGRADE_AT": 0.8,
        "QA_TIMEZONE": "UTC", "LLM_PRICE_INPUT_PER_MTOK": 1.0, "LLM_PRICE_OUTPUT_PER_MTOK": 2.0,
        "LOGIN_MAX_FAILURES": 10, "LOGIN_LOCK_MINUTES": 15, "LLM_API_KEY": "test-key",
    }.items():
        monkeypatch.setattr(config, name, value)
    # Admission waits a few seconds for a previous question to end; tests need no grace
    monkeypatch.setattr("src.services.guard.BUSY_GRACE_SECONDS", 0.0)


@pytest.fixture
def make_user() -> Callable[..., User]:
    def make(role: UserRole = UserRole.USER, email: str | None = None) -> User:
        with SessionLocal() as db:
            user = User(full_name="Test User", email=email or f"{uuid.uuid4().hex[:10]}@example.com",
                        password_hash=hash_password(PASSWORD), role=role)
            db.add(user)
            db.commit()
            return user
    return make


@pytest.fixture
def client_for() -> Callable[[User], TestClient]:
    """An API client signed in as the given user."""
    def make(user: User) -> TestClient:
        c = TestClient(app)
        c.cookies.set("access_token", create_access_token(user.id))
        return c
    return make


class FakeAnswering:
    """Stands in for retrieval + LLM. Each question "spends" prompt/completion tokens on the
    active request meter (as llm._post would), then answers, fails or calls `hook`."""

    def __init__(self):
        self.prompt_tokens, self.completion_tokens = 1000, 100
        self.found = True
        self.error: Exception | None = None
        self.hook: Callable[[], None] | None = None
        self.calls: list[dict] = []

    def __call__(self, db, question, top_k=None, cfg=None, mode=None, max_volume=None, on_event=None,
                 token_budget=None) -> Answer:
        self.calls.append({"question": question, "mode": mode, "token_budget": token_budget,
                           "max_volume": max_volume})
        meter = llm._meter.get()
        if meter is not None:
            meter.check()
            meter.add({"usage": {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens},
                       "model": "fake-model"}, "fake-model")
        if self.hook:
            self.hook()
        if self.error:
            raise self.error
        return Answer(question=question, answer="Rem is a maid [1]." if self.found else "Not found in the "
                      "provided passages.", found=self.found, sources=[], model="fake-model",
                      mode=mode or "agent", trace=[{"step": 1, "tool": "search", "args": {"query": question}}])


@pytest.fixture
def fake_answer(monkeypatch) -> FakeAnswering:
    fake = FakeAnswering()
    monkeypatch.setattr("src.api.qa.answer_question", fake)
    # No follow-up rewriting unless a test asks for it (it would call the LLM)
    monkeypatch.setattr("src.api.qa.followup.standalone", lambda question, history: question)
    return fake

