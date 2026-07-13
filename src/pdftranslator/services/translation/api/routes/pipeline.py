"""
Translation Pipeline API Routes.

CUPID Principle: Composable
- Each stage independently testable
- Clear request/response contracts via Pydantic
- State machine for pipeline stages
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from ...domain.services.translation_service import TranslationService
from ...domain.services.commands import (
    DetectLanguageCommand,
    SegmentTextCommand,
    TranslateSegmentsCommand,
    QualityCheckCommand,
    StoreTranslationsCommand,
    CreatePipelineCommand,
    GetPipelineStatusCommand,
    ResumePipelineCommand,
)
from ...domain.repositories.exceptions import NotFoundError, DomainError
from ..schemas.pipeline import (
    DetectLanguageRequest,
    DetectLanguageResponse,
    SegmentTextRequest,
    SegmentTextResponse,
    TranslateSegmentsRequest,
    TranslateSegmentsResponse,
    QualityCheckRequest,
    QualityCheckResponse,
    StoreTranslationsRequest,
    StoreTranslationsResponse,
    CreatePipelineRequest,
    TranslationPipelineResultResponse,
    TranslationPipelineResponse,
    ResumePipelineRequest,
)
from ..dependencies import get_translation_service


router = APIRouter(prefix="/pipelines", tags=["translation-pipelines"])


# =================== INDIVIDUAL STAGE ENDPOINTS ===================

@router.post(
    "/stages/detect",
    response_model=DetectLanguageResponse,
    summary="Stage 1: Detect language",
)
async def detect_language(
    request: DetectLanguageRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> DetectLanguageResponse:
    """
    Stage 1: Detect source language and analyze text properties.

    This endpoint can be called independently for testing/debugging.
    """
    command = DetectLanguageCommand(
        text=request.text,
        job_id=request.job_id,
        work_id=request.work_id,
        volume_id=request.volume_id,
    )
    try:
        result = await translation_service.detect_language(command)
        return DetectLanguageResponse(
            detected_lang=result.detected_lang,
            confidence=result.confidence,
            text_stats=result.text_stats,
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/stages/segment",
    response_model=SegmentTextResponse,
    summary="Stage 2: Segment text",
)
async def segment_text(
    request: SegmentTextRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> SegmentTextResponse:
    """
    Stage 2: Segment text into translation units.

    Splits text by sentences, respecting max segment length.
    Returns created segments (not yet persisted).
    """
    command = SegmentTextCommand(
        text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        job_id=request.job_id,
        max_segment_length=request.max_segment_length,
        split_by_sentences=request.split_by_sentences,
    )
    try:
        result = await translation_service.segment_text(command)
        return SegmentTextResponse(
            total_segments=result.total_segments,
            total_chars=result.total_chars,
            segments=[
                {
                    "segment_number": s.segment_number,
                    "source_text": s.source_text,
                    "word_count": s.word_count_source,
                }
                for s in result.segments
            ],
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/stages/translate",
    response_model=TranslateSegmentsResponse,
    summary="Stage 3: Translate segments",
)
async def translate_segments(
    request: TranslateSegmentsRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> TranslateSegmentsResponse:
    """
    Stage 3: Translate segments using LLM.

    Uses job's LLM provider and model if not specified.
    Can translate specific segments or all untranslated.
    """
    command = TranslateSegmentsCommand(
        job_id=request.job_id,
        llm_provider=request.llm_provider,
        model_name=request.model_name,
        segment_ids=request.segment_ids,
        glossary_ids=request.glossary_ids,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    try:
        result = await translation_service.translate_segments(command)
        return TranslateSegmentsResponse(
            translated_count=result.translated_count,
            failed_count=result.failed_count,
            errors=result.errors,
            duration_ms=result.duration_ms,
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/stages/quality-check",
    response_model=QualityCheckResponse,
    summary="Stage 4: Quality check translations",
)
async def quality_check(
    request: QualityCheckRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> QualityCheckResponse:
    """
    Stage 4: Quality check translations.

    Runs configurable checks: completeness, terminology, fluency, consistency, formatting.
    """
    command = QualityCheckCommand(
        job_id=request.job_id,
        check_types=request.check_types,
        segment_ids=request.segment_ids,
        threshold=request.threshold,
    )
    try:
        result = await translation_service.quality_check(command)
        return QualityCheckResponse(
            checked_count=result.checked_count,
            passed_count=result.passed_count,
            failed_count=result.failed_count,
            issues=result.issues,
            overall_score=result.overall_score,
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/stages/store",
    response_model=StoreTranslationsResponse,
    summary="Stage 5: Store translations",
)
async def store_translations(
    request: StoreTranslationsRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> StoreTranslationsResponse:
    """
    Stage 5: Store translated segments and update job status.

    Marks job as completed if all segments translated.
    """
    command = StoreTranslationsCommand(
        job_id=request.job_id,
        segment_ids=request.segment_ids,
        overwrite=request.overwrite,
    )
    try:
        result = await translation_service.store_translations(command)
        return StoreTranslationsResponse(
            stored_count=result.stored_count,
            errors=result.errors,
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =================== FULL PIPELINE ===================

@router.post(
    "/run",
    response_model=TranslationPipelineResultResponse,
    summary="Execute full 5-stage translation pipeline",
)
async def run_pipeline(
    request: CreatePipelineRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> TranslationPipelineResultResponse:
    """
    Execute full translation pipeline.

    Stages:
    1. Detect - Language detection
    2. Segment - Text segmentation
    3. Translate - LLM translation
    4. Quality-check - Quality assessment
    5. Store - Persist translations
    """
    command = CreatePipelineCommand(
        job_id=request.job_id,
        work_id=request.work_id,
        volume_id=request.volume_id,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
    )
    # Store source_text for pipeline execution
    if request.source_text:
        command.source_text = request.source_text

    try:
        result = await translation_service.run_pipeline(command)
        return TranslationPipelineResultResponse(
            pipeline_id=result.pipeline_id,
            job_id=result.job_id,
            stages_completed=result.stages_completed,
            stages_skipped=result.stages_skipped,
            errors=result.errors,
            duration_ms=result.duration_ms,
            success=result.success,
        )
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{job_id}",
    response_model=TranslationPipelineResponse,
    summary="Get pipeline status",
)
async def get_pipeline_status(
    job_id: int,
    translation_service: TranslationService = Depends(get_translation_service),
) -> TranslationPipelineResponse:
    """Get pipeline status for a job."""
    command = GetPipelineStatusCommand(job_id=job_id)
    try:
        result = await translation_service.get_pipeline_status(command)
        return TranslationPipelineResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{job_id}/resume",
    response_model=TranslationPipelineResponse,
    summary="Resume failed/paused pipeline",
)
async def resume_pipeline(
    job_id: int,
    request: ResumePipelineRequest,
    translation_service: TranslationService = Depends(get_translation_service),
) -> TranslationPipelineResponse:
    """Resume a failed or paused pipeline from a specific stage."""
    command = ResumePipelineCommand(job_id=job_id, from_stage=request.from_stage)
    try:
        result = await translation_service.resume_pipeline(command)
        return TranslationPipelineResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))