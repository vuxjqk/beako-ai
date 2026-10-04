import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.ingest.search import _COLUMNS, _JOINS, Hit
from src.ingest.settings import MODEL_NAME
from src.models import Conversation, SessionLocal, User, get_db
from src.schemas.qa import AskRequest, AskResponse, ChunkResponse, FeedbackRequest, FeedbackResponse
from src.services import conversations, guard, llm, usage
from src.services.qa import answer_question

router = APIRouter(prefix="/qa", tags=["qa"])
log = logging.getLogger("beako.qa")

# Seconds between keep-alive comments while the answer is being prepared
KEEPALIVE_SECONDS = 15
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
            on_event=None) -> AskResponse:
    """Answer, store the answer and complete the request log; raises QAFailed."""
    question, max_volume = body.question.strip(), body.max_volume
    t0 = time.perf_counter()

    def ms() -> int:
        return round((time.perf_counter() - t0) * 1000)

    with llm.metered() as meter:
        try:
            result = answer_question(db, question, body.top_k, mode=adm.mode, max_volume=max_volume,
                                     on_event=on_event, token_budget=adm.token_budget)
        except llm.LLMError as e:
            log.warning("answering failed (%s): %s", e.kind, e)
            db.rollback()
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
    msg = conversations.save_answer(db, conv, result, max_volume)
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


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
def ask_stream(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Server-sent events while the question is answered:
    - status: progress ({"type": "route" | "tool" | "llm", ...}; tool events carry the tool name
      and arguments, e.g. a search query), shown as "searching / reading" steps
    - answer: the final AskResponse (same body as POST /qa)
    - error: {"status": int, "code": str, "detail": str, "retryAfter": int | null}
    Guardrail refusals and a bad conversation id are plain HTTP errors (as for POST /qa) before
    the stream starts. The answer is stored even if the client disconnects before it arrives."""
    adm, conv = _admit(db, user, body)
    max_volume = body.max_volume
    events: queue.Queue = queue.Queue()

    def work() -> None:
        # Own session: the request's session is closed once the response starts streaming
        with SessionLocal() as wdb:
            conv_w = wdb.merge(conv)
            try:
                response = _answer(wdb, conv_w, adm, body, on_event=lambda e: events.put(("status", e)))
                events.put(("answer", response.model_dump(mode="json", by_alias=True)))
            except QAFailed as e:
                events.put(("error", e.event()))
            except Exception:  # noqa: BLE001 - e.g. the database failed while storing the answer
                log.exception("streaming answer failed")
                events.put(("error", QAFailed(500, "internal", "Internal error while answering").event()))
            finally:
                events.put(None)

    threading.Thread(target=work, daemon=True, name="qa-stream").start()

    def stream() -> Iterator[str]:
        yield STREAM_PADDING
        yield _sse("start", {"conversationId": str(conv.id), "maxVolume": max_volume})
        while True:
            try:
                item = events.get(timeout=KEEPALIVE_SECONDS)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                return
            yield _sse(*item)

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
