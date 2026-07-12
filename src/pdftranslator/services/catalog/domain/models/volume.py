"""
Rich Domain Model for Volume.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from .chapter import Chapter
from ..repositories.exceptions import DomainError


@dataclass
class Volume:
    """
    Volume entity within a Work.

    Invariants:
    - Volume number must be positive
    - Belongs to exactly one Work
    - Chapters managed through aggregate
    """

    work_id: int
    volume_number: int
    title: Optional[str] = None
    full_text: Optional[str] = None
    translated_text: Optional[str] = None
    id: Optional[int] = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    glossary_built_at: Optional[datetime] = None
    glossary_build_status: str = "pending"
    glossary_error_message: Optional[str] = None
    glossary_resume_phase: Optional[str] = None
    _chapters: List[Chapter] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.volume_number <= 0:
            raise DomainError("Volume number must be positive")
        if self.work_id is None or self.work_id <= 0:
            raise DomainError("Volume must belong to a valid work")

    @property
    def chapters(self) -> tuple[Chapter, ...]:
        return tuple(self._chapters)

    @property
    def chapter_count(self) -> int:
        return len(self._chapters)

    @property
    def translated_chapters(self) -> int:
        return sum(1 for c in self._chapters if c.is_translated)

    @property
    def translation_progress(self) -> float:
        if self.chapter_count == 0:
            return 0.0
        return (self.translated_chapters / self.chapter_count) * 100

    def add_chapter(self, chapter: Chapter) -> None:
        if chapter.volume_id is not None and chapter.volume_id != self.id:
            raise DomainError("Chapter belongs to a different volume")
        if any(c.chapter_number == chapter.chapter_number for c in self._chapters):
            raise DomainError(f"Chapter {chapter.chapter_number} already exists")
        chapter.volume_id = self.id
        self._chapters.append(chapter)
        self._touch()

    def get_chapter(self, chapter_number: int) -> Optional[Chapter]:
        return next((c for c in self._chapters if c.chapter_number == chapter_number), None)

    def mark_glossary_built(self) -> None:
        self.glossary_built_at = datetime.utcnow()
        self.glossary_build_status = "completed"
        self._touch()

    def mark_glossary_failed(self, error: str) -> None:
        self.glossary_build_status = "failed"
        self.glossary_error_message = error
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.utcnow()