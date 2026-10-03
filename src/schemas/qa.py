from pydantic import Field

from src.schemas.auth import CamelModel


class AskRequest(CamelModel):
    # English only at this stage
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
