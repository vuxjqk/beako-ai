"""Tool-using agent for questions one search cannot answer (summaries, comparisons, multi-part).

The LLM gets four tools over the same retrieval the simple path uses: search (optionally
restricted to volumes/a chapter), read_around (neighbouring chunks of a result),
list_chapters (a volume's table of contents) and read_chapter (a chapter, page by page).
It loops: think, call tools, read results, repeat, then answer citing the passages it was
shown. The loop is bounded by AGENT_MAX_STEPS model calls and AGENT_MAX_CONTEXT_TOKENS; when
either runs out the model must answer with what it has. Every tool call is traced.
"""

import json
import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.ingest.search import _COLUMNS, _JOINS, Hit
from src.services import llm, retrieval
from src.services.retrieval import RetrievalConfig, Scope

log = logging.getLogger("beako.agent")

NOT_FOUND = "Not found in the provided passages."
SEARCH_K = 5
PAGE_CHUNKS = 5

SYSTEM_PROMPT = f"""You answer questions about the light novel series "Re:ZERO -Starting Life in Another World-" (main Volumes 1–28 and Short Story Collections 1–4), using ONLY passages you retrieve with your tools. The novel text is in English.

Where things are (for navigating only, not as facts for your answer): Arc 1 = Volume 1 (royal capital, loot house); Arc 2 = Volumes 2–3 (Roswaal Manor); Arc 3 = Volumes 4–9 (royal selection, White Whale, Petelgeuse/Sloth); Arc 4 = Volumes 10–15 (the Sanctuary, Echidna's trials); Arc 5 = Volumes 16–20 (Pristella, the water city); Arc 6 = Volumes 21–25 (Pleiades Watchtower); Arc 7 = Volumes 26–28 (Volakian Empire).

How to work:
1. Work out which separate facts the question needs. Search for each one separately with a short, specific ENGLISH query built from names and key terms (translate the question if it is not in English). Do not search the whole question at once when it has several parts.
2. When the question names volumes or a chapter, or you know which arc it concerns, pass volumes (and chapter) to search. For comparisons, search each side separately.
3. If a passage is relevant but cut off, use read_around on it. For a summary of a volume or arc, call list_chapters, then read_chapter on the chapters that matter most (usually the climax and the ending), and search for the key events.
4. You have at most {config.AGENT_MAX_STEPS} rounds of tool calls; call several tools in one round when you can. Stop as soon as you have enough.

Final answer:
- Use only information stated in the passages you were shown. Cite the passage number for every claim, e.g. [3] or [2][5].
- If the passages do not contain the answer, reply with exactly: {NOT_FOUND}
- If the question assumes something the passages show to be false, say so instead of answering it.
- Answer in the language of the question, concisely: at most about 150 words, or 300 for a summary."""

TOOLS = [
    {"type": "function", "function": {
        "name": "search",
        "description": "Search the novels for passages relevant to a query. Returns the best matching passages, "
                       "each with a number to cite. Use one search per fact you need.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Short English search query with names and key terms."},
            "volumes": {"type": "array", "items": {"type": "integer"},
                        "description": "Only search these main volumes (1-28)."},
            "chapter": {"type": "integer", "description": "Only this chapter number (needs exactly one volume)."},
            "short_story_collection": {"type": "integer",
                                       "description": "Search this Short Story Collection (1-4) instead of main volumes."},
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "read_around",
        "description": "Read the text just before and/or after a passage you were shown, e.g. when it is cut off.",
        "parameters": {"type": "object", "properties": {
            "passage": {"type": "integer", "description": "The passage number."},
            "direction": {"type": "string", "enum": ["before", "after", "both"]},
        }, "required": ["passage"]}}},
    {"type": "function", "function": {
        "name": "list_chapters",
        "description": "Table of contents of a volume: chapter labels, titles and how many pages read_chapter has.",
        "parameters": {"type": "object", "properties": {
            "volume": {"type": "integer", "description": "Main volume number (1-28)."},
            "short_story_collection": {"type": "integer", "description": "Or a Short Story Collection (1-4)."},
        }}}},
    {"type": "function", "function": {
        "name": "read_chapter",
        "description": f"Read a chapter in order, {PAGE_CHUNKS} passages per page. Use list_chapters first to see "
                       "the chapters. Good for summaries and for following events in sequence.",
        "parameters": {"type": "object", "properties": {
            "volume": {"type": "integer"},
            "short_story_collection": {"type": "integer"},
            "chapter": {"type": "string", "description": "Chapter label as listed, e.g. \"Chapter 7\", \"Interlude\", "
                                                         "or the title of a short story."},
            "page": {"type": "integer", "description": "1-based page; default 1."},
        }, "required": ["chapter"]}}},
]


@dataclass
class AgentResult:
    answer: str
    found: bool
    hits: list[Hit]  # every passage shown to the model, in citation order ([1] = hits[0])
    model: str
    usage: dict
    trace: list[dict] = field(default_factory=list)
    timings_ms: dict = field(default_factory=dict)


class _Session:
    def __init__(self, db: Session, embedder, cfg: RetrievalConfig):
        self.db, self.embedder, self.cfg = db, embedder, cfg
        self.hits: list[Hit] = []
        self.number: dict[int, int] = {}  # chunk id -> passage number
        self.tool_ms = 0.0

    # --- helpers ----------------------------------------------------------------------------
    def _volume(self, args: dict) -> tuple[str, int] | None:
        if args.get("short_story_collection"):
            return "short_story_collection", int(args["short_story_collection"])
        if args.get("volume"):
            return "main", int(args["volume"])
        return None

    def _show(self, hits: list[Hit]) -> str:
        """Number new passages and render them; passages seen before are only referenced."""
        out = []
        for h in hits:
            if h.row.id in self.number:
                out.append(f"[{self.number[h.row.id]}] (already shown above)")
                continue
            self.hits.append(h)
            n = self.number[h.row.id] = len(self.hits)
            out.append(f"[{n}] {h.row.heading} (¶{h.row.start_seq}–{h.row.end_seq})\n{h.row.text}")
        return "\n\n".join(out) or "No passages found."

    def _rows(self, where: str, params: dict, order: str = "c.ordinal") -> list[Hit]:
        rows = self.db.execute(text(f"SELECT {_COLUMNS}, c.ordinal FROM book_chunks c {_JOINS} WHERE {where} "
                                    f"ORDER BY {order}"), params).all()
        return [Hit(0.0, r) for r in rows]

    def _chapter_parts(self, kind: str, number: int) -> list:
        return self.db.execute(text("""
            SELECT pt.id, pt.label, pt.title, count(c.id) AS chunks
            FROM book_parts pt JOIN volumes v ON v.id = pt.volume_id
            JOIN book_chunks c ON c.part_id = pt.id
            WHERE v.kind = :k AND v.number = :n AND pt.kind = 'story'
            GROUP BY pt.id, pt.label, pt.title, pt.ordinal ORDER BY pt.ordinal
        """), {"k": kind, "n": number}).all()

    # --- tools ------------------------------------------------------------------------------
    def search(self, query: str, volumes: list[int] | None = None, chapter: int | None = None,
               short_story_collection: int | None = None) -> str:
        scope = None
        if short_story_collection:
            scope = Scope("short_story_collection", (int(short_story_collection),))
        elif volumes:
            vols = tuple(sorted({int(v) for v in volumes}))
            scope = Scope("main", vols, int(chapter) if chapter and len(vols) == 1 else None)
        hits = retrieval.retrieve(self.db.connection(), self.embedder, query, SEARCH_K, self.cfg, scope)
        return self._show(hits)

    def read_around(self, passage: int, direction: str = "both") -> str:
        if not 1 <= int(passage) <= len(self.hits):
            return f"There is no passage [{passage}]."
        r = self.hits[int(passage) - 1].row
        ordinal = self.db.execute(text("SELECT volume_id, ordinal FROM book_chunks WHERE id = :i"),
                                  {"i": r.id}).one()
        wanted = {"before": [-1], "after": [1]}.get(direction, [-1, 1])
        hits = self._rows("c.volume_id = :v AND c.ordinal = ANY(:o)",
                          {"v": ordinal.volume_id, "o": [ordinal.ordinal + d for d in wanted]})
        return self._show(hits)

    def list_chapters(self, volume: int | None = None, short_story_collection: int | None = None) -> str:
        vol = self._volume({"volume": volume, "short_story_collection": short_story_collection})
        if vol is None:
            return "Give a volume or a short_story_collection."
        parts = self._chapter_parts(*vol)
        if not parts:
            return "No such volume."
        return "\n".join(f"- {': '.join(x for x in (p.label, p.title) if x)} "
                         f"({-(-p.chunks // PAGE_CHUNKS)} pages)" for p in parts)

    def read_chapter(self, chapter: str, volume: int | None = None, short_story_collection: int | None = None,
                     page: int = 1) -> str:
        vol = self._volume({"volume": volume, "short_story_collection": short_story_collection})
        if vol is None:
            return "Give a volume or a short_story_collection."
        want = str(chapter).strip().lower()
        parts = self._chapter_parts(*vol)
        match = [p for p in parts if want in {(p.label or "").lower(), (p.title or "").lower(),
                                              ": ".join(x for x in (p.label, p.title) if x).lower()}]
        if not match and want.isdigit():
            match = [p for p in parts if (p.label or "").lower() == f"chapter {want}"]
        if not match:
            return "No such chapter. Chapters:\n" + self.list_chapters(volume, short_story_collection)
        p = match[0]
        pages = -(-p.chunks // PAGE_CHUNKS)
        page = max(1, min(int(page or 1), pages))
        hits = self._rows("c.part_id = :p", {"p": p.id})[(page - 1) * PAGE_CHUNKS: page * PAGE_CHUNKS]
        return f"Page {page} of {pages}.\n\n" + self._show(hits)

    def call(self, name: str, raw_args: str) -> tuple[str, dict]:
        try:
            args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            return f"Invalid JSON arguments: {raw_args[:200]}", {}
        fn = {"search": self.search, "read_around": self.read_around, "list_chapters": self.list_chapters,
              "read_chapter": self.read_chapter}.get(name)
        if fn is None:
            return f"Unknown tool {name!r}.", args
        t0 = time.perf_counter()
        try:
            result = fn(**{k: v for k, v in args.items() if v is not None})
        except (TypeError, ValueError) as e:
            result = f"Bad arguments: {e}"
        self.tool_ms += (time.perf_counter() - t0) * 1000
        return result, args


def _add_usage(total: dict, usage: dict) -> None:
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[k] = total.get(k, 0) + (usage.get(k) or 0)


ANSWER_NOW = "Stop searching. Write your final answer now from the passages above, following the answer rules."


def run(db: Session, embedder, question: str, cfg: RetrievalConfig) -> AgentResult:
    if not config.LLM_API_KEY:
        raise llm.LLMNotConfigured("LLM_API_KEY is not set")
    s = _Session(db, embedder, cfg)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    usage: dict = {}
    trace: list[dict] = []
    timing = {"llm": 0.0}
    model = config.LLM_MODEL

    def step(n: int, tool_choice: str, forced: bool = False) -> llm.ToolTurn:
        nonlocal model
        t0 = time.perf_counter()
        turn = llm.chat_tools(messages, TOOLS, tool_choice=tool_choice)
        timing["llm"] += (time.perf_counter() - t0) * 1000
        _add_usage(usage, turn.usage)
        model = turn.model
        trace.append({"step": n, "llm": {"prompt_tokens": turn.usage.get("prompt_tokens"),
                                         "completion_tokens": turn.usage.get("completion_tokens"),
                                         "finish_reason": turn.finish_reason, **({"forced": True} if forced else {})}})
        return turn

    answer = ""
    n = 0
    for n in range(1, config.AGENT_MAX_STEPS):
        turn = step(n, "auto")
        if not turn.tool_calls:
            answer = turn.text
            break
        messages.append(turn.message)
        for tc in turn.tool_calls:
            name = tc.get("function", {}).get("name", "")
            before = len(s.hits)
            result, args = s.call(name, tc.get("function", {}).get("arguments", "{}"))
            new = list(range(before + 1, len(s.hits) + 1))
            trace.append({"step": n, "tool": name, "args": args, "new_passages": [new[0], new[-1]] if new else []})
            log.info("agent step %d %s(%s) -> %d new passages", n, name, json.dumps(args, ensure_ascii=False), len(new))
            messages.append({"role": "tool", "tool_call_id": tc.get("id", name), "content": result})
        if (turn.usage.get("prompt_tokens") or 0) > config.AGENT_MAX_CONTEXT_TOKENS:
            break  # reading budget used up: answer now
    else:
        n = config.AGENT_MAX_STEPS - 1  # step budget used up: answer now
    if not answer:
        # Out of steps or budget. Models sometimes keep calling tools even when told not to, so
        # ask twice before giving up
        messages.append({"role": "user", "content": ANSWER_NOW})
        for attempt in range(2):
            turn = step(n + 1 + attempt, "none", forced=True)
            if turn.text and not turn.tool_calls:
                answer = turn.text
                break
        else:
            answer = NOT_FOUND
    found = bool(answer) and not answer.startswith(NOT_FOUND.rstrip("."))
    return AgentResult(answer, found, s.hits, model, usage, trace,
                       {"retrieval": round(s.tool_ms), "llm": round(timing["llm"])})
