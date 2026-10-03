"""Run the baseline QA on questions with known answers and write data/reports/qa_report.md.

    docker compose exec backend python -m src.qa_eval                   # full run (needs LLM_API_KEY)
    docker compose exec backend python -m src.qa_eval --retrieval-only  # no LLM call

Automatic scoring is a rough guide (answer mentions an expected keyword, and a cited source
comes from an expected volume); the report shows every answer so it can be read by a person.
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from src.core import config
from src.ingest.search import vector_search
from src.ingest.settings import MODEL_NAME
from src.models import SessionLocal
from src.services.llm import LLMError
from src.services.qa import answer_question, get_embedder

REPORT_PATH = Path("data/reports/qa_report.md")
# Gemini free tier allows 5 requests/minute for gemini-3.8-flash
PAUSE = 13
ANY = None

# (question, any-of answer keywords, acceptable main volumes or ANY)
IN_SCOPE = [
    ("Who killed Subaru in the loot house when he first died?", ["Elsa"], {1}),
    ("What is the name of the ability that sends Subaru back in time when he dies?",
     ["Return by Death"], ANY),
    ("Who is the Witch Cult's Archbishop of the Seven Deadly Sins representing Sloth?",
     ["Petelgeuse"], {5, 6, 7, 8, 9}),
    ("Who killed the White Whale?", ["Wilhelm"], {7}),
    ("What does Otto Suwen's divine protection allow him to do?",
     ["animal", "creature", "insect", "beast", "voices"], ANY),
    ("Who is Rem's twin sister?", ["Ram"], ANY),
    ("Who did Beatrice form a contract with in the end?", ["Subaru"], {15, 16, 17, 18, 19, 20, 21}),
    ("What happened to Rem after the battle against the White Whale?",
     ["Gluttony", "eaten", "memor", "name", "coma", "sleep"], {7, 8, 9, 10, 11}),
    ("What is the name of the spirit contracted with Emilia?", ["Puck"], ANY),
    ("Which sin does Regulus Corneas represent as an Archbishop?", ["Greed"], ANY),
    ("Who was Wilhelm van Astrea's wife?", ["Theresia"], ANY),
]
OUT_OF_SCOPE = [
    "What is the capital of France?",
    "Which country won the 2022 FIFA World Cup?",
    "What is Subaru's favorite Pokémon?",
    "Why did Emilia become an Archbishop of the Witch Cult?",  # false premise
]


def _volumes(sources: list[dict], cited_only: bool) -> set[int]:
    return {int(s["volume"].split()[-1]) for s in sources
            if s["volume"].startswith("Volume") and (s["cited"] or not cited_only)}


def run(retrieval_only: bool) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    score_in = score_out = errors = 0
    with SessionLocal() as db:
        get_embedder()  # load once so timings reflect steady state
        for q, keywords, vols in IN_SCOPE:
            if retrieval_only:
                hits = vector_search(db.connection(), get_embedder(), q, k=config.QA_TOP_K)
                lines += [f"### {q}", ""] + [f"{i}. `{h.score:.3f}` {h.citation} — "
                                              f"{h.row.text[:160].replace(chr(10) * 2, ' ')}…"
                                              for i, h in enumerate(hits, 1)] + [""]
                continue
            try:
                a = answer_question(db, q)
            except LLMError as e:
                errors += 1
                lines += [f"### ⚠️ {q}", "", f"Lỗi LLM: `{str(e)[:300]}`", ""]
                continue
            has_kw = any(k.lower() in a.answer.lower() for k in keywords)
            cited_vols = _volumes(a.sources, cited_only=True)
            src_ok = a.found and bool(a.sources) and any(s["cited"] for s in a.sources) and (
                vols is ANY or bool(cited_vols & vols))
            ok = a.found and has_kw and src_ok
            score_in += ok
            lines += [f"### {'✅' if ok else '❌'} {q}", "",
                      f"Kỳ vọng: nhắc tới {' / '.join(keywords)}"
                      f"{'' if vols is ANY else '; nguồn trong tập ' + ', '.join(map(str, sorted(vols)))}"
                      f" — từ khóa {'có' if has_kw else 'KHÔNG có'}, nguồn {'đúng' if src_ok else 'SAI/thiếu'}", "",
                      *[f"> {line}" for line in a.answer.splitlines()], "",
                      "Nguồn được trích:", ""]
            lines += [f"- [{s['ref']}] {s['citation']} (score {s['score']})" for s in a.sources if s["cited"]]
            lines += ["", f"<sub>{a.model} · token {a.usage.get('prompt_tokens', '?')} vào / "
                          f"{a.usage.get('completion_tokens', '?')} ra · "
                          f"truy xuất {a.timings_ms['retrieval']} ms, LLM {a.timings_ms['llm']} ms</sub>", ""]
            time.sleep(PAUSE)
        if not retrieval_only:
            lines += ["## Câu hỏi ngoài phạm vi (phải từ chối)", ""]
            for q in OUT_OF_SCOPE:
                try:
                    a = answer_question(db, q)
                except LLMError as e:
                    errors += 1
                    lines += [f"### ⚠️ {q}", "", f"Lỗi LLM: `{str(e)[:300]}`", ""]
                    continue
                refused = not a.found
                score_out += refused
                lines += [f"### {'✅' if refused else '⚠️'} {q}", "",
                          *[f"> {line}" for line in a.answer.splitlines()], ""]
                time.sleep(PAUSE)

    header = ["# Báo cáo hỏi đáp baseline", "",
              f"Tạo lúc {now}. Truy xuất: vector `{MODEL_NAME}`, top {config.QA_TOP_K}. "
              f"LLM: `{config.LLM_PROVIDER}` / `{config.LLM_MODEL}`, tối đa "
              f"{config.LLM_MAX_OUTPUT_TOKENS} token đầu ra, temperature {config.LLM_TEMPERATURE}.", ""]
    if retrieval_only:
        header += ["Chế độ chỉ truy xuất (không gọi LLM).", ""]
    else:
        header += [f"- Câu hỏi biết đáp án: **{score_in}/{len(IN_SCOPE)}** trả lời đúng kèm nguồn đúng "
                   "(chấm tự động: có từ khóa đáp án + có nguồn được trích thuộc tập kỳ vọng).",
                   f"- Câu hỏi ngoài phạm vi: **{score_out}/{len(OUT_OF_SCOPE)}** được từ chối.",
                   f"- Lỗi gọi LLM: {errors}.", "",
                   "## Câu hỏi biết đáp án", ""]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    if not retrieval_only:
        print(f"in-scope correct: {score_in}/{len(IN_SCOPE)}; out-of-scope refused: "
              f"{score_out}/{len(OUT_OF_SCOPE)}")
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval-only", action="store_true")
    run(ap.parse_args().retrieval_only)
