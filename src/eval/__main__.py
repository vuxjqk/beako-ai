"""Evaluation CLI (run inside the backend container: docker compose exec backend python -m src.eval ...).

    check                       validate the golden set's evidence locations against the database
    show ID [ID ...]            print questions with their evidence text, for reading by a person
    retrieval [--label L]       retrieval metrics only (no LLM; run after every change)
                                --set key=value overrides a RetrievalConfig field, e.g.
                                --set method=hybrid scope=true
    generation [--label L]      full QA + LLM judge (uses quota; --resume DIR continues a stopped run)
                                retrieval and generation take --golden FILE for another question file
                                with the same ids, e.g. data/eval/golden_set_vi.json (questions in Vietnamese)
    combine --simple D --agent D --policy P
                                simulate an auto-mode routing policy from a simple run and an
                                agent run (no LLM calls); saved as a run marked "simulated"
    report                      rebuild data/reports/eval_report.md from all saved runs
    feedback                    export users' right/wrong ratings to data/eval/feedback.jsonl
    regress retrieval|generation [--baseline DIR] [--tolerance T]
                                compare the latest run with the previous one; exit 1 if quality dropped
    usage [--days N]            question answering per day: questions, cost, "not found" and thumbs-down
                                rates (from qa_requests; the same numbers as the admin usage page)

retrieval and generation also rebuild the report when they finish.
"""

import argparse
from pathlib import Path

from src.core import config
from src.eval import feedback, generation, golden, regress, report, retrieval
from src.models import SessionLocal
from src.services import usage
from src.services.retrieval import default_config


def _pct(x) -> str:
    return "-" if x is None else f"{x * 100:.0f}%"


def print_usage(r: dict) -> None:
    t = r["today"]
    budget = f" of ${t['budget_usd']:g} ({t['state']})" if t["budget_usd"] else ""
    print(f"Today ({r['timezone']}): ${t['spent_usd']:.4f} spent{budget}; model {r['limits']['model']} at "
          f"${r['limits']['price_input_per_mtok']:g}/${r['limits']['price_output_per_mtok']:g} per M tokens in/out\n")
    print(f"{'day':10} {'asked':>5} {'users':>5} {'cost $':>9} {'$/q':>8} {'tok in':>9} {'tok out':>8} "
          f"{'agent':>5} {'not found':>9} {'errors':>6} {'refused':>7} {'up':>3} {'down':>4} {'down%':>5} "
          f"{'avg s':>6} {'p95 s':>6}")
    for d in r["days"]:
        sec = lambda ms: "-" if ms is None else f"{ms / 1000:.1f}"
        print(f"{d['day']:10} {d['questions']:>5} {d['users']:>5} {d['cost_usd']:>9.4f} "
              f"{d['cost_per_question_usd'] or 0:>8.4f} {d['prompt_tokens']:>9} {d['completion_tokens']:>8} "
              f"{d['agent']:>5} {_pct(d['not_found_rate']):>9} {d['errors']:>6} {d['rejected']:>7} "
              f"{d['thumbs_up']:>3} {d['thumbs_down']:>4} {_pct(d['thumbs_down_rate']):>5} "
              f"{sec(d['latency_avg_ms']):>6} {sec(d['latency_p95_ms']):>6}")
    if r["issues"]:
        print("\nRefused / failed:", ", ".join(f"{i['status']} {i['kind'] or '?'} x{i['count']}" for i in r["issues"]))


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m src.eval")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p = sub.add_parser("show")
    p.add_argument("ids", nargs="+")
    p = sub.add_parser("retrieval")
    p.add_argument("--label")
    p.add_argument("--depth", type=int, default=retrieval.DEPTH)
    p.add_argument("--only", nargs="*", help="question ids (default: all)")
    p.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="retrieval setting overrides")
    p.add_argument("--golden", type=Path, default=golden.GOLDEN_PATH, help="question file")
    p = sub.add_parser("generation")
    p.add_argument("--label")
    p.add_argument("--judge-model", help="default: LLM_MODEL")
    p.add_argument("--pause", type=float, default=4.0, help="seconds between LLM calls (free-tier rate limits)")
    p.add_argument("--resume", type=Path, help="run directory to continue")
    p.add_argument("--mode", choices=["simple", "agent", "auto"], help="QA path (default: QA_MODE)")
    p.add_argument("--max-retry-wait", type=float, default=90.0,
                   help="seconds to sit out a rate limit before failing a question (batch runs can wait longer "
                        "than an API request; free tier asks for up to ~60 s)")
    p.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="retrieval setting overrides")
    p.add_argument("--only", nargs="*", help="question ids (default: all)")
    p.add_argument("--golden", type=Path, default=golden.GOLDEN_PATH,
                   help="question file (a --resume run keeps the one it started with)")
    p = sub.add_parser("combine")
    p.add_argument("--simple", required=True, help="run directory name of a --mode simple run")
    p.add_argument("--agent", required=True, help="run directory name of a --mode agent run")
    p.add_argument("--policy", required=True, choices=generation.POLICIES)
    p.add_argument("--label")
    sub.add_parser("report")
    sub.add_parser("feedback")
    p = sub.add_parser("regress")
    p.add_argument("kind", choices=list(regress.METRICS))
    p.add_argument("--baseline", help="run directory name (default: the previous run on the same golden set)")
    p.add_argument("--tolerance", type=float, default=0.02, help="largest allowed drop, absolute")
    p = sub.add_parser("usage")
    p.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    if args.cmd == "regress":
        lines, regressed = regress.check(args.kind, args.baseline, args.tolerance)
        print("\n".join(lines))
        raise SystemExit(1 if regressed else 0)

    if args.cmd == "combine":
        r = generation.combine(args.simple, args.agent, args.policy, args.label)
        i = r["summary"]["in_scope"]
        print(f"[{args.policy}] score={i['score']} correct={i['correct']} false_refusal={i['false_refusal']} "
              f"oos_handled={r['summary']['out_of_scope']['handled']} "
              f"llm_calls={r['summary']['cost']['llm_calls_avg']} agent_share={r['summary']['cost']['agent_share']}")
        print(f"run: {r['path']}")
        print(f"report: {report.build()}")
        return
    if args.cmd == "report":
        print(f"report: {report.build()}")
        return
    with SessionLocal() as db:
        if args.cmd == "feedback":
            print(feedback.export(db))
            return
        if args.cmd == "usage":
            print_usage(usage.report(db, args.days))
            return
        if args.cmd == "check":
            questions, _ = golden.load()
            problems = golden.check(db, questions)
            print("\n".join(problems) or f"{len(questions)} questions, all evidence locations valid")
            raise SystemExit(1 if problems else 0)
        if args.cmd == "show":
            questions = {q.id: q for q in golden.load()[0]}
            for qid in args.ids:
                q = questions[qid]
                print(f"== {q.id} [{q.category}] {q.question}\n-> {q.answer}")
                for s in q.spans:
                    print(f"  -- {s}")
                    for seq, t in golden.evidence_text(db, s):
                        print(f"  {seq}: {t}")
                print()
            return
        if args.cmd == "retrieval":
            cfg = default_config().with_overrides(args.set)
            r = retrieval.run(db, args.label, cfg, args.depth, set(args.only or []), args.golden)
            # Only dev is printed: decisions are made on dev, test is read in the report at the end
            s = r["summary"]["dev"]["overall"]
            print(f"[{cfg.label()}] dev n={s['n']} hit@6={s['hit@6']:.3f} hit@20={s['hit@20']:.3f} "
                  f"mrr={s['mrr']:.3f} span_recall@20={s['span_recall@20']:.3f} "
                  f"latency={r['summary']['latency_ms_avg']}ms fingerprint={r['fingerprint']}")
        else:
            cfg = default_config().with_overrides(args.set)
            config.LLM_MAX_RETRY_WAIT_SECONDS = args.max_retry_wait
            r = generation.run(db, args.label, args.judge_model, args.pause, cfg,
                               args.mode or config.QA_MODE, args.resume, set(args.only or []), args.golden)
            i, o = r["summary"]["in_scope"], r["summary"]["out_of_scope"]
            print(f"score={i['score']} correct={i['correct']} false_refusal={i['false_refusal']} "
                  f"oos_handled={o['handled']} errors={r['summary']['errors']}")
        print(f"run: {r['path']}")
    print(f"report: {report.build()}")


if __name__ == "__main__":
    main()
