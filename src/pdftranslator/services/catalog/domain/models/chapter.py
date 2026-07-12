"""
Rich Domain Model for Chapter.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from ..repositories.exceptions import DomainError


@dataclass
class Chapter:
    """
    Chapter entity within a Volume.

    Invariants:
    - Chapter number must be positive (if set)
    - Text content managed through methods
    - Translation state tracked
    """

    volume_id: int
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    id: Optional[int] = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.chapter_number is not None and self.chapter_number <= 0:
            raise DomainError("Chapter number must be positive if set")

    @property
    def is_translated(self) -> bool:
        return self.translated_text is not None and bool(self.translated_text.strip())

    @property
    def word_count_original(self) -> int:
        return len(self.original_text.split()) if self.original_text else 0

    @property
    def word_count_translated(self) -> int:
        return len(self.translated_text.split()) if self.translated_text else 0

    def set_original_text(self, text: str) -> None:
        if not text or not text.strip():
            raise DomainError("Original text cannot be empty")
        self.original_text = text.strip()
        self._touch()

    def set_translation(self, translation: str) -> None:
        if not translation or not translation.strip():
            raise DomainError("Translation cannot be empty")
        self.translated_text = translation.strip()
        self._touch()

    def clear_translation(self) -> None:
        self.translated_text = None
        self._touch()

    def update_metadata(
        self,
        title: Optional[str] = None,
        chapter_number: Optional[int] = None,
    ) -> None:
        if title is not None:
            self.title = title
        if chapter_number is not None:
            if chapter_number <= 0:
                raise DomainError("Chapter number must be positive")
            self.chapter_number = chapter_number
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.utcnow()