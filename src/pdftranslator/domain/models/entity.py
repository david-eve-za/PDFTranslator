"""Domain models for entity extraction and glossary building.

Maps from SQL schema:
- glossary_build_progress -> GlossaryBuildProgress
- entity_blacklist -> EntityBlacklist
- fantasy_terms -> FantasyTerm

EntityCandidate and BuildResult are pipeline-only (no SQL table).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EntityCandidate:
    text: str = ""
    entity_type: str = "other"
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"
    translation: str | None = None
    validated: bool = False

    def add_context(self, context: str) -> None:
        if context and context not in self.contexts:
            self.contexts.append(context[:300])

    def best_context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    def to_embed_text(self) -> str:
        return f"{self.text} {self.entity_type} {self.best_context()}"


@dataclass
class BuildResult:
    extracted: int = 0
    new: int = 0
    skipped: int = 0
    entities_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class GlossaryBuildProgress:
    id: int | None = None
    work_id: int | None = None
    volume_id: int | None = None
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
        return self.phase == "saved"

    def next_phase(self) -> str | None:
        phases = ["extracted", "validated", "translated", "saved"]
        if self.phase not in phases:
            return phases[0]
        current = phases.index(self.phase)
        if current >= len(phases) - 1:
            return None
        return phases[current + 1]


@dataclass
class EntityBlacklist:
    id: int | None = None
    term: str = ""
    reason: str | None = None


@dataclass
class FantasyTerm:
    id: int | None = None
    term: str = ""
    entity_type: str = "other"
    do_not_translate: bool = False
    context_hint: str | None = None
