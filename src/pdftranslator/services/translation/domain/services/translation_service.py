"""
Translation Domain Service - Business Logic.
"""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass

from ..models.job import TranslationJob, JobStatus, JobPriority
from ..models.segment import Segment
from ..models.glossary_ref import GlossaryReference
from ..repositories.protocols import (
    TranslationJobRepository,
    SegmentRepository,
    TranslationUnitOfWork,
    PaginationParams,
    PaginatedResult,
)
from ..repositories.exceptions import DomainError, NotFoundError


@dataclass
class CreateJobCommand:
    source_lang: str
    target_lang: str
    work_id: int
    volume_id: Optional[int] = None
    source_text: Optional[str] = None
    priority: JobPriority = JobPriority.NORMAL
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None


@dataclass
class CreateSegmentsCommand:
    job_id: int
    segments: List[Segment]


class TranslationService:
    """Domain service for translation operations."""

    def __init__(self, uow: TranslationUnitOfWork):
        self._uow = uow

    # =================== JOB OPERATIONS ===================

    async def create_job(self, command: CreateJobCommand) -> TranslationJob:
        job = TranslationJob(
            source_lang=command.source_lang,
            target_lang=command.target_lang,
            work_id=command.work_id,
            volume_id=command.volume_id,
            source_text=command.source_text,
            priority=command.priority,
            llm_provider=command.llm_provider,
            model_name=command.model_name,
        )

        async with self._uow:
            created = await self._uow.jobs.create(job)
            await self._uow.commit()
            return created

    async def get_job(self, job_id: int) -> TranslationJob:
        job = await self._uow.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Translation job {job_id} not found")

        # Load segments
        segments = await self._uow.segments.get_by_job_id(job_id)
        job._segments = segments
        return job

    async def get_job_by_uuid(self, uuid: str) -> TranslationJob:
        job = await self._uow.jobs.get_by_uuid(uuid)
        if not job:
            raise NotFoundError(f"Translation job with UUID {uuid} not found")
        return job

    async def list_jobs(
        self,
        pagination: PaginationParams,
        status: Optional[JobStatus] = None,
        work_id: Optional[int] = None,
    ) -> PaginatedResult[TranslationJob]:
        return await self._uow.jobs.get_all(pagination, status, work_id)

    async def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        error_message: Optional[str] = None,
        target_text: Optional[str] = None,
    ) -> TranslationJob:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(job_id)
            if not job:
                raise NotFoundError(f"Translation job {job_id} not found")

            if status == JobStatus.QUEUED:
                job.queue()
            elif status == JobStatus.IN_PROGRESS:
                if not job.llm_provider or not job.model_name:
                    raise DomainError("LLM provider and model required to start")
                job.start(job.llm_provider, job.model_name)
            elif status == JobStatus.COMPLETED:
                job.complete(target_text or "")
            elif status == JobStatus.FAILED:
                job.fail(error_message or "Unknown error")
            elif status == JobStatus.PAUSED:
                job.pause()
            elif status == JobStatus.CANCELLED:
                job.cancel()
            else:
                raise DomainError(f"Invalid status: {status}")

            updated = await self._uow.jobs.update(job)
            await self._uow.commit()
            return updated

    async def delete_job(self, job_id: int) -> bool:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(job_id)
            if not job:
                raise NotFoundError(f"Translation job {job_id} not found")
            deleted = await self._uow.jobs.delete(job_id)
            await self._uow.commit()
            return deleted

    # =================== SEGMENT OPERATIONS ===================

    async def create_segments(self, command: CreateSegmentsCommand) -> List[Segment]:
        async with self._uow:
            job = await self._uow.jobs.get_by_id(command.job_id)
            if not job:
                raise NotFoundError(f"Translation job {command.job_id} not found")

            created_segments = []
            for segment in command.segments:
                job.add_segment(segment)
                created = await self._uow.segments.create(segment)
                created_segments.append(created)

            await self._uow.commit()
            return created_segments

    async def get_segments_for_job(self, job_id: int) -> List[Segment]:
        job = await self._uow.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Translation job {job_id} not found")
        return await self._uow.segments.get_by_job_id(job_id)

    async def get_segment(self, segment_id: int) -> Segment:
        segment = await self._uow.segments.get_by_id(segment_id)
        if not segment:
            raise NotFoundError(f"Segment {segment_id} not found")
        return segment

    async def update_segment_translation(self, segment_id: int, target_text: str) -> Segment:
        async with self._uow:
            segment = await self._uow.segments.get_by_id(segment_id)
            if not segment:
                raise NotFoundError(f"Segment {segment_id} not found")
            segment.set_target_text(target_text)
            updated = await self._uow.segments.update(segment)
            await self._uow.commit()
            return updated