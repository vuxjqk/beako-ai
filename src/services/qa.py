"""Question answering: retrieval over book_chunks + one LLM call.

Retrieval is configured by RetrievalConfig (src/services/retrieval.py); English only.
"""

import re
import threading
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.core import config
from src.ingest.search import Hit
from src.services import llm, retrieval
from src.services.retrieval import RetrievalConfig

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
    # simple | agent | simple+agent (simple path refused, agent retried)
    mode: str = "simple"
    route_reason: str | None = None
    trace: list[dict] = field(default_factory=list)


# Questions one search rarely answers: summaries, comparisons, changes over time, lists
COMPLEX_RE = re.compile(
    r"\b(summar\w*|overview|recap|compare|comparison|contrast|differ\w*|evolv\w*|"
    r"how many times|each of|all the|list (?:all|the)|name the|timeline|"
    r"chang\w* (?:from|between|over|across)|from .{3,60}? to (?:the )?(?:events|end|volume))\b",
    re.I)
# Letters only Vietnamese uses (not é/è/ê, which appear in names such as Romanée-Conti)
VIETNAMESE_RE = re.compile("[ăâđôơưạảãằẳẵặắầẩẫậấẻẽẹềểễệếỉĩịỏõọồổỗộốờởỡợớủũụừửữựứỳỷỹỵ]", re.I)


def route(question: str) -> tuple[str, str | None]:
    """("agent", reason) for questions the simple path handles badly, else ("simple", None)."""
    if VIETNAMESE_RE.search(question):
        return "agent", "not English: the agent translates its searches"
    m = COMPLEX_RE.search(question)
    if m:
        return "agent", f"complex question ({m.group(0)!r})"
    return "simple", None


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


def retrieve(db: Session, question: str, k: int, cfg: RetrievalConfig | None = None) -> list[Hit]:
    """The retrieval step of answer_question, also called by the evaluation (src.eval)."""
    return retrieval.retrieve(db.connection(), get_embedder(), question, k, cfg or retrieval.default_config())


def _sources(hits: list[Hit], cited: set[int]) -> list[dict]:
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
    return sources


def _simple(db: Session, question: str, k: int, cfg: RetrievalConfig | None) -> Answer:
    t0 = time.perf_counter()
    hits = retrieve(db, question, k, cfg)
    t1 = time.perf_counter()
    completion = llm.chat(SYSTEM_PROMPT, build_prompt(question, hits))
    t2 = time.perf_counter()
    text = completion.text
    found = bool(text) and not text.startswith(NOT_FOUND.rstrip("."))
    return Answer(
        question=question,
        answer=text,
        found=found,
        sources=_sources(hits, cited_numbers(text, len(hits)) if found else set()),
        model=completion.model,
        usage=completion.usage,
        timings_ms={"retrieval": round((t1 - t0) * 1000), "llm": round((t2 - t1) * 1000)},
    )


def _agent(db: Session, question: str, cfg: RetrievalConfig | None) -> Answer:
    from src.services import agent

    r = agent.run(db, get_embedder(), question, cfg or retrieval.default_config())
    return Answer(
        question=question,
        answer=r.answer,
        found=r.found,
        sources=_sources(r.hits, cited_numbers(r.answer, len(r.hits)) if r.found else set()),
        model=r.model,
        usage=r.usage,
        timings_ms=r.timings_ms,
        mode="agent",
        trace=r.trace,
    )


def answer_question(db: Session, question: str, top_k: int | None = None,
                    cfg: RetrievalConfig | None = None, mode: str | None = None) -> Answer:
    """mode: simple (one search + one LLM call), agent (tool-using loop), or auto (route by
    question; with QA_ESCALATE a simple-path "not found" is retried by the agent)."""
    if not config.LLM_API_KEY:
        raise llm.LLMNotConfigured("LLM_API_KEY is not set")
    requested = mode or config.QA_MODE
    if requested not in ("simple", "agent", "auto"):
        raise ValueError(f"unknown QA mode {requested!r}")
    path, reason = route(question) if requested == "auto" else (requested, None)
    if path == "agent":
        a = _agent(db, question, cfg)
        a.route_reason = reason
        return a
    a = _simple(db, question, top_k or config.QA_TOP_K, cfg)
    if requested == "auto" and config.QA_ESCALATE and not a.found:
        b = _agent(db, question, cfg)
        b.mode, b.route_reason = "simple+agent", "simple path found nothing"
        b.usage = {k: a.usage.get(k, 0) + b.usage.get(k, 0) for k in set(a.usage) | set(b.usage)}
        b.timings_ms = {k: a.timings_ms.get(k, 0) + b.timings_ms.get(k, 0) for k in a.timings_ms}
        return b
    return a
