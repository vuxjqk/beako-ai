"""Split story text into retrieval chunks.

Sizes come from surveying the corpus with the bge tokenizer: story paragraphs are short
(median 24 tokens, p99 84) while sections are long (median ~2,200 tokens), and only two
paragraphs exceed the 512-token model limit (Echidna, LN12; Regulus, LN19).

Within one part (chapter / short story; chunks never cross parts) the text is a sequence of
paragraphs, each preceded by a boundary of some strength. The packer prefers to cut at the
strongest boundary available: section start, then scene break, then paragraph. A paragraph
is only cut itself when it is longer than MAX_TOKENS, and then at sentence ends. Adjacent
chunks in a part share up to OVERLAP_TOKENS of whole paragraphs. Short sections simply get
absorbed, because a cut is only taken once the chunk holds MIN_TOKENS.
"""

import hashlib
import re
from dataclasses import dataclass, field

TARGET_TOKENS = 350
MAX_TOKENS = 450  # + heading stays under the 512-token limit of the bge models
MIN_TOKENS = 120  # no cut at a section boundary below this
SCENE_CUT_TOKENS = 175  # no cut at a scene break below this
OVERLAP_TOKENS = 80
CHUNKER_VERSION = (
    f"v1 target={TARGET_TOKENS} max={MAX_TOKENS} min={MIN_TOKENS} "
    f"scene={SCENE_CUT_TOKENS} overlap={OVERLAP_TOKENS}"
)

SECTION, SCENE, PARAGRAPH = 3, 2, 1
SENTENCE_END_RE = re.compile(r"(?<=[.!?…—])[”’)]*\s+")


@dataclass
class Item:
    """A whole paragraph, or one sentence-aligned piece of an over-long paragraph."""

    paragraph_id: int
    seq: int
    section_id: int
    text: str
    tokens: int
    boundary: int  # strength of the boundary before this item
    start_char: int = 0
    end_char: int | None = None  # None = to the end of the paragraph
    gap: str = ""  # original whitespace before this piece when it continues a paragraph


@dataclass
class Chunk:
    part_id: int
    items: list[Item] = field(default_factory=list)
    heading: str = ""

    @property
    def tokens(self) -> int:
        return sum(i.tokens for i in self.items)

    @property
    def text(self) -> str:
        out: list[str] = []
        for prev, item in zip([None, *self.items], self.items):
            if prev is not None and prev.paragraph_id == item.paragraph_id:
                out[-1] += item.gap + item.text  # next piece of the same split paragraph
                continue
            if prev is not None and item.boundary == SCENE:
                out.append("* * *")
            out.append(item.text)
        return "\n\n".join(out)

    @property
    def embed_input(self) -> str:
        return f"{self.heading}\n\n{self.text}"

    def content_hash(self, model: str) -> str:
        return hashlib.sha256(f"{model}\n{self.embed_input}".encode()).hexdigest()


def split_long(text: str, count_tokens, limit: int) -> list[tuple[int, int, int]]:
    """(start_char, end_char, tokens) pieces of at most `limit` tokens, cut at sentence ends."""
    bounds = [0] + [m.end() for m in SENTENCE_END_RE.finditer(text)] + [len(text)]
    sentences = [(a, b) for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()]
    counts = count_tokens([text[a:b] for a, b in sentences])
    pieces: list[tuple[int, int, int]] = []
    start, end, total = None, None, 0
    for (a, b), n in zip(sentences, counts):
        if start is not None and total + n > limit:
            pieces.append((start, end, total))
            start, total = None, 0
        if start is None:
            start = a
        end, total = b, total + n
    if start is not None:
        pieces.append((start, end, total))
    return pieces


def build_items(paragraphs: list, count_tokens) -> list[Item]:
    """paragraphs: rows of one part in reading order (id, seq, section_id, kind, text)."""
    texts = [p for p in paragraphs if p.kind == "text"]
    counts = dict(zip((p.id for p in texts), count_tokens([p.text for p in texts])))
    items: list[Item] = []
    boundary = SECTION
    last_section = None
    for p in paragraphs:
        if p.section_id != last_section:
            boundary, last_section = SECTION, p.section_id
        if p.kind == "scene_break":
            boundary = max(boundary, SCENE)
            continue
        if p.kind != "text":
            continue  # ornaments such as <END>
        n = counts[p.id]
        if n <= TARGET_TOKENS:
            items.append(Item(p.id, p.seq, p.section_id, p.text, n, boundary))
        else:
            gap = ""
            for k, (a, b, m) in enumerate(split_long(p.text, count_tokens, TARGET_TOKENS)):
                raw = p.text[a:b]
                items.append(Item(p.id, p.seq, p.section_id, raw.strip(), m,
                                  boundary if k == 0 else PARAGRAPH, a,
                                  None if b >= len(p.text) else b, gap))
                gap = raw[len(raw.rstrip()):]
        boundary = PARAGRAPH
    return items


def pack(part_id: int, items: list[Item], heading: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur = Chunk(part_id, heading=heading)
    fresh = 0  # items in `cur` that are not overlap carried from the previous chunk

    def cut() -> None:
        nonlocal cur, fresh
        chunks.append(cur)
        carry: list[Item] = []
        total = 0
        for item in reversed(cur.items):
            if total + item.tokens > OVERLAP_TOKENS:
                break
            carry.insert(0, item)
            total += item.tokens
        if len(carry) == len(cur.items):
            carry = carry[1:]  # always move forward
        cur = Chunk(part_id, list(carry), heading)
        fresh = 0

    for item in items:
        size = cur.tokens
        if fresh:
            natural = (item.boundary == SECTION and size >= MIN_TOKENS) or (
                item.boundary == SCENE and size >= SCENE_CUT_TOKENS)
            if size + item.tokens > MAX_TOKENS or size >= TARGET_TOKENS or natural:
                cut()
                # Carried overlap must not push a large item past the ceiling
                while cur.items and cur.tokens + item.tokens > MAX_TOKENS:
                    cur.items.pop(0)
        cur.items.append(item)
        fresh += 1
    if fresh:
        # A small tail is folded into the previous chunk when it fits
        tail = cur.items[len(cur.items) - fresh:]
        if chunks and sum(i.tokens for i in tail) < MIN_TOKENS and \
                chunks[-1].tokens + sum(i.tokens for i in tail) <= MAX_TOKENS:
            chunks[-1].items.extend(tail)
        else:
            chunks.append(cur)
    return chunks
