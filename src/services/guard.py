"""Guardrails in front of /qa: what a question may contain, how often and how much a user may
ask, and the system-wide daily budget.

admit() runs before any LLM call. It refuses (and logs) questions that look like prompt
injection, users over their per-minute / per-day / token limits or with a question already
running, and everyone once the day's budget is spent; near the budget it switches the agent
off. An admitted question gets a "running" row in qa_requests that usage.finish() completes.
The checks and the insert run under a per-user advisory lock, so parallel requests from one
user cannot all slip past the limits.
"""

import logging
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.models import QaRequest, User, UserRole
from src.services import agent, qa

log = logging.getLogger("beako.guard")

# A "running" row older than this belongs to a crashed worker and no longer blocks the user
STALE_RUNNING = "10 minutes"
# How long a new question waits for the user's previous one to end before "busy": covers a
# reload or a reopened tab, where the old stream is still being torn down
BUSY_GRACE_SECONDS = 3.0

# Start of today in QA_TIMEZONE, as a timestamptz
DAY_START = "(date_trunc('day', now() AT TIME ZONE :tz) AT TIME ZONE :tz)"


class Refused(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


@dataclass
class Admission:
    request_id: uuid.UUID
    mode: str | None  # "simple" when the budget is nearly spent; None = QA_MODE
    token_budget: int | None  # tokens this question may still spend (the user's daily remainder)


# --- input ------------------------------------------------------------------------------------

def _fold(s: str) -> str:
    """Lowercase without diacritics, so one pattern covers "bỏ qua" and "bo qua"."""
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c))


# Basic prompt-injection phrasings, English and Vietnamese (matched on folded text). Kept
# narrow on purpose: questions about the story ("why did Subaru ignore the rules of the
# Sanctuary?") must not trip them, so each needs an instruction-like target
_INSTRUCTIONS = r"(instructions?|prompts?|rules|guidelines|directions|constraints|guardrails)"
_HUONG_DAN = r"(quy tac|quy dinh|chi dan|huong dan|chi thi|cau lenh|prompt|loi nhac)"
INJECTION_PATTERNS = [re.compile(p) for p in (
    rf"\b(ignore|disregard|forget|override|bypass|skip)\b[^.?!]{{0,30}}\b(previous|prior|above|earlier|preceding"
    rf"|your|system|initial|original|these|those)\b[^.?!]{{0,20}}\b{_INSTRUCTIONS}\b",
    r"\b(ignore|disregard|forget|override|bypass)\s+(all\s+)?(instructions?|prompts?|guardrails)\b",
    r"\b(system|developer|hidden|initial|original|secret)\s+(prompt|message|instructions?)\b",
    rf"\b(reveal|show|print|repeat|output|leak|display|dump|tell me|what (is|are|were))\b[^.?!]{{0,30}}"
    rf"\b(your\s+(system\s+)?{_INSTRUCTIONS}|the\s+(system\s+)?prompt)\b",
    r"\b(jailbreak|jailbroken|developer mode|do anything now)\b",
    r"\byou are (now|no longer)\b|\bfrom now on,? you\b",
    r"<\|?(im_start|im_end|system)\|?>|\[/?inst\]|(^|\n)\s*(system|assistant|developer)\s*:",
    rf"\b(bo qua|phot lo|lo di|quen( di| het)?|khong (can )?(tuan theo|tuan thu|lam theo))\s+"
    rf"(moi|tat ca|het|cac|nhung)\s+(cac\s+)?{_HUONG_DAN}",
    rf"\b(bo qua|phot lo|lo di|quen( di| het)?|khong (can )?(tuan theo|tuan thu|lam theo))\s+{_HUONG_DAN}"
    rf"\s+(truoc( do)?|o tren|ben tren|cua ban|he thong|ban dau|da cho|nay)\b",
    rf"\b{_HUONG_DAN}\s+(he thong|goc|an|ban dau)\b",
    rf"\b(tiet lo|hien thi|in ra|lap lai|nhac lai|cho (toi|minh|tao) (xem|biet))\b[^.?!]{{0,30}}{_HUONG_DAN}"
    rf"\s+cua (ban|may|mi)\b",
    r"\b(che do nha phat trien|che do developer)\b",
    r"\b(tu (bay )?gio|bay gio)\b[^.?!]{0,10}\bban (la|se la|hay dong vai)\b",
)]


def check_question(question: str) -> str | None:
    """Why this question is refused, or None. Length is limited by the request schema."""
    if any(unicodedata.category(c) == "Cc" and c not in "\n\t" for c in question):
        return "control characters"
    folded = _fold(question)
    for p in INJECTION_PATTERNS:
        if m := p.search(folded):
            return f"prompt injection ({m.group(0)[:60]!r})"
    return None


# --- output -----------------------------------------------------------------------------------

REFUSAL = "Sorry, I can only answer questions about the Re:ZERO light novels."
SHINGLE = 8


def _words(s: str) -> list[str]:
    return re.sub(r"[^\w]+", " ", s.lower()).split()


def _prompt_shingles() -> set[tuple[str, ...]]:
    shingles = set()
    for prompt in (qa.SYSTEM_PROMPT, agent.SYSTEM_PROMPT):
        # Phrases an honest answer may well repeat are not evidence of a leak (an answer listing
        # the sins with their English names can match the glossary)
        for common in ("Re:ZERO -Starting Life in Another World-", qa.NOT_FOUND, agent.GLOSSARY_TEXT):
            prompt = prompt.replace(common, " | ")
        for part in prompt.split("|"):
            w = _words(part)
            shingles.update(tuple(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1))
    return shingles


_SHINGLES = _prompt_shingles()


def leaks_prompt(answer: str) -> bool:
    """Whether the answer copies the system prompt (two runs of 8 words from it)."""
    w = _words(answer)
    hits = {tuple(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)} & _SHINGLES
    return len(hits) >= 2


# --- limits -----------------------------------------------------------------------------------

def _lock_key(user_id: uuid.UUID) -> int:
    return int.from_bytes(user_id.bytes[:8], "big", signed=True)


def _refuse(db: Session, user: User, question: str, status: int, code: str, message: str,
            retry_after: int | None = None, detail: str | None = None) -> Refused:
    db.rollback()
    db.add(QaRequest(user_id=user.id, status="rejected", error_kind=code, error=detail,
                     question_chars=len(question), finished_at=datetime.now(timezone.utc)))
    db.commit()
    log.warning("qa refused user=%s code=%s %s", user.id, code, detail or "")
    return Refused(status, code, message, retry_after)


def _wait_for_slot(db: Session, user: User) -> None:
    """Give a just-abandoned question (closed tab) a moment to be cancelled; the limit itself
    is still checked under the lock in admit()."""
    deadline = time.monotonic() + BUSY_GRACE_SECONDS
    while time.monotonic() < deadline:
        running = db.execute(text(f"""
            SELECT count(*) FROM qa_requests WHERE user_id = :u AND status = 'running'
              AND created_at > now() - interval '{STALE_RUNNING}'
        """), {"u": user.id}).scalar()
        db.rollback()  # each poll sees the latest commits
        if running < config.QA_USER_MAX_CONCURRENT:
            return
        time.sleep(0.25)


def admit(db: Session, user: User, question: str) -> Admission:
    """Admit a question or raise Refused. On success a "running" qa_requests row is committed."""
    if reason := check_question(question):
        raise _refuse(db, user, question, 400, "input_rejected",
                      "This question looks like an attempt to change the assistant's instructions", detail=reason)

    if user.role != UserRole.ADMIN:
        _wait_for_slot(db, user)
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _lock_key(user.id)})
    s = db.execute(text(f"""
        SELECT coalesce((SELECT sum(cost_usd) FROM qa_requests WHERE created_at >= {DAY_START}), 0) AS spent,
               ceil(extract(epoch FROM {DAY_START} + interval '1 day' - now()))::int AS to_midnight
    """), {"tz": config.QA_TIMEZONE}).one()
    budget = config.QA_DAILY_BUDGET_USD
    if budget > 0 and float(s.spent) >= budget:
        raise _refuse(db, user, question, 503, "budget",
                      "The assistant has reached today's usage limit; please come back tomorrow",
                      s.to_midnight, f"spent ${float(s.spent):.4f} of ${budget:g}")
    degraded = budget > 0 and float(s.spent) >= budget * config.QA_DEGRADE_AT

    token_budget = None
    if user.role != UserRole.ADMIN:
        u = db.execute(text(f"""
            SELECT count(*) FILTER (WHERE status = 'running'
                                    AND created_at > now() - interval '{STALE_RUNNING}') AS running,
                   count(*) FILTER (WHERE status <> 'rejected'
                                    AND created_at > now() - interval '1 minute') AS last_minute,
                   ceil(extract(epoch FROM min(created_at) FILTER (
                       WHERE status <> 'rejected' AND created_at > now() - interval '1 minute')
                       + interval '1 minute' - now()))::int AS minute_frees_in,
                   count(*) FILTER (WHERE status <> 'rejected' AND created_at >= {DAY_START}) AS today,
                   coalesce(sum(prompt_tokens + completion_tokens)
                            FILTER (WHERE created_at >= {DAY_START}), 0) AS tokens_today
            FROM qa_requests
            WHERE user_id = :u AND created_at >= least({DAY_START}, now() - interval '{STALE_RUNNING}')
        """), {"u": user.id, "tz": config.QA_TIMEZONE}).one()
        if u.running >= config.QA_USER_MAX_CONCURRENT:
            raise _refuse(db, user, question, 429, "busy",
                          "Your previous question is still being answered; wait for it to finish", 5)
        if u.last_minute >= config.QA_USER_PER_MINUTE:
            raise _refuse(db, user, question, 429, "rate_limited",
                          "You are asking too fast; wait a moment", max(1, u.minute_frees_in or 60),
                          f"{u.last_minute} questions in the last minute")
        if u.today >= config.QA_USER_PER_DAY:
            raise _refuse(db, user, question, 429, "user_quota",
                          "You have used today's question allowance; it resets tomorrow", s.to_midnight,
                          f"{u.today} questions today")
        if u.tokens_today >= config.QA_USER_DAILY_TOKENS:
            raise _refuse(db, user, question, 429, "user_quota",
                          "You have used today's question allowance; it resets tomorrow", s.to_midnight,
                          f"{u.tokens_today} tokens today")
        token_budget = config.QA_USER_DAILY_TOKENS - u.tokens_today

    row = QaRequest(user_id=user.id, status="running", question_chars=len(question), degraded=degraded)
    db.add(row)
    db.commit()  # also releases the lock
    if degraded:
        log.warning("qa budget %.4f of $%g spent: agent switched off", float(s.spent), budget)
    return Admission(row.id, "simple" if degraded else None, token_budget)
