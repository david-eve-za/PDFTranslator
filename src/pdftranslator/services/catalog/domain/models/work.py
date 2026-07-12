"""
Rich Domain Model for Work (Literary Work/Book).

CUPID Principle: Domain-Focused
- Encapsulates business invariants
- Behavior over data
- No anemic models
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from .volume import Volume
from ..repositories.exceptions import DomainError


@dataclass
class Work:
    """
    Aggregate Root for the Catalog domain.

    Invariants:
    - Title cannot be empty
    - Source and target languages must be valid ISO codes
    - Volumes are managed through the aggregate (not directly mutated)
    """

    title: str
    source_lang: str
    target_lang: str
    author: Optional[str] = None
    title_translated: Optional[str] = None
    id: Optional[int] = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _volumes: List[Volume] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Validate invariants on creation."""
        self._validate()

    def _validate(self) -> None:
        """Enforce domain invariants."""
        if not self.title or not self.title.strip():
            raise DomainError("Work title cannot be empty")
        if not self.source_lang or len(self.source_lang) != 2:
            raise DomainError("Source language must be ISO 639-1 code (2 chars)")
        if not self.target_lang or len(self.target_lang) != 2:
            raise DomainError("Target language must be ISO 639-1 code (2 chars)")
        if self.source_lang == self.target_lang:
            raise DomainError("Source and target languages must differ")

    @property
    def volumes(self) -> tuple[Volume, ...]:
        """Return immutable view of volumes."""
        return tuple(self._volumes)

    @property
    def volume_count(self) -> int:
        return len(self._volumes)

    @property
    def total_chapters(self) -> int:
        return sum(v.chapter_count for v in self._volumes)

    @property
    def translated_chapters(self) -> int:
        return sum(v.translated_chapters for v in self._volumes)

    @property
    def translation_progress(self) -> float:
        """Calculate translation progress as percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (self.translated_chapters / self.total_chapters) * 100

    def add_volume(self, volume: Volume) -> None:
        """Add a volume to this work (maintains aggregate consistency)."""
        if volume.work_id is not None and volume.work_id != self.id:
            raise DomainError("Volume belongs to a different work")
        if any(v.volume_number == volume.volume_number for v in self._volumes):
            raise DomainError(f"Volume {volume.volume_number} already exists")
        volume.work_id = self.id
        self._volumes.append(volume)
        self._touch()

    def get_volume(self, volume_number: int) -> Optional[Volume]:
        """Get volume by number."""
        return next((v for v in self._volumes if v.volume_number == volume_number), None)

    def remove_volume(self, volume_number: int) -> bool:
        """Remove volume by number."""
        volume = self.get_volume(volume_number)
        if volume:
            self._volumes.remove(volume)
            self._touch()
            return True
        return False

    def update_metadata(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        title_translated: Optional[str] = None,
    ) -> None:
        """Update work metadata with validation."""
        if title is not None:
            if not title.strip():
                raise DomainError("Work title cannot be empty")
            self.title = title
        if author is not None:
            self.author = author
        if title_translated is not None:
            self.title_translated = title_translated
        self._touch()

    def _touch(self) -> None:
        """Update modification timestamp."""
        self.updated_at = datetime.utcnow()