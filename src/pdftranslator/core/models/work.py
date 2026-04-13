"""Work-related domain models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Work:
    """Represents a literary work (book, light novel, etc.)."""

    id: Optional[int] = None
    title: str = ""
    title_translated: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    author: Optional[str] = None
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
    full_text: Optional[str] = None
    translated_text: Optional[str] = None
    embedding: Optional[list] = None
    created_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Volume(id={self.id}, number={self.volume_number})"


@dataclass
class Chapter:
    """Represents a chapter within a volume."""

    id: Optional[int] = None
    volume_id: Optional[int] = None
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    embedding: Optional[list] = None
    created_at: Optional[datetime] = None

    def __repr__(self) -> str:
        if self.chapter_number:
            return f"Chapter(id={self.id}, number={self.chapter_number})"
        return f"Chapter(id={self.id}, title='{self.title}')"


@dataclass
class GlossaryEntry:
    """Represents a glossary term for translation consistency."""

    id: Optional[int] = None
    work_id: Optional[int] = None
    term: str = ""
    translation: Optional[str] = None
    entity_type: str = "other"
    context: Optional[str] = None
    is_proper_noun: bool = False
    frequency: int = 0
    source_lang: str = "en"
    target_lang: str = "es"
    embedding: Optional[list] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"GlossaryEntry(id={self.id}, '{self.term}' -> '{self.translation}')"


@dataclass
class TermContext:
    """Represents a context for a glossary term."""

    id: Optional[int] = None
    term_id: Optional[int] = None
    context_hint: str = ""
    translation: str = ""
    example_usage: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ContextExample:
    """Represents an example sentence for a term context."""

    id: Optional[int] = None
    context_id: Optional[int] = None
    original_sentence: str = ""
    translated_sentence: str = ""
    chapter_id: Optional[int] = None
    created_at: Optional[datetime] = None
