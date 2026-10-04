"""Retrieval for question answering: vector, keyword or hybrid search, with optional
volume/chapter scoping and cross-encoder reranking.

Every knob lives in RetrievalConfig. The defaults come from .env (RETRIEVAL_*), and the
evaluation overrides single fields (python -m src.eval retrieval --set method=hybrid), so
each variant can be measured without editing code. The config is saved with every eval run.
"""

import re
import threading
from dataclasses import asdict, dataclass, fields, replace
from math import log

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.core import config
from src.ingest.search import _COLUMNS, _JOINS, Hit

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had
has have having he her here hers herself him himself his how i if in into is it its itself just
me more most my myself no nor not now of off on once only or other our ours out over own same she
should so some such than that the their theirs them themselves then there these they this those
through to too under until up very was we were what when where which while who whom why will with
would you your yours s t d ll m re ve does doing according tell name named called happen happens
happened volume volumes chapter chapters book novel story series""".split())
TOKEN_RE = re.compile(r"[^\W_]+")


@dataclass(frozen=True)
class RetrievalConfig:
    # vector | keyword | hybrid (vector + keyword fused with reciprocal rank fusion)
    method: str = "vector"
    # keyword backend: bm25 (in-memory index with IDF) | ts (Postgres full-text, OR of terms)
    keyword: str = "bm25"
    # candidates taken from each retriever before fusion / reranking
    candidates: int = 50
    rrf_k: int = 60
    # exact (sequential) vector search instead of the HNSW index
    exact: bool = False
    # volume(s)/chapter a question names ("In Volume 1, Chapter 2, ..."): off | filter (search
    # only there) | boost (also fuse a ranking restricted to them, so other volumes can still appear)
    scope: str = "off"
    # cross-encoder model name, or "" for none; reorders the top rerank_top results
    rerank: str = ""
    rerank_top: int = 20

    def label(self) -> str:
        """Compact description of the fields that differ from the plain vector baseline."""
        base = RetrievalConfig()
        diff = [f"{f.name}={getattr(self, f.name)}" for f in fields(self)
                if f.name != "method" and getattr(self, f.name) != getattr(base, f.name)]
        return " ".join([self.method] + diff)

    def as_dict(self) -> dict:
        return asdict(self)

    def with_overrides(self, pairs: list[str]) -> "RetrievalConfig":
        """Apply "key=value" strings, converting to each field's type."""
        changes = {}
        types = {f.name: f.type for f in fields(self)}
        for pair in pairs:
            key, _, value = pair.partition("=")
            if key not in types:
                raise ValueError(f"unknown retrieval setting {key!r}; known: {', '.join(types)}")
            t = types[key]
            changes[key] = (value.lower() in ("1", "true", "yes", "on")) if t in (bool, "bool") else \
                int(value) if t in (int, "int") else value
        return replace(self, **changes)


def default_config() -> RetrievalConfig:
    return RetrievalConfig(
        method=config.RETRIEVAL_METHOD,
        keyword=config.RETRIEVAL_KEYWORD,
        candidates=config.RETRIEVAL_CANDIDATES,
        rrf_k=config.RETRIEVAL_RRF_K,
        exact=config.RETRIEVAL_EXACT,
        scope=config.RETRIEVAL_SCOPE,
        rerank=config.RETRIEVAL_RERANK,
        rerank_top=config.RETRIEVAL_RERANK_TOP,
    )


# --- scope: volume / chapter named in the question ------------------------------------------

@dataclass(frozen=True)
class Scope:
    kind: str  # main | short_story_collection
    volumes: tuple[int, ...]
    chapter: int | None = None

    def sql(self) -> tuple[str, dict]:
        cond = " AND v.kind = :scope_kind AND v.number = ANY(:scope_volumes)"
        params = {"scope_kind": self.kind, "scope_volumes": list(self.volumes)}
        if self.chapter is not None:
            cond += " AND pt.part_type = 'chapter' AND pt.number = :scope_chapter"
            params["scope_chapter"] = self.chapter
        return cond, params

    def contains(self, kind: str, number: int, part_type: str, part_no: int | None) -> bool:
        return kind == self.kind and number in self.volumes and (
            self.chapter is None or (part_type == "chapter" and part_no == self.chapter))


_RANGE = r"\d+(?:\s*(?:–|—|-|to)\s*\d+)?"
_VOLUME_RE = re.compile(rf"\b(Short Story Collection|Volumes?|Vol\.)\s*({_RANGE}(?:\s*(?:,|and|&)\s*{_RANGE})*)", re.I)
_CHAPTER_RE = re.compile(r"\bChapter\s+(\d+)\b", re.I)


