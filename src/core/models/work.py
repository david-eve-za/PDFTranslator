"""Work-related domain models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Work:
    """Represents a literary work (book, light novel, etc.)."""

    id: Optional[int] = None
    title: str = ""
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Work(id={self.id}, title='{self.title}')"


@dataclass
class Volume:
    """Represents a volume within a work."""

    id: Optional[int] = None
    work_id: Optional[int] = None
    volume_number: int = 0
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Volume(id={self.id}, number={self.volume_number})"


@dataclass
class Chapter:
    """Represents a chapter within a volume."""

    id: Optional[int] = None
    volume_id: Optional[int] = None
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        if self.chapter_number:
            return f"Chapter(id={self.id}, number={self.chapter_number})"
        return f"Chapter(id={self.id}, title='{self.title}')"


@dataclass
class GlossaryEntry:
    """Represents a glossary term for translation consistency."""

    id: Optional[int] = None
    work_id: Optional[int] = None
    volume_id: Optional[int] = None
    source_term: str = ""
    target_term: str = ""
    context: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return (
            f"GlossaryEntry(id={self.id}, '{self.source_term}' -> '{self.target_term}')"
        )
