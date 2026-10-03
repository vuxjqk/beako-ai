"""Check the ingested text against the source epubs and write a Markdown report.

The fidelity check deliberately does not reuse the extractor's parser: it strips tags from
the raw XHTML with a regex and confirms every stored paragraph occurs there, in order.
"""

import html
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from src.ingest.epub import Epub, VolumeFile, scan_folder
from src.models import engine

SAMPLE_SEED = 2026
SAMPLE_COUNT = 12
LONG_PARAGRAPH = 2500  # characters
SHORT_SECTION = 200  # characters of story text
COVERAGE_MIN = 0.97  # share of a story file's letters that must be found in the DB

ALLOWED_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n"
    "!?.,;:'\"()[]{}*/&%#@$+=-_~^|<>"
    "’‘“”…—–■●・•©éèêëàâäáÁïîôöōŌüûùçñ菜月昴"
)
GARBAGE = {
    # Real tag names only: the afterwords print announcements in literal <<...>> brackets
    "HTML tag": re.compile(r"</?(?:p|span|div|a|img|br|em|i|b|strong|section|h\d|html|body|sup|sub"
                           r"|ruby|rt|li|ul|ol|table|tr|td|nav|svg)\b[^>]*>", re.I),
    "HTML entity": re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);"),
    "replacement char": re.compile("�"),
    "control char": re.compile(r"[\x00-\x08\x0b-\x1f\x7f]"),
    "mojibake": re.compile(r"â€|Ã[\x80-\xbf]|Â"),
    "lost dash image (“”)": re.compile(r"“”"),
    "double space": re.compile(r"  "),
    "edge whitespace": re.compile(r"^\s|\s$"),
    "ASCII ellipsis": re.compile(r"\.\.\."),
    "ad text": re.compile(r"Just Light Novels|lightnovel|novelupdates", re.I),
    "URL": re.compile(r"https?://|\bwww\.\w", re.I),
}
# URLs are expected on publisher pages
GARBAGE_EXEMPT = {"URL": {"copyright", "newsletter", "ad", "front_matter", "afterword"},
                  "ad text": {"ad"}}


def _letters(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _fingerprint(conn) -> dict:
    fp = {}
    for t in ("volumes", "book_parts", "book_sections", "book_paragraphs"):
        cols = "id, volume_id, seq, section_id, ordinal, kind, text, source_file, source_block, page" \
            if t == "book_paragraphs" else "*"
        if t == "volumes":
            cols = "id, kind, number, title, file_name, file_size, file_sha256"
        row = conn.execute(text(
            f"SELECT count(*), md5(coalesce(string_agg(r::text, '|' ORDER BY r.id), '')),"
            f" coalesce(max(x::text::bigint), 0)"
            f" FROM (SELECT {cols}, xmin AS x FROM {t}) r"
        )).one()
        fp[t] = {"rows": row[0], "content_md5": row[1], "max_xmin": row[2]}
    return fp


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    def add(self, *lines: str) -> None:
        self.lines.extend(lines)


def verify(epub_dir: Path, volumes: list[VolumeFile], report_path: Path) -> bool:
    r = Report()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- 1. Inventory: folder vs volumes.csv vs DB ---------------------------------
    on_disk = {v.file_name: v for v in scan_folder(epub_dir)}
    in_csv = {v.file_name: v for v in volumes}
    r.check("Thư mục có đúng 32 file epub", len(on_disk) == 32, f"{len(on_disk)} file")
    r.check("volumes.csv khớp thư mục (tên file + sha256)", on_disk == in_csv,
            ", ".join(sorted(set(on_disk) ^ set(in_csv))) or
            ", ".join(k for k in in_csv if on_disk.get(k) != in_csv[k]))
    mains = sorted(v.number for v in volumes if v.kind == "main")
    sscs = sorted(v.number for v in volumes if v.kind == "short_story_collection")
    r.check("28 tập chính đánh số 1–28, 4 Short Story Collection đánh số 1–4",
            mains == list(range(1, 29)) and sscs == list(range(1, 5)), f"main={mains} ssc={sscs}")

    with engine.connect() as conn:
        db_vols = {row.file_name: row for row in conn.execute(text(
            "SELECT id, kind, number, title, file_name, file_sha256 FROM volumes"))}
        r.check("DB có đúng 32 volume, khớp volumes.csv (sha256)",
                len(db_vols) == 32 and all(
                    v.file_name in db_vols and db_vols[v.file_name].file_sha256 == v.sha256
                    for v in volumes),
                f"{len(db_vols)} volume trong DB")

        paras = conn.execute(text("""
            SELECT v.file_name, v.kind AS vkind, v.number AS vnum, pt.ordinal AS part_ord,
                   pt.kind AS part_kind, pt.part_type, pt.number AS chapter, pt.label, pt.title,
                   s.ordinal AS sec_ord, s.number AS sec_num, bp.seq, bp.ordinal, bp.kind,
                   bp.text, bp.source_file, bp.source_block, bp.page
            FROM book_paragraphs bp
            JOIN book_sections s ON s.id = bp.section_id
            JOIN book_parts pt ON pt.id = s.part_id
            JOIN volumes v ON v.id = bp.volume_id
            ORDER BY v.kind, v.number, bp.seq
        """)).all()
        parts = conn.execute(text("""
            SELECT v.file_name, pt.ordinal, pt.kind, pt.part_type, pt.number, pt.label, pt.title,
                   (SELECT count(*) FROM book_sections s WHERE s.part_id = pt.id) AS sections
            FROM book_parts pt JOIN volumes v ON v.id = pt.volume_id
            ORDER BY v.kind, v.number, pt.ordinal
        """)).all()
        fingerprint = _fingerprint(conn)

    by_vol: dict[str, list] = defaultdict(list)
    for p in paras:
        by_vol[p.file_name].append(p)
    parts_by_vol: dict[str, list] = defaultdict(list)
    for p in parts:
        parts_by_vol[p.file_name].append(p)

    # --- 2. Per-volume statistics --------------------------------------------------
    stats = []
    for v in volumes:
        rows = by_vol[v.file_name]
        story = [p for p in rows if p.part_kind == "story" and p.kind == "text"]
        vparts = parts_by_vol[v.file_name]
        stats.append({
            "vf": v,
            "story_parts": sum(p.kind == "story" for p in vparts),
            "other_parts": sum(p.kind != "story" for p in vparts),
            "sections": sum(p.sections for p in vparts if p.kind == "story"),
            "paragraphs": len(rows),
            "story_paragraphs": len(story),
            "scene_breaks": sum(p.kind == "scene_break" for p in rows),
            "words": sum(len(p.text.split()) for p in story),
            "chars": sum(len(p.text) for p in story),
            "paged": any(p.page for p in rows),
            "kinds": Counter(p.kind for p in vparts),
        })

    for kind in ("main", "short_story_collection"):
        group = [s for s in stats if s["vf"].kind == kind]
        med = statistics.median(s["words"] for s in group)
        odd = [f"{s['vf'].slug}={s['words']}" for s in group if not 0.5 * med <= s["words"] <= 2 * med]
        r.check(f"Số từ cốt truyện mỗi file ({kind}) nằm trong 0.5×–2× trung vị ({med:,.0f})",
                not odd, ", ".join(odd))
    r.check("Mỗi file có ít nhất 1 phần cốt truyện",
            all(s["story_parts"] > 0 for s in stats),
            ", ".join(s["vf"].slug for s in stats if not s["story_parts"]))
    r.check("Mỗi file có đúng 1 lời bạt (afterword) được gắn nhãn",
            all(s["kinds"]["afterword"] == 1 for s in stats),
            ", ".join(f"{s['vf'].slug}={s['kinds']['afterword']}" for s in stats
                      if s["kinds"]["afterword"] != 1))

    # --- 3. Empty / abnormal sizes -------------------------------------------------
    empty_parts = [f"{p.file_name}#{p.ordinal}" for p in parts if p.sections == 0]
    r.check("Không có phần (part) rỗng", not empty_parts, ", ".join(empty_parts[:10]))
    r.check("Không có đoạn văn rỗng", not [p for p in paras if not p.text.strip()])
    section_text: dict[tuple, list] = defaultdict(list)
    for p in paras:
        section_text[(p.file_name, p.part_ord, p.sec_ord)].append(p)
    no_text = [k for k, ps in section_text.items() if not any(p.kind == "text" for p in ps)]
    r.check("Không có section chỉ toàn dấu ngắt cảnh / không có chữ", not no_text, str(no_text[:5]))

    story_sections = {k: ps for k, ps in section_text.items() if ps[0].part_kind == "story"}
    sec_len = {k: sum(len(p.text) for p in ps if p.kind == "text") for k, ps in story_sections.items()}
    med_sec = statistics.median(sec_len.values())
    short = sorted((n, k) for k, n in sec_len.items() if n < SHORT_SECTION)
    long_ = sorted(((n, k) for k, n in sec_len.items() if n > 8 * med_sec), reverse=True)
    long_paras = sorted(((len(p.text), p) for p in paras if len(p.text) > LONG_PARAGRAPH),
                        key=lambda x: -x[0])

    # --- 4. Garbage ------------------------------------------------------------------
    garbage: dict[str, list] = defaultdict(list)
    odd_chars: Counter = Counter()
    odd_char_example: dict[str, str] = {}
    for p in paras:
        if p.kind == "ornament":
            continue
        for name, rx in GARBAGE.items():
            if p.part_kind in GARBAGE_EXEMPT.get(name, ()):
                continue
            if rx.search(p.text):
                garbage[name].append(p)
        for ch in set(p.text) - ALLOWED_CHARS:
            odd_chars[ch] += 1
            odd_char_example.setdefault(ch, f"{p.file_name} seq {p.seq}: {p.text[:80]}")
    for name in GARBAGE:
        hits = garbage.get(name, [])
        r.check(f"Không còn rác: {name}", not hits,
                "; ".join(f"{h.file_name.split('/')[-1]} seq {h.seq}: {h.text[:60]!r}" for h in hits[:3]))
    r.check("Không có ký tự ngoài bảng ký tự cho phép", not odd_chars,
            ", ".join(f"{c!r}×{n}" for c, n in odd_chars.most_common(10)))

    # --- 5. Structure and order ----------------------------------------------------
    seq_bad, order_bad, secnum_bad, chap_bad, break_bad = [], [], [], [], []
    fidelity_missing, low_coverage = [], []
    checked_paragraphs = 0
    for v in volumes:
        rows = by_vol[v.file_name]
        if [p.seq for p in rows] != list(range(1, len(rows) + 1)):
            seq_bad.append(v.slug)
        epub = Epub(epub_dir / v.file_name)
        spine_pos = {h: i for i, h in enumerate(epub.spine)}
        keys = [(spine_pos.get(p.source_file, -1), p.source_block) for p in rows]
        if any(k[0] < 0 for k in keys) or keys != sorted(keys):
            order_bad.append(v.slug)

        # Section numbers 1..n inside each story part; chapter numbers 1..n per volume
        per_part: dict[int, list] = defaultdict(list)
        for k, ps in story_sections.items():
            if k[0] == v.file_name:
                per_part[k[1]].append(ps[0].sec_num)
        for part_ord, nums in per_part.items():
            nums = [n for n in nums if n is not None]
            if nums and nums != list(range(nums[0], nums[0] + len(nums))):
                secnum_bad.append(f"{v.slug} part {part_ord}: {nums}")
        chapters = [p.number for p in parts_by_vol[v.file_name] if p.part_type == "chapter"]
        if chapters and chapters != list(range(1, len(chapters) + 1)):
            chap_bad.append(f"{v.slug}: {chapters}")

        for ps in section_text.values():
            if ps[0].file_name != v.file_name:
                continue
            kinds = [p.kind for p in ps]
            if kinds[0] == "scene_break" or kinds[-1] == "scene_break" or any(
                    a == b == "scene_break" for a, b in zip(kinds, kinds[1:])):
                break_bad.append(f"{v.slug} seq {ps[0].seq}")

        # Fidelity: stored paragraphs, in order, inside the raw text of their file
        by_file: dict[str, list] = defaultdict(list)
        for p in rows:
            if p.kind == "text":
                by_file[p.source_file].append(p)
        for href, ps in by_file.items():
            raw = epub.read_text(href)
            body = raw[raw.find("<body"):]
            letters = _letters(html.unescape(re.sub(r"<[^>]+>", " ", body)))
            # Story headings (chapter titles, section numbers) are stored as structure, not
            # paragraphs, so they don't count against coverage
            no_headings = re.sub(r"<h\d\b.*?</h\d>", " ", body, flags=re.S)
            coverage_total = len(_letters(html.unescape(re.sub(r"<[^>]+>", " ", no_headings))))
            pos = found = 0
            for p in ps:
                needle = _letters(p.text)
                checked_paragraphs += 1
                if not needle:
                    continue
                i = letters.find(needle, pos)
                if i < 0:
                    fidelity_missing.append(f"{v.slug} {href}#{p.source_block}: {p.text[:60]!r}")
                    continue
                pos = i + len(needle)
                found += len(needle)
            if ps[0].part_kind == "story" and coverage_total and found / coverage_total < COVERAGE_MIN:
                low_coverage.append(f"{v.slug} {href}: {found / coverage_total:.1%}")

    r.check("seq liên tục 1..N trong mỗi file", not seq_bad, ", ".join(seq_bad))
    r.check("Thứ tự đoạn trùng thứ tự đọc của epub (spine + vị trí khối)", not order_bad,
            ", ".join(order_bad))
    r.check("Số section trong mỗi chương liên tục", not secnum_bad, "; ".join(secnum_bad[:5]))
    r.check("Số chương trong mỗi tập liên tục từ 1", not chap_bad, "; ".join(chap_bad))
    r.check("Dấu ngắt cảnh không nằm đầu/cuối section, không lặp đôi", not break_bad,
            ", ".join(break_bad[:5]))
    r.check(f"Đối chiếu độc lập: mọi đoạn văn ({checked_paragraphs:,}) có trong epub, đúng thứ tự",
            not fidelity_missing, "; ".join(fidelity_missing[:5]))
    r.check(f"Độ phủ: mỗi file nội dung truyện ≥ {COVERAGE_MIN:.0%} chữ của epub có trong DB",
            not low_coverage, "; ".join(low_coverage[:5]))

    # --- 6. Idempotency fingerprint --------------------------------------------------
    fp_path = report_path.with_name("fingerprint.json")
    previous = json.loads(fp_path.read_text()) if fp_path.exists() else None
    same_as_before = previous == fingerprint
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(json.dumps(fingerprint, indent=2))

    # --- Report ----------------------------------------------------------------------
    passed = all(ok for _, ok, _ in r.checks)
    r.add(f"# Báo cáo kiểm tra dữ liệu văn bản Re:ZERO", "",
          f"Tạo lúc {now}. Nguồn: `{epub_dir}` ({len(volumes)} file epub). "
          f"Kết quả: **{'ĐẠT' if passed else 'CÓ LỖI'}** "
          f"({sum(ok for _, ok, _ in r.checks)}/{len(r.checks)} kiểm tra đạt).", "")
    r.add("## Kiểm tra", "", "| | Kiểm tra | Ghi chú |", "|---|---|---|")
    for name, ok, detail in r.checks:
        r.add(f"| {'✅' if ok else '❌'} | {name} | {detail.replace('|', '/')} |")

    r.add("", "## Chạy lại không đổi dữ liệu (idempotency)", "",
          "Dấu vân tay của các bảng (số dòng, md5 nội dung, `max(xmin)` — xmin đổi khi có dòng bị ghi lại):", "",
          "| Bảng | Số dòng | md5 nội dung | max(xmin) |", "|---|---:|---|---:|")
    for t, f in fingerprint.items():
        r.add(f"| {t} | {f['rows']:,} | `{f['content_md5']}` | {f['max_xmin']} |")
    r.add("", ("So với lần verify trước: **không thay đổi**." if same_as_before else
               "So với lần verify trước: " + ("chưa có lần trước." if previous is None else
                                             "**có thay đổi** (bình thường nếu vừa nạp dữ liệu mới).")))

    totals = {k: sum(s[k] for s in stats) for k in ("story_parts", "other_parts", "sections",
                                                    "paragraphs", "scene_breaks", "words")}
    r.add("", "## Số liệu từng file", "",
          "| File | Loại | Phần truyện | Phần khác | Section | Đoạn (tổng) | Ngắt cảnh | Từ (truyện) | Có số trang |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|")
    for s in stats:
        v = s["vf"]
        r.add(f"| {v.slug} | {'chính' if v.kind == 'main' else 'SSC'} | {s['story_parts']} | "
              f"{s['other_parts']} | {s['sections']} | {s['paragraphs']:,} | {s['scene_breaks']} | "
              f"{s['words']:,} | {'có' if s['paged'] else '—'} |")
    r.add(f"| **Tổng** | | {totals['story_parts']} | {totals['other_parts']} | {totals['sections']} | "
          f"{totals['paragraphs']:,} | {totals['scene_breaks']:,} | {totals['words']:,} | |")

    kinds_total = Counter()
    for s in stats:
        kinds_total.update(s["kinds"])
    r.add("", "Nhãn phần (`book_parts.kind`): " +
          ", ".join(f"`{k}` {n}" for k, n in kinds_total.most_common()) + ".")

    r.add("", "## Độ dài bất thường (để xem xét, không phải lỗi)", "",
          f"Trung vị độ dài section truyện: {med_sec:,.0f} ký tự.", "",
          f"Section truyện ngắn hơn {SHORT_SECTION} ký tự ({len(short)}):")
    for n, k in short:
        ps = story_sections[k]
        r.add(f"- {ps[0].file_name.split('/')[-1]} — {ps[0].label or ps[0].title}, section "
              f"{ps[0].sec_num}: {n} ký tự — “{' / '.join(p.text for p in ps if p.kind == 'text')[:120]}”")
    r.add("", f"Section dài hơn 8× trung vị ({len(long_)}):")
    for n, k in long_[:10]:
        ps = story_sections[k]
        r.add(f"- {ps[0].file_name.split('/')[-1]} — {ps[0].label or ps[0].title}, section {ps[0].sec_num}: {n:,} ký tự")
    r.add("", f"Đoạn văn dài hơn {LONG_PARAGRAPH:,} ký tự ({len(long_paras)}):")
    for n, p in long_paras[:10]:
        r.add(f"- {p.file_name.split('/')[-1]} seq {p.seq} ({p.part_kind}): {n:,} ký tự — “{p.text[:100]}…”")

    if odd_chars:
        r.add("", "## Ký tự lạ", "")
        for c, n in odd_chars.most_common():
            r.add(f"- {c!r} ×{n}: {odd_char_example[c]}")

    rng = random.Random(SAMPLE_SEED)
    story_rows = [p for p in paras if p.part_kind == "story" and p.kind == "text"]
    r.add("", "## Đọc thử ngẫu nhiên", "",
          f"{SAMPLE_COUNT} đoạn chọn ngẫu nhiên (seed {SAMPLE_SEED}), mỗi đoạn kèm đoạn trước và sau "
          "để kiểm tra thứ tự. Vị trí để mở sách đối chiếu: file, chương, section, số trang in "
          "(nếu epub có), file XHTML và chỉ số khối trong file.", "")
    for p in sorted(rng.sample(story_rows, SAMPLE_COUNT), key=lambda x: (x.vkind, x.vnum, x.seq)):
        rows = by_vol[p.file_name]
        i = p.seq - 1
        where = (f"{p.file_name.split('/')[-1]} · {p.label or ''} {('“' + p.title + '”') if p.title else ''}"
                 f" · section {p.sec_num} · {'trang ' + p.page if p.page else 'không có số trang'}"
                 f" · `{p.source_file}` khối {p.source_block} · seq {p.seq}")
        r.add(f"### {where}", "")
        for q in rows[max(0, i - 1): i + 2]:
            mark = "**→**" if q.seq == p.seq else "&nbsp;&nbsp;"
            r.add(f"> {mark} {q.text}", ">")
        r.add("")

    r.add("## Ghi chú về nguồn", "",
          "- Các trang chỉ có ảnh (bìa, tranh minh họa, trang tiêu đề) không có chữ nên không có dòng nào trong DB.",
          "- Dấu gạch dài “——” trong nhiều tập là ảnh nội dòng; độ dài được khôi phục theo bề rộng ảnh "
          "(ảnh phổ biến nhất của mỗi tập = “——”). Hai ảnh chữ đặc biệt được chép tay: "
          "LN25 `chi.jpg` = “菜月・昴”, LN13 `Art_1.jpg` = “●・●・●・●”.",
          "- Chỉ những tập có mốc trang dày đặc trong epub mới có `page`; các tập khác để trống.",
          "- LN22: phần preview mở đầu giữa câu vì câu đầu nằm trong ảnh minh họa của sách.",
          "- Phần không phải cốt truyện được gắn nhãn qua `book_parts.kind` (afterword, preview, "
          "copyright, toc, newsletter, ad, front_matter); lọc truyện bằng `kind = 'story'`.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(r.lines) + "\n", encoding="utf-8")
    for name, ok, detail in r.checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    print(f"fingerprint {'unchanged' if same_as_before else 'changed'} since last verify")
    print(f"report: {report_path}")
    return passed
