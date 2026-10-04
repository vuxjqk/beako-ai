import json
import logging
import queue
import threading
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
from src.models import SessionLocal, User, get_db
from src.schemas.qa import AskRequest, AskResponse, ChunkResponse, FeedbackRequest, FeedbackResponse
from src.services import conversations, llm
from src.services.qa import answer_question

router = APIRouter(prefix="/qa", tags=["qa"])
log = logging.getLogger("beako.qa")

# Seconds between keep-alive comments while the answer is being prepared
KEEPALIVE_SECONDS = 15
# Safari buffers a stream until it has received about 1 KB; pad the start so status events show at once
STREAM_PADDING = ":" + " " * 2048 + "\n\n"


def _response(conv, msg, result, max_volume) -> AskResponse:
    return AskResponse(**vars(result), embedding_model=MODEL_NAME, max_volume=max_volume,
                       conversation_id=conv.id, message_id=msg.id)


def _start(db: Session, user_id: uuid.UUID, body: AskRequest):
    try:
        return conversations.start_turn(db, user_id, body.question.strip(), body.max_volume,
                                        body.conversation_id)
    except conversations.ConversationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")


# Signed-in users only: every call spends LLM quota
@router.post("", response_model=AskResponse)
def ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    conv = _start(db, user.id, body)
    try:
        result = answer_question(db, body.question.strip(), body.top_k, max_volume=body.max_volume)
    except llm.LLMNotConfigured as e:
        db.rollback()
        conversations.save_error(db, conv, str(e), body.max_volume)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Question answering is not configured: {e}")
    except llm.LLMError as e:
        db.rollback()
        conversations.save_error(db, conv, str(e), body.max_volume)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
    db.rollback()  # end the read-only retrieval transaction before writing
    msg = conversations.save_answer(db, conv, result, body.max_volume)
    return _response(conv, msg, result, body.max_volume)


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
    - error: {"status": int, "detail": str}
    The answer is stored even if the client disconnects before it arrives."""
    conv = _start(db, user.id, body)  # errors here (bad conversation id) are still plain HTTP errors
    question, max_volume, top_k = body.question.strip(), body.max_volume, body.top_k
    events: queue.Queue = queue.Queue()

    def work() -> None:
        # Own session: the request's session is closed once the response starts streaming
        with SessionLocal() as wdb:
            conv_w = wdb.merge(conv)
            try:
                result = answer_question(wdb, question, top_k, max_volume=max_volume,
                                         on_event=lambda e: events.put(("status", e)))
                wdb.rollback()
                msg = conversations.save_answer(wdb, conv_w, result, max_volume)
                response = _response(conv_w, msg, result, max_volume)
                events.put(("answer", response.model_dump(mode="json", by_alias=True)))
            except llm.LLMNotConfigured as e:
                wdb.rollback()
                conversations.save_error(wdb, conv_w, str(e), max_volume)
                events.put(("error", {"status": 503, "detail": f"Question answering is not configured: {e}"}))
            except llm.LLMError as e:
                wdb.rollback()
                conversations.save_error(wdb, conv_w, str(e), max_volume)
                events.put(("error", {"status": 502, "detail": str(e)}))
            except Exception as e:  # noqa: BLE001 - report every failure to the client, then log it
                log.exception("streaming answer failed")
                wdb.rollback()
                conversations.save_error(wdb, conv_w, f"{type(e).__name__}: {e}", max_volume)
                events.put(("error", {"status": 500, "detail": "Internal error while answering"}))
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
