"""Small helpers shared by the tests."""

from fastapi.testclient import TestClient
from sqlalchemy import text

from src.models import SessionLocal


def ask(client: TestClient, question: str = "Who is Rem?", **body):
    return client.post("/qa", json={"question": question, **body})


def request_rows(user_id=None) -> list:
    with SessionLocal() as db:
        q = "SELECT * FROM qa_requests" + (" WHERE user_id = :u" if user_id else "") + " ORDER BY created_at, id"
        return db.execute(text(q), {"u": user_id}).mappings().all()
