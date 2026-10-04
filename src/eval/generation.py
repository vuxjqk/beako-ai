"""Answer evaluation: runs the full QA pipeline, then an LLM judge grades each answer.

Uses LLM quota (one answer call per question, plus one judge call per non-refused answer),
so it is run less often than the retrieval evaluation. Results are appended to
results.jsonl as they come in; an interrupted run (quota, network) continues with --resume.

Per answerable question it records:
- correctness against the reference answer / key points (judge): correct | partial | incorrect,
  or refused when the system said it could not find the answer
- faithfulness against the passages the answer cites (judge): supported | partially_supported |
  unsupported, or no_citations
- whether a chunk overlapping the gold evidence was in the LLM's context at all; together with
  correctness this splits failures into retrieval misses and reading errors
Out-of-scope questions should be refused, or (false premise) have the premise corrected.
"""

import json
import re
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.eval import golden, runs
from src.services import llm
from src.services.qa import answer_question, get_embedder
from src.services.retrieval import RetrievalConfig

JUDGE_MAX_TOKENS = 600
# Stop (and leave the run resumable) after this many LLM failures in a row: usually quota
MAX_CONSECUTIVE_ERRORS = 3

JUDGE_SYSTEM = """You grade answers produced by a question-answering system over the light novel series "Re:ZERO -Starting Life in Another World-". Be strict and literal. Reply with a single JSON object and nothing else."""

JUDGE_IN_SCOPE = """Question:
{question}

Reference answer (written by a person who checked the novel text):
{reference}

Key points the answer should contain:
{key_points}

System answer (the [n] marks cite the passages below):
{answer}

Passages cited by the system answer:
{passages}

Grade two things independently.

1. "correctness": compare the system answer with the reference answer and key points.
   - "correct": the main facts asked for are present and nothing important contradicts the reference. Extra true detail is fine; wording does not matter.
   - "partial": some key points are present, or the answer is right but incomplete, or it mixes correct facts with a wrong one.
   - "incorrect": the main fact is wrong or missing.
2. "faithfulness": judge ONLY against the cited passages above, not against the reference or your own knowledge.
   - "supported": every factual claim in the answer is stated in or directly implied by the passage it cites.
   - "partially_supported": some claims are supported, at least one is not.
   - "unsupported": the main claims are not found in the cited passages.

Reply with JSON:
{{"correctness": "correct|partial|incorrect", "faithfulness": "supported|partially_supported|unsupported", "unsupported_claims": ["claims not backed by the cited passages, if any"], "explanation": "one or two sentences"}}"""

JUDGE_OUT_OF_SCOPE = """The question below cannot be answered from the novels. Reason:
{reason}

Question:
{question}

System answer:
{answer}

Classify the system answer:
- "declined": it says the information is not available / not in the passages, without inventing an answer.
- "corrected_premise": it points out that the question's assumption is wrong, based on the passages, without inventing an answer.
- "answered": it gives an answer as if the question were valid (accepting a false premise, or using outside knowledge).

Reply with JSON:
{{"verdict": "declined|corrected_premise|answered", "explanation": "one sentence"}}"""


def _parse_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError(f"judge reply has no JSON object: {raw[:200]!r}")
    return json.loads(m.group(0))


