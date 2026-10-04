"""Baseline question answering: vector retrieval over book_chunks + one LLM call.

Deliberately simple (no query rewriting, no keyword fusion, no reranking, English only) so it
can serve as the reference point for later improvements.
"""

import re
import threading
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.core import config
from src.ingest.search import Hit, vector_search
from src.services import llm

NOT_FOUND = "Not found in the provided passages."

SYSTEM_PROMPT = f"""You answer questions about the light novel series "Re:ZERO -Starting Life in Another World-".
You are given numbered passages retrieved from the novels. Follow these rules strictly:
1. Use ONLY information stated in the passages. Do not use outside knowledge of the series (anime, wiki, later volumes), even if you know it.
2. Cite the passage number for every claim in square brackets, e.g. [2] or [1][3].
3. If the passages do not contain enough information to answer, reply with exactly: {NOT_FOUND}
4. Do not guess or fill gaps. If the passages answer only part of the question, answer that part and say what is missing.
5. Answer in English, concisely (at most about 150 words)."""

CITATION_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

_embedder = None
_embedder_lock = threading.Lock()


def get_embedder():
    """The chunk embedding model, loaded once per process on first use."""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                from src.ingest.embed import Embedder  # heavy import, only when QA is used

                _embedder = Embedder()
    return _embedder


@dataclass
class Answer:
    question: str
    answer: str
    found: bool
    sources: list[dict]
    model: str
    usage: dict = field(default_factory=dict)
    timings_ms: dict = field(default_factory=dict)


def _label(hit: Hit) -> str:
    r = hit.row
    book = f"Volume {r.volume_number}" if r.volume_kind == "main" else \
        f"Short Story Collection {r.volume_number}"
    part = ": ".join(x for x in (r.label, r.title) if x)
    return f"{book} — {part}"


def build_prompt(question: str, hits: list[Hit]) -> str:
    blocks = [f"[{i}] {_label(h)}\n{h.row.text}" for i, h in enumerate(hits, 1)]
    return "Passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}"


def cited_numbers(text: str, limit: int) -> set[int]:
    nums = set()
    for group in CITATION_RE.findall(text):
        nums.update(int(n) for n in re.split(r"\s*,\s*", group))
    return {n for n in nums if 1 <= n <= limit}


# Recorded with every evaluation run; change it whenever retrieve() changes behaviour
RETRIEVAL_METHOD = "vector"


def retrieve(db: Session, question: str, k: int) -> list[Hit]:
    """The retrieval step of answer_question, also called by the evaluation (src.eval)."""
    return vector_search(db.connection(), get_embedder(), question, k=k)


def answer_question(db: Session, question: str, top_k: int | None = None) -> Answer:
    if not config.LLM_API_KEY:
        raise llm.LLMNotConfigured("LLM_API_KEY is not set")
    k = top_k or config.QA_TOP_K
    t0 = time.perf_counter()
    hits = retrieve(db, question, k)
    t1 = time.perf_counter()
    completion = llm.chat(SYSTEM_PROMPT, build_prompt(question, hits))
    t2 = time.perf_counter()

    text = completion.text
    found = bool(text) and not text.startswith(NOT_FOUND.rstrip("."))
    cited = cited_numbers(text, len(hits)) if found else set()
    sources = []
    for i, h in enumerate(hits, 1):
        r = h.row
        sources.append({
            "ref": i,
            "cited": i in cited,
            "score": round(float(h.score), 4),
            "volume": f"{'Volume' if r.volume_kind == 'main' else 'Short Story Collection'} {r.volume_number}",
            "chapter": ": ".join(x for x in (r.label, r.title) if x),
            "sections": [n for n in dict.fromkeys((r.start_section, r.end_section)) if n is not None],
            "pages": [p for p in dict.fromkeys((r.start_page, r.end_page)) if p],
            "paragraphs": [r.start_seq, r.end_seq],
            "chunk_id": r.id,
            "citation": h.citation,
            "excerpt": r.text[:300],
        })
    return Answer(
        question=question,
        answer=text,
        found=found,
        sources=sources,
        model=completion.model,
        usage=completion.usage,
        timings_ms={"retrieval": round((t1 - t0) * 1000), "llm": round((t2 - t1) * 1000)},
    )

