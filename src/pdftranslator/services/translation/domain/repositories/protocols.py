"""
Repository Protocols for Translation Domain.

CUPID Principle: Composable - Protocol-based DI.
"""

from __future__ import annotations
from typing import Optional, List, Protocol, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..models.job import TranslationJob
    from ..models.segment import Segment
    from ..models.glossary_ref import GlossaryReference
from ..models.enums import JobStatus, JobPriority


@dataclass(frozen=True)
class PaginationParams:
    page: int = 1
    page_size: int = 20

    def __post_init__(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class PaginatedResult:
    items: List
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True)
class PipelineStageResult:
    """Result of a pipeline stage execution."""
    stage: str
    status: str  # pending, running, completed, failed, skipped
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: int = 0


class TranslationPipelineRepository(Protocol):
    async def get_by_job_id(self, job_id: int) -> Optional[TranslationPipeline]: ...
    async def create(self, pipeline: TranslationPipeline) -> TranslationPipeline: ...
    async def update(self, pipeline: TranslationPipeline) -> TranslationPipeline: ...
    async def delete(self, pipeline_id: str) -> bool: ...


class TranslationPipelineStageRepository(Protocol):
    async def get_by_pipeline_id(self, pipeline_id: str) -> List[PipelineStage]: ...
    async def create(self, stage: PipelineStage) -> PipelineStage: ...
    async def update(self, stage: PipelineStage) -> PipelineStage: ...


@dataclass
class TranslationPipeline:
    """Translation pipeline aggregate."""
    id: str  # UUID
    job_id: int
    work_id: int
    volume_id: Optional[int]
    source_lang: str
    target_lang: str
    status: str = "pending"  # pending, running, completed, failed, paused, cancelled
    current_stage: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())


@dataclass
class PipelineStage:
    """Pipeline stage entity."""
    id: Optional[int]
    pipeline_id: str
    name: str  # detect, segment, translate, quality_check, store
    status: str = "pending"  # pending, running, completed, failed, skipped
    input_data: Optional[str] = None  # JSON
    output_data: Optional[str] = None  # JSON
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class TranslationUnitOfWork(Protocol):
    @property
    def jobs(self) -> TranslationJobRepository: ...
    @property
    def segments(self) -> SegmentRepository: ...
    @property
    def pipelines(self) -> TranslationPipelineRepository: ...
    @property
    def pipeline_stages(self) -> TranslationPipelineStageRepository: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> TranslationUnitOfWork: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...


class TranslationJobRepository(Protocol):
    async def get_by_id(self, job_id: int) -> Optional[TranslationJob]: ...
    async def get_by_uuid(self, uuid: str) -> Optional[TranslationJob]: ...
    async def list(self, params: PaginationParams, status: Optional[str] = None, work_id: Optional[int] = None) -> PaginatedResult: ...
    async def create(self, job: TranslationJob) -> TranslationJob: ...
    async def update(self, job: TranslationJob) -> TranslationJob: ...
    async def delete(self, job_id: int) -> bool: ...


class SegmentRepository(Protocol):
    async def get_by_job_id(self, job_id: int) -> List[Segment]: ...
    async def get_by_id(self, segment_id: int) -> Optional[Segment]: ...
    async def create(self, segment: Segment) -> Segment: ...
    async def update(self, segment: Segment) -> Segment: ...
    async def delete_by_job_id(self, job_id: int) -> bool: ...