"""Compare the latest evaluation run with a baseline and fail when quality dropped.

Run it after every change (retrieval needs no LLM; generation only after a generation run):

    python -m src.eval retrieval --label <change> && python -m src.eval regress retrieval

The baseline is the run before the latest one on the same golden set, or --baseline DIR.
Exit status 1 when any metric got worse by more than --tolerance (absolute, e.g. 0.02 = 2 points).
"""

from src.eval import runs

# (path in the summary, higher is better)
METRICS = {
    "retrieval": [
        (("dev", "overall", "hit@6"), True),
        (("dev", "overall", "hit@20"), True),
        (("dev", "overall", "mrr"), True),
        (("dev", "overall", "span_recall@20"), True),
    ],
    "generation": [
        (("in_scope", "score"), True),
        (("in_scope", "correct"), True),
        (("in_scope", "false_refusal"), False),
        (("in_scope", "incorrect"), False),
        (("out_of_scope", "handled"), True),
        (("faithfulness", "supported"), True),
    ],
}


def _get(summary: dict, path: tuple):
    for key in path:
        summary = (summary or {}).get(key)
    return summary


def check(kind: str, baseline: str | None, tolerance: float) -> tuple[list[str], bool]:
    """Report lines, and whether quality regressed."""
    candidates = [r for r in runs.load_all(kind) if not r.get("simulated")]
    if len(candidates) < (1 if baseline else 2):
        return [f"need at least two {kind} runs to compare"], False
    latest = candidates[-1]
    if baseline:
        base = next((r for r in candidates if r["dir"] == baseline), None)
        if base is None:
            return [f"no {kind} run named {baseline}"], False
    else:
        same_set = [r for r in candidates[:-1] if r["golden_set"]["sha256"] == latest["golden_set"]["sha256"]]
        if not same_set:
            return ["no earlier run on the same golden set"], False
        base = same_set[-1]
    lines = [f"{kind}: {latest['dir']} vs baseline {base['dir']} (tolerance {tolerance:g})"]
    regressed = False
    for path, higher_better in METRICS[kind]:
        new, old = _get(latest["summary"], path), _get(base["summary"], path)
        if new is None or old is None:
            continue
        delta = new - old
        worse = -delta if higher_better else delta
        flag = "REGRESSED" if worse > tolerance else ""
        regressed |= bool(flag)
        lines.append(f"  {'.'.join(path):28} {old:.4f} -> {new:.4f} ({delta:+.4f}) {flag}")
    if kind == "generation" and latest["summary"].get("errors"):
        lines.append(f"  note: {latest['summary']['errors']} questions failed in the latest run")
    return lines, regressed
