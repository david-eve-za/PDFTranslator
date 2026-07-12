"""
Entity Candidate - Extracted entity awaiting validation.

CUPID Principle: Predictable
- Immutable once created
- Self-validating (frequency, confidence bounds)
- Rich domain behavior (context management, embeddings)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid

from .entity import EntityType


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    """
    Entity extracted from source text, pending validation.

    Invariants:
    - text must not be empty after stripping
    - frequency must be >= 1
    - confidence must be in [0.0, 1.0]
    - entity_type must be valid EntityType
    """

    # Identity
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    # Core attributes
    text: str = ""                          # Original entity text
    entity_type: EntityType = EntityType.OTHER
    frequency: int = 1                      # Occurrence count in text
    source_language: str = "en"             # ISO 639-1 source language

    # Context & metadata
    contexts: List[str] = field(default_factory=list)
    confidence: float = 0.5                 # Detection confidence [0, 1]

    # Validation results (populated after LLM validation)
    validated: bool = False
    translation: Optional[str] = None       # Suggested translation

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate invariants after initialization."""
        object.__setattr__(self, "text", self.text.strip())
        if not object.__getattribute__(self, "text"):
            raise ValueError("Entity text cannot be empty")

        if self.frequency < 1:
            raise ValueError("Frequency must be >= 1")

        confidence = object.__getattribute__(self, "confidence")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be in [0.0, 1.0]")

        # Normalize entity_type to EntityType enum
        entity_type = object.__getattribute__(self, "entity_type")
        if isinstance(entity_type, str):
            object.__setattr__(self, "entity_type", EntityType.from_str(entity_type))

    def add_context(self, context: str, max_contexts: int = 5) -> "EntityCandidate":
        """Add context snippet (returns new instance - immutable)."""
        if context not in self.contexts and len(self.contexts) < max_contexts:
            new_contexts = list(self.contexts) + [context[:300]]
            return self._replace(contexts=new_contexts)
        return self

    def with_translation(self, translation: str) -> "EntityCandidate":
        """Add translation suggestion (returns new instance)."""
        return self._replace(
            validated=True,
            translation=translation.strip(),
            validated_at=datetime.utcnow(),
        )

    def with_confidence(self, confidence: float) -> "EntityCandidate":
        """Update confidence (returns new instance)."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be in [0.0, 1.0]")
        return self._replace(confidence=confidence)

    def with_frequency(self, frequency: int) -> "EntityCandidate":
        """Update frequency (returns new instance)."""
        if frequency < 1:
            raise ValueError("Frequency must be >= 1")
        return self._replace(frequency=frequency)

    def _replace(self, **changes) -> "EntityCandidate":
        """Create new instance with updated fields (dataclass replace pattern)."""
        return EntityCandidate(
            id=self.id,
            text=self.text,
            entity_type=self.entity_type,
            frequency=self.frequency,
            source_language=self.source_language,
            contexts=self.contexts,
            confidence=self.confidence,
            validated=self.validated,
            translation=self.translation,
            created_at=self.created_at,
            validated_at=self.validated_at,
            **changes,
        )

    @property
    def embed_text(self) -> str:
        """Text to embed for vector similarity search."""
        ctx = self.contexts[0] if self.contexts else ""
        return f"{self.text} {self.entity_type.value} {ctx}"

    @property
    def key(self) -> str:
        """Unique key for deduplication (lowercase text)."""
        return self.text.lower()

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EntityCandidate):
            return NotImplemented
        return self.id == other.id