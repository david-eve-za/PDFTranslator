"""
Pipeline Stage API Schemas for Translation Service.

CUPID Principle: Predictable
- Clear request/response contracts via Pydantic v2
- Validation at boundaries
- Documentation via OpenAPI
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# =================== STAGE 1: DETECT ===================

class DetectLanguageRequest(BaseModel):
    """Request for language detection."""

    text: str = Field(..., min_length=1, description="Text to analyze")
    job_id: Optional[int] = Field(None, gt=0, description="Associated job ID")
    work_id: Optional[int] = Field(None, gt=0, description="Work ID")
    volume_id: Optional[int] = Field(None, gt=0, description="Volume ID")


class DetectLanguageResponse(BaseModel):
    """Response for language detection."""

    detected_lang: str = Field(..., pattern="^[a-z]{2}$", description="ISO 639-1 language code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    text_stats: Dict[str, Any] = Field(default_factory=dict, description="Text statistics")

    model_config = ConfigDict(from_attributes=True)


# =================== STAGE 2: SEGMENT ===================

class SegmentTextRequest(BaseModel):
    """Request for text segmentation."""

    text: str = Field(..., min_length=1, description="Text to segment")
    source_lang: str = Field(..., pattern="^[a-z]{2}$", description="Source language")
    target_lang: str = Field(..., pattern="^[a-z]{2}$", description="Target language")
    job_id: int = Field(..., gt=0, description="Job ID to associate segments with")
    max_segment_length: int = Field(2000, ge=10, le=10000, description="Max characters per segment")
    split_by_sentences: bool = Field(True, description="Split by sentence boundaries")


class SegmentInfo(BaseModel):
    """Segment info in response."""

    segment_number: int
    source_text: str
    word_count: int

    model_config = ConfigDict(from_attributes=True)


class SegmentTextResponse(BaseModel):
    """Response for text segmentation."""

    total_segments: int
    total_chars: int
    segments: List[SegmentInfo] = Field(default_factory=list, description="Created segments")

    model_config = ConfigDict(from_attributes=True)


# =================== STAGE 3: TRANSLATE ===================

class TranslateSegmentsRequest(BaseModel):
    """Request for segment translation."""

    job_id: int = Field(..., gt=0, description="Job ID")
    llm_provider: str = Field(..., min_length=1, description="LLM provider (nvidia, openai, etc.)")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    segment_ids: Optional[List[int]] = Field(None, description="Specific segments to translate (None = all untranslated)")
    glossary_ids: Optional[List[int]] = Field(None, description="Glossary IDs for terminology")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4000, ge=1, le=32000, description="Max output tokens")


class TranslateSegmentsResponse(BaseModel):
    """Response for segment translation."""

    translated_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)
    duration_ms: int

    model_config = ConfigDict(from_attributes=True)


# =================== STAGE 4: QUALITY CHECK ===================

class QualityCheckRequest(BaseModel):
    """Request for quality checking translations."""

    job_id: int = Field(..., gt=0, description="Job ID")
    check_types: List[str] = Field(
        default_factory=lambda: ["completeness", "terminology", "fluency"],
        description="Types of checks: completeness, terminology, fluency, consistency, formatting"
    )
    segment_ids: Optional[List[int]] = Field(None, description="Specific segments to check (None = all translated)")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Quality threshold")


class QualityIssue(BaseModel):
    """Quality check issue."""

    segment_id: int
    segment_number: int
    check_type: str
    severity: str  # error, warning
    message: str


class QualityCheckResponse(BaseModel):
    """Response for quality check."""

    checked_count: int
    passed_count: int
    failed_count: int
    issues: List[QualityIssue] = Field(default_factory=list)
    overall_score: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


# =================== STAGE 5: STORE ===================

class StoreTranslationsRequest(BaseModel):
    """Request for storing translations."""

    job_id: int = Field(..., gt=0, description="Job ID")
    segment_ids: Optional[List[int]] = Field(None, description="Specific segments to store (None = all)")
    overwrite: bool = Field(True, description="Overwrite existing translations")


class StoreTranslationsResponse(BaseModel):
    """Response for storing translations."""

    stored_count: int
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# =================== FULL PIPELINE ===================

class TranslationPipelineStageResponse(BaseModel):
    """Pipeline stage status."""

    name: str
    status: str  # pending, running, completed, failed, skipped
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TranslationPipelineResponse(BaseModel):
    """Pipeline status response."""

    job_id: int
    pipeline_id: str
    status: str
    current_stage: int
    stages: List[TranslationPipelineStageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CreatePipelineRequest(BaseModel):
    """Request to create/run full pipeline."""

    job_id: int = Field(..., gt=0, description="Job ID")
    work_id: int = Field(..., gt=0, description="Work ID")
    volume_id: Optional[int] = Field(None, gt=0, description="Volume ID")
    source_lang: str = Field(..., pattern="^[a-z]{2}$", description="Source language")
    target_lang: str = Field(..., pattern="^[a-z]{2}$", description="Target language")
    source_text: Optional[str] = Field(None, description="Text to translate (optional if job has source_text)")


class TranslationPipelineResultResponse(BaseModel):
    """Full pipeline execution result."""

    pipeline_id: str
    job_id: int
    stages_completed: List[str]
    stages_skipped: List[str]
    errors: List[str]
    duration_ms: int
    success: bool

    model_config = ConfigDict(from_attributes=True)


class ResumePipelineRequest(BaseModel):
    """Request to resume a pipeline."""

    job_id: int = Field(..., gt=0, description="Job ID")
    from_stage: Optional[str] = Field(None, description="Stage to resume from (detect, segment, translate, quality_check, store)")