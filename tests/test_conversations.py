"""Conversation history: a user sees and changes only their own conversations and answers."""

import uuid

from sqlalchemy import text

from src.models import SessionLocal

from tests.helpers import ask, request_rows


def _conversation(client, *questions):
    cid = None
    for q in questions:
        r = ask(client, q, **({"conversationId": cid} if cid else {}))
        assert r.status_code == 200
        cid = r.json()["conversationId"]
    return cid


def test_history_lists_and_opens_own_conversations(make_user, client_for, fake_answer):
    c = client_for(make_user())
    cid = _conversation(c, "Who is Rem?", "Who is Ram?")
    [item] = c.get("/qa/conversations").json()["items"]
    assert (item["id"], item["title"]) == (cid, "Who is Rem?")
    detail = c.get(f"/qa/conversations/{cid}").json()
    assert [t["question"] for t in detail["turns"]] == ["Who is Rem?", "Who is Ram?"]
    assert all(t["answer"]["answer"] == "Rem is a maid [1]." for t in detail["turns"])


def test_paging_returns_every_conversation_once(make_user, client_for, fake_answer):
    c = client_for(make_user())
    ids = [_conversation(c, f"Question number {i}?") for i in range(5)]
    seen, cursor = [], None
    while True:
        params = {"limit": 2, **({"before": cursor} if cursor else {})}
        page = c.get("/qa/conversations", params=params).json()
        seen += [i["id"] for i in page["items"]]
        cursor = page["nextCursor"]
        if not cursor:
            break
    assert seen == list(reversed(ids))  # most recent first


def test_other_users_cannot_see_or_change_a_conversation(make_user, client_for, fake_answer):
    owner, other = client_for(make_user()), client_for(make_user())
    cid = _conversation(owner, "Who is Rem?")
    message_id = owner.get(f"/qa/conversations/{cid}").json()["turns"][0]["answer"]["messageId"]

    assert other.get("/qa/conversations").json()["items"] == []
    assert other.get(f"/qa/conversations/{cid}").status_code == 404
    assert other.patch(f"/qa/conversations/{cid}", json={"title": "mine now"}).status_code == 404
    assert other.delete(f"/qa/conversations/{cid}").status_code == 404
    assert ask(other, "Who is Ram?", conversationId=cid).status_code == 404
    assert other.put(f"/qa/messages/{message_id}/feedback", json={"rating": -1}).status_code == 404
    # Still intact for the owner
    assert owner.get(f"/qa/conversations/{cid}").json()["title"] == "Who is Rem?"


def test_unknown_conversation_is_404(make_user, client_for):
    c = client_for(make_user())
    assert c.get(f"/qa/conversations/{uuid.uuid4()}").status_code == 404
    assert c.get("/qa/conversations", params={"before": "not-a-cursor"}).status_code == 422


def test_signed_out_requests_are_rejected(fake_answer):
    from fastapi.testclient import TestClient

    from src.main import app

    anonymous = TestClient(app)
    assert anonymous.get("/qa/conversations").status_code == 401
    assert anonymous.post("/qa", json={"question": "Who is Rem?"}).status_code == 401
    assert fake_answer.calls == []


def test_rename_keeps_the_order(make_user, client_for, fake_answer):
    c = client_for(make_user())
    older = _conversation(c, "Who is Rem?")
    newer = _conversation(c, "Who is Ram?")
    r = c.patch(f"/qa/conversations/{older}", json={"title": "  Rem   and Ram "})
    assert r.json()["title"] == "Rem and Ram"
    assert [i["id"] for i in c.get("/qa/conversations").json()["items"]] == [newer, older]
    assert c.patch(f"/qa/conversations/{older}", json={"title": "   "}).status_code == 422


def test_delete_keeps_the_usage_log(make_user, client_for, fake_answer):
    user = make_user()
    c = client_for(user)
    cid = _conversation(c, "Who is Rem?")
    assert c.delete(f"/qa/conversations/{cid}").status_code == 204
    assert c.get(f"/qa/conversations/{cid}").status_code == 404
    [row] = request_rows(user.id)
    # Spending stays on record, so deleting a conversation does not give tokens back
    assert row["prompt_tokens"] == 1000 and row["message_id"] is None


def test_feedback_is_returned_with_the_history(make_user, client_for, fake_answer):
    c = client_for(make_user())
    cid = _conversation(c, "Who is Rem?")
    message_id = c.get(f"/qa/conversations/{cid}").json()["turns"][0]["answer"]["messageId"]
    assert c.put(f"/qa/messages/{message_id}/feedback", json={"rating": -1, "comment": "wrong volume"}).status_code == 200
    assert c.get(f"/qa/conversations/{cid}").json()["turns"][0]["feedback"] == {"rating": -1, "comment": "wrong volume"}


def test_source_text_only_for_passages_the_user_was_shown(make_user, client_for, fake_answer):
    owner, other = client_for(make_user()), client_for(make_user())
    cid = _conversation(owner, "Who is Rem?")
    # Pretend the answer cited chunk 42
    with SessionLocal() as db:
        db.execute(text("UPDATE qa_messages SET sources = '[{\"chunk_id\": 42}]' "
                        "WHERE conversation_id = :c AND role = 'assistant'"), {"c": cid})
        db.commit()
    # Not shown to the other user: 404 before the book is even looked up
    assert other.get("/qa/chunks/42").status_code == 404
    assert other.get("/qa/chunks/43").status_code == 404


def test_stopped_answer_shows_as_cancelled(make_user, client_for, fake_answer):
    from src.services import llm

    c = client_for(make_user())
    cid = _conversation(c, "Who is Rem?")
    fake_answer.error = llm.LLMError("cancelled: the client disconnected", "cancelled")
    ask(c, "Who is Ram?", conversationId=cid)
    turns = c.get(f"/qa/conversations/{cid}").json()["turns"]
    assert [(t["answer"] is not None, t["error"]) for t in turns] == [(True, None), (False, "cancelled")]
    assert request_rows()[-1]["status"] == "cancelled"
