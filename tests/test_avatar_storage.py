"""Avatar storage: on disk (local runs) or in the database (hosts without a persistent disk)."""

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.api import uploads
from src.core import config
from src.models import SessionLocal

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def _avatar_rows() -> int:
    with SessionLocal() as db:
        return db.execute(text("SELECT count(*) FROM avatar_files")).scalar()


@pytest.fixture
def db_storage(monkeypatch):
    monkeypatch.setattr(config, "STORAGE_BACKEND", "db")
    # The app picks local or db serving at import; serve db avatars from a small app instead
    server = FastAPI()
    server.include_router(uploads.router)
    return TestClient(server)


def test_db_storage_round_trip(make_user, client_for, db_storage):
    c = client_for(make_user())
    url = c.put("/auth/me/avatar", files={"file": ("a.png", PNG, "image/png")}).json()["avatar"]
    assert url.startswith("/uploads/avatars/") and url.endswith(".png")
    r = db_storage.get(url)
    assert (r.status_code, r.headers["content-type"], r.content) == (200, "image/png", PNG)
    assert "immutable" in r.headers["cache-control"]


def test_db_storage_replaces_and_deletes(make_user, client_for, db_storage):
    c = client_for(make_user())
    first = c.put("/auth/me/avatar", files={"file": ("a.png", PNG, "image/png")}).json()["avatar"]
    second = c.put("/auth/me/avatar", files={"file": ("b.png", PNG, "image/png")}).json()["avatar"]
    assert first != second
    assert db_storage.get(first).status_code == 404  # the old one is removed
    assert _avatar_rows() == 1
    c.delete("/auth/me/avatar")
    assert db_storage.get(second).status_code == 404
    assert _avatar_rows() == 0


def test_db_storage_rejects_non_images_and_bad_names(make_user, client_for, db_storage):
    c = client_for(make_user())
    r = c.put("/auth/me/avatar", files={"file": ("a.png", b"<script>alert(1)</script>", "image/png")})
    assert r.status_code == 415
    assert _avatar_rows() == 0
    assert db_storage.get("/uploads/avatars/not-a-uuid.png").status_code == 404
    assert db_storage.get("/uploads/avatars/../../etc/passwd").status_code == 404


def test_local_storage_is_unchanged(make_user, client_for, monkeypatch, tmp_path):
    from src.services import storage

    monkeypatch.setattr(storage, "AVATAR_DIR", tmp_path / "avatars")
    c = client_for(make_user())
    url = c.put("/auth/me/avatar", files={"file": ("a.png", PNG, "image/png")}).json()["avatar"]
    saved = tmp_path / "avatars" / url.rsplit("/", 1)[1]
    assert saved.read_bytes() == PNG
    assert _avatar_rows() == 0
    c.delete("/auth/me/avatar")
    assert not saved.exists()
