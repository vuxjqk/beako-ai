"""The question log (qa_requests): completing a row when a question ends, and the daily usage
report built from it (questions, cost, "not found" rate, 👎 rate)."""

import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.models import QaRequest
from src.services import llm
from src.services.guard import DAY_START
from src.services.qa import Answer

log = logging.getLogger("beako.qa.usage")


def cost_usd(prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Estimated price of LLM_MODEL calls, from LLM_PRICE_*_PER_MTOK."""
    usd = (prompt_tokens * config.LLM_PRICE_INPUT_PER_MTOK
           + completion_tokens * config.LLM_PRICE_OUTPUT_PER_MTOK) / 1_000_000
    return Decimal(str(round(usd, 6)))


def finish(db: Session, request_id: uuid.UUID, status: str, *, meter: llm.Meter | None = None,
           latency_ms: int | None = None, answer: Answer | None = None, message_id: uuid.UUID | None = None,
           error_kind: str | None = None, error: str | None = None, output_blocked: bool = False) -> None:
    """Complete a request admitted by guard.admit(): answered | not_found | error | rejected.
    meter holds every LLM call the question made, even when it failed halfway."""
    row = db.get(QaRequest, request_id)
    if row is None:
        return
    m = meter or llm.Meter()
    row.status = status
    row.finished_at = datetime.now(timezone.utc)
    row.latency_ms = latency_ms
    row.message_id = message_id
    row.error_kind, row.error = error_kind, error[:2000] if error else None
    row.llm_calls = m.calls
    row.prompt_tokens, row.completion_tokens = m.prompt_tokens, m.completion_tokens
    row.cost_usd = cost_usd(m.prompt_tokens, m.completion_tokens)
    row.model = m.model or (answer.model if answer else None)
    row.output_blocked = output_blocked
    if answer is not None:
        row.mode, row.found = answer.mode, answer.found
        row.tools = [t["tool"] for t in answer.trace if "tool" in t] or None
    db.commit()
    # One line per question for the container logs (the table is the source for reports)
    log.info("qa_request %s", json.dumps({
        "id": str(row.id), "user": str(row.user_id), "status": status, "error_kind": error_kind,
        "mode": row.mode, "degraded": row.degraded, "model": row.model, "steps": row.llm_calls,
        "tools": row.tools, "prompt_tokens": row.prompt_tokens, "completion_tokens": row.completion_tokens,
        "cost_usd": float(row.cost_usd), "latency_ms": latency_ms, "found": row.found,
        "retry_wait_s": round(m.retry_wait_s, 1), "output_blocked": output_blocked,
    }))


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def report(db: Session, days: int = 14) -> dict:
    """Per-day usage for the last `days` days (today included), today's budget state, the
    heaviest users today and why questions were refused or failed."""
    tz = {"tz": config.QA_TIMEZONE, "days": days}
    since = f"({DAY_START} - make_interval(days => :days - 1))"
    rows = db.execute(text(f"""
        SELECT (r.created_at AT TIME ZONE :tz)::date AS day,
               count(*) FILTER (WHERE r.status <> 'rejected') AS questions,
               count(*) FILTER (WHERE r.status = 'answered') AS answered,
               count(*) FILTER (WHERE r.status = 'not_found') AS not_found,
               count(*) FILTER (WHERE r.status = 'error') AS errors,
               count(*) FILTER (WHERE r.status = 'rejected') AS rejected,
               count(DISTINCT r.user_id) FILTER (WHERE r.status <> 'rejected') AS users,
               count(*) FILTER (WHERE r.mode LIKE '%agent%') AS agent,
               count(*) FILTER (WHERE r.degraded) AS degraded,
               coalesce(sum(r.llm_calls), 0) AS llm_calls,
               coalesce(sum(r.prompt_tokens), 0) AS prompt_tokens,
               coalesce(sum(r.completion_tokens), 0) AS completion_tokens,
               coalesce(sum(r.cost_usd), 0) AS cost_usd,
               round(avg(r.latency_ms) FILTER (WHERE r.status IN ('answered', 'not_found'))) AS latency_avg_ms,
               round(percentile_cont(0.95) WITHIN GROUP (ORDER BY r.latency_ms)
                     FILTER (WHERE r.status IN ('answered', 'not_found'))) AS latency_p95_ms,
               count(*) FILTER (WHERE m.feedback = 1) AS thumbs_up,
               count(*) FILTER (WHERE m.feedback = -1) AS thumbs_down
        FROM qa_requests r LEFT JOIN qa_messages m ON m.id = r.message_id
        WHERE r.created_at >= {since}
        GROUP BY 1 ORDER BY 1 DESC
    """), tz).mappings().all()
    out_days = []
    for r in rows:
        d = dict(r)
        d["day"] = r["day"].isoformat()
        d["cost_usd"] = float(r["cost_usd"])
        for k in ("latency_avg_ms", "latency_p95_ms"):
            d[k] = int(r[k]) if r[k] is not None else None
        answered = r["answered"] + r["not_found"]
        rated = r["thumbs_up"] + r["thumbs_down"]
        d["not_found_rate"] = _rate(r["not_found"], answered)
        d["error_rate"] = _rate(r["errors"], r["questions"])
        d["thumbs_down_rate"] = _rate(r["thumbs_down"], rated)
        d["rated_share"] = _rate(rated, answered)
        d["cost_per_question_usd"] = round(d["cost_usd"] / r["questions"], 6) if r["questions"] else None
        out_days.append(d)

    t = db.execute(text(f"SELECT (now() AT TIME ZONE :tz)::date AS date, coalesce(sum(cost_usd), 0) AS spent "
                        f"FROM qa_requests WHERE created_at >= {DAY_START}"), tz).one()
    spent = float(t.spent)
    budget = config.QA_DAILY_BUDGET_USD
    state = "normal"
    if budget > 0 and spent >= budget:
        state = "stopped"
    elif budget > 0 and spent >= budget * config.QA_DEGRADE_AT:
        state = "degraded"

    top_users = db.execute(text(f"""
        SELECT r.user_id, u.email, u.full_name, count(*) FILTER (WHERE r.status <> 'rejected') AS questions,
               count(*) FILTER (WHERE r.status = 'rejected') AS rejected,
               coalesce(sum(r.prompt_tokens + r.completion_tokens), 0) AS tokens,
               coalesce(sum(r.cost_usd), 0) AS cost_usd
        FROM qa_requests r LEFT JOIN users u ON u.id = r.user_id
        WHERE r.created_at >= {DAY_START}
        GROUP BY 1, 2, 3 ORDER BY cost_usd DESC, questions DESC LIMIT 10
    """), tz).mappings().all()
    issues = db.execute(text(f"""
        SELECT status, coalesce(CASE WHEN output_blocked THEN 'output_blocked' END, error_kind, '') AS kind,
               count(*) AS count
        FROM qa_requests WHERE created_at >= {since} AND (status IN ('error', 'rejected') OR output_blocked)
        GROUP BY 1, 2 ORDER BY 3 DESC
    """), tz).mappings().all()

    return {
        "timezone": config.QA_TIMEZONE,
        "days": out_days,
        "today": {
            "date": t.date.isoformat(),
            "spent_usd": round(spent, 6),
            "budget_usd": budget or None,
            "degrade_at_usd": round(budget * config.QA_DEGRADE_AT, 4) if budget else None,
            "state": state,
        },
        "limits": {
            "user_per_minute": config.QA_USER_PER_MINUTE,
            "user_per_day": config.QA_USER_PER_DAY,
            "user_daily_tokens": config.QA_USER_DAILY_TOKENS,
            "user_max_concurrent": config.QA_USER_MAX_CONCURRENT,
            "price_input_per_mtok": config.LLM_PRICE_INPUT_PER_MTOK,
            "price_output_per_mtok": config.LLM_PRICE_OUTPUT_PER_MTOK,
            "model": config.LLM_MODEL,
        },
        "top_users_today": [{**dict(u), "user_id": str(u["user_id"]) if u["user_id"] else None,
                             "cost_usd": float(u["cost_usd"])} for u in top_users],
        "issues": [{**dict(i), "kind": i["kind"] or None} for i in issues],
    }
