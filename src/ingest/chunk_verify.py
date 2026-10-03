"""Check book_chunks (coverage, sizes, source trace, embeddings), run trial queries, and write
data/reports/chunk_report.md."""

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from src.ingest.chunk import CHUNKER_VERSION, MAX_TOKENS, MIN_TOKENS, TARGET_TOKENS
from src.ingest.embed import Embedder
from src.ingest.search import keyword_search, vector_search
from src.ingest.settings import EMBEDDING_DIM, MODEL_NAME
from src.models import engine

# (query, expected volume as (kind, number) set, expected part labels or None = any part)
TRIAL_QUERIES = [
    ("Elsa cuts open Subaru's stomach in the loot house", {("main", 1)}, None),
    ("Rem confesses her love and Subaru decides to start over from zero", {("main", 6)}, {"Chapter 5"}),
    ("Wilhelm kills the White Whale and speaks to Theresia", {("main", 7)}, {"Chapter 5"}),
    ("Petelgeuse Romanée-Conti says his brain trembles", {("main", n) for n in (5, 6, 7, 8)}, None),
    ("Echidna explains why she wants Subaru's Return by Death and offers a contract", {("main", 12)}, {"Chapter 6"}),
    ("Otto's divine protection lets him hear the voices of animals", {("main", 13)}, {"Chapter 5"}),
    ("Beatrice chooses Subaru and forms a contract with him in the burning mansion", {("main", 15)}, {"Chapter 7"}),
    ("Regulus Corneas hides his heart inside his wives with the Lion's Heart", {("main", 19)}, None),
    ("Subaru wakes up in the watchtower with no memories", {("main", 23)}, {"Chapter 1", "Chapter 2"}),
    ("Subaru has lost all his memories and doesn't recognize Emilia or Beatrice", {("main", 23)},
     {"Chapter 1", "Chapter 2"}),
    ("Rem tỏ tình với Subaru và cậu quyết định bắt đầu lại từ con số không", {("main", 6)}, {"Chapter 5"}),
    ("Beatrice ký khế ước với Subaru", {("main", 15)}, {"Chapter 7"}),
    ("Otto có thể nghe tiếng nói của động vật", {("main", 13)}, {"Chapter 5"}),
]
VIETNAMESE_RE = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
KEYWORD_QUERIES = ["Petelgeuse", "Ryuzu Meyer", "Pandora", "Al Aldebaran"]


def _fingerprint(conn) -> dict:
    row = conn.execute(text("""
        SELECT count(*),
               md5(coalesce(string_agg(concat_ws('|', id, volume_id, ordinal, part_id,
                   start_paragraph_id, end_paragraph_id, start_char, end_char, content_hash,
                   embedding_model, embedding_model_version, text), '#' ORDER BY id), '')),
               coalesce(max(xmin::text::bigint), 0)
        FROM book_chunks
    """)).one()
    return {"rows": row[0], "content_md5": row[1], "max_xmin": row[2]}


def _pct(xs: list[int], p: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p / 100))]


def verify_chunks(report_path: Path) -> bool:
    checks: list[tuple[str, bool, str]] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with engine.connect() as conn:
        chunks = conn.execute(text("""
            SELECT c.*, v.kind AS vkind, v.number AS vnum,
                   ss.part_id AS start_part, es.part_id AS end_part,
                   vector_dims(c.embedding) AS dims, vector_norm(c.embedding) AS norm
            FROM book_chunks c
            JOIN volumes v ON v.id = c.volume_id
            JOIN book_sections ss ON ss.id = c.start_section_id
            JOIN book_sections es ON es.id = c.end_section_id
            ORDER BY v.kind, v.number, c.ordinal
        """)).all()
        paras = conn.execute(text("""
            SELECT bp.id, bp.volume_id, bp.seq, bp.text, s.part_id
            FROM book_paragraphs bp
            JOIN book_sections s ON s.id = bp.section_id
            JOIN book_parts pt ON pt.id = s.part_id
            WHERE pt.kind = 'story' AND bp.kind = 'text'
        """)).all()
        non_story = conn.execute(text("""
            SELECT count(*) FROM book_chunks c JOIN book_parts pt ON pt.id = c.part_id
            WHERE pt.kind <> 'story'
        """)).scalar()
        fingerprint = _fingerprint(conn)

    # --- Coverage: every story paragraph, every character of split paragraphs -----------
    by_vol: dict[int, list] = defaultdict(list)
    for c in chunks:
        by_vol[c.volume_id].append(c)
    para_by_key = {(p.volume_id, p.seq): p for p in paras}
    covered: dict[tuple, list[tuple[int, int]]] = defaultdict(list)  # char intervals
    not_verbatim = []
    for c in chunks:
        for seq in range(c.start_seq, c.end_seq + 1):
            p = para_by_key.get((c.volume_id, seq))
            if p is None:
                continue  # scene break / ornament
            a = c.start_char if seq == c.start_seq else 0
            b = (c.end_char if c.end_char is not None else len(p.text)) if seq == c.end_seq else len(p.text)
            covered[(c.volume_id, seq)].append((a, b))
            if p.text[a:b].strip() not in c.text:
                not_verbatim.append(f"chunk {c.id} ¶{seq}")
    missing, partial = [], []
    for key, p in para_by_key.items():
        spans = sorted(covered.get(key, []))
        if not spans:
            missing.append(key)
            continue
        pos = 0
        for a, b in spans:
            if a > pos and p.text[pos:a].strip():
                break
            pos = max(pos, b)
        else:
            if not p.text[pos:].strip():
                continue
        partial.append(key)
    total = len(para_by_key)
    checks.append((f"Độ phủ: mọi đoạn story ({total:,}) nằm trong ít nhất một chunk",
                   not missing, f"thiếu {len(missing)}: {missing[:5]}"))
    checks.append(("Đoạn quá dài bị cắt: mọi ký tự đều nằm trong một chunk", not partial, str(partial[:5])))
    checks.append(("Văn bản chunk khớp nguyên văn đoạn nguồn theo vị trí ghi lại", not not_verbatim,
                   str(not_verbatim[:5])))

    # --- Structure / trace ----------------------------------------------------------------
    cross_part = [c.id for c in chunks if not (c.start_part == c.end_part == c.part_id)]
    checks.append(("Chunk không vượt ranh giới phần (chương/truyện)", not cross_part, str(cross_part[:5])))
    checks.append(("Chỉ có phần kind = 'story' được chunk", non_story == 0, f"{non_story} chunk"))
    bad_order = []
    for vid, cs in by_vol.items():
        if [c.ordinal for c in cs] != list(range(1, len(cs) + 1)):
            bad_order.append(f"{cs[0].vkind}{cs[0].vnum} ordinal")
        for a, b in zip(cs, cs[1:]):
            if b.start_seq < a.start_seq or b.end_seq < a.end_seq or b.start_seq > a.end_seq + 2 \
                    and a.part_id == b.part_id:
                bad_order.append(f"{cs[0].vkind}{cs[0].vnum} #{b.ordinal}")
    checks.append(("Chunk liên tục, đúng thứ tự đọc trong mỗi tập", not bad_order, str(bad_order[:5])))

    # --- Sizes ------------------------------------------------------------------------------
    tokens = [c.token_count for c in chunks]
    empty = [c.id for c in chunks if not c.text.strip() or c.token_count == 0]
    checks.append(("Không có chunk rỗng", not empty, str(empty[:5])))
    checks.append((f"Mọi chunk ≤ {MAX_TOKENS} token (vừa giới hạn 512 của mô hình)",
                   max(tokens) <= MAX_TOKENS, f"max {max(tokens)}"))
    small = [c for c in chunks if c.token_count < MIN_TOKENS]
    # Small chunks are only acceptable when a whole part is that short
    lone_small = [c for c in small if sum(1 for x in by_vol[c.volume_id] if x.part_id == c.part_id) > 1]
    checks.append((f"Chunk < {MIN_TOKENS} token chỉ khi cả phần ngắn như vậy", not lone_small,
                   ", ".join(f"{c.vkind}{c.vnum}#{c.ordinal}={c.token_count}" for c in lone_small[:8])))

    # --- Embeddings -------------------------------------------------------------------------
    bad_emb = [c.id for c in chunks if c.dims != EMBEDDING_DIM or abs(c.norm - 1) > 0.01
               or c.embedding_model != MODEL_NAME]
    versions = Counter(c.embedding_model_version for c in chunks)
    checks.append((f"Mọi chunk có vector {EMBEDDING_DIM} chiều (chuẩn hóa) của {MODEL_NAME}",
                   not bad_emb, str(bad_emb[:5])))
    checks.append(("Một phiên bản mô hình duy nhất", len(versions) == 1, str(dict(versions))))

    # --- Trial queries --------------------------------------------------------------------
    embedder = Embedder()
    trial_lines = []
    found = {"en": [0, 0], "vi": [0, 0]}  # [in top 5, total]
    with engine.connect() as conn:
        for q, vols, labels in TRIAL_QUERIES:
            lang = "vi" if VIETNAMESE_RE.search(q) else "en"
            hits = vector_search(conn, embedder, q, k=10)
            ok = [(h.row.volume_kind, h.row.volume_number) in vols and
                  (labels is None or h.row.label in labels) for h in hits]
            rank = next((i + 1 for i, o in enumerate(ok) if o), None)
            found[lang][0] += rank is not None and rank <= 5
            found[lang][1] += 1
            mark = "✅" if rank and rank <= 5 else "❌"
            trial_lines.append(f"### {mark} “{q}”" + (" (tiếng Việt)" if lang == "vi" else ""))
            trial_lines.append("")
            trial_lines.append(f"Kỳ vọng: {', '.join(f'{k} {n}' for k, n in sorted(vols))}"
                               f"{' / ' + ', '.join(sorted(labels)) if labels else ''} — "
                               f"{'khớp ở hạng ' + str(rank) if rank else 'không có trong top 10'}")
            trial_lines.append("")
            for i, h in enumerate(hits[:3], 1):
                snippet = h.row.text.replace("\n\n", " ")[:220]
                trial_lines.append(f"{i}. `{h.score:.3f}` **{h.citation}** — {snippet}…")
            trial_lines.append("")
        kw_lines = []
        for q in KEYWORD_QUERIES:
            hits = keyword_search(conn, q, k=3)
            count = conn.execute(text(
                "SELECT count(*) FROM book_chunks WHERE tsv @@ websearch_to_tsquery('simple', :q)"),
                {"q": q}).scalar()
            kw_lines.append(f"- **{q}** — {count} chunk chứa từ khóa; top 3: " +
                            "; ".join(h.citation for h in hits))
    en_ok, en_total = found["en"]
    vi_ok, vi_total = found["vi"]
    checks.append((f"Truy vấn thử tiếng Anh: đúng chỗ trong top 5 ({en_ok}/{en_total}, cần ≥ 80%)",
                   en_ok >= 0.8 * en_total, ""))
    checks.append((f"Truy vấn thử tiếng Việt (chỉ để tham khảo, mô hình tiếng Anh): {vi_ok}/{vi_total}",
                   True, ""))

    # --- Idempotency fingerprint ----------------------------------------------------------
    fp_path = report_path.with_name("chunk_fingerprint.json")
    previous = json.loads(fp_path.read_text()) if fp_path.exists() else None
    same = previous == fingerprint
    fp_path.write_text(json.dumps(fingerprint, indent=2))

    # --- Report ---------------------------------------------------------------------------
    passed = all(ok for _, ok, _ in checks)
    story_tokens = sum(c.token_count for c in chunks)
    lines = [
        "# Báo cáo kiểm tra chunk và embedding", "",
        f"Tạo lúc {now}. Kết quả: **{'ĐẠT' if passed else 'CÓ LỖI'}** "
        f"({sum(ok for _, ok, _ in checks)}/{len(checks)} kiểm tra đạt).", "",
        f"- Mô hình embedding: `{MODEL_NAME}` ({EMBEDDING_DIM} chiều), phiên bản `{next(iter(versions))}`",
        f"- Bộ cắt: `{CHUNKER_VERSION}` (đếm token bằng tokenizer của chính mô hình)",
        f"- Chỉ mục: HNSW `vector_cosine_ops` trên `embedding`; GIN trên `tsv` "
        "(`to_tsvector('simple', heading || text)`, không stemming để khớp đúng tên riêng)", "",
        "## Kiểm tra", "", "| | Kiểm tra | Ghi chú |", "|---|---|---|",
    ]
    for name, ok, detail in checks:
        lines.append(f"| {'✅' if ok else '❌'} | {name} | {'' if ok else detail.replace('|', '/')} |")

    lines += ["", "## Chạy lại không đổi dữ liệu", "",
              f"`book_chunks`: {fingerprint['rows']:,} dòng, md5 `{fingerprint['content_md5']}`, "
              f"max(xmin) {fingerprint['max_xmin']}. So với lần kiểm tra trước: "
              + ("**không thay đổi**." if same else
                 ("chưa có lần trước." if previous is None else "**có thay đổi**.")), ""]

    buckets = Counter(min(n // 50 * 50, 450) for n in tokens)
    lines += ["## Số chunk và phân bố độ dài", "",
              f"{len(chunks):,} chunk, {story_tokens:,} token (gồm phần chồng lấn). "
              f"Đích {TARGET_TOKENS}, trần {MAX_TOKENS}, sàn cắt {MIN_TOKENS}.", "",
              f"Token mỗi chunk: min {min(tokens)}, p5 {_pct(tokens, 5)}, p25 {_pct(tokens, 25)}, "
              f"trung vị {statistics.median(tokens):.0f}, p75 {_pct(tokens, 75)}, p95 {_pct(tokens, 95)}, "
              f"max {max(tokens)}; trung bình {statistics.mean(tokens):.0f}.", "",
              "| Token | Số chunk | |", "|---|---:|---|"]
    peak = max(buckets.values())
    for b in sorted(buckets):
        label = f"{b}–{b + 49}" if b < 450 else "450"
        lines.append(f"| {label} | {buckets[b]:,} | {'█' * max(1, round(30 * buckets[b] / peak))} |")
    lines += ["", (f"Chunk dưới {MIN_TOKENS} token: không có (section ngắn đã được gộp)." if not small else
                   f"Chunk dưới {MIN_TOKENS} token: {len(small)} (phần truyện ngắn trọn vẹn"
                   f"{'' if not lone_small else ', trừ ' + str(len(lone_small))})."), "",
              "| Tập | Chunk | Token |", "|---|---:|---:|"]
    for vid, cs in by_vol.items():
        name = f"{'ln' if cs[0].vkind == 'main' else 'ssc'}{cs[0].vnum:02d}"
        lines.append(f"| {name} | {len(cs):,} | {sum(c.token_count for c in cs):,} |")

    lines += ["", "## Chọn mô hình embedding", "",
              "Thử trước khi chạy toàn bộ (2026-10-03): 1.383 chunk của LN7, 12, 13, 19 và 12 truy vấn "
              "có đáp án biết trước (9 tiếng Anh, 3 tiếng Việt), CPU 8 nhân trong Docker, không GPU, "
              "không API key — nên chỉ xét mô hình chạy cục bộ miễn phí qua fastembed (ONNX).", "",
              "| Mô hình | Chiều | Tốc độ | Ước tính toàn bộ | hit@1 | hit@5 |",
              "|---|---:|---:|---:|---:|---:|",
              "| **BAAI/bge-small-en-v1.5** (chọn) | 384 | 4,2 chunk/s | ~44 phút | 10/12 | 10/12 |",
              "| BAAI/bge-base-en-v1.5 | 768 | 1,4 chunk/s | ~2 giờ 10 | 10/12 | 11/12 |",
              "| snowflake/snowflake-arctic-embed-m | 768 | 1,4 chunk/s | ~2 giờ 10 | — | — |",
              "| google/embeddinggemma-300m, intfloat/multilingual-e5-large | — | — | — | không nạp được (lỗi ONNX external data) | |",
              "",
              "bge-base chỉ hơn 1 truy vấn ở top 5 nhưng chậm gấp 3 lần cho mỗi lần tạo lại; "
              "bge-small đủ tốt cho giai đoạn này. Truy vấn tiếng Việt vẫn khớp nhờ tên riêng; "
              "giai đoạn sau nên dịch/viết lại câu hỏi sang tiếng Anh trước khi tìm.", ""]
    lines += ["## Truy vấn thử (tìm vector, top 3)", "",
              "Kiểm tra sơ bộ, chưa phải đánh giá chính thức. Truy vấn tiếng Việt chạy trên mô hình "
              "tiếng Anh: khớp chủ yếu nhờ tên riêng.", ""] + trial_lines
    lines += ["## Tìm theo từ khóa (tên riêng)", ""] + kw_lines + [""]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    print(f"fingerprint {'unchanged' if same else 'changed'} since last check")
    print(f"report: {report_path}")
    return passed
