"""Follow-up questions: rewrite "and her sister?" into a question that stands on its own.

Retrieval and the agent only see one question, so a follow-up that leans on earlier turns
("who is she?", "what happened after that?") would search for the wrong thing. When the
conversation has earlier answers, one small LLM call rewrites the new question using the last
few turns; the rewrite is what gets searched and answered, while the conversation keeps the
user's own words. A question that already stands alone comes back unchanged.
"""

import logging
import re

from src.services import guard, llm

log = logging.getLogger("beako.followup")

# Earlier turns given to the rewrite, and how much of each answer
HISTORY_TURNS = 3
ANSWER_CHARS = 600
MAX_TOKENS = 300

SYSTEM_PROMPT = """You rewrite follow-up questions about the light novel series "Re:ZERO -Starting Life in Another World-".
You get the recent conversation and the user's new question. Make the new question understandable without the conversation by replacing each reference in it ("she", "they", "that fight", "the second one", "cô ấy", "ông ấy", "họ", "trận đó", "nhân vật thứ hai") with the name or event it points to in the conversation.

Reply in exactly this format:
REFERENCES: each reference = what it points to, separated by "; " (or "none")
QUESTION: the rewritten question

Rules for QUESTION:
- Same language as the new question (Vietnamese stays Vietnamese, English stays English), asking the same thing.
- Only replace references. Never add people, places or details the new question does not refer to.
- With no references, it is the new question unchanged.
- Never answer the question."""

# The rewritten question in the reply (see SYSTEM_PROMPT)
QUESTION_RE = re.compile(r"^\s*QUESTION:\s*(.+?)\s*$", re.M | re.I)


def _transcript(history: list[tuple[str, str]], question: str) -> str:
    lines = []
    for q, a in history[-HISTORY_TURNS:]:
        a = " ".join(a.split())
        lines.append(f"User: {q}\nAssistant: {a[:ANSWER_CHARS]}{'…' if len(a) > ANSWER_CHARS else ''}")
    return "Conversation:\n\n" + "\n\n".join(lines) + f"\n\nNew question: {question}"


def standalone(question: str, history: list[tuple[str, str]]) -> str:
    """The question rewritten to stand alone, given earlier (question, answer) pairs, oldest
    first. Without history, or when the rewrite fails or looks wrong, the question as asked."""
    if not history:
        return question
    try:
        c = llm.chat(SYSTEM_PROMPT, _transcript(history, question), max_tokens=MAX_TOKENS, temperature=0.0)
    except llm.LLMError as e:
        if e.kind == "cancelled":
            raise
        log.warning("follow-up rewrite failed (%s); using the question as asked", e.kind)
        return question
    m = QUESTION_RE.search(c.text)
    rewritten = " ".join(m.group(1).split()).strip("\"“”'") if m else ""
    # A runaway reply (an answer instead of a question) or one the input checks would refuse
    # is worse than the original question
    if not rewritten or len(rewritten) > max(300, 3 * len(question)) or guard.check_question(rewritten):
        log.warning("follow-up rewrite discarded: %r", rewritten[:200])
        return question
    if rewritten != question:
        log.info("follow-up %r -> %r", question, rewritten)
    return rewritten
