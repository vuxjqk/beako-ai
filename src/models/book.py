"""Cleaned light-novel text extracted from the source epubs (the epubs stay outside the DB).

volumes -> book_parts -> book_sections -> book_paragraphs, all keyed by reading order so the
ingest can upsert on natural keys and a rerun on unchanged input writes nothing.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class VolumeKind(str, enum.Enum):
    MAIN = "main"
    SHORT_STORY_COLLECTION = "short_story_collection"


class PartKind(str, enum.Enum):
    # Narrative text (chapters, prologues, interludes, short stories)
    STORY = "story"
    # Labelled instead of deleted so they can be filtered out later
    AFTERWORD = "afterword"
    PREVIEW = "preview"  # character banter "next volume preview" after the afterword
    FRONT_MATTER = "front_matter"
    TOC = "toc"
    COPYRIGHT = "copyright"
    NEWSLETTER = "newsletter"
    AD = "ad"  # third-party ad pages injected into some files


class ParagraphKind(str, enum.Enum):
    TEXT = "text"
    SCENE_BREAK = "scene_break"  # unified as "* * *"
    ORNAMENT = "ornament"  # typographic end marks such as "<END>"


class Volume(Base):
    __tablename__ = "volumes"
    __table_args__ = (UniqueConstraint("kind", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[VolumeKind] = mapped_column(_enum(VolumeKind, "volume_kind"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BookPart(Base):
    __tablename__ = "book_parts"
    __table_args__ = (UniqueConstraint("volume_id", "ordinal"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    volume_id: Mapped[int] = mapped_column(
        ForeignKey("volumes.id", ondelete="CASCADE"), index=True
    )
    # 1-based reading order within the volume
    ordinal: Mapped[int] = mapped_column(Integer)
    kind: Mapped[PartKind] = mapped_column(_enum(PartKind, "book_part_kind"))
    # Finer label for story parts: chapter, prologue, interlude, epilogue, short_story, ...
    part_type: Mapped[str] = mapped_column(String(32))
    number: Mapped[int | None] = mapped_column(Integer)  # chapter number when there is one
    label: Mapped[str | None] = mapped_column(String(64))  # "Chapter 3", "Interlude"
    title: Mapped[str | None] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(String(255))
    # epub-internal paths (relative to the OPF) the part was read from, in spine order
    source_files: Mapped[list[str]] = mapped_column(ARRAY(Text))


class BookSection(Base):
    __tablename__ = "book_sections"
    __table_args__ = (UniqueConstraint("part_id", "ordinal"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(
        ForeignKey("book_parts.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    # The printed section number ("1", "2", ...); null for unnumbered text
    number: Mapped[int | None] = mapped_column(Integer)


class BookParagraph(Base):
    __tablename__ = "book_paragraphs"
    __table_args__ = (UniqueConstraint("volume_id", "seq"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    volume_id: Mapped[int] = mapped_column(ForeignKey("volumes.id", ondelete="CASCADE"))
    section_id: Mapped[int] = mapped_column(
        ForeignKey("book_sections.id", ondelete="CASCADE"), index=True
    )
    # 1-based reading order across the whole volume
    seq: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)  # 1-based within the section
    kind: Mapped[ParagraphKind] = mapped_column(_enum(ParagraphKind, "book_paragraph_kind"))
    text: Mapped[str] = mapped_column(Text)
    source_file: Mapped[str] = mapped_column(String(255))
    # 0-based index of the source <p>/<h*> element within source_file
    source_block: Mapped[int] = mapped_column(Integer)
    # Printed page the paragraph starts on, when the epub carries page markers
    page: Mapped[str | None] = mapped_column(String(16))
