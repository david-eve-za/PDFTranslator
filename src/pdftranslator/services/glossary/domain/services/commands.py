"""
Command objects for Glossary Service operations.

CUPID Principle: Predictable
- Explicit command objects for all operations
- Single responsibility per command
- Validated at construction
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from ...models.glossary import GlossaryEntry, GlossaryStatus
from ...models.build_pipeline import BuildPipeline, PipelineStageStatus, BuildPipelineStatus
from ...models.entity import EntityCandidate, EntityType


# =================== COMMANDS ===================

@dataclass(frozen=True, slots=True)
class CreateGlossaryCommand:
    """Create a new glossary for a work."""

    work_id: int
    name: str
    source_lang: str = "en"
    target_lang: str = "es"

    def __post_init__(self):
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.source_lang == self.target_lang:
            raise ValueError("source_lang and target_lang must differ")


@dataclass(frozen=True, slots=True)
class BuildGlossaryCommand:
    """Execute glossary build pipeline."""

    work_id: int
    volume_id: int
    text: str
    source_lang: str = "en"
    target_lang: str = "es"
    min_frequency: int = 2
    suggest_translations: bool = True
    resume: bool = False
    force_restart: bool = False
    dry_run: bool = False

    def __post_init__(self):
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if self.volume_id <= 0:
            raise ValueError("volume_id must be > 0")
        if not self.text.strip():
            raise ValueError("text cannot be empty")
        if self.source_lang == self.target_lang:
            raise ValueError("source_lang and target_lang must differ")
        if self.min_frequency < 1:
            raise ValueError("min_frequency must be >= 1")


@dataclass(frozen=True, slots=True)
class UpdateGlossaryEntryCommand:
    """Update a glossary entry."""

    entry_id: int
    translation: Optional[str] = None
    is_verified: Optional[bool] = None
    confidence: Optional[float] = None
    entity_type: Optional[EntityType] = None
    is_proper_noun: Optional[bool] = None
    do_not_translate: Optional[bool] = None
    context: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SearchGlossaryCommand:
    """Search glossary entries."""

    work_id: int
    query: str
    page: int = 1
    page_size: int = 20
    entity_type: Optional[EntityType] = None
    verified_only: bool = False


@dataclass(frozen=True, slots=True)
class ValidateEntitiesCommand:
    """Validate entities with LLM."""

    entities: List[EntityCandidate]
    source_lang: str
    work_id: int
    volume_id: int
    batch_size: int = 50


@dataclass(frozen=True, slots=True)
class GenerateEmbeddingsCommand:
    """Generate embeddings for entities."""

    entities: List[EntityCandidate]
    model_name: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SuggestTranslationsCommand:
    """Suggest translations for entities."""

    entities: List[EntityCandidate]
    source_lang: str
    target_lang: str
    batch_size: int = 50


@dataclass(frozen=True, slots=True)
class SaveGlossaryEntriesCommand:
    """Save entities to glossary."""

    work_id: int
    entities: List[EntityCandidate]
    source_lang: str
    target_lang: str


@dataclass(frozen=True, slots=True)
class ListPipelinesCommand:
    """List build pipelines."""

    page: int = 1
    page_size: int = 20
    work_id: Optional[int] = None
    status: Optional[BuildPipelineStatus] = None


@dataclass(frozen=True, slots=True)
class GetPipelineStatusCommand:
    """Get pipeline status by work/volume."""

    work_id: int
    volume_id: int


@dataclass(frozen=True, slots=True)
class ResumePipelineCommand:
    """Resume a failed pipeline."""

    work_id: int
    volume_id: int


# =================== RESULTS ===================

@dataclass(frozen=True, slots=True)
class GlossaryBuildResult:
    """Result of glossary build operation."""

    pipeline_id: str
    extracted: int
    validated: int
    embedded: int
    translated: int
    saved: int
    skipped: int
    errors: List[str]
    duration_ms: int

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_processed(self) -> int:
        return self.extracted

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "extracted": self.extracted,
            "validated": self.validated,
            "embedded": self.embedded,
            "translated": self.translated,
            "saved": self.saved,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


# =================== PIPELINE DATA CLASSES ===================

# These are defined in models/build_pipeline.py but included here
# for convenience when importing from this module


# Re-export for convenience
__all__ = [
    "CreateGlossaryCommand",
    "BuildGlossaryCommand",
    "UpdateGlossaryEntryCommand",
    "SearchGlossaryCommand",
    "ValidateEntitiesCommand",
    "GenerateEmbeddingsCommand",
    "SuggestTranslationsCommand",
    "SaveGlossaryEntriesCommand",
    "ListPipelinesCommand",
    "GetPipelineStatusCommand",
    "ResumePipelineCommand",
    "GlossaryBuildResult",
]