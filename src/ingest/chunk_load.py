"""Chunk the story text, embed what is new, and upsert into book_chunks.

Idempotent and cheap to rerun: a chunk's content_hash covers the embedding model and the
exact embedded input, so only chunks whose hash is not already stored get embedded (and a
vector is reused when identical content merely moved to another position). Each volume is
committed on its own, so an interrupted run resumes where it stopped.
"""

import time
from collections import OrderedDict

from sqlalchemy import Table, delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from src.ingest.chunk import CHUNKER_VERSION, MAX_TOKENS, Chunk, build_items, pack
from src.ingest.embed import Embedder
from src.ingest.epub import VolumeFile
from src.ingest.settings import MODEL_NAME
from src.models import engine
from src.models.book import BookChunk

chunks_t: Table = BookChunk.__table__
BATCH = 500
# Columns that describe how the stored vector was made; only written with a new vector
EMBED_COLS = ("content_hash", "embedding", "embedding_model", "embedding_model_version")

STORY_PARAGRAPHS = text("""
    SELECT bp.id, bp.seq, bp.section_id, bp.kind, bp.text,
           pt.id AS part_id, pt.label, pt.title, v.id AS volume_id
    FROM book_paragraphs bp
    JOIN book_sections s ON s.id = bp.section_id
    JOIN book_parts pt ON pt.id = s.part_id
    JOIN volumes v ON v.id = bp.volume_id
    WHERE pt.kind = 'story' AND v.kind = :kind AND v.number = :number
    ORDER BY bp.seq
""")


def heading_for(vf: VolumeFile, label: str | None, title: str | None) -> str:
    book = f"Volume {vf.number}" if vf.kind == "main" else f"Short Story Collection {vf.number}"
    return f"{book} — {': '.join(x for x in (label, title) if x)}"


def volume_chunks(conn: Connection, vf: VolumeFile, embedder: Embedder) -> tuple[int | None, list[Chunk]]:
    rows = conn.execute(STORY_PARAGRAPHS, {"kind": vf.kind, "number": vf.number}).all()
    by_part: OrderedDict[int, list] = OrderedDict()
    for r in rows:
        by_part.setdefault(r.part_id, []).append(r)
    chunks: list[Chunk] = []
    for part_id, paragraphs in by_part.items():
        head = heading_for(vf, paragraphs[0].label, paragraphs[0].title)
        chunks.extend(pack(part_id, build_items(paragraphs, embedder.count_tokens), head))
    return (rows[0].volume_id if rows else None), chunks


def _row(volume_id: int, ordinal: int, c: Chunk, version: str) -> dict:
    first, last = c.items[0], c.items[-1]
    return {
        "volume_id": volume_id, "ordinal": ordinal, "part_id": c.part_id,
        "start_section_id": first.section_id, "end_section_id": last.section_id,
        "start_paragraph_id": first.paragraph_id, "end_paragraph_id": last.paragraph_id,
        "start_seq": first.seq, "end_seq": last.seq,
        "start_char": first.start_char, "end_char": last.end_char,
        "heading": c.heading, "text": c.text, "token_count": c.tokens,
        "chunker_version": CHUNKER_VERSION, "content_hash": c.content_hash(MODEL_NAME),
        "embedding_model": MODEL_NAME, "embedding_model_version": version,
    }


def _upsert_new(conn: Connection, rows: list[dict]) -> int:
    """Insert or overwrite rows whose content (and so vector) is new at that position."""
    written = 0
    for i in range(0, len(rows), BATCH):
        stmt = insert(chunks_t).values(rows[i : i + BATCH])
        cols = [c for c in rows[0] if c not in ("volume_id", "ordinal")]
        stmt = stmt.on_conflict_do_update(
            index_elements=["volume_id", "ordinal"],
            set_={c: stmt.excluded[c] for c in cols},
        ).returning(chunks_t.c.id)
        written += len(conn.execute(stmt).all())
    return written


def _update_metadata(conn: Connection, volume_id: int, rows: list[dict]) -> int:
    """Rows whose content is unchanged: refresh only source/trace columns that differ
    (e.g. paragraph ids after a phase-1 reload); the vector and its provenance stay."""
    cols = [c for c in rows[0] if c not in EMBED_COLS and c not in ("volume_id", "ordinal")]
    stored = {r.ordinal: r for r in conn.execute(
        select(chunks_t.c.ordinal, *(chunks_t.c[c] for c in cols))
        .where(chunks_t.c.volume_id == volume_id))}
    written = 0
    for r in rows:
        old = stored[r["ordinal"]]
        diff = {c: r[c] for c in cols if getattr(old, c) != r[c]}
        if diff:
            conn.execute(update(chunks_t).where(chunks_t.c.volume_id == volume_id,
                                                chunks_t.c.ordinal == r["ordinal"]).values(**diff))
            written += 1
    return written


def load_chunks(volumes: list[VolumeFile]) -> None:
    embedder = Embedder()
    version = embedder.version
    totals = {"chunks": 0, "embedded": 0, "reused": 0, "written": 0, "deleted": 0}
    for vf in volumes:
        t0 = time.time()
        with engine.begin() as conn:
            volume_id, chunks = volume_chunks(conn, vf, embedder)
            if volume_id is None:
                print(f"{vf.slug}: no story text, skipped")
                continue
            rows = [_row(volume_id, i, c, version) for i, c in enumerate(chunks, 1)]

            too_long = [r["ordinal"] for r, n in zip(rows, embedder.count_tokens(
                [c.embed_input for c in chunks])) if n > 510]
            if too_long:
                raise RuntimeError(f"{vf.slug}: chunks {too_long} exceed the model's 512 tokens")
            assert all(r["token_count"] <= MAX_TOKENS for r in rows)

            stored = dict(conn.execute(
                select(chunks_t.c.ordinal, chunks_t.c.content_hash)
                .where(chunks_t.c.volume_id == volume_id)).all())
            changed = [(r, c) for r, c in zip(rows, chunks)
                       if stored.get(r["ordinal"]) != r["content_hash"]]
            unchanged = [r for r in rows if stored.get(r["ordinal"]) == r["content_hash"]]

            # Reuse vectors of identical content stored anywhere (e.g. shifted ordinals)
            wanted = list({r["content_hash"] for r, _ in changed})
            known = {}
            for i in range(0, len(wanted), BATCH):
                known.update(conn.execute(
                    select(chunks_t.c.content_hash, chunks_t.c.embedding)
                    .where(chunks_t.c.content_hash.in_(wanted[i : i + BATCH]))).all())
            to_embed = [(r, c) for r, c in changed if r["content_hash"] not in known]
            if to_embed:
                vectors = embedder.embed_passages([c.embed_input for _, c in to_embed])
                for (r, _), v in zip(to_embed, vectors):
                    known[r["content_hash"]] = v
            for r, _ in changed:
                r["embedding"] = known[r["content_hash"]]

            written = 0
            if changed:
                written += _upsert_new(conn, [r for r, _ in changed])
            if unchanged:
                written += _update_metadata(conn, volume_id, unchanged)
            deleted = conn.execute(delete(chunks_t).where(
                chunks_t.c.volume_id == volume_id, chunks_t.c.ordinal > len(rows))).rowcount

        totals["chunks"] += len(rows)
        totals["embedded"] += len(to_embed)
        totals["reused"] += len(changed) - len(to_embed)
        totals["written"] += written
        totals["deleted"] += deleted
        print(f"{vf.slug}: {len(rows)} chunks | embedded {len(to_embed)}, reused "
              f"{len(changed) - len(to_embed)} | rows written {written}, deleted {deleted}"
              f" | {time.time() - t0:.0f}s", flush=True)
    print(f"done: {totals['chunks']} chunks, embedded {totals['embedded']}, reused {totals['reused']},"
          f" rows written {totals['written']}, deleted {totals['deleted']}"
          + (" (no changes)" if not (totals["written"] or totals["deleted"]) else ""))
