"""Turn one epub into ordered parts -> sections -> paragraphs of clean text.

Structure rules come from surveying all 32 files (they differ by publisher toolchain:
plain Yen Press markup, Kobo spans, calibre classes):

* A chapter starts at <h1 class="chapter-number"> ("CHAPTER 3", "INTERLUDE", ...) followed
  by <h1 class="chapter-title">; short story collections only have the chapter-title.
  One chapter usually spans several spine files, split wherever an illustration sits.
* Sections inside a chapter are headings holding just a number ("1", "2", ...).
* A scene break is not a separate element: the paragraph after the break carries a
  class containing "space-break" (top margin); a few volumes also use <p class="orn">* * *.
* Long dashes ("——") are often inline images (Art_mdash3.jpg, Emdash2.jpg, ...); their
  length is recovered from the image width relative to the volume's commonest dash image.
* Non-story pages are labelled (PartKind) rather than dropped. Image-only pages (cover,
  inserts, illustrations) carry no text and are skipped.
"""

import posixpath
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from src.ingest.epub import Epub, Node, VolumeFile, find, parse_html
from src.models.book import ParagraphKind, PartKind

SCENE_BREAK = "* * *"

# Inline images that stand for text other than dashes, keyed by (volume slug, file name)
SPECIAL_IMAGES = {
    # The title on Subaru's "book of the dead", printed in Japanese
    ("ln25", "chi.jpg"): "菜月・昴",
    # Garbled voice in Otto's flashback
    ("ln13", "Art_1.jpg"): "●・●・●・●",
}

DASH_IMG_RE = re.compile(r"dash|3em", re.I)
SECTION_NUM_RE = re.compile(r"\d{1,3}")
PAGE_ID_RE = re.compile(r"^page[-_]?([0-9ivxlcdm]+)$", re.I)
CHAPTER_LABEL_RE = re.compile(
    r"^(PROLOGUE|EPILOGUE|INTERLUDE|FRAGMENTS?|ADDENDUM|CLOSING CHAPTER|ENDING CHAPTER"
    r"|CHA?P?TER\s+(\d+))$",
    re.I,
)
END_RE = re.compile(r"<\s*END\s*>", re.I)
# Volumes with fewer page anchors than this only mark a page or two (title page), so a
# "current page" would be stale for the whole book; their paragraphs get no page
MIN_PAGE_ANCHORS = 100
SMALL_WORDS = {"a", "an", "the", "and", "or", "nor", "but", "of", "to", "in", "on", "at",
               "for", "with", "by", "from", "as", "upon", "into"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
CONTAINER_TAGS = {"div", "section", "blockquote", "ul", "ol", "body", "nav", "article",
                  "aside", "figure", "table", "tbody", "tr", "td", "header", "footer"}
SKIP_TAGS = {"head", "script", "style", "rt", "rp"}

DROP_CHARS = dict.fromkeys(map(ord, "­​‌‍⁠﻿"), None)
CHAR_MAP = {ord("∼"): "~", ord("〜"): "~"}  # tilde operator / wave dash
SPACE_RE = re.compile(r"[ \t\r\f\v  -   　]+")


def clean_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s).translate(DROP_CHARS).translate(CHAR_MAP)
    lines = (SPACE_RE.sub(" ", line).strip() for line in s.split("\n"))
    return "\n".join(line for line in lines if line)


@dataclass
class Block:
    tag: str
    cls: str
    text: str
    index: int  # position among the file's blocks
    page: str | None


@dataclass
class Paragraph:
    kind: ParagraphKind
    text: str
    source_file: str
    source_block: int
    page: str | None


@dataclass
class Section:
    number: int | None
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass
class Part:
    kind: PartKind
    part_type: str
    label: str | None = None
    number: int | None = None
    title: str | None = None
    subtitle: str | None = None
    source_files: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def add_source(self, href: str) -> None:
        if href not in self.source_files:
            self.source_files.append(href)


@dataclass
class ExtractedVolume:
    file: VolumeFile
    title: str
    parts: list[Part]
    warnings: list[str]


class _BlockReader:
    """Flattens one spine document into text blocks, resolving inline images and pages."""

    def __init__(self, epub: Epub, slug: str, dash_unit: float | None, warnings: list[str]):
        self.epub = epub
        self.slug = slug
        self.dash_unit = dash_unit
        self.warnings = warnings
        self.page: str | None = None  # carried across files in reading order
        self.anchor_count = 0

    def read(self, href: str) -> list[Block]:
        self.href = href
        body = find(parse_html(self.epub.read_text(href)), "body")
        self.blocks: list[Block] = []
        self._index = 0
        if body is not None:
            self._walk(body)
        return self.blocks

    def _note_page(self, node: Node) -> str | None:
        m = PAGE_ID_RE.match(node.attrs.get("id", ""))
        if m:
            self.anchor_count += 1
        return m.group(1) if m else None

    def _walk(self, node: Node) -> None:
        if p := self._note_page(node):
            self.page = p
        for c in node.children:
            if isinstance(c, str):
                if c.strip() and node.tag not in ("#root", "html"):
                    self.warnings.append(f"{self.href}: loose text in <{node.tag}>: {c.strip()[:60]!r}")
                continue
            if c.tag in SKIP_TAGS:
                continue
            if c.tag in BLOCK_TAGS or (c.tag in CONTAINER_TAGS and not self._has_blocks(c)
                                        and self._raw_text(c).strip()):
                self._emit(c)
            else:
                self._walk(c)

    def _has_blocks(self, node: Node) -> bool:
        return any(
            isinstance(c, Node) and (c.tag in BLOCK_TAGS or c.tag in CONTAINER_TAGS or self._has_blocks(c))
            for c in node.children
        )

    def _raw_text(self, node: Node) -> str:
        return "".join(c if isinstance(c, str) else self._raw_text(c) for c in node.children)

    def _emit(self, node: Node) -> None:
        parts: list[str] = []
        anchors: list[tuple[int, str]] = []  # (text offset, page)

        def inline(n: Node) -> None:
            if p := self._note_page(n):
                anchors.append((len("".join(parts).strip()), p))
            for c in n.children:
                if isinstance(c, str):
                    parts.append(c)
                elif c.tag in SKIP_TAGS:
                    continue
                elif c.tag == "br":
                    parts.append("\n")
                elif c.tag == "img":
                    parts.append(self._image_text(c))
                else:
                    inline(c)

        inline(node)
        start_page = self.page
        if anchors and anchors[0][0] == 0:
            start_page = anchors[0][1]
        if anchors:
            self.page = anchors[-1][1]
        tag = node.tag if node.tag in BLOCK_TAGS else "p"
        self.blocks.append(Block(tag, node.cls, clean_text("".join(parts)), self._index, start_page))
        self._index += 1

    def _image_text(self, img: Node) -> str:
        member = self.epub.resolve(img.attrs.get("src", ""), self.href)
        name = posixpath.basename(member)
        if special := SPECIAL_IMAGES.get((self.slug, name)):
            return special
        if DASH_IMG_RE.search(name):
            size = self.epub.image_size(member)
            if size and self.dash_unit:
                return "—" * max(1, round(2 * size[0] / self.dash_unit))
            return "——"
        # Full-page illustration wrapped in a <p>: no text to keep
        return ""


def _dash_unit(epub: Epub) -> float | None:
    """Pixel width of the commonest inline dash image in this volume, taken to be '——'."""
    widths: Counter[int] = Counter()
    for href in epub.spine:
        text = epub.read_text(href)
        for m in re.finditer(r'<img\b[^>]*?src="([^"]+)"', text):
            member = epub.resolve(m.group(1), href)
            if DASH_IMG_RE.search(posixpath.basename(member)):
                if size := epub.image_size(member):
                    widths[size[0]] += 1
    return float(widths.most_common(1)[0][0]) if widths else None


def _file_kind(href: str, blocks: list[Block]) -> PartKind | None:
    """Classify a spine document that is not part of the narrative flow; None = flow."""
    name = posixpath.basename(href).lower()
    text = " ".join(b.text for b in blocks)
    classes = " ".join(b.cls for b in blocks)
    if "copyright" in name or "copyright-title" in classes:
        return PartKind.COPYRIGHT
    if re.match(r"(toc|nav)\b", name) or "toc-title" in classes:
        return PartKind.TOC
    if "newsletter" in name or text.startswith("Thank you for buying this ebook"):
        return PartKind.NEWSLETTER
    if "Just Light Novels" in text and len(text) < 500:
        return PartKind.AD
    if re.match(r"(welcome|cover|titlepage|title|insert|photo-insert)\b", name):
        return PartKind.FRONT_MATTER
    return None


def _label(raw: str) -> tuple[str, str, int | None]:
    """'CHAPTER 3' -> ('chapter', 'Chapter 3', 3); 'CLOSING CHAPTER' -> ('closing_chapter', ...)."""
    m = CHAPTER_LABEL_RE.match(raw.strip())
    if m is None:
        return "chapter", raw.strip().title(), None
    if m.group(2):
        n = int(m.group(2))
        return "chapter", f"Chapter {n}", n
    word = m.group(1).upper()
    part_type = {"FRAGMENTS": "fragment", "FRAGMENT": "fragment"}.get(word, word.lower().replace(" ", "_"))
    return part_type, word.title(), None


def _norm_key(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", unicodedata.normalize("NFKC", s).casefold())


def _title_case(s: str) -> str:
    words = s.lower().split(" ")
    return " ".join(
        w if (i and w in SMALL_WORDS) else re.sub(r"(^|-)([^a-z]*)([a-z])", lambda m: m.group(1) + m.group(2) + m.group(3).upper(), w)
        for i, w in enumerate(words)
    )


def _nice_title(heading: str, toc: list[str]) -> str:
    """Prefer the NCX spelling (proper case) of a title printed in caps in the body."""
    key = _norm_key(heading)
    if key:
        for label in toc:
            tail = label.split(":", 1)[-1].strip()
            if _norm_key(tail) == key or _norm_key(label) == key:
                return tail
    if heading.isupper():
        return _title_case(heading)
    return heading


def _toc_title_for(label: str, toc: list[str]) -> str | None:
    """Title from an NCX entry "Chapter 1: <title>" when the body heading has no text."""
    for entry in toc:
        head, sep, tail = entry.partition(":")
        if sep and _norm_key(head) == _norm_key(label) and tail.strip():
            return clean_text(tail)
    return None


def extract(epub_path, vf: VolumeFile) -> ExtractedVolume:
    epub = Epub(epub_path)
    warnings: list[str] = []
    reader = _BlockReader(epub, vf.slug, _dash_unit(epub), warnings)
    toc = epub.toc_labels()
    parts: list[Part] = []
    cur: Part | None = None
    awaiting_title = False

    def new_part(kind: PartKind, part_type: str, **kw) -> Part:
        nonlocal cur
        cur = Part(kind=kind, part_type=part_type, **kw)
        cur.sections.append(Section(None))
        parts.append(cur)
        return cur

    def add(kind: ParagraphKind, b: Block, href: str, text: str | None = None) -> None:
        sec = cur.sections[-1]
        sec.paragraphs.append(Paragraph(kind, b.text if text is None else text, href, b.index, b.page))
        cur.add_source(href)

    def add_text(b: Block, href: str) -> None:
        if not b.text:
            return  # page-break filler (<p><br/></p>, pgbrk)
        if END_RE.fullmatch(b.text):
            add(ParagraphKind.ORNAMENT, b, href)
            return
        if "orn" in b.cls.split() or b.text in ("* * *", "***", "*"):
            add_break(b, href)
            return
        if "space-break" in b.cls:
            add_break(b, href)
        add(ParagraphKind.TEXT, b, href)

    def add_break(b: Block, href: str) -> None:
        paras = cur.sections[-1].paragraphs
        # A break only means something between two pieces of text in the same section
        if paras and paras[-1].kind == ParagraphKind.TEXT:
            add(ParagraphKind.SCENE_BREAK, b, href, SCENE_BREAK)

    for href in epub.spine:
        blocks = reader.read(href)
        if not any(b.text for b in blocks):
            continue  # image-only page
        kind = _file_kind(href, blocks)
        if kind is not None:
            if not (cur and cur.kind == kind and cur.part_type == kind.value):
                new_part(kind, kind.value, label=kind.value.replace("_", " ").title())
            for b in blocks:
                if b.text:
                    add(ParagraphKind.TEXT, b, href)
            awaiting_title = False
            continue

        first = next(b for b in blocks if b.text)
        if first.tag[0] != "h" and cur is not None and cur.kind == PartKind.AFTERWORD:
            # Text right after the afterword without a heading: the character-banter
            # "next volume preview" page
            new_part(PartKind.PREVIEW, "preview", label="Preview")

        for b in blocks:
            if b.tag[0] != "h":
                if cur is None:
                    warnings.append(f"{href}: text before any heading, kept as front matter")
                    new_part(PartKind.FRONT_MATTER, "front_matter", label="Front Matter")
                awaiting_title = False
                add_text(b, href)
                continue
            text = b.text
            if not text:
                continue
            if "chapter-number" in b.cls or CHAPTER_LABEL_RE.match(text):
                part_type, label, number = _label(text)
                new_part(PartKind.STORY, part_type, label=label, number=number).add_source(href)
                awaiting_title = True
            elif "chapter-title" in b.cls:
                title = _nice_title(text.replace("\n", " "), toc)
                if awaiting_title:
                    cur.title = title
                else:
                    new_part(PartKind.STORY, "short_story", title=title).add_source(href)
                awaiting_title = False
            elif "chapter-subtitle" in b.cls and cur is not None:
                cur.subtitle = text
            elif "appendix-title" in b.cls or _norm_key(text) == "afterword":
                new_part(PartKind.AFTERWORD, "afterword", label="Afterword").add_source(href)
                awaiting_title = False
            elif SECTION_NUM_RE.fullmatch(text) and cur is not None and cur.kind == PartKind.STORY:
                sec = cur.sections[-1]
                if sec.paragraphs or sec.number is not None:
                    cur.sections.append(Section(int(text)))
                else:
                    sec.number = int(text)
                awaiting_title = False
            else:
                warnings.append(f"{href}: unrecognised heading <{b.tag} class={b.cls!r}> {text[:60]!r}")
                add_text(b, href)

    # Drop trailing scene breaks and sections left empty by headings with no text
    for part in parts:
        for sec in part.sections:
            while sec.paragraphs and sec.paragraphs[-1].kind == ParagraphKind.SCENE_BREAK:
                sec.paragraphs.pop()
        empty = [s for s in part.sections if not s.paragraphs]
        for s in empty:
            if s.number is not None:
                warnings.append(f"{part.label or part.title}: section {s.number} has no text")
        part.sections = [s for s in part.sections if s.paragraphs]
    for part in parts:
        if not part.sections:
            warnings.append(f"part {part.label or part.title!r} has no text")
    parts = [p for p in parts if p.sections]

    for part in parts:
        if part.kind == PartKind.STORY and not part.title and part.label:
            part.title = _toc_title_for(part.label, toc)
    if reader.anchor_count < MIN_PAGE_ANCHORS:
        for part in parts:
            for sec in part.sections:
                for para in sec.paragraphs:
                    para.page = None
    return ExtractedVolume(vf, epub.title, parts, warnings)
