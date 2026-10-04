from pydantic import Field

from src.schemas.auth import CamelModel


class AskRequest(CamelModel):
    # Any language in agent mode (it searches in English and answers in the question's language);
    # the simple path is English only
    question: str = Field(min_length=3, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class Source(CamelModel):
    ref: int  # the [n] number used in the answer
    cited: bool
    score: float
    volume: str
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
