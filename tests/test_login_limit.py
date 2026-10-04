"""Wrong-password limits per account."""

import concurrent.futures as cf

from fastapi.testclient import TestClient

from src.core import config
from src.main import app

from tests.conftest import PASSWORD


def login(email, password):
    return TestClient(app).post("/auth/login", json={"email": email, "password": password})


def test_locks_after_too_many_failures_even_with_the_right_password(make_user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 3)
    user = make_user()
    assert [login(user.email, "wrong").status_code for _ in range(3)] == [401, 401, 401]
    r = login(user.email, PASSWORD)
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 15 * 60


def test_success_resets_the_count(make_user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 3)
    user = make_user()
    assert [login(user.email, "wrong").status_code for _ in range(2)] == [401, 401]
    assert login(user.email, PASSWORD).status_code == 200
    assert [login(user.email, "wrong").status_code for _ in range(3)] == [401, 401, 401]
    assert login(user.email, "wrong").status_code == 429


def test_lock_is_per_email(make_user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 2)
    victim, bystander = make_user(), make_user()
    for _ in range(2):
        login(victim.email, "wrong")
    assert login(victim.email, PASSWORD).status_code == 429
    assert login(bystander.email, PASSWORD).status_code == 200


def test_unknown_emails_are_limited_alike(monkeypatch):
    """Same answers as for a real account, so the limit does not reveal which emails exist."""
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 2)
    codes = [login("nobody@example.com", "wrong").status_code for _ in range(3)]
    assert codes == [401, 401, 429]


def test_email_case_does_not_bypass_the_limit(make_user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 2)
    user = make_user()
    login(user.email, "wrong")
    login(user.email.upper(), "wrong")
    assert login(user.email, PASSWORD).status_code == 429


def test_parallel_guesses_cannot_slip_past(make_user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 5)
    user = make_user()
    with cf.ThreadPoolExecutor(10) as pool:
        codes = list(pool.map(lambda _: login(user.email, "wrong").status_code, range(15)))
    assert codes.count(401) == 5
    assert codes.count(429) == 10