def _chunk_texts(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(text("SELECT id, text FROM book_chunks WHERE id = ANY(:ids)"), {"ids": ids}).all()
    return {r[0]: r[1] for r in rows}


def _judge(prompt: str, model: str) -> tuple[dict, dict]:
    c = llm.chat(JUDGE_SYSTEM, prompt, model=model, max_tokens=JUDGE_MAX_TOKENS, temperature=0.0)
    return _parse_json(c.text), c.usage


def evaluate_question(db: Session, q: golden.Question, judge_model: str, pause: float,
                      cfg: RetrievalConfig, mode: str) -> dict:
    a = answer_question(db, q.question, cfg=cfg, mode=mode)
    out = {
        "id": q.id,
        "category": q.category,
        "split": q.split,
        "oos_type": q.oos_type,
        "answer": a.answer,
        "found": a.found,
        "model": a.model,
        "usage": a.usage,
        "timings_ms": a.timings_ms,
        "mode": a.mode,
        "route_reason": a.route_reason,
        "llm_calls": sum(1 for t in a.trace if "llm" in t) or 1,
        "trace": a.trace,
        "context_chunk_ids": [s["chunk_id"] for s in a.sources],
        "cited_refs": [s["ref"] for s in a.sources if s["cited"]],
        "judge_usage": {},
    }
    if q.in_scope:
        refs = golden.chunk_refs(db, out["context_chunk_ids"])
        ctx_spans = [golden.matching_spans(refs[cid], q.spans) for cid in out["context_chunk_ids"]]
        out["gold_context_ranks"] = [i for i, m in enumerate(ctx_spans, 1) if m]
        out["gold_in_context"] = bool(out["gold_context_ranks"])
        out["context_span_recall"] = len({i for m in ctx_spans for i in m}) / len(q.spans)
        out["cited_gold"] = any(ctx_spans[r - 1] for r in out["cited_refs"])
    if not a.found:
        # An empty completion (provider returned nothing) is a system failure, not a refusal
        out["verdict"] = "refused" if a.answer else "empty"
        return out

    time.sleep(pause)
    if q.in_scope:
        cited = [s for s in a.sources if s["cited"]]
        texts = _chunk_texts(db, [s["chunk_id"] for s in cited])
        passages = "\n\n".join(f"[{s['ref']}] {s['volume']} — {s['chapter']}\n{texts.get(s['chunk_id'], '')}"
                               for s in cited) or "(the answer cites no passages)"
        verdict, usage = _judge(JUDGE_IN_SCOPE.format(
            question=q.question, reference=q.answer, key_points="\n".join(f"- {k}" for k in q.key_points),
            answer=a.answer, passages=passages), judge_model)
        out["verdict"] = verdict.get("correctness")
        out["faithfulness"] = verdict.get("faithfulness") if cited else "no_citations"
        out["unsupported_claims"] = verdict.get("unsupported_claims") or []
    else:
        verdict, usage = _judge(JUDGE_OUT_OF_SCOPE.format(
            reason=q.answer, question=q.question, answer=a.answer), judge_model)
        out["verdict"] = verdict.get("verdict")
    out["judge_explanation"] = verdict.get("explanation")
    out["judge_usage"] = usage
    return out


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 1) if xs else None


def aggregate(results: list[dict]) -> dict:
    # Runs saved before "empty" existed recorded empty completions as refusals
    ok = [{**r, "verdict": "empty"} if r.get("verdict") == "refused" and not r.get("answer") else r
          for r in results if "error" not in r]
    ins = [r for r in ok if r["category"] != "out_of_scope"]
    oos = [r for r in ok if r["category"] == "out_of_scope"]
    answered = [r for r in ins if r["verdict"] not in ("refused", "empty")]

    def rate(rows, pred):
        return round(sum(1 for r in rows if pred(r)) / len(rows), 4) if rows else None

    s = {
        "errors": len(results) - len(ok),
        "in_scope": {
            "n": len(ins),
            "correct": rate(ins, lambda r: r["verdict"] == "correct"),
            "partial": rate(ins, lambda r: r["verdict"] == "partial"),
            "incorrect": rate(ins, lambda r: r["verdict"] == "incorrect"),
            "false_refusal": rate(ins, lambda r: r["verdict"] == "refused"),
            "empty": rate(ins, lambda r: r["verdict"] == "empty"),
            # correct = 1, partial = 0.5
            "score": round(sum({"correct": 1, "partial": 0.5}.get(r["verdict"], 0) for r in ins) / len(ins), 4)
            if ins else None,
            "gold_in_context": rate(ins, lambda r: r["gold_in_context"]),
        },
        "faithfulness": {
            "n_answered": len(answered),
            "supported": rate(answered, lambda r: r.get("faithfulness") == "supported"),
            "partially_supported": rate(answered, lambda r: r.get("faithfulness") == "partially_supported"),
            "unsupported": rate(answered, lambda r: r.get("faithfulness") == "unsupported"),
            "no_citations": rate(answered, lambda r: r.get("faithfulness") == "no_citations"),
            "cites_gold_chunk": rate(answered, lambda r: r["cited_gold"]),
        },
        "out_of_scope": {
            "n": len(oos),
            "handled": rate(oos, lambda r: r["verdict"] in ("refused", "declined", "corrected_premise")),
            "answered": rate(oos, lambda r: r["verdict"] == "answered"),
            "empty": rate(oos, lambda r: r["verdict"] == "empty"),
            "by_type": {t: rate([r for r in oos if r["oos_type"] == t],
                                lambda r: r["verdict"] in ("refused", "declined", "corrected_premise"))
                        for t in golden.OOS_TYPES if any(r["oos_type"] == t for r in oos)},
        },
        "cost": {
            "prompt_tokens_avg": _mean([r["usage"].get("prompt_tokens", 0) for r in ok]),
            "completion_tokens_avg": _mean([r["usage"].get("completion_tokens", 0) for r in ok]),
            "judge_tokens_avg": _mean([r["judge_usage"].get("total_tokens", 0) for r in ok if r["judge_usage"]]),
            "retrieval_ms_avg": _mean([r["timings_ms"]["retrieval"] for r in ok]),
            "llm_ms_avg": _mean([r["timings_ms"]["llm"] for r in ok]),
            "total_ms_avg": _mean([r["timings_ms"]["retrieval"] + r["timings_ms"]["llm"] for r in ok]),
            "llm_calls_avg": _mean([r.get("llm_calls", 1) for r in ok]),
            "agent_share": rate(ok, lambda r: r.get("mode", "simple") != "simple"),
        },
    }
    # Where the failures come from: was the gold evidence in the context the LLM saw?
    attribution = {}
    for where, pred in (("gold_in_context", True), ("gold_not_in_context", False)):
        rows = [r for r in ins if r["gold_in_context"] is pred]
        attribution[where] = {v: sum(1 for r in rows if r["verdict"] == v)
                              for v in ("correct", "partial", "incorrect", "refused", "empty")}
    s["attribution"] = attribution
    s["by_split"] = {sp: {"n": len(rows), "correct": rate(rows, lambda r: r["verdict"] == "correct"),
                          "score": round(sum({"correct": 1, "partial": 0.5}.get(r["verdict"], 0)
                                             for r in rows) / len(rows), 4)}
                     for sp in golden.SPLITS if (rows := [r for r in ins if r.get("split") == sp])}
    s["by_category"] = {c: {"n": len(rows), "correct": rate(rows, lambda r: r["verdict"] == "correct"),
                            "score": round(sum({"correct": 1, "partial": 0.5}.get(r["verdict"], 0)
                                               for r in rows) / len(rows), 4)}
                        for c in golden.CATEGORIES[:-1]
                        if (rows := [r for r in ins if r["category"] == c])}
    return s


