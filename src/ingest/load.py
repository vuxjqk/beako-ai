"""Upsert extracted volumes into Postgres.

Every table is written with INSERT .. ON CONFLICT (natural key) DO UPDATE .. WHERE the row
actually differs, followed by deleting rows past the new end. A rerun on unchanged input
therefore touches no rows at all (no new tuple versions), and row ids stay stable.
"""

from pathlib import Path

from sqlalchemy import Table, and_, delete, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from src.ingest.epub import VolumeFile
from src.ingest.extract import ExtractedVolume, extract
from src.models import engine
from src.models.book import BookParagraph, BookPart, BookSection, Volume, VolumeKind

BATCH = 2000

volumes_t: Table = Volume.__table__
parts_t: Table = BookPart.__table__
sections_t: Table = BookSection.__table__
paragraphs_t: Table = BookParagraph.__table__


def _upsert(conn: Connection, table: Table, rows: list[dict], key: list[str]) -> int:
    """Insert or update rows on `key`; returns how many rows were written."""
    written = 0
    for i in range(0, len(rows), BATCH):
        stmt = insert(table).values(rows[i : i + BATCH])
        cols = [c for c in rows[0] if c not in key]
        stmt = stmt.on_conflict_do_update(
            index_elements=key,
            set_={c: stmt.excluded[c] for c in cols},
            where=or_(*(table.c[c].is_distinct_from(stmt.excluded[c]) for c in cols)),
        ).returning(table.c.id)
        # RETURNING yields only rows actually inserted or updated (rowcount is -1 here)
        written += len(conn.execute(stmt).all())
    return written


def load_volume(conn: Connection, vol: ExtractedVolume) -> dict[str, int]:
    vf = vol.file
    stats = {"written": 0, "deleted": 0}
    kind = VolumeKind(vf.kind)
    stats["written"] += _upsert(conn, volumes_t, [{
        "kind": kind, "number": vf.number, "title": vol.title, "file_name": vf.file_name,
        "file_size": vf.file_size, "file_sha256": vf.sha256,
    }], ["kind", "number"])
    volume_id = conn.scalar(
        select(volumes_t.c.id).where(volumes_t.c.kind == kind, volumes_t.c.number == vf.number)
    )

    part_rows = [
        {"volume_id": volume_id, "ordinal": i, "kind": p.kind, "part_type": p.part_type,
         "number": p.number, "label": p.label, "title": p.title, "subtitle": p.subtitle,
         "source_files": p.source_files}
        for i, p in enumerate(vol.parts, 1)
    ]
    stats["written"] += _upsert(conn, parts_t, part_rows, ["volume_id", "ordinal"])
    part_ids = dict(conn.execute(
        select(parts_t.c.ordinal, parts_t.c.id).where(parts_t.c.volume_id == volume_id)
    ).all())

    section_rows = [
        {"part_id": part_ids[pi], "ordinal": si, "number": s.number}
        for pi, p in enumerate(vol.parts, 1)
        for si, s in enumerate(p.sections, 1)
    ]
    stats["written"] += _upsert(conn, sections_t, section_rows, ["part_id", "ordinal"])
    section_ids = {
        (r.part_id, r.ordinal): r.id
        for r in conn.execute(
            select(sections_t.c.part_id, sections_t.c.ordinal, sections_t.c.id)
            .where(sections_t.c.part_id.in_(part_ids.values()))
        )
    }

    para_rows = []
    seq = 0
    for pi, p in enumerate(vol.parts, 1):
        for si, s in enumerate(p.sections, 1):
            sid = section_ids[(part_ids[pi], si)]
            for oi, para in enumerate(s.paragraphs, 1):
                seq += 1
                para_rows.append({
                    "volume_id": volume_id, "seq": seq, "section_id": sid, "ordinal": oi,
                    "kind": para.kind, "text": para.text, "source_file": para.source_file,
                    "source_block": para.source_block, "page": para.page,
                })
    stats["written"] += _upsert(conn, paragraphs_t, para_rows, ["volume_id", "seq"])

    # Trim whatever lies past the new end (children first; cascades cover the rest)
    stats["deleted"] += conn.execute(delete(paragraphs_t).where(
        paragraphs_t.c.volume_id == volume_id, paragraphs_t.c.seq > seq)).rowcount
    keep_sections = [(r["part_id"], r["ordinal"]) for r in section_rows]
    stats["deleted"] += conn.execute(delete(sections_t).where(
        sections_t.c.part_id.in_(part_ids.values()),
        tuple_(sections_t.c.part_id, sections_t.c.ordinal).not_in(keep_sections))).rowcount
    stats["deleted"] += conn.execute(delete(parts_t).where(
        parts_t.c.volume_id == volume_id, parts_t.c.ordinal > len(part_rows))).rowcount
    stats.update(parts=len(part_rows), sections=len(section_rows), paragraphs=len(para_rows))
    return stats


def load_all(epub_dir: Path, volumes: list[VolumeFile]) -> None:
    total_written = total_deleted = 0
    for vf in volumes:
        vol = extract(epub_dir / vf.file_name, vf)
        for w in vol.warnings:
            print(f"    ! {vf.slug}: {w}")
        # One transaction per volume: a failure never leaves a half-written volume
        with engine.begin() as conn:
            s = load_volume(conn, vol)
        total_written += s["written"]
        total_deleted += s["deleted"]
        print(f"{vf.slug}: {s['parts']} parts, {s['sections']} sections, {s['paragraphs']} paragraphs"
              f" | rows written {s['written']}, deleted {s['deleted']}")

    # Volumes no longer listed in volumes.csv
    listed = [(VolumeKind(v.kind), v.number) for v in volumes]
    with engine.begin() as conn:
        gone = conn.execute(delete(volumes_t).where(
            and_(tuple_(volumes_t.c.kind, volumes_t.c.number).not_in(listed)))).rowcount
    total_deleted += gone
    print(f"done: rows written {total_written}, rows deleted {total_deleted}"
          + (" (no changes)" if total_written == total_deleted == 0 else ""))
