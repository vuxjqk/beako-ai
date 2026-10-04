"""Retrieval evaluation: no LLM, no quota, so it can run after every change.

For each answerable question, take the top `depth` chunks from the same retrieve() the QA
endpoint uses and find where the evidence shows up:
- hit@k: some chunk in the top k overlaps an evidence span
- span recall@k: share of the question's evidence spans covered in the top k (multi-part
  questions need all of them)
- reciprocal rank: 1 / rank of the first relevant chunk (0 if none within depth)
"""

import hashlib
import json
import time

from sqlalchemy.orm import Session

from src.eval import golden, runs
from src.services.qa import get_embedder, retrieve

KS = (6, 20)
DEPTH = 50


def evaluate_question(db: Session, q: golden.Question, depth: int) -> dict:
    t0 = time.perf_counter()
    hits = retrieve(db, q.question, depth)
    ms = (time.perf_counter() - t0) * 1000
    refs = golden.chunk_refs(db, [h.row.id for h in hits])
    ranked = [h.row.id for h in hits]
    span_rank: list[int | None] = [None] * len(q.spans)  # first rank covering each span
    relevant_ranks = []
    for rank, cid in enumerate(ranked, 1):
        matched = golden.matching_spans(refs[cid], q.spans)
        if matched:
            relevant_ranks.append(rank)
        for i in matched:
            if span_rank[i] is None:
                span_rank[i] = rank
    first = relevant_ranks[0] if relevant_ranks else None
    out = {
        "id": q.id,
        "category": q.category,
        "first_rank": first,
        "rr": 1 / first if first else 0.0,
        "span_ranks": span_rank,
        "relevant_ranks": relevant_ranks[:10],
        "ranked_chunk_ids": ranked,
        "top_scores": [round(float(h.score), 4) for h in hits[:3]],
        "latency_ms": round(ms, 1),
    }
    for k in KS:
        out[f"hit@{k}"] = bool(first and first <= k)
        out[f"span_recall@{k}"] = sum(1 for r in span_rank if r and r <= k) / len(span_rank)
    return out


def aggregate(results: list[dict]) -> dict:
    def agg(rows: list[dict]) -> dict:
        if not rows:
            return {"n": 0}
        n = len(rows)
        m = {"n": n, "mrr": round(sum(r["rr"] for r in rows) / n, 4)}
        for k in KS:
            m[f"hit@{k}"] = round(sum(r[f"hit@{k}"] for r in rows) / n, 4)
            m[f"span_recall@{k}"] = round(sum(r[f"span_recall@{k}"] for r in rows) / n, 4)
        m["all_spans@20"] = round(sum(r["span_recall@20"] == 1 for r in rows) / n, 4)
        return m

    out = {"overall": agg(results)}
    for cat in golden.CATEGORIES[:-1]:
        out[cat] = agg([r for r in results if r["category"] == cat])
    out["latency_ms_avg"] = round(sum(r["latency_ms"] for r in results) / len(results), 1)
    return out


def fingerprint(results: list[dict]) -> str:
    """Hash of every ranked list: equal fingerprints mean identical retrieval output."""
    payload = json.dumps([(r["id"], r["ranked_chunk_ids"]) for r in results])
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def run(db: Session, label: str | None, depth: int = DEPTH, only: set[str] | None = None) -> dict:
    questions, sha = golden.load()
    targets = [q for q in questions if q.in_scope and (not only or q.id in only)]
    get_embedder()  # load the model before timing anything
    run_dir = runs.new_run_dir("retrieval", label)
    record = runs.header("retrieval", label, sha, len(targets))
    record["config"] = runs.retrieval_config(db, depth)
    results = []
    for q in targets:
        results.append(evaluate_question(db, q, depth))
        db.rollback()  # retrieve() sets a transaction-local ef_search; start each query clean
    record["summary"] = aggregate(results)
    record["fingerprint"] = fingerprint(results)
    record["results"] = results
    record["path"] = str(runs.save(run_dir, record))
    return record
