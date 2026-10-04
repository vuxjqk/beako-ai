"""The golden question set and matching retrieved chunks against its evidence.

Evidence is a volume + an inclusive range of book_paragraphs.seq, not chunk ids, so the set
stays valid when the text is re-chunked: a chunk counts as relevant when its paragraph range
overlaps an evidence span in the same volume.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

GOLDEN_PATH = Path("data/eval/golden_set.json")
CATEGORIES = ("fact", "relationship", "multi_hop", "summary", "out_of_scope")
OOS_TYPES = ("general", "not_in_text", "false_premise", "beyond_corpus")
# Tune on dev; test only confirms a change (otherwise rules get fitted to these questions)
SPLITS = ("dev", "test")


@dataclass(frozen=True)
class Span:
    volume: str  # "LN07" (main volume) or "SSC02" (short story collection)
    chapter: str
    start: int
    end: int

    @property
    def key(self) -> tuple[str, int]:
        return ("short_story_collection", int(self.volume[3:])) if self.volume.startswith("SSC") \
            else ("main", int(self.volume[2:]))

    def __str__(self) -> str:
        return f"{self.volume} {self.chapter} ¶{self.start}–{self.end}"


@dataclass
class Question:
    id: str
    category: str
    question: str
    answer: str
    key_points: list[str]
    spans: list[Span]
    split: str = "dev"
    oos_type: str | None = None

    @property
    def in_scope(self) -> bool:
        return self.category != "out_of_scope"


def load(path: Path = GOLDEN_PATH) -> tuple[list[Question], str]:
    """The questions and the sha256 of the file (recorded with every run)."""
    raw = path.read_bytes()
    data = json.loads(raw)
    questions, seen = [], set()
    for q in data["questions"]:
        if q["id"] in seen:
            raise ValueError(f"duplicate question id {q['id']}")
        seen.add(q["id"])
        if q["category"] not in CATEGORIES:
            raise ValueError(f"{q['id']}: unknown category {q['category']!r}")
        spans = [Span(e["volume"], e["chapter"], *e["paragraphs"]) for e in q["evidence"]]
        if (q["category"] == "out_of_scope") != (not spans):
            raise ValueError(f"{q['id']}: out-of-scope questions have no evidence, all others need some")
        if q["category"] == "out_of_scope" and q.get("oos_type") not in OOS_TYPES:
            raise ValueError(f"{q['id']}: oos_type must be one of {OOS_TYPES}")
        if q.get("split") not in SPLITS:
            raise ValueError(f"{q['id']}: split must be one of {SPLITS}")
        if any(s.start > s.end for s in spans):
            raise ValueError(f"{q['id']}: evidence range start > end")
        questions.append(Question(q["id"], q["category"], q["question"], q["answer"],
                                  q.get("key_points", []), spans, q["split"], q.get("oos_type")))
    return questions, hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ChunkRef:
    id: int
    volume_kind: str
    volume_number: int
    start_seq: int
    end_seq: int


def chunk_refs(db: Session, ids: list[int]) -> dict[int, ChunkRef]:
    if not ids:
        return {}
    rows = db.execute(text("""
        SELECT c.id, v.kind, v.number, c.start_seq, c.end_seq
        FROM book_chunks c JOIN volumes v ON v.id = c.volume_id
        WHERE c.id = ANY(:ids)
    """), {"ids": list(ids)}).all()
    return {r[0]: ChunkRef(*r) for r in rows}


def matching_spans(chunk: ChunkRef, spans: list[Span]) -> list[int]:
    """Indexes of the evidence spans this chunk overlaps."""
    return [i for i, s in enumerate(spans)
            if s.key == (chunk.volume_kind, chunk.volume_number)
            and chunk.start_seq <= s.end and s.start <= chunk.end_seq]


def check(db: Session, questions: list[Question]) -> list[str]:
    """Problems with the evidence locations: unknown volume, paragraphs outside a story part,
    chapter label that does not match, or no chunk covering the span."""
    problems = []
    for q in questions:
        for s in q.spans:
            kind, number = s.key
            parts = db.execute(text("""
                SELECT DISTINCT pt.kind, pt.label, pt.title
                FROM book_paragraphs bp
                JOIN volumes v ON v.id = bp.volume_id
                JOIN book_sections sc ON sc.id = bp.section_id
                JOIN book_parts pt ON pt.id = sc.part_id
                WHERE v.kind = :k AND v.number = :n AND bp.seq BETWEEN :a AND :b
            """), {"k": kind, "n": number, "a": s.start, "b": s.end}).all()
            if not parts:
                problems.append(f"{q.id}: {s} matches no paragraphs")
                continue
            if any(p.kind != "story" for p in parts):
                problems.append(f"{q.id}: {s} includes non-story text")
            names = {n for p in parts for n in (p.label, p.title, ": ".join(x for x in (p.label, p.title) if x)) if n}
            if s.chapter not in names:
                problems.append(f"{q.id}: {s} is in {sorted(names)}, not {s.chapter!r}")
            covered = db.execute(text("""
                SELECT count(*) FROM book_chunks c JOIN volumes v ON v.id = c.volume_id
                WHERE v.kind = :k AND v.number = :n AND c.start_seq <= :b AND :a <= c.end_seq
            """), {"k": kind, "n": number, "a": s.start, "b": s.end}).scalar()
            if not covered:
                problems.append(f"{q.id}: {s} is not covered by any chunk")
    return problems


def evidence_text(db: Session, span: Span) -> list[tuple[int, str]]:
    kind, number = span.key
    return [tuple(r) for r in db.execute(text("""
        SELECT bp.seq, bp.text FROM book_paragraphs bp JOIN volumes v ON v.id = bp.volume_id
        WHERE v.kind = :k AND v.number = :n AND bp.seq BETWEEN :a AND :b ORDER BY bp.seq
    """), {"k": kind, "n": number, "a": span.start, "b": span.end}).all()]
