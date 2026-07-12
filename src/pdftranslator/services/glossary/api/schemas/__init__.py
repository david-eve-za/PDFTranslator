"""
API Schemas for Glossary Service.

CUPID Principle: Predictable
- Pydantic v2 models with validation
- Clear request/response contracts
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

T = TypeVar('T')


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResult(BaseModel, Generic[T]):
    """Paginated result wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """API paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# GLOSSARY SCHEMAS
# ============================================================================

class GlossaryBase(BaseSchema):
    """Base glossary fields."""
    name: str = Field(..., min_length=1, max_length=200)
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    target_lang: str = Field(default="es", pattern=r"^[a-z]{2,3}$")


class GlossaryCreate(GlossaryBase):
    """Request to create a glossary."""
    work_id: int = Field(..., gt=0)


class GlossaryUpdate(BaseSchema):
    """Request to update a glossary."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = Field(None, pattern=r"^(draft|active|archived)$")


class GlossaryResponse(GlossaryBase):
    """Glossary response."""
    id: int
    uuid: UUID
    work_id: int
    status: str
    entry_count: int
    verified_count: int
    completion_percent: float
    created_at: datetime
    updated_at: datetime


class GlossaryDetailResponse(GlossaryResponse):
    """Glossary response with entries."""
    entries: List["GlossaryEntryResponse"] = Field(default_factory=list)


# ============================================================================
# GLOSSARY ENTRY SCHEMAS
# ============================================================================

class GlossaryEntryBase(BaseSchema):
    """Base glossary entry fields."""
    term: str = Field(..., min_length=1, max_length=200)
    translation: Optional[str] = Field(None, max_length=500)
    entity_type: str = Field(default="other")
    is_proper_noun: bool = False
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    frequency: int = Field(default=1, ge=1)
    context: Optional[str] = None
    notes: Optional[str] = None
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    target_lang: str = Field(default="es", pattern=r"^[a-z]{2,3}$")


class GlossaryEntryCreate(GlossaryEntryBase):
    """Request to create a glossary entry."""
    pass


class GlossaryEntryUpdate(BaseSchema):
    """Request to update a glossary entry."""
    translation: Optional[str] = Field(None, max_length=500)
    is_verified: Optional[bool] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    entity_type: Optional[str] = None
    is_proper_noun: Optional[bool] = None
    do_not_translate: Optional[bool] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class GlossaryEntryResponse(GlossaryEntryBase):
    """Glossary entry response."""
    id: int
    uuid: UUID
    work_id: int
    effective_translation: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# BUILD PIPELINE SCHEMAS
# ============================================================================

class BuildGlossaryRequest(BaseSchema):
    """Request to build glossary."""
    work_id: int = Field(..., gt=0)
    volume_id: int = Field(..., gt=0)
    text: str = Field(..., min_length=1)
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    target_lang: str = Field(default="es", pattern=r"^[a-z]{2,3}$")
    min_frequency: int = Field(default=2, ge=1)
    suggest_translations: bool = True
    resume: bool = False
    force_restart: bool = False


class StageExecutionResponse(BaseSchema):
    """Single pipeline stage execution status."""
    name: str
    status: str
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0


class BuildPipelineResponse(BaseSchema):
    """Build pipeline status response."""
    id: UUID
    work_id: int
    volume_id: int
    source_lang: str
    target_lang: str
    min_frequency: int
    dry_run: bool
    status: str
    progress_percent: float
    stages: List[StageExecutionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GlossaryBuildResultResponse(BaseSchema):
    """Glossary build result."""
    work_id: int
    volume_id: int
    entities_extracted: int
    entities_filtered: int
    entities_validated: int
    entities_embedded: int
    entities_translated: int
    entities_saved: int
    duration_seconds: float
    status: str
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()


# ============================================================================
# INDIVIDUAL STAGE SCHEMAS
# ============================================================================

class EntityCandidateResponse(BaseSchema):
    """Entity candidate in API response."""
    id: Optional[str] = None
    text: str
    entity_type: str
    frequency: int
    source_language: str
    contexts: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    validated: bool = False
    translation: Optional[str] = None


# Stage 1: Extract
class ExtractEntitiesRequest(BaseSchema):
    """Request to extract entities from text."""
    text: str = Field(..., min_length=1)
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    min_frequency: int = Field(default=2, ge=1)


class ExtractEntitiesResponse(BaseSchema):
    """Response with extracted entities."""
    entities: List[EntityCandidateResponse]
    total: int


# Stage 2: Filter
class FilterEntitiesRequest(BaseSchema):
    """Request to filter entities against existing glossary."""
    work_id: int = Field(..., gt=0)
    entities: List[EntityCandidateResponse]


class FilterEntitiesResponse(BaseSchema):
    """Response with filtered entities."""
    new_entities: List[EntityCandidateResponse]
    skipped_count: int


# Stage 3: Validate
class ValidateEntitiesRequest(BaseSchema):
    """Request to validate entities with LLM."""
    entities: List[EntityCandidateResponse]
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    work_id: int = Field(..., gt=0)
    volume_id: int = Field(..., gt=0)
    batch_size: int = Field(default=50, ge=1, le=200)


class ValidateEntitiesResponse(BaseSchema):
    """Response with validated entities."""
    validated_entities: List[EntityCandidateResponse]
    rejected_count: int


# Stage 4: Embed
class GenerateEmbeddingsRequest(BaseSchema):
    """Request to generate embeddings."""
    entities: List[EntityCandidateResponse]
    model_name: Optional[str] = None


class GenerateEmbeddingsResponse(BaseSchema):
    """Response with entities that have embeddings."""
    entities_with_embeddings: List[EntityCandidateResponse]


# Stage 5: Translate
class SuggestTranslationsRequest(BaseSchema):
    """Request to suggest translations."""
    entities: List[EntityCandidateResponse]
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    target_lang: str = Field(default="es", pattern=r"^[a-z]{2,3}$")
    batch_size: int = Field(default=50, ge=1, le=200)


class SuggestTranslationsResponse(BaseSchema):
    """Response with translated entities."""
    translated_entities: List[EntityCandidateResponse]


# Stage 6: Store
class SaveEntitiesRequest(BaseSchema):
    """Request to save entities to glossary."""
    work_id: int = Field(..., gt=0)
    entities: List[EntityCandidateResponse]
    source_lang: str = Field(default="en", pattern=r"^[a-z]{2,3}$")
    target_lang: str = Field(default="es", pattern=r"^[a-z]{2,3}$")


class SaveEntitiesResponse(BaseSchema):
    """Response after saving entities."""
    saved_count: int


# ============================================================================
# SEARCH SCHEMAS
# ============================================================================

class SearchGlossaryRequest(BaseSchema):
    """Request to search glossary."""
    work_id: int
    query: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    entity_type: Optional[str] = None
    verified_only: bool = False


class ListPipelinesRequest(BaseSchema):
    """Request to list pipelines."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    work_id: Optional[int] = None
    status: Optional[str] = None


# ============================================================================
# MODEL REBUILD
# ============================================================================

GlossaryDetailResponse.model_rebuild()
PaginatedResponse.model_rebuild()

# Fix forward references
from typing import Generic, TypeVar
T = TypeVar('T')