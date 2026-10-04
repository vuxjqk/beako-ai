import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from src.schemas.auth import CamelModel

# Main volumes in the corpus; a reader's spoiler limit is one of these
MAX_VOLUME = 28


class AskRequest(CamelModel):
    # Any language in agent mode (it searches in English and answers in the question's language);
    # the simple path is English only
    question: str = Field(min_length=3, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)
    # Spoiler limit: "I have read up to Volume N". Only main volumes <= N are searched
    max_volume: int | None = Field(default=None, ge=1, le=MAX_VOLUME)
    # Continue an existing conversation (messages are stored there); omitted = start a new one
    conversation_id: uuid.UUID | None = None


class Source(CamelModel):
    ref: int  # the [n] number used in the answer
    cited: bool
    score: float
    volume: str
    volume_kind: Literal["main", "short_story_collection"]
    volume_number: int
    chapter: str
    sections: list[int]
    pages: list[str]
    paragraphs: list[int]  # first and last book_paragraphs.seq in the volume
    chunk_id: int
    citation: str
    excerpt: str


class AskResponse(CamelModel):
    question: str
    answer: str
    found: bool  # false when the passages did not contain the answer
    sources: list[Source]
    model: str
    embedding_model: str
    usage: dict
    timings_ms: dict
    mode: str  # simple | agent | simple+agent
    route_reason: str | None = None
    trace: list[dict] = []  # agent tool calls and per-step token use
    max_volume: int | None = None
    conversation_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None  # the stored answer; send feedback to it


class FeedbackRequest(CamelModel):
    # 1 = the answer is right, -1 = wrong, null = take back the rating
    rating: Literal[1, -1] | None
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(CamelModel):
    message_id: uuid.UUID
    rating: int | None
    comment: str | None
    feedback_at: datetime | None


class ChunkResponse(CamelModel):
    chunk_id: int
    citation: str
    volume: str
    chapter: str
    paragraphs: list[int]
    text: str


class ConversationSummary(CamelModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationPage(CamelModel):
    items: list[ConversationSummary]
    # Pass as `before` for the next (older) page; null when there is none
    next_cursor: str | None = None


class TurnFeedback(CamelModel):
    rating: int
    comment: str | None


class ConversationTurn(CamelModel):
    question: str
    max_volume: int | None
    asked_at: datetime
    # One of: the answer; an error (cancelled = the asker left before it was ready); or neither,
    # while the question is still being answered
    answer: AskResponse | None = None
    error: Literal["cancelled", "failed"] | None = None
    feedback: TurnFeedback | None = None


class ConversationDetail(ConversationSummary):
    turns: list[ConversationTurn]


class RenameConversationRequest(CamelModel):
    title: str = Field(min_length=1, max_length=255)