def parse_scope(question: str) -> Scope | None:
    """The volumes (and chapter, when a single volume is named) a question mentions, e.g.
    "Volume 3", "Volumes 16–20", "Volumes 5–9 ... Volumes 16–20". None when nothing is named."""
    matches = _VOLUME_RE.findall(question)
    if not matches or len({m[0].lower().startswith("short") for m in matches}) > 1:
        return None
    volumes: set[int] = set()
    for _, ranges in matches:
        for part in re.split(r"\s*(?:,|and|&)\s*", ranges):
            bounds = re.split(r"\s*(?:–|—|-|to)\s*", part)
            a, b = int(bounds[0]), int(bounds[-1])
            if b < a or b - a > 30:
                return None
            volumes.update(range(a, b + 1))
    kind = "short_story_collection" if matches[0][0].lower().startswith("short") else "main"
    chapter = None
    if len(volumes) == 1:
        ch = set(_CHAPTER_RE.findall(question))
        if len(ch) == 1:
            chapter = int(ch.pop())
    return Scope(kind, tuple(sorted(volumes)), chapter)


# --- retrievers: each returns chunk ids, best first ----------------------------------------

def _vector_ids(conn: Connection, embedder, question: str, n: int, scope: Scope | None,
                exact: bool) -> list[tuple[int, float]]:
    qv = str(embedder.embed_query(question))
    # A filtered or exact query must not go through HNSW: the index returns its ef_search
    # nearest chunks first and filters afterwards, which can leave almost nothing
    use_index = not exact and scope is None
    conn.execute(text(f"SET LOCAL enable_indexscan = {'on' if use_index else 'off'}"))
    conn.execute(text("SET LOCAL hnsw.ef_search = 100"))
    cond, params = scope.sql() if scope else ("", {})
    rows = conn.execute(text(f"""
        SELECT c.id, 1 - (c.embedding <=> CAST(:qv AS vector)) FROM book_chunks c
        JOIN volumes v ON v.id = c.volume_id JOIN book_parts pt ON pt.id = c.part_id
        WHERE true {cond}
        ORDER BY c.embedding <=> CAST(:qv AS vector), c.id
        LIMIT :n
    """), {"qv": qv, "n": n, **params}).all()
    conn.execute(text("SET LOCAL enable_indexscan = on"))
    return [(r[0], float(r[1])) for r in rows]


def query_terms(question: str) -> list[str]:
    seen = []
    for t in TOKEN_RE.findall(question.lower()):
        if t not in STOPWORDS and len(t) > 1 and t not in seen:
            seen.append(t)
    return seen


def _ts_ids(conn: Connection, question: str, n: int, scope: Scope | None) -> list[int]:
    terms = query_terms(question)
    if not terms:
        return []
    tsq = " | ".join("'" + t.replace("'", "''") + "'" for t in terms)
    cond, params = scope.sql() if scope else ("", {})
    rows = conn.execute(text(f"""
        SELECT c.id FROM book_chunks c
        JOIN volumes v ON v.id = c.volume_id JOIN book_parts pt ON pt.id = c.part_id,
        to_tsquery('simple', :q) q
        WHERE c.tsv @@ q {cond}
        ORDER BY ts_rank_cd(c.tsv, q) DESC, c.id
        LIMIT :n
    """), {"q": tsq, "n": n, **params}).all()
    return [r[0] for r in rows]


class BM25:
    """Okapi BM25 over heading + text of every chunk, held in memory (about 10k chunks).

    Postgres full-text ranking has no inverse document frequency, so a common name such as
    "Subaru" weighs as much as a rare one such as "Batenkaitos"; BM25 fixes that."""

    K1, B = 1.2, 0.75

    def __init__(self, conn: Connection):
        rows = conn.execute(text("""
            SELECT c.id, c.heading, c.text, v.kind, v.number, pt.part_type, pt.number
            FROM book_chunks c JOIN volumes v ON v.id = c.volume_id JOIN book_parts pt ON pt.id = c.part_id
            ORDER BY c.id
        """)).all()
        self.meta = {r[0]: (r[3], r[4], r[5], r[6]) for r in rows}
        self.postings: dict[str, list[tuple[int, int]]] = {}
        self.length: dict[int, int] = {}
        for cid, heading, body, *_ in rows:
            counts: dict[str, int] = {}
            tokens = TOKEN_RE.findall(f"{heading} {body}".lower())
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
            self.length[cid] = len(tokens)
            for t, c in counts.items():
                self.postings.setdefault(t, []).append((cid, c))
        self.n = len(rows)
        self.avg_len = sum(self.length.values()) / max(self.n, 1)
        self.signature = (self.n, max(self.length, default=0))

    def _allowed(self, cid: int, scope: Scope | None) -> bool:
        return scope is None or scope.contains(*self.meta[cid])

    def search(self, question: str, n: int, scope: Scope | None) -> list[int]:
        scores: dict[int, float] = {}
        for t in query_terms(question):
            plist = self.postings.get(t)
            if not plist:
                continue
            idf = log(1 + (self.n - len(plist) + 0.5) / (len(plist) + 0.5))
            for cid, tf in plist:
                norm = self.K1 * (1 - self.B + self.B * self.length[cid] / self.avg_len)
                scores[cid] = scores.get(cid, 0.0) + idf * tf * (self.K1 + 1) / (tf + norm)
        ranked = sorted((cid for cid in scores if self._allowed(cid, scope)), key=lambda c: (-scores[c], c))
        return ranked[:n]


