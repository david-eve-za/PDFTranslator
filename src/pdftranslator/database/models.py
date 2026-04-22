"""
DEPRECATED: Use models.work instead.
This module is kept for backward compatibility.

The following classes are now in models.work:
- Work
- Volume
- Chapter
- GlossaryEntry

Other classes remain here until migrated.
"""

# Backward compatibility imports
# Classes that remain in this module (not yet migrated)
from dataclasses import dataclass, field
from datetime import datetime

from pdftranslator.core.models.work import Chapter, GlossaryEntry, Volume, Work


@dataclass
class UploadedFile:
    """Represents an uploaded file pending processing."""

    id: int | None = None
    filename: str = ""
    original_name: str = ""
    file_path: str | None = None
    file_size: int = 0
    file_type: str = ""
    mime_type: str | None = None
    work_id: int | None = None
    volume_id: int | None = None
    status: str = "uploaded"
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __repr__(self) -> str:
        return f"UploadedFile(id={self.id}, filename='{self.filename}', status='{self.status}')"


@dataclass
class ContextExample:
    id: int | None
    context_id: int
    original_sentence: str
    translated_sentence: str
    chapter_id: int | None = None


@dataclass
class TermContext:
    id: int | None
    term_id: int
    context_hint: str
    translation: str
    example_usage: str | None = None
    examples: list[ContextExample] = field(default_factory=list)


@dataclass
class EntityBlacklist:
    id: int | None
    term: str
    reason: str | None = None


@dataclass
class FantasyTerm:
    id: int | None
    term: str
    entity_type: str
    do_not_translate: bool = False
    context_hint: str | None = None


@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"
    translation: str | None = None
    validated: bool = False

    def add_context(self, context: str):
        if context not in self.contexts:
            self.contexts.append(context[:300])

    def best_context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    def to_embed_text(self) -> str:
        return f"{self.text} {self.entity_type} {self.best_context()}"


@dataclass
class BuildResult:
    extracted: int
    new: int
    skipped: int
    entities_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class GlossaryBuildProgress:
    """Tracks progress of glossary build pipeline for a single entity."""

    id: int | None = None
    work_id: int = 0
    volume_id: int = 0
    entity_text: str = ""
    phase: str = "extracted"
    entity_type: str | None = None
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    translation: str | None = None
    embedding: list[float] | None = None
    validation_batch: int | None = None
    translation_batch: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_complete(self) -> bool:
        """Check if the entity has completed all pipeline phases."""
        return self.phase == "saved"

    def next_phase(self) -> str | None:
        """Get the next phase in the pipeline, or None if complete."""
        phases = ["extracted", "validated", "translated", "saved"]
        if self.phase in phases:
            idx = phases.index(self.phase)
            return phases[idx + 1] if idx < len(phases) - 1 else None
        return None


@dataclass
class SubstitutionRule:
    """Text substitution rule with regex pattern."""

    id: int | None = None
    name: str = ""
    pattern: str = ""
    replacement: str = ""
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


__all__ = [
    # From models.work (backward compatibility)
    "Work",
    "Volume",
    "Chapter",
    "GlossaryEntry",
    # From this module
    "UploadedFile",
    "ContextExample",
    "TermContext",
    "EntityBlacklist",
    "FantasyTerm",
    "EntityCandidate",
    "BuildResult",
    "GlossaryBuildProgress",
    "SubstitutionRule",
]
