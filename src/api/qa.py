import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.ingest.search import _COLUMNS, _JOINS, Hit
from src.ingest.settings import MODEL_NAME
from src.models import Conversation, Message, SessionLocal, User, get_db
from src.schemas.qa import (
    AskRequest,
    AskResponse,
    ChunkResponse,
    ConversationDetail,
    ConversationPage,
    ConversationSummary,
    ConversationTurn,
    FeedbackRequest,
    FeedbackResponse,
    RenameConversationRequest,
    TurnFeedback,
)
from src.services import conversations, followup, guard, llm, usage
from src.services.qa import answer_question

router = APIRouter(prefix="/qa", tags=["qa"])
log = logging.getLogger("beako.qa")

# Seconds between keep-alive comments while the answer is being prepared
KEEPALIVE_SECONDS = 15
POLL_SECONDS = 1.0
# Safari buffers a stream until it has received about 1 KB; pad the start so status events show at once
STREAM_PADDING = ":" + " " * 2048 + "\n\n"

# What the user is told when the LLM provider fails, by LLMError.kind (the raw error is only logged)
LLM_FAILURES = {
    "not_configured": (503, "Question answering is not configured on the server"),
    "quota": (503, "The AI provider's quota is used up; please try again later"),
    "rate_limited": (503, "The AI provider is overloaded right now; please try again in a minute"),
    "unavailable": (503, "The AI provider is temporarily unavailable; please try again shortly"),
    "timeout": (504, "The AI provider took too long to answer; please try again"),
    "empty": (502, "The AI returned an empty reply; please ask again"),
}


class QAFailed(Exception):
    """A question that could not be answered, as told to the client: HTTP status, a stable code
    (busy, rate_limited, user_quota, budget, input_rejected, llm_<kind>, internal) and a message."""

    def __init__(self, status_code: int, code: str, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.retry_after = status_code, code, message, retry_after

    def http(self) -> HTTPException:
        return HTTPException(self.status, {"code": self.code, "message": self.message},
                             headers={"Retry-After": str(self.retry_after)} if self.retry_after else None)

    def event(self) -> dict:
        return {"status": self.status, "code": self.code, "detail": self.message, "retryAfter": self.retry_after}


def _response(conv, msg, result, max_volume) -> AskResponse:
    return AskResponse(**vars(result), embedding_model=MODEL_NAME, max_volume=max_volume,
                       conversation_id=conv.id, message_id=msg.id)


def _admit(db: Session, user: User, body: AskRequest) -> tuple[guard.Admission, Conversation]:
    """Guardrails first (nothing is stored for a refused question), then the user's message."""
    question = body.question.strip()
    try:
        adm = guard.admit(db, user, question)
    except guard.Refused as e:
        raise QAFailed(e.status, e.code, e.message, e.retry_after).http()
    try:
        conv = conversations.start_turn(db, user.id, question, body.max_volume, body.conversation_id)
    except conversations.ConversationNotFound:
        db.rollback()
        usage.finish(db, adm.request_id, "rejected", error_kind="conversation_not_found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return adm, conv


def _answer(db: Session, conv: Conversation, adm: guard.Admission, body: AskRequest,
            on_event=None, cancel: threading.Event | None = None) -> AskResponse:
    """Answer, store the answer and complete the request log; raises QAFailed. Setting `cancel`
    stops the work at its next LLM call (the request is logged as cancelled)."""
    question, max_volume = body.question.strip(), body.max_volume
    t0 = time.perf_counter()

    def ms() -> int:
        return round((time.perf_counter() - t0) * 1000)

    # Earlier answered turns, for follow-ups ("and her sister?")
    history = [(q.content, a.content) for q, a in conversations.turns(db, conv) if a is not None and not a.error]

    with llm.metered(cancel) as meter:
        try:
            asked = followup.standalone(question, history)
            if asked != question and on_event:
                on_event({"type": "rewrite", "question": asked})
            remaining = None if adm.token_budget is None else \
                adm.token_budget - meter.prompt_tokens - meter.completion_tokens
            result = answer_question(db, asked, body.top_k, mode=adm.mode, max_volume=max_volume,
                                     on_event=on_event, token_budget=remaining)
            # The conversation keeps the user's words; the rewrite is shown and kept in the trace
            result.question = question
            if asked != question:
                result.standalone_question = asked
                result.trace = [{"rewrite": asked}, *result.trace]
        except llm.LLMError as e:
            db.rollback()
            if e.kind == "cancelled":
                log.info("client left; stopped answering after %d LLM calls (request %s)", meter.calls, adm.request_id)
                conversations.save_error(db, conv, str(e), max_volume)
                usage.finish(db, adm.request_id, "cancelled", meter=meter, latency_ms=ms(),
                             error_kind="client_disconnected")
                raise QAFailed(499, "cancelled", "The question was cancelled")
            log.warning("answering failed (%s): %s", e.kind, e)
            conversations.save_error(db, conv, str(e), max_volume)
            usage.finish(db, adm.request_id, "error", meter=meter, latency_ms=ms(), error_kind=e.kind, error=str(e))
            code, message = LLM_FAILURES.get(e.kind, (502, "The AI provider could not answer; please try again"))
            raise QAFailed(code, f"llm_{e.kind}", message)
        except Exception as e:  # noqa: BLE001 - log it, store it, and tell the user something went wrong
            log.exception("answering failed")
            db.rollback()
            conversations.save_error(db, conv, f"{type(e).__name__}: {e}", max_volume)
            usage.finish(db, adm.request_id, "error", meter=meter, latency_ms=ms(), error_kind="internal",
                         error=f"{type(e).__name__}: {e}")
            raise QAFailed(500, "internal", "Internal error while answering")
    db.rollback()  # end the read-only retrieval transaction before writing
    blocked = guard.leaks_prompt(result.answer)
    if blocked:
        log.warning("answer repeated the system prompt; replaced (request %s)", adm.request_id)
        result.answer, result.found = guard.REFUSAL, False
        result.sources = [{**src, "cited": False} for src in result.sources]
    try:
        msg = conversations.save_answer(db, conv, result, max_volume)
    except Exception as e:
        # The LLM calls were made and paid for: log them before the error goes up
        db.rollback()
        usage.finish(db, adm.request_id, "error", meter=meter, latency_ms=ms(), answer=result,
                     error_kind="internal", error=f"storing the answer failed: {type(e).__name__}: {e}")
        raise
    usage.finish(db, adm.request_id, "answered" if result.found else "not_found", meter=meter,
                 latency_ms=ms(), answer=result, message_id=msg.id, output_blocked=blocked)
    return _response(conv, msg, result, max_volume)


# Signed-in users only: every call spends LLM quota
@router.post("", response_model=AskResponse)
def ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    """Failures carry {"detail": {"code", "message"}}; the guardrails answer 429 (400 for a
    rejected question, 503 once the daily budget is spent), with Retry-After when it helps."""
    adm, conv = _admit(db, user, body)
    try:
        return _answer(db, conv, adm, body)
    except QAFailed as e:
        raise e.http()
    finally:
        usage.release(db, adm.request_id)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
def ask_stream(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Server-sent events while the question is answered:
    - status: progress ({"type": "rewrite" | "route" | "tool" | "llm", ...}; rewrite carries a
      follow-up as it will be answered, tool events the tool name
      and arguments (e.g. a search query); shown as "searching / reading" steps
    - answer: the final AskResponse (same body as POST /qa)
    - error: {"status": int, "code": str, "detail": str, "retryAfter": int | null}
    Guardrail refusals and a bad conversation id are plain HTTP errors (as for POST /qa) before
    the stream starts. When the client disconnects (closes the tab) the work stops at its next
    LLM call and the user's question slot is released, so asking again works at once."""
    adm, conv = _admit(db, user, body)
    max_volume = body.max_volume
    events: queue.Queue = queue.Queue()
    cancel = threading.Event()

    def work() -> None:
        # Own session: the request's session is closed once the response starts streaming
        with SessionLocal() as wdb:
            conv_w = wdb.merge(conv)
            try:
                response = _answer(wdb, conv_w, adm, body, on_event=lambda e: events.put(("status", e)),
                                   cancel=cancel)
                events.put(("answer", response.model_dump(mode="json", by_alias=True)))
            except QAFailed as e:
                events.put(("error", e.event()))
            except Exception:  # noqa: BLE001 - e.g. the database failed while storing the answer
                log.exception("streaming answer failed")
                events.put(("error", QAFailed(500, "internal", "Internal error while answering").event()))
            finally:
                usage.release(wdb, adm.request_id)
                events.put(None)

    threading.Thread(target=work, daemon=True, name="qa-stream").start()

    async def stream() -> AsyncIterator[str]:
        # Async so that a disconnect cancels it right away (Starlette cancels the response task),
        # which runs the finally below
        delivered = False
        try:
            yield STREAM_PADDING
            yield _sse("start", {"conversationId": str(conv.id), "maxVolume": max_volume})
            quiet = 0.0
            while True:
                try:
                    # Short waits: a cancelled wait leaves its thread blocked for at most this long
                    item = await asyncio.to_thread(events.get, True, POLL_SECONDS)
                except queue.Empty:
                    quiet += POLL_SECONDS
                    if quiet >= KEEPALIVE_SECONDS:
                        quiet = 0.0
                        yield ": keep-alive\n\n"
                    continue
                if item is None:
                    delivered = True
                    return
                quiet = 0.0
                yield _sse(*item)
        finally:
            if not delivered:
                # The client left (closed the tab): stop the work and free the user's slot at once.
                # A thread, because this finally runs in a cancelled task and must not await
                cancel.set()
                threading.Thread(target=usage.mark_cancelled, args=(adm.request_id,), daemon=True).start()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        # no-transform: proxies must not compress (and so buffer) the stream
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


@router.put("/messages/{message_id}/feedback", response_model=FeedbackResponse)
def set_feedback(
    message_id: uuid.UUID,
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """Mark an answer right (1) or wrong (-1), optionally with a comment; rating null clears it.
    Rated answers are collected as real evaluation data."""
    msg = conversations.own_answer(db, user.id, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Answer not found")
    if msg.error:
        raise HTTPException(status.HTTP_409_CONFLICT, "This answer failed and cannot be rated")
    msg.feedback = body.rating
    msg.feedback_comment = body.comment.strip() if body.comment and body.rating is not None else None
    msg.feedback_at = datetime.now(timezone.utc) if body.rating is not None else None
    db.commit()
    return FeedbackResponse(message_id=msg.id, rating=msg.feedback, comment=msg.feedback_comment,
                            feedback_at=msg.feedback_at)


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
def get_chunk(
    chunk_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChunkResponse:
    """Full text of a source passage, for passages that were shown to this user."""
    if not conversations.chunk_was_shown(db, user.id, chunk_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Passage not found")
    row = db.execute(text(f"SELECT {_COLUMNS} FROM book_chunks c {_JOINS} WHERE c.id = :i"),
                     {"i": chunk_id}).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Passage not found")
    book = "Volume" if row.volume_kind == "main" else "Short Story Collection"
    return ChunkResponse(chunk_id=row.id, citation=Hit(0.0, row).citation, volume=f"{book} {row.volume_number}",
                         chapter=": ".join(x for x in (row.label, row.title) if x),
                         paragraphs=[row.start_seq, row.end_seq], text=row.text)


# --- conversation history -----------------------------------------------------------------------

def _own(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    conv = conversations.own_conversation(db, user.id, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


def _stored_answer(conv: Conversation, q: Message, a: Message) -> AskResponse:
    return AskResponse(question=q.content, answer=a.content, found=bool(a.found), sources=a.sources or [],
                       model=a.model or "", embedding_model=MODEL_NAME, usage=a.usage or {},
                       timings_ms=a.timings_ms or {}, mode=a.mode or "", trace=a.trace or [],
                       max_volume=a.max_volume, conversation_id=conv.id, message_id=a.id,
                       standalone_question=next((t["rewrite"] for t in a.trace or [] if "rewrite" in t), None))


@router.get("/conversations", response_model=ConversationPage)
def list_conversations(
    limit: int = Query(30, ge=1, le=100),
    before: str | None = Query(None, max_length=100, description="nextCursor of the previous page"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationPage:
    """The user's conversations, most recently active first."""
    try:
        rows, cursor = conversations.list_conversations(db, user.id, limit, before)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid cursor")
    return ConversationPage(items=[ConversationSummary.model_validate(c, from_attributes=True) for c in rows],
                            next_cursor=cursor)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Every question of a conversation with its stored answer, sources and the user's rating."""
    conv = _own(db, user, conversation_id)
    out = []
    for q, a in conversations.turns(db, conv):
        turn = ConversationTurn(question=q.content, max_volume=q.max_volume, asked_at=q.created_at)
        if a is not None and a.error:
            turn.error = "cancelled" if a.error.startswith("cancelled") else "failed"
        elif a is not None:
            turn.answer = _stored_answer(conv, q, a)
            if a.feedback is not None:
                turn.feedback = TurnFeedback(rating=a.feedback, comment=a.feedback_comment)
        out.append(turn)
    return ConversationDetail(id=conv.id, title=conv.title, created_at=conv.created_at,
                              updated_at=conv.updated_at, turns=out)


@router.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(
    conversation_id: uuid.UUID,
    body: RenameConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationSummary:
    conv = _own(db, user, conversation_id)
    title = " ".join(body.title.split())
    if not title:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Title cannot be empty")
    conversations.rename(db, conv, title)
    return ConversationSummary.model_validate(conv, from_attributes=True)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a conversation and its messages. Usage and cost records are kept."""
    conversations.delete(db, _own(db, user, conversation_id))