_bm25: BM25 | None = None
_reranker: tuple[str, object] | None = None
_lock = threading.Lock()


def _get_bm25(conn: Connection) -> BM25:
    """Built on first use; rebuilt when the chunk table changed (count or highest id)."""
    global _bm25
    sig = tuple(conn.execute(text("SELECT count(*), coalesce(max(id), 0) FROM book_chunks")).one())
    with _lock:
        if _bm25 is None or _bm25.signature != sig:
            _bm25 = BM25(conn)
    return _bm25


def _get_reranker(model: str):
    global _reranker
    with _lock:
        if _reranker is None or _reranker[0] != model:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            from src.ingest.embed import CACHE_DIR

            _reranker = (model, TextCrossEncoder(model, cache_dir=CACHE_DIR))
    return _reranker[1]


def rrf(rankings: list[list[int]], k: int) -> list[int]:
    """Reciprocal rank fusion: score = sum over rankings of 1 / (k + rank)."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, 1):
            scores[cid] = scores.get(cid, 0.0) + 1 / (k + rank)
    return sorted(scores, key=lambda c: (-scores[c], c))


def _fetch(conn: Connection, ids: list[int], scores: list[float]) -> list[Hit]:
    if not ids:
        return []
    rows = conn.execute(text(f"SELECT {_COLUMNS} FROM book_chunks c {_JOINS} WHERE c.id = ANY(:ids)"),
                        {"ids": ids}).all()
    by_id = {r.id: r for r in rows}
    return [Hit(s, by_id[i]) for i, s in zip(ids, scores)]


def _rankings(conn: Connection, embedder, question: str, n: int, scope: Scope | None,
              cfg: RetrievalConfig) -> tuple[list[list[int]], dict[int, float]]:
    rankings, cosine = [], {}
    if cfg.method in ("vector", "hybrid"):
        vec = _vector_ids(conn, embedder, question, n, scope, cfg.exact)
        cosine = dict(vec)
        rankings.append([cid for cid, _ in vec])
    if cfg.method in ("keyword", "hybrid"):
        rankings.append(_get_bm25(conn).search(question, n, scope) if cfg.keyword == "bm25"
                        else _ts_ids(conn, question, n, scope))
    if not rankings:
        raise ValueError(f"unknown retrieval method {cfg.method!r}")
    return rankings, cosine


def retrieve(conn: Connection, embedder, question: str, k: int, cfg: RetrievalConfig) -> list[Hit]:
    if cfg.scope not in ("off", "filter", "boost"):
        raise ValueError(f"unknown scope mode {cfg.scope!r}")
    scope = parse_scope(question) if cfg.scope != "off" else None
    n = max(cfg.candidates, k)
    rankings, cosine = _rankings(conn, embedder, question, n, scope if cfg.scope == "filter" else None, cfg)
    if scope is not None and cfg.scope == "boost":
        rankings += _rankings(conn, embedder, question, n, scope, cfg)[0]
    if scope is not None and cfg.scope == "filter" and not any(rankings):
        # The named volume/chapter does not exist (or holds nothing): search everything
        return retrieve(conn, embedder, question, k, replace(cfg, scope="off"))
    ids = rankings[0] if len(rankings) == 1 else rrf(rankings, cfg.rrf_k)
    ids = ids[:n]
    # Cosine similarity for plain vector search; otherwise rank-based (raw scores differ in scale)
    scores = [cosine[c] for c in ids] if len(rankings) == 1 and cfg.method == "vector" else [1 / (r + 1) for r in range(len(ids))]

    if cfg.rerank and ids:
        head = _fetch(conn, ids[:cfg.rerank_top], scores)
        model = _get_reranker(cfg.rerank)
        ce = list(model.rerank(question, [f"{h.row.heading}\n{h.row.text}" for h in head]))
        order = sorted(range(len(head)), key=lambda i: (-ce[i], i))
        ids = [head[i].row.id for i in order] + ids[cfg.rerank_top:]
        scores = [float(ce[i]) for i in order] + scores[cfg.rerank_top:]
    return _fetch(conn, ids[:k], scores[:k])
