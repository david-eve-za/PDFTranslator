"""
Segment Entity within TranslationJob aggregate.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from ..repositories.exceptions import DomainError


@dataclass
class Segment:
    """
    Translation segment (sentence/paragraph unit).

    Invariants:
    - Segment number positive if set
    - Text content managed through methods
    - Translation state tracked
    """

    job_id: int
    segment_number: Optional[int] = None
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    id: Optional[int] = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.segment_number is not None and self.segment_number <= 0:
            raise DomainError("Segment number must be positive if set")

    @property
    def is_translated(self) -> bool:
        return self.target_text is not None and bool(self.target_text.strip())

    @property
    def word_count_source(self) -> int:
        return len(self.source_text.split()) if self.source_text else 0

    @property
    def word_count_target(self) -> int:
        return len(self.target_text.split()) if self.target_text else 0

    def set_source_text(self, text: str) -> None:
        if not text or not text.strip():
            raise DomainError("Source text cannot be empty")
        self.source_text = text.strip()
        self._touch()

    def set_target_text(self, text: str) -> None:
        if not text or not text.strip():
            raise DomainError("Target text cannot be empty")
        self.target_text = text.strip()
        self._touch()

    def clear_target_text(self) -> None:
        self.target_text = None
        self._touch()

    def update_context(self, before: Optional[str] = None, after: Optional[str] = None) -> None:
        if before is not None:
            self.context_before = before
        if after is not None:
            self.context_after = after
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.utcnow()