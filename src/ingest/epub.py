"""Minimal epub reading: inventory of the source folder, OPF spine, NCX labels, and a
forgiving HTML tree (some files use HTML entities, so a strict XML parser is not enough)."""

import csv
import hashlib
import html
import posixpath
import re
import struct
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

MAIN_RE = re.compile(r"\bLN (\d+)\.epub$", re.I)
SSC_RE = re.compile(r"Short Story Collection, Vol\. (\d+)\.epub$", re.I)

CSV_FIELDS = ["file_name", "kind", "number", "title", "file_size", "sha256"]


@dataclass(frozen=True)
class VolumeFile:
    file_name: str  # path relative to the epub folder, "/"-separated
    kind: str  # "main" | "short_story_collection"
    number: int
    title: str
    file_size: int
    sha256: str

    @property
    def slug(self) -> str:
        return f"{'ln' if self.kind == 'main' else 'ssc'}{self.number:02d}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_folder(epub_dir: Path) -> list[VolumeFile]:
    """Find every epub under epub_dir and classify it by its file name."""
    found = []
    for path in sorted(epub_dir.rglob("*.epub")):
        rel = path.relative_to(epub_dir).as_posix()
        if m := SSC_RE.search(path.name):
            kind = "short_story_collection"
        elif m := MAIN_RE.search(path.name):
            kind = "main"
        else:
            raise ValueError(f"Unrecognised epub file name: {rel}")
        found.append(
            VolumeFile(
                file_name=rel,
                kind=kind,
                number=int(m.group(1)),
                title=Epub(path).title,
                file_size=path.stat().st_size,
                sha256=_sha256(path),
            )
        )
    found.sort(key=lambda v: (v.kind != "main", v.number))
    return found


def write_csv(volumes: list[VolumeFile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        for v in volumes:
            w.writerow({k: getattr(v, k) for k in CSV_FIELDS})


def read_csv(path: Path) -> list[VolumeFile]:
    with path.open(newline="", encoding="utf-8") as f:
        return [
            VolumeFile(
                file_name=r["file_name"],
                kind=r["kind"],
                number=int(r["number"]),
                title=r["title"],
                file_size=int(r["file_size"]),
                sha256=r["sha256"],
            )
            for r in csv.DictReader(f)
        ]


# --- HTML tree -----------------------------------------------------------------

VOID_TAGS = {"img", "br", "hr", "meta", "link", "input", "col", "area", "base", "wbr"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    children: list["Node | str"] = field(default_factory=list)

    @property
    def cls(self) -> str:
        return self.attrs.get("class", "")


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag):
        # Pop to the matching open tag; ignore stray end tags
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text: str) -> Node:
    b = _TreeBuilder()
    b.feed(text)
    b.close()
    return b.root


def find(node: Node, tag: str) -> Node | None:
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag:
                return c
            if r := find(c, tag):
                return r
    return None


# --- epub container ------------------------------------------------------------


def image_size(data: bytes) -> tuple[int, int] | None:
    """(width, height) of a JPEG/PNG/GIF from its header bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    return None


class Epub:
    def __init__(self, path: Path):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        container = self.zip.read("META-INF/container.xml").decode("utf-8")
        self.opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
        self.base = posixpath.dirname(self.opf_path)
        opf = self.zip.read(self.opf_path).decode("utf-8")

        self.manifest: dict[str, str] = {}
        self.media: dict[str, str] = {}
        for m in re.finditer(r"<item\b([^>]*?)/?>", opf):
            a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
            href = html.unescape(a["href"])
            self.manifest[a["id"]] = href
            self.media[href] = a.get("media-type", "")
        self.spine = [
            self.manifest[i] for i in re.findall(r'<itemref\b[^>]*?idref="([^"]+)"', opf)
        ]
        t = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", opf, re.S)
        self.title = html.unescape(t.group(1)).strip() if t else path.stem
        self._sizes: dict[str, tuple[int, int] | None] = {}

    def resolve(self, href: str, relative_to: str = "") -> str:
        """Zip member path for an href found in a spine document (or the OPF if empty)."""
        href = html.unescape(href.split("#")[0])
        start = posixpath.dirname(posixpath.join(self.base, relative_to))
        return posixpath.normpath(posixpath.join(start, href))

    def read_text(self, href: str) -> str:
        return self.zip.read(self.resolve(href)).decode("utf-8")

    def image_size(self, member: str) -> tuple[int, int] | None:
        if member not in self._sizes:
            try:
                self._sizes[member] = image_size(self.zip.read(member))
            except KeyError:
                self._sizes[member] = None
        return self._sizes[member]

    def toc_labels(self) -> list[str]:
        """Top-level labels from the NCX navMap (page lists excluded)."""
        ncx = next((h for h, t in self.media.items() if "ncx" in t), None)
        if not ncx:
            return []
        t = self.read_text(ncx)
        nav = t[t.find("<navMap") : t.find("</navMap>")]
        return [
            html.unescape(re.sub(r"\s+", " ", x)).strip()
            for x in re.findall(r"<text>(.*?)</text>", nav, re.S)
        ]
