"""
Translation Job API Routes.
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...domain.services.translation_service import TranslationService, CreateJobCommand
from ...domain.models.job import JobStatus, JobPriority
from ...domain.repositories.exceptions import NotFoundError, DomainError
from ...domain.repositories.protocols import PaginationParams
from ..schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse, SegmentSummary, GlossaryRefSchema
from ..dependencies import get_translation_service


router = APIRouter(prefix="/jobs", tags=["translation-jobs"])


@router.get("", response_model=JobListResponse, summary="List translation jobs")
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = Query(None),
    work_id: Optional[int] = Query(None, gt=0),
    translation_service: TranslationService = Depends(get_translation_service),
) -> JobListResponse:
    """List translation jobs with pagination and filtering."""
    pagination = PaginationParams(page=page, page_size=page_size)
    result = await translation_service.list_jobs(pagination, status, work_id)

    return JobListResponse(
        items=[_job_to_response(j) for j in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/{job_id}", response_model=JobResponse, summary="Get job by ID")
async def get_job(
    job_id: int,
    translation_service: TranslationService = Depends(get_translation_service),
) -> JobResponse:
    """Get translation job by ID with all segments loaded."""
    try:
        job = await translation_service.get_job(job_id)
        return _job_to_response(job)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{job_id}/segments", response_model=List[SegmentSummary], summary="Get segments for job")
async def get_job_segments(
    job_id: int,
    translation_service: TranslationService = Depends(get_translation_service),
) -> List[SegmentSummary]:
    """Get all segments for a translation job."""
    try:
        segments = await translation_service.get_segments_for_job(job_id)
        return [
            SegmentSummary(
                id=s.id,
                segment_number=s.segment_number,
                is_translated=s.is_translated,
                word_count_source=s.word_count_source,
                word_count_target=s.word_count_target,
            )
            for s in segments
        ]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED, summary="Create translation job")
async def create_job(
    job_data: JobCreate,
    translation_service: TranslationService = Depends(get_translation_service),
) -> JobResponse:
    """Create a new translation job."""
    try:
        command = CreateJobCommand(
            source_lang=job_data.source_lang,
            target_lang=job_data.target_lang,
            work_id=job_data.work_id,
            volume_id=job_data.volume_id,
            source_text=job_data.source_text,
            priority=job_data.priority,
            llm_provider=job_data.llm_provider,
            model_name=job_data.model_name,
        )
        job = await translation_service.create_job(command)
        return _job_to_response(job)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{job_id}/status", response_model=JobResponse, summary="Update job status")
async def update_job_status(
    job_id: int,
    status: JobStatus,
    error_message: Optional[str] = None,
    target_text: Optional[str] = None,
    translation_service: TranslationService = Depends(get_translation_service),
) -> JobResponse:
    """Update job status (queue, start, complete, fail, pause, resume, cancel)."""
    try:
        job = await translation_service.update_job_status(job_id, status, error_message, target_text)
        return _job_to_response(job)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete job")
async def delete_job(
    job_id: int,
    translation_service: TranslationService = Depends(get_translation_service),
) -> None:
    """Delete a translation job and all its segments."""
    try:
        await translation_service.delete_job(job_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _job_to_response(job) -> JobResponse:
    return JobResponse(
        id=job.id,
        uuid=str(job.uuid),
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        work_id=job.work_id,
        volume_id=job.volume_id,
        status=job.status,
        priority=job.priority,
        source_text=job.source_text,
        target_text=job.target_text,
        llm_provider=job.llm_provider,
        model_name=job.model_name,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        glossary_refs=[GlossaryRefSchema(**vars(r)) for r in job.glossary_refs],
        segment_count=job.segment_count,
        translated_segment_count=job.translated_segment_count,
        progress=job.progress,
        word_count_source=job.word_count_source,
        word_count_target=job.word_count_target,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )