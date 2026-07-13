"""
Command objects for Translation Service operations.

CUPID Principle: Predictable
- Explicit command objects for all operations
- Single responsibility per command
- Validated at construction
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from ..models.job import TranslationJob, JobStatus, JobPriority
from ..models.segment import Segment
from ..models.glossary_ref import GlossaryReference


# =================== COMMANDS ===================

@dataclass(frozen=True, slots=True)
class CreateJobCommand:
    """Create a new translation job."""

    source_lang: str
    target_lang: str
    work_id: int
    volume_id: Optional[int] = None
    source_text: Optional[str] = None
    priority: JobPriority = JobPriority.NORMAL
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None

    def __post_init__(self):
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if self.source_lang == self.target_lang:
            raise ValueError("source_lang and target_lang must differ")
        if len(self.source_lang) != 2 or len(self.target_lang) != 2:
            raise ValueError("Languages must be ISO 639-1 codes (2 chars)")


@dataclass(frozen=True, slots=True)
class CreateSegmentsCommand:
    """Create multiple segments for a job."""

    job_id: int
    segments: List[Segment]


# =================== PIPELINE STAGE COMMANDS ===================

@dataclass(frozen=True, slots=True)
class DetectLanguageCommand:
    """Stage 1: Detect source language and text properties."""

    text: str
    job_id: Optional[int] = None
    work_id: Optional[int] = None
    volume_id: Optional[int] = None

    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")
        if sum(x is not None for x in [self.job_id, self.work_id]) == 0:
            raise ValueError("Either job_id or work_id must be provided")


@dataclass(frozen=True, slots=True)
class SegmentTextCommand:
    """Stage 2: Segment text into translation units."""

    text: str
    source_lang: str
    target_lang: str
    job_id: int
    max_segment_length: int = 2000
    split_by_sentences: bool = True

    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")
        if len(self.source_lang) != 2 or len(self.target_lang) != 2:
            raise ValueError("Languages must be ISO 639-1 codes")
        if self.source_lang == self.target_lang:
            raise ValueError("Source and target languages must differ")
        if self.max_segment_length < 10:
            raise ValueError("max_segment_length must be >= 10")


@dataclass(frozen=True, slots=True)
class TranslateSegmentsCommand:
    """Stage 3: Translate segments using LLM."""

    job_id: int
    llm_provider: str
    model_name: str
    segment_ids: Optional[List[int]] = None  # None = all untranslated segments
    glossary_ids: Optional[List[int]] = None
    temperature: float = 0.3
    max_tokens: int = 4000

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")
        if not self.llm_provider or not self.llm_provider.strip():
            raise ValueError("llm_provider is required")
        if not self.model_name or not self.model_name.strip():
            raise ValueError("model_name is required")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")


@dataclass(frozen=True, slots=True)
class QualityCheckCommand:
    """Stage 4: Quality check translations."""

    job_id: int
    check_types: List[str] = field(default_factory=lambda: ["completeness", "terminology", "fluency"])
    segment_ids: Optional[List[int]] = None
    threshold: float = 0.7

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")
        if self.threshold < 0.0 or self.threshold > 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        valid_checks = {"completeness", "terminology", "fluency", "consistency", "formatting"}
        for check in self.check_types:
            if check not in valid_checks:
                raise ValueError(f"Invalid check type: {check}. Valid: {valid_checks}")


@dataclass(frozen=True, slots=True)
class StoreTranslationsCommand:
    """Stage 5: Store translated segments."""

    job_id: int
    segment_ids: Optional[List[int]] = None
    overwrite: bool = True

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")


# =================== PIPELINE MANAGEMENT COMMANDS ===================

@dataclass(frozen=True, slots=True)
class CreatePipelineCommand:
    """Create a new translation pipeline for a job."""

    job_id: int
    work_id: int
    source_lang: str
    target_lang: str
    volume_id: Optional[int] = None
    source_text: Optional[str] = None

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")
        if self.work_id <= 0:
            raise ValueError("work_id must be > 0")
        if len(self.source_lang) != 2 or len(self.target_lang) != 2:
            raise ValueError("Languages must be ISO 639-1 codes")


@dataclass(frozen=True, slots=True)
class GetPipelineStatusCommand:
    """Get pipeline status by job_id."""

    job_id: int

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")


@dataclass(frozen=True, slots=True)
class ResumePipelineCommand:
    """Resume a failed/paused pipeline."""

    job_id: int
    from_stage: Optional[str] = None

    def __post_init__(self):
        if self.job_id <= 0:
            raise ValueError("job_id must be > 0")
        if self.from_stage and self.from_stage not in ["detect", "segment", "translate", "quality_check", "store"]:
            raise ValueError("Invalid from_stage")


# =================== RESULTS ===================

@dataclass(frozen=True, slots=True)
class DetectLanguageResult:
    """Result of language detection."""

    detected_lang: str
    confidence: float
    text_stats: dict  # char_count, word_count, etc.


@dataclass(frozen=True, slots=True)
class SegmentTextResult:
    """Result of text segmentation."""

    segments: List[Segment]
    total_segments: int
    total_chars: int


@dataclass(frozen=True, slots=True)
class TranslateSegmentsResult:
    """Result of segment translation."""

    translated_count: int
    failed_count: int
    errors: List[str]
    duration_ms: int


@dataclass(frozen=True, slots=True)
class QualityCheckResult:
    """Result of quality check."""

    checked_count: int
    passed_count: int
    failed_count: int
    issues: List[dict]  # segment_id, check_type, severity, message
    overall_score: float


@dataclass(frozen=True, slots=True)
class StoreTranslationsResult:
    """Result of storing translations."""

    stored_count: int
    errors: List[str]


@dataclass(frozen=True, slots=True)
class TranslationPipelineResult:
    """Result of full pipeline execution."""

    pipeline_id: str
    job_id: int
    stages_completed: List[str]
    stages_skipped: List[str]
    errors: List[str]
    duration_ms: int

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# Re-export commonly used
__all__ = [
    "CreateJobCommand",
    "CreateSegmentsCommand",
    "DetectLanguageCommand",
    "SegmentTextCommand",
    "TranslateSegmentsCommand",
    "QualityCheckCommand",
    "StoreTranslationsCommand",
    "CreatePipelineCommand",
    "GetPipelineStatusCommand",
    "ResumePipelineCommand",
    "DetectLanguageResult",
    "SegmentTextResult",
    "TranslateSegmentsResult",
    "QualityCheckResult",
    "StoreTranslationsResult",
    "TranslationPipelineResult",
]