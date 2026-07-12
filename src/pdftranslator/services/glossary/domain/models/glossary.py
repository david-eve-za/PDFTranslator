"""
Glossary aggregate and entry models.

CUPID Principle: Domain-Focused
- Glossary is the aggregate root for translation terms
- Entries are value objects within the aggregate
- Business invariants enforced at aggregate level
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .entity import EntityType


class GlossaryStatus(Enum):
    """Glossary lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    """
    Single glossary term entry.

    Immutable value object - changes create new instances.
    """

    # Identity
    id: Optional[int] = None  # DB-assigned
    uuid: uuid.UUID = field(default_factory=uuid.uuid4)

    # Core attributes
    term: str = ""
    translation: Optional[str] = None
    entity_type: EntityType = EntityType.OTHER

    # Metadata
    is_proper_noun: bool = False
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = 0.0
    frequency: int = 1

    # Context
    context: Optional[str] = None
    notes: Optional[str] = None

    # Language
    source_lang: str = "en"
    target_lang: str = "es"

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        term = self.term.strip()
        if not term:
            raise ValueError("Term cannot be empty")

        translation = self.translation
        if translation is not None:
            translation = translation.strip()
            if not translation:
                object.__setattr__(self, "translation", None)

        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be in [0.0, 1.0]")

        if self.frequency < 1:
            raise ValueError("Frequency must be >= 1")

        if self.source_lang == self.target_lang:
            raise ValueError("Source and target languages must differ")

        # Normalize entity_type
        etype = self.entity_type
        if isinstance(etype, str):
            object.__setattr__(self, "entity_type", EntityType.from_str(etype))

    @property
    def key(self) -> str:
        """Deduplication key (lowercase term)."""
        return self.term.lower()

    @property
    def effective_translation(self) -> str:
        """Get effective translation (original if do_not_translate)."""
        if self.do_not_translate or not self.translation:
            return self.term
        return self.translation

    def with_translation(self, translation: str) -> "GlossaryEntry":
        """Create entry with updated translation."""
        return GlossaryEntry(
            id=self.id,
            uuid=self.uuid,
            term=self.term,
            translation=translation.strip(),
            entity_type=self.entity_type,
            is_proper_noun=self.is_proper_noun,
            do_not_translate=self.do_not_translate,
            is_verified=self.is_verified,
            confidence=self.confidence,
            frequency=self.frequency,
            context=self.context,
            notes=self.notes,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def with_verification(self, verified: bool) -> "GlossaryEntry":
        """Create entry with updated verification status."""
        return GlossaryEntry(
            id=self.id,
            uuid=self.uuid,
            term=self.term,
            translation=self.translation,
            entity_type=self.entity_type,
            is_proper_noun=self.is_proper_noun,
            do_not_translate=self.do_not_translate,
            is_verified=verified,
            confidence=self.confidence,
            frequency=self.frequency,
            context=self.context,
            notes=self.notes,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def with_confidence(self, confidence: float) -> "GlossaryEntry":
        """Create entry with updated confidence."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be in [0.0, 1.0]")
        return GlossaryEntry(
            id=self.id,
            uuid=self.uuid,
            term=self.term,
            translation=self.translation,
            entity_type=self.entity_type,
            is_proper_noun=self.is_proper_noun,
            do_not_translate=self.do_not_translate,
            is_verified=self.is_verified,
            confidence=confidence,
            frequency=self.frequency,
            context=self.context,
            notes=self.notes,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "term": self.term,
            "translation": self.translation,
            "entity_type": self.entity_type.value,
            "is_proper_noun": self.is_proper_noun,
            "do_not_translate": self.do_not_translate,
            "is_verified": self.is_verified,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "context": self.context,
            "notes": self.notes,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "effective_translation": self.effective_translation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class Glossary:
    """
    Glossary aggregate root for a Work.

    Contains all translation terms for a work/language pair.
    Enforces uniqueness and business rules.
    """

    id: Optional[int] = None  # DB-assigned
    uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    work_id: int = 0
    name: str = ""
    source_lang: str = "en"
    target_lang: str = "es"
    status: GlossaryStatus = GlossaryStatus.DRAFT
    entries: Dict[str, GlossaryEntry] = field(default_factory=dict)  # key -> entry
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if not self.name.strip():
            raise ValueError("Glossary name cannot be empty")
        if self.source_lang == self.target_lang:
            raise ValueError("Source and target languages must differ")

    def add_entry(self, entry: GlossaryEntry) -> "Glossary":
        """Add entry, enforcing uniqueness."""
        if entry.key in self.entries:
            raise ValueError(f"Entry '{entry.term}' already exists")
        if entry.source_lang != self.source_lang or entry.target_lang != self.target_lang:
            raise ValueError("Entry language mismatch")
        new_entries = dict(self.entries)
        new_entries[entry.key] = entry
        return self._replace(entries=new_entries, updated_at=datetime.utcnow())

    def remove_entry(self, term: str) -> "Glossary":
        """Remove entry by term."""
        key = term.lower()
        if key not in self.entries:
            raise KeyError(f"Entry '{term}' not found")
        new_entries = dict(self.entries)
        del new_entries[key]
        return self._replace(entries=new_entries, updated_at=datetime.utcnow())

    def update_entry(self, term: str, **changes) -> "Glossary":
        """Update an existing entry."""
        key = term.lower()
        if key not in self.entries:
            raise KeyError(f"Entry '{term}' not found")
        entry = self.entries[key]
        updated = GlossaryEntry(
            id=entry.id,
            uuid=entry.uuid,
            term=changes.get("term", entry.term),
            translation=changes.get("translation", entry.translation),
            entity_type=changes.get("entity_type", entry.entity_type),
            is_proper_noun=changes.get("is_proper_noun", entry.is_proper_noun),
            do_not_translate=changes.get("do_not_translate", entry.do_not_translate),
            is_verified=changes.get("is_verified", entry.is_verified),
            confidence=changes.get("confidence", entry.confidence),
            frequency=changes.get("frequency", entry.frequency),
            context=changes.get("context", entry.context),
            notes=changes.get("notes", entry.notes),
            source_lang=entry.source_lang,
            target_lang=entry.target_lang,
            created_at=entry.created_at,
            updated_at=datetime.utcnow(),
        )
        new_entries = dict(self.entries)
        new_entries[key] = updated
        return self._replace(entries=new_entries, updated_at=datetime.utcnow())

    def get_entry(self, term: str) -> Optional[GlossaryEntry]:
        """Get entry by term (case-insensitive)."""
        return self.entries.get(term.lower())

    def get_entries_by_type(self, entity_type: EntityType) -> List[GlossaryEntry]:
        """Get all entries of a specific type."""
        return [e for e in self.entries.values() if e.entity_type == entity_type]

    def get_verified_entries(self) -> List[GlossaryEntry]:
        """Get all verified entries."""
        return [e for e in self.entries.values() if e.is_verified]

    def get_unverified_entries(self) -> List[GlossaryEntry]:
        """Get all unverified entries."""
        return [e for e in self.entries.values() if not e.is_verified]

    def _replace(self, **changes) -> "Glossary":
        """Create new glossary with updated fields."""
        return Glossary(
            id=self.id,
            uuid=self.uuid,
            work_id=self.work_id,
            name=self.name,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            status=self.status,
            entries=self.entries,
            created_at=self.created_at,
            updated_at=self.updated_at,
            **changes,
        )

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def verified_count(self) -> int:
        return len(self.get_verified_entries())

    @property
    def completion_percent(self) -> float:
        if self.entry_count == 0:
            return 0.0
        return (self.verified_count / self.entry_count) * 100

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "work_id": self.work_id,
            "name": self.name,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "status": self.status.value,
            "entry_count": self.entry_count,
            "verified_count": self.verified_count,
            "completion_percent": self.completion_percent,
            "entries": [e.to_dict() for e in self.entries.values()],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }