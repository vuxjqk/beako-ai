"""Builds data/reports/eval_report.md from every saved run, side by side."""

from pathlib import Path

from src.eval import generation, golden, retrieval, runs

REPORT_PATH = Path("data/reports/eval_report.md")


def _pct(x) -> str:
    return "–" if x is None else f"{x * 100:.1f}%"


def _num(x) -> str:
    return "–" if x is None else f"{x:g}"


def _chunkers(cfg: dict) -> str:
    return ", ".join(f"`{c['chunker_version']}` ({c['count']})" for c in cfg["chunks"])


def _short(s: str, n: int = 90) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _question_file(run: dict) -> str:
    return run["golden_set"].get("path", golden.GOLDEN_PATH.as_posix())


def _other_files_section(other: list[dict]) -> list[str]:
    """Runs on another question file (same ids, e.g. the Vietnamese copy): listed apart, so the
    sections above compare like with like."""
    out = ["## Bộ câu hỏi khác", "",
           "Các lần chạy trên một file câu hỏi khác cùng id (vd. bản tiếng Việt). So sánh từng câu với một lần "
           "chạy trên `golden_set.json` cùng mã và cấu hình, không so với bảng ở trên.", "",
           "| Lần chạy | Loại | File câu hỏi | Nhãn | Chế độ | dev Hit@6 / Điểm | Đúng | Từ chối nhầm "
           "| Ngoài phạm vi xử lý đúng |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in other:
        s = r["summary"]
        if r["kind"] == "retrieval":
            out.append(f"| {r['dir']} | retrieval | `{_question_file(r)}` | {r.get('label') or ''} | "
                       f"| {_pct(s['dev']['overall']['hit@6'])} | | | |")
        else:
            i = s["in_scope"]
            out.append(f"| {r['dir']} | generation | `{_question_file(r)}` | {r.get('label') or ''} "
                       f"| {r['config']['generation'].get('qa_mode', 'simple')} | {_pct(i['score'])} "
                       f"| {_pct(i['correct'])} | {_pct(i['false_refusal'])} | {_pct(s['out_of_scope']['handled'])} |")
    return out + [""]


def _retrieval_key(run: dict) -> tuple:
    c = run["config"]
    return (run["code"]["src_sha256"], c["method"], c["embedding_model"], c["depth"], _chunkers(c),
            run["golden_set"]["sha256"])


def _retrieval_section(rruns: list[dict], questions: dict[str, golden.Question]) -> list[str]:
    out = ["## Truy xuất", "",
           "Không gọi LLM. Một chunk được coi là đúng khi khoảng đoạn văn của nó giao với một vị trí bằng chứng "
           "(cùng tập). Hit@k: có chunk đúng trong top k. MRR: trung bình 1/hạng của chunk đúng đầu tiên "
           "(0 nếu không có trong top độ sâu). Span recall@20: tỉ lệ vị trí bằng chứng của câu hỏi được phủ "
           "trong top 20 (câu nhiều phần cần đủ mọi phần). All spans@20: tỉ lệ câu được phủ đủ mọi phần.", "",
           "Chỉ số được tách theo split: **dev** dùng để chọn cấu hình, **test** chỉ để xác nhận thay đổi "
           "đã chọn (không tinh chỉnh theo test).", "",
           "| Lần chạy | Nhãn | Commit / mã `src` | Cấu hình truy xuất | Chunker (số chunk) | dev Hit@6 "
           "| dev Hit@20 | dev MRR | dev Span recall@20 | test Hit@6 | test Hit@20 | test MRR | ms/câu "
           "| Vân tay kết quả |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rruns:
        c, d, t = r["config"], r["summary"]["dev"]["overall"], r["summary"]["test"]["overall"]
        out.append(f"| {r['dir']} | {r.get('label') or ''} | `{r['code']['commit'] or '?'}` / "
                   f"`{r['code']['src_sha256']}` | `{c['method']}` | {_chunkers(c)} "
                   f"| {_pct(d['hit@6'])} | {_pct(d['hit@20'])} | {d['mrr']:.3f} | {_pct(d['span_recall@20'])} "
                   f"| {_pct(t['hit@6'])} | {_pct(t['hit@20'])} | {t['mrr']:.3f} "
                   f"| {r['summary']['latency_ms_avg']} | `{r['fingerprint']}` |")
    out += ["", f"Embedding: `{rruns[-1]['config']['embedding_model']}`. Mã `src` là hash của mọi file "
                "`src/**/*.py` lúc chạy, nên phân biệt được cả thay đổi chưa commit.", ""]

    # Determinism: runs with the same configuration must produce the same ranked lists
    groups: dict[tuple, list[dict]] = {}
    for r in rruns:
        groups.setdefault(_retrieval_key(r), []).append(r)
    repeated = {k: g for k, g in groups.items() if len(g) > 1}
    if repeated:
        out += ["### Kiểm tra tính lặp lại", ""]
        for g in repeated.values():
            fps = {r["fingerprint"] for r in g}
            status = "giống hệt nhau ✅" if len(fps) == 1 else "KHÁC NHAU ❌"
            out.append(f"- {len(g)} lần chạy cùng cấu hình ({', '.join(r['dir'] for r in g)}): kết quả {status}")
        out.append("")

    latest = rruns[-1]
    out += [f"### Theo loại câu hỏi — {latest['dir']}", "",
            "| Split | Loại | n | Hit@6 | Hit@20 | MRR | Span recall@6 | Span recall@20 | All spans@20 |",
            "|---|---|---|---|---|---|---|---|---|"]
    for split in golden.SPLITS:
        for cat in golden.CATEGORIES[:-1] + ("overall",):
            s = latest["summary"][split].get(cat)
            if s and s["n"]:
                out.append(f"| {split} | {cat} | {s['n']} | {_pct(s['hit@6'])} | {_pct(s['hit@20'])} "
                           f"| {s['mrr']:.3f} | {_pct(s['span_recall@6'])} | {_pct(s['span_recall@20'])} "
                           f"| {_pct(s['all_spans@20'])} |")
    out += ["", f"Độ trễ truy xuất trung bình: {latest['summary']['latency_ms_avg']} ms/câu "
                f"(top {latest['config']['depth']}).", ""]

    if len(rruns) > 1:
        prev = rruns[-2]
        before = {r["id"]: r["first_rank"] for r in prev["results"]}
        changes = [(r["id"], before.get(r["id"]), r["first_rank"]) for r in latest["results"]
                   if r["id"] in before and before[r["id"]] != r["first_rank"]]
        out += [f"### Thay đổi so với lần trước ({prev['dir']} → {latest['dir']})", ""]
        if changes:
            out += ["| Câu | Hạng trước | Hạng sau | |", "|---|---|---|---|"]
            for qid, a, b in changes:
                better = (b or 999) < (a or 999)
                out.append(f"| {qid} | {a or '–'} | {b or '–'} | {'tốt hơn' if better else 'TỆ HƠN'} |")
        else:
            out.append("Không câu nào đổi hạng chunk đúng đầu tiên.")
        out.append("")

    out += [f"### Chi tiết từng câu — {latest['dir']}", "",
            "Hạng của chunk đúng đầu tiên, và hạng đầu tiên phủ từng vị trí bằng chứng (– = không có trong top "
            f"{latest['config']['depth']}).", "",
            "| Câu | Split | Loại | Hạng đầu | Hạng theo vị trí | Câu hỏi |", "|---|---|---|---|---|---|"]
    for r in latest["results"]:
        spans = " / ".join(str(x) if x else "–" for x in r["span_ranks"])
        q = questions.get(r["id"])
        out.append(f"| {r['id']} | {r['split']} | {r['category']} | {r['first_rank'] or '–'} | {spans} "
                   f"| {_short(q.question) if q else ''} |")
    return out + [""]


def _generation_section(gruns: list[dict], questions: dict[str, golden.Question]) -> list[str]:
    out = ["## Sinh câu trả lời", "",
           "Chạy toàn bộ `/qa` (truy xuất top `QA_TOP_K` + LLM), sau đó một LLM chấm: **đúng** so với đáp án chuẩn "
           "(đúng / một phần / sai; điểm = đúng + 0,5 × một phần), **trung thực** chỉ so với các đoạn được trích. "
           "Từ chối nhầm: câu có đáp án nhưng hệ thống trả lời không tìm thấy. Câu ngoài phạm vi được tính là "
           "xử lý đúng khi hệ thống từ chối hoặc chỉ ra tiền đề sai.", "",
           "Lần chạy *mô phỏng* (`python -m src.eval combine`) ghép kết quả từng câu của một lần chạy simple và "
           "một lần chạy agent theo chính sách định tuyến, không gọi LLM thêm.", "",
           "| Lần chạy | Nhãn | Chế độ | Truy xuất | Mô hình | Prompt | Giám khảo | Đủ | Điểm | Đúng | Một phần | Sai "
           "| Từ chối nhầm | Bằng chứng trong ngữ cảnh | Trung thực | Trích chunk đúng | Ngoài phạm vi xử lý đúng "
           "| Gọi LLM/câu | Token vào/ra | Tổng ms |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in gruns:
        g, s = r["config"]["generation"], r["summary"]
        i, f, o, c = s["in_scope"], s["faithfulness"], s["out_of_scope"], s["cost"]
        out.append(f"| {r['dir']} | {r.get('label') or ''} | {g.get('qa_mode', 'simple')} "
                   f"| `{r['config']['retrieval']['method']}` "
                   f"| `{g['model']}` | `{g['system_prompt_sha256']}` "
                   f"| `{g['judge_model']}` | {'✅' if r.get('complete') else '⚠️ ' + str(s['errors']) + ' lỗi'} "
                   f"| {_pct(i['score'])} | {_pct(i['correct'])} | {_pct(i['partial'])} | {_pct(i['incorrect'])} "
                   f"| {_pct(i['false_refusal'])} | {_pct(i['gold_in_context'])} | {_pct(f['supported'])} "
                   f"| {_pct(f['cites_gold_chunk'])} | {_pct(o['handled'])} "
                   f"| {_num(c.get('llm_calls_avg') or 1)} "
                   f"| {_num(c['prompt_tokens_avg'])}/{_num(c['completion_tokens_avg'])} "
                   f"| {_num(c.get('total_ms_avg') or c['llm_ms_avg'])} |")
    out.append("")

    # The comparison that decides whether a change helps: score per question type, per run
    cats = list(golden.CATEGORIES[:-1])
    out += ["### Điểm theo loại câu và split, từng lần chạy", "",
            "| Lần chạy | Chế độ | " + " | ".join(cats) + " | dev | test | Ngoài phạm vi |",
            "|---|---|" + "---|" * (len(cats) + 3)]
    for r in gruns:
        s = r["summary"]
        cells = [_pct(s["by_category"].get(c, {}).get("score")) for c in cats]
        cells += [_pct(s["by_split"].get(sp, {}).get("score")) for sp in golden.SPLITS]
        out.append(f"| {r['dir']} | {r['config']['generation'].get('qa_mode', 'simple')} | " + " | ".join(cells)
                   + f" | {_pct(s['out_of_scope']['handled'])} |")
    out.append("")

    latest = gruns[-1]
    s = latest["summary"]
    g = latest["config"]["generation"]
    out += [f"### Phân loại lỗi — {latest['dir']}", "",
            "Bằng chứng có nằm trong các chunk đưa cho LLM không? Hàng thứ nhất mà sai là lỗi **đọc/suy luận** "
            "(sửa prompt/mô hình); hàng thứ hai là lỗi **truy xuất** (sửa giai đoạn tìm kiếm).", "",
            "| | Đúng | Một phần | Sai | Từ chối | Trả về rỗng |", "|---|---|---|---|---|---|"]
    for where, label in (("gold_in_context", "Bằng chứng có trong ngữ cảnh"),
                         ("gold_not_in_context", "Bằng chứng KHÔNG có trong ngữ cảnh")):
        a = s["attribution"][where]
        out.append(f"| {label} | {a['correct']} | {a['partial']} | {a['incorrect']} | {a['refused']} | {a.get('empty', 0)} |")
    out += ["", "| Split / loại | n | Đúng | Điểm |", "|---|---|---|---|"]
    for sp, v in s["by_split"].items():
        out.append(f"| {sp} | {v['n']} | {_pct(v['correct'])} | {_pct(v['score'])} |")
    for cat, v in s["by_category"].items():
        out.append(f"| {cat} | {v['n']} | {_pct(v['correct'])} | {_pct(v['score'])} |")
    f, o, c = s["faithfulness"], s["out_of_scope"], s["cost"]
    out += ["",
            f"- Trung thực (trên {f['n_answered']} câu có trả lời): được hỗ trợ {_pct(f['supported'])}, "
            f"một phần {_pct(f['partially_supported'])}, không được hỗ trợ {_pct(f['unsupported'])}, "
            f"không trích nguồn {_pct(f['no_citations'])}; trích ít nhất một chunk chứa bằng chứng chuẩn "
            f"{_pct(f['cites_gold_chunk'])}.",
            f"- Câu có đáp án mà LLM trả về rỗng (lỗi phía nhà cung cấp, không phải từ chối): "
            f"{_pct(s['in_scope'].get('empty'))}.",
            f"- Ngoài phạm vi ({o['n']} câu): xử lý đúng {_pct(o['handled'])}, bịa câu trả lời {_pct(o['answered'])}; "
            "theo loại: " + ", ".join(f"{t} {_pct(v)}" for t, v in o["by_type"].items()) + ".",
            f"- Chi phí trung bình mỗi câu: {_num(c['prompt_tokens_avg'])} token vào, "
            f"{_num(c['completion_tokens_avg'])} token ra (giám khảo thêm {_num(c['judge_tokens_avg'])} token); "
            f"truy xuất {_num(c['retrieval_ms_avg'])} ms, LLM {_num(c['llm_ms_avg'])} ms.",
            f"- Cấu hình: `{g['provider']}` / `{g['model']}`, temperature {g['temperature']}, tối đa "
            f"{g['max_output_tokens']} token ra, top {latest['config']['retrieval']['qa_top_k']}, "
            f"chunker {_chunkers(latest['config']['retrieval'])}.", ""]

    out += [f"### Chi tiết từng câu — {latest['dir']}", "",
            "| Câu | Kết quả | Bằng chứng trong ngữ cảnh (hạng) | Trung thực | Câu trả lời | Nhận xét giám khảo |",
            "|---|---|---|---|---|---|"]
    for r in latest["results"]:
        if "error" in r:
            out.append(f"| {r['id']} | ⚠️ lỗi | | | {_short(r['error'], 80)} | |")
            continue
        ctx = "–" if r["category"] == "out_of_scope" else (
            ", ".join(map(str, r["gold_context_ranks"])) or "không")
        answer = _short(r["answer"], 140).replace("|", "\\|")
        expl = _short(r.get("judge_explanation") or "", 120).replace("|", "\\|")
        out.append(f"| {r['id']} | {r['verdict']} | {ctx} | {r.get('faithfulness') or ''} | {answer} | {expl} |")
    return out + [""]


def build() -> Path:
    questions = {q.id: q for q in golden.load()[0]}
    rruns, gruns = runs.load_all("retrieval"), runs.load_all("generation")
    # Recompute summaries from the stored per-question results, so metric fixes apply to old runs
    for r in rruns + gruns:  # runs from before the dev/test split: take it from the golden set
        for res in r["results"]:
            res["split"] = questions[res["id"]].split if res["id"] in questions else "dev"
    for r in rruns:
        r["summary"] = retrieval.aggregate(r["results"])
    for r in gruns:
        r["summary"] = generation.aggregate(r["results"])
    main = golden.GOLDEN_PATH.as_posix()
    other = [r for r in rruns + gruns if _question_file(r) != main]
    rruns = [r for r in rruns if _question_file(r) == main]
    gruns = [r for r in gruns if _question_file(r) == main]
    counts: dict[str, int] = {}
    for q in questions.values():
        counts[q.category] = counts.get(q.category, 0) + 1
    lines = ["# Báo cáo đánh giá", "",
             "Tạo bởi `python -m src.eval report` từ mọi lần chạy trong `data/eval/runs/`. Bộ câu hỏi: "
             f"`data/eval/golden_set.json`, {len(questions)} câu ("
             + ", ".join(f"{c} {n}" for c, n in counts.items()) + ").", "",
             "Cách chạy (trong container `backend`):", "",
             "```",
             "python -m src.eval retrieval --label <mô tả thay đổi>   # nhanh, không tốn quota: chạy sau mỗi thay đổi",
             "python -m src.eval generation --label <mô tả>           # gọi LLM: chạy khi cần",
             "python -m src.eval report                               # dựng lại báo cáo này",
             "```", ""]
    lines += ["## Giới hạn của phép đo", "",
              "- Vị trí bằng chứng không vét cạn: một sự kiện nhắc lại ở nhiều tập (vd. Puck là tinh linh của "
              "Emilia) có thể được trả lời đúng từ đoạn khác. Câu \"Đúng\" nằm ở hàng \"bằng chứng KHÔNG có trong "
              "ngữ cảnh\" là dấu hiệu nên bổ sung vị trí vào bộ câu hỏi; chỉ số truy xuất vì vậy là cận dưới.",
              "- Giám khảo mặc định là chính mô hình sinh câu trả lời, nên có thể dễ dãi với chính nó; khi so sánh "
              "mô hình, giữ cố định `--judge-model`. Với bộ nhỏ, đọc cột nhận xét để kiểm tra lại.",
              "- Span recall coi mọi vị trí của một câu là bắt buộc; với câu có vị trí thay thế (multi-06), "
              "Hit@k phản ánh đúng hơn.",
              "- Đổi bộ câu hỏi làm đổi `golden_set.sha256`; chỉ so sánh các lần chạy cùng hash.", ""]
    lines += _retrieval_section(rruns, questions) if rruns else ["## Truy xuất", "", "Chưa có lần chạy.", ""]
    lines += _generation_section(gruns, questions) if gruns else ["## Sinh câu trả lời", "", "Chưa có lần chạy.", ""]
    if other:
        lines += _other_files_section(other)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH
