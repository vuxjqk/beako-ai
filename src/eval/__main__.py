"""Evaluation CLI (run inside the backend container: docker compose exec backend python -m src.eval ...).

    check                       validate the golden set's evidence locations against the database
    show ID [ID ...]            print questions with their evidence text, for reading by a person
    retrieval [--label L]       retrieval metrics only (no LLM; run after every change)
                                --set key=value overrides a RetrievalConfig field, e.g.
                                --set method=hybrid scope=true
    generation [--label L]      full QA + LLM judge (uses quota; --resume DIR continues a stopped run)
    report                      rebuild data/reports/eval_report.md from all saved runs

retrieval and generation also rebuild the report when they finish.
"""

import argparse
from pathlib import Path

from src.eval import generation, golden, report, retrieval
from src.models import SessionLocal
from src.services.retrieval import default_config


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
    p = sub.add_parser("generation")
    p.add_argument("--label")
    p.add_argument("--judge-model", help="default: LLM_MODEL")
    p.add_argument("--pause", type=float, default=4.0, help="seconds between LLM calls (free-tier rate limits)")
    p.add_argument("--resume", type=Path, help="run directory to continue")
    p.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="retrieval setting overrides")
    p.add_argument("--only", nargs="*", help="question ids (default: all)")
    sub.add_parser("report")
    args = ap.parse_args()

    if args.cmd == "report":
        print(f"report: {report.build()}")
        return
    with SessionLocal() as db:
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
            r = retrieval.run(db, args.label, cfg, args.depth, set(args.only or []))
            # Only dev is printed: decisions are made on dev, test is read in the report at the end
            s = r["summary"]["dev"]["overall"]
            print(f"[{cfg.label()}] dev n={s['n']} hit@6={s['hit@6']:.3f} hit@20={s['hit@20']:.3f} "
                  f"mrr={s['mrr']:.3f} span_recall@20={s['span_recall@20']:.3f} "
                  f"latency={r['summary']['latency_ms_avg']}ms fingerprint={r['fingerprint']}")
        else:
            cfg = default_config().with_overrides(args.set)
            r = generation.run(db, args.label, args.judge_model, args.pause, cfg, args.resume,
                               set(args.only or []))
            i, o = r["summary"]["in_scope"], r["summary"]["out_of_scope"]
            print(f"score={i['score']} correct={i['correct']} false_refusal={i['false_refusal']} "
                  f"oos_handled={o['handled']} errors={r['summary']['errors']}")
        print(f"run: {r['path']}")
    print(f"report: {report.build()}")


if __name__ == "__main__":
    main()