def run(db: Session, label: str | None, judge_model: str | None, pause: float, cfg: RetrievalConfig,
        mode: str, resume: Path | None = None, only: set[str] | None = None) -> dict:
    if not config.LLM_API_KEY:
        raise llm.LLMNotConfigured("LLM_API_KEY is not set")
    questions, sha = golden.load()
    targets = [q for q in questions if not only or q.id in only]
    judge_model = judge_model or config.LLM_MODEL
    get_embedder()
    if resume:
        run_dir = resume
        record = json.loads((run_dir / "header.json").read_text(encoding="utf-8"))
        if record["golden_set"]["sha256"] != sha[:12]:
            raise SystemExit("golden set changed since this run started; start a new run")
    else:
        run_dir = runs.new_run_dir("generation", label)
        record = runs.header("generation", label, sha, len(targets))
        record["config"] = {"retrieval": runs.retrieval_config(db, config.QA_TOP_K, cfg),
                            "generation": runs.generation_config(judge_model, mode)}
        (run_dir / "header.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    judge_model = record["config"]["generation"]["judge_model"]  # a resumed run keeps its judge
    cfg = RetrievalConfig(**record["config"]["retrieval"]["settings"]) if resume else cfg
    mode = record["config"]["generation"].get("qa_mode", "simple")

    results_path = run_dir / "results.jsonl"
    done: dict[str, dict] = {}
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done[r["id"]] = r
    consecutive = 0
    with results_path.open("a", encoding="utf-8") as f:
        for i, q in enumerate(targets, 1):
            if q.id in done:
                continue
            try:
                r = evaluate_question(db, q, judge_model, pause, cfg, mode)
                consecutive = 0
            except (llm.LLMError, ValueError) as e:
                r = {"id": q.id, "category": q.category, "error": str(e)[:500]}
                consecutive += 1
            db.rollback()
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(targets)}] {q.id}: {r.get('verdict') or 'ERROR ' + r['error'][:120]}", flush=True)
            if "error" not in r:
                done[q.id] = r
            if consecutive >= MAX_CONSECUTIVE_ERRORS:
                print(f"{consecutive} LLM failures in a row, stopping. Continue later with --resume {run_dir}")
                break
            time.sleep(pause)

    results = [done[q.id] if q.id in done else {"id": q.id, "category": q.category, "error": "not run"}
               for q in targets]
    record["complete"] = all("error" not in r for r in results)
    record["summary"] = aggregate(results)
    record["results"] = results
    record["path"] = str(runs.save(run_dir, record))
    return record


POLICIES = ("route", "escalate", "route+escalate")


def combine(simple_dir: str, agent_dir: str, policy: str, label: str | None) -> dict:
    """Simulate an auto-mode policy from a simple-mode run and an agent-mode run of the same
    golden set, without new LLM calls: each question takes the result its path would have produced.
    - route: questions route() sends to the agent take the agent result
    - escalate: simple-path refusals are retried by the agent (cost of both is counted)
    The result is saved as a generation run marked "simulated"; confirm a chosen policy with a
    real --mode auto run."""
    from src.services.qa import route

    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    load = lambda d: json.loads((runs.RUNS_DIR / d / "run.json").read_text(encoding="utf-8"))
    simple, agent = load(simple_dir), load(agent_dir)
    if simple["golden_set"] != agent["golden_set"]:
        raise SystemExit("the two runs used different golden sets")
    questions = {q.id: q for q in golden.load()[0]}
    by_agent = {r["id"]: r for r in agent["results"]}
    results = []
    for s in simple["results"]:
        a = by_agent.get(s["id"])
        use = s
        if a is not None and "error" not in a and "error" not in s:
            routed = route(questions[s["id"]].question)[0] == "agent" if "route" in policy else False
            refused = s.get("verdict") in ("refused", "empty")
            if routed:
                use = {**a, "mode": "agent"}
            elif "escalate" in policy and refused:
                use = {**a, "mode": "simple+agent",
                       "usage": {k: s["usage"].get(k, 0) + a["usage"].get(k, 0)
                                 for k in set(s["usage"]) | set(a["usage"])},
                       "timings_ms": {k: s["timings_ms"].get(k, 0) + a["timings_ms"].get(k, 0)
                                      for k in s["timings_ms"]},
                       "llm_calls": s.get("llm_calls", 1) + a.get("llm_calls", 1)}
        results.append(use)
    run_dir = runs.new_run_dir("generation", label or f"sim-{policy}")
    record = runs.header("generation", label or f"sim-{policy}", "", len(results))
    record["golden_set"] = simple["golden_set"]
    record["simulated"] = {"policy": policy, "simple_run": simple_dir, "agent_run": agent_dir}
    record["config"] = {"retrieval": simple["config"]["retrieval"],
                        "generation": {**agent["config"]["generation"], "qa_mode": f"auto ({policy}, simulated)"}}
    record["complete"] = all("error" not in r for r in results)
    record["summary"] = aggregate(results)
    record["results"] = results
    record["path"] = str(runs.save(run_dir, record))
    return record
