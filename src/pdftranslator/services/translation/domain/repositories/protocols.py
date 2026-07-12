"""
Repository Protocols for Translation Domain.

CUPID Principle: Composable - Protocol-based DI.
"""

from __future__ import annotations
from typing import Optional, List, Protocol
from dataclasses import dataclass

from ..models.job import TranslationJob, JobStatus
from ..models.segment import Segment
from ..models.glossary_ref import GlossaryReference


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


class TranslationJobRepository(Protocol):
    async def get_by_id(self, job_id: int) -> Optional[TranslationJob]: ...
    async def get_by_uuid(self, uuid: str) -> Optional[TranslationJob]: ...
    async def get_all(self, pagination: PaginationParams, status: Optional[JobStatus] = None, work_id: Optional[int] = None) -> PaginatedResult[TranslationJob]: ...
    async def create(self, job: TranslationJob) -> TranslationJob: ...
    async def update(self, job: TranslationJob) -> TranslationJob: ...
    async def delete(self, job_id: int) -> bool: ...


class SegmentRepository(Protocol):
    async def get_by_id(self, segment_id: int) -> Optional[Segment]: ...
    async def get_by_job_id(self, job_id: int) -> List[Segment]: ...
    async def create(self, segment: Segment) -> Segment: ...
    async def update(self, segment: Segment) -> Segment: ...
    async def delete(self, segment_id: int) -> bool: ...


class TranslationUnitOfWork(Protocol):
    @property
    def jobs(self) -> TranslationJobRepository: ...
    @property
    def segments(self) -> SegmentRepository: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> TranslationUnitOfWork: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...