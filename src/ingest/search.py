"""Retrieval over book_chunks: vector (cosine, HNSW) and keyword (full-text, 'simple' config)."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.ingest.embed import Embedder

_COLUMNS = """
    c.id, c.heading, c.text, c.start_seq, c.end_seq, c.start_char, c.end_char,
    v.kind AS volume_kind, v.number AS volume_number, pt.label, pt.title,
    ss.number AS start_section, es.number AS end_section,
    sp.page AS start_page, ep.page AS end_page
"""
_JOINS = """
    JOIN volumes v ON v.id = c.volume_id
    JOIN book_parts pt ON pt.id = c.part_id
    JOIN book_sections ss ON ss.id = c.start_section_id
    JOIN book_sections es ON es.id = c.end_section_id
    JOIN book_paragraphs sp ON sp.id = c.start_paragraph_id
    JOIN book_paragraphs ep ON ep.id = c.end_paragraph_id
"""


@dataclass
class Hit:
    score: float
    row: object

    @property
    def citation(self) -> str:
        r = self.row
        book = f"LN{r.volume_number:02d}" if r.volume_kind == "main" else f"SSC{r.volume_number:02d}"
        part = ": ".join(x for x in (r.label, r.title) if x)
        sec = (f"§{r.start_section}" if r.start_section == r.end_section
               else f"§{r.start_section}–{r.end_section}") if r.start_section else ""
        page = f"p.{r.start_page}" if r.start_page else ""
        return " · ".join(x for x in (book, part, sec, page, f"¶{r.start_seq}–{r.end_seq}") if x)


def vector_search(conn: Connection, embedder: Embedder, query: str, k: int = 5) -> list[Hit]:
    qv = str(embedder.embed_query(query))
    conn.execute(text("SET LOCAL hnsw.ef_search = 100"))
    rows = conn.execute(text(f"""
        SELECT {_COLUMNS}, 1 - (c.embedding <=> CAST(:qv AS vector)) AS score
        FROM book_chunks c {_JOINS}
        ORDER BY c.embedding <=> CAST(:qv AS vector)
        LIMIT :k
    """), {"qv": qv, "k": k}).all()
    return [Hit(r.score, r) for r in rows]


def keyword_search(conn: Connection, query: str, k: int = 5) -> list[Hit]:
    rows = conn.execute(text(f"""
        SELECT {_COLUMNS}, ts_rank_cd(c.tsv, q) AS score
        FROM book_chunks c {_JOINS}, websearch_to_tsquery('simple', :q) q
        WHERE c.tsv @@ q
        ORDER BY score DESC, c.volume_id, c.ordinal
        LIMIT :k
    """), {"q": query, "k": k}).all()
    return [Hit(r.score, r) for r in rows]
