"""Epub -> Postgres text ingest.

Run inside the backend container with the epub folder mounted read-only, e.g.:
    docker compose run --rm -v "D:/Documents/Zero:/data/epub:ro" backend python -m src.ingest all

Commands:
    inventory  scan the epub folder and (re)write data/volumes.csv
    dump       extract every volume to plain-text files for eyeballing (no DB)
    load       extract every volume listed in volumes.csv and upsert it into Postgres
    verify     check the DB against volumes.csv and write data/reports/ingest_report.md
    all        inventory + load + verify
    chunk      split story text into chunks, embed new ones, upsert into book_chunks
    chunk-verify  check chunks/embeddings, run trial queries, write data/reports/chunk_report.md
    search     try a query: python -m src.ingest search "Echidna's contract" [--keyword]
"""

import argparse
import os
import sys
from pathlib import Path

from src.ingest.epub import read_csv, scan_folder, write_csv

DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "volumes.csv"
REPORT_PATH = DATA_DIR / "reports" / "ingest_report.md"
CHUNK_REPORT_PATH = DATA_DIR / "reports" / "chunk_report.md"


def cmd_inventory(epub_dir: Path) -> None:
    volumes = scan_folder(epub_dir)
    write_csv(volumes, CSV_PATH)
    main = sum(v.kind == "main" for v in volumes)
    print(f"wrote {CSV_PATH}: {len(volumes)} files ({main} main, {len(volumes) - main} short story collections)")


def cmd_dump(epub_dir: Path, out: Path) -> None:
    from src.ingest.extract import extract

    out.mkdir(parents=True, exist_ok=True)
    for vf in read_csv(CSV_PATH):
        vol = extract(epub_dir / vf.file_name, vf)
        lines = [f"# {vol.title}"]
        for i, part in enumerate(vol.parts, 1):
            head = " / ".join(x for x in (part.label, part.title, part.subtitle) if x)
            lines.append(f"\n\n=== [{i}] {part.kind.value}:{part.part_type} {head}  {part.source_files}")
            for sec in part.sections:
                lines.append(f"\n--- section {sec.number}")
                for p in sec.paragraphs:
                    lines.append(f"[{p.source_file}#{p.source_block} p{p.page}] {p.text}"
                                 if os.getenv("DUMP_SOURCES") else p.text)
        (out / f"{vf.slug}.txt").write_text("\n".join(lines), encoding="utf-8")
        paras = sum(len(s.paragraphs) for p in vol.parts for s in p.sections)
        print(f"{vf.slug}: {len(vol.parts)} parts, {paras} paragraphs, {len(vol.warnings)} warnings")
        for w in vol.warnings:
            print(f"    ! {w}")


def cmd_search(query: str | None, keyword: bool, k: int) -> None:
    from src.ingest.search import keyword_search, vector_search
    from src.models import engine

    if not query:
        sys.exit("search needs a query")
    with engine.connect() as conn:
        if keyword:
            hits = keyword_search(conn, query, k)
        else:
            from src.ingest.embed import Embedder

            hits = vector_search(conn, Embedder(), query, k)
    for i, h in enumerate(hits, 1):
        snippet = h.row.text[:300].replace("\n\n", " / ")
        print(f"{i}. [{h.score:.3f}] {h.citation}\n   {snippet}\n")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m src.ingest", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["inventory", "dump", "load", "verify", "all",
                                        "chunk", "chunk-verify", "search"])
    ap.add_argument("query", nargs="?", help="search: the query text")
    ap.add_argument("--keyword", action="store_true", help="search: full-text instead of vector")
    ap.add_argument("-k", type=int, default=5, help="search: number of results")
    ap.add_argument("--epub-dir", type=Path, default=Path(os.getenv("EPUB_DIR", "/data/epub")))
    ap.add_argument("--out", type=Path, default=DATA_DIR / "dump", help="dump: output folder")
    args = ap.parse_args()

    # These work from the DB alone; no epub folder needed
    if args.command == "chunk":
        from src.ingest.chunk_load import load_chunks

        return load_chunks(read_csv(CSV_PATH))
    if args.command == "chunk-verify":
        from src.ingest.chunk_verify import verify_chunks

        return sys.exit(0 if verify_chunks(CHUNK_REPORT_PATH) else 1)
    if args.command == "search":
        return cmd_search(args.query, args.keyword, args.k)

    if not args.epub_dir.is_dir():
        sys.exit(f"epub folder not found: {args.epub_dir}")
    if args.command in ("inventory", "all"):
        cmd_inventory(args.epub_dir)
    if args.command == "dump":
        cmd_dump(args.epub_dir, args.out)
    if args.command in ("load", "all"):
        from src.ingest.load import load_all

        load_all(args.epub_dir, read_csv(CSV_PATH))
    if args.command in ("verify", "all"):
        from src.ingest.verify import verify

        ok = verify(args.epub_dir, read_csv(CSV_PATH), REPORT_PATH)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
