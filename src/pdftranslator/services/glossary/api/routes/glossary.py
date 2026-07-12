"""
Glossary API Routes.

CUPID Principle: Composable
- Each endpoint is independently testable
- Clear request/response contracts via Pydantic
- State machine for pipeline stages
"""

from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...domain.services.glossary_service import GlossaryService
from ...domain.services.commands import (
    CreateGlossaryCommand,
    BuildGlossaryCommand,
    UpdateGlossaryEntryCommand,
    SearchGlossaryCommand,
    ListPipelinesCommand,
    GetPipelineStatusCommand,
    ResumePipelineCommand,
)
from ...domain.models.entity import EntityCandidate
from ...domain.models.build_pipeline import PipelineStageEnum
from ..schemas import (
    GlossaryCreate,
    GlossaryUpdate,
    GlossaryResponse,
    GlossaryDetailResponse,
    GlossaryEntryCreate,
    GlossaryEntryUpdate,
    GlossaryEntryResponse,
    BuildGlossaryRequest,
    BuildPipelineResponse,
    GlossaryBuildResultResponse,
    ExtractEntitiesRequest,
    ExtractEntitiesResponse,
    FilterEntitiesRequest,
    FilterEntitiesResponse,
    ValidateEntitiesRequest,
    ValidateEntitiesResponse,
    GenerateEmbeddingsRequest,
    GenerateEmbeddingsResponse,
    SuggestTranslationsRequest,
    SuggestTranslationsResponse,
    SaveEntitiesRequest,
    SaveEntitiesResponse,
    SearchGlossaryRequest,
    PaginatedResponse,
    ListPipelinesRequest,
    EntityCandidateResponse,
)
from ..dependencies import get_glossary_service


router = APIRouter(prefix="/glossaries", tags=["glossaries"])


# =================== GLOSSARY CRUD ===================

@router.post(
    "",
    response_model=GlossaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create glossary for a work",
)
async def create_glossary(
    glossary_data: GlossaryCreate,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryResponse:
    """Create a new glossary for a work."""
    try:
        command = CreateGlossaryCommand(
            work_id=glossary_data.work_id,
            name=glossary_data.name,
            source_lang=glossary_data.source_lang,
            target_lang=glossary_data.target_lang,
        )
        glossary = await service.create_glossary(command)
        return _glossary_to_response(glossary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=PaginatedResponse[GlossaryResponse],
    summary="List glossaries",
)
async def list_glossaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    work_id: Optional[int] = Query(None, gt=0),
    status: Optional[str] = Query(None),
    service: GlossaryService = Depends(get_glossary_service),
) -> PaginatedResponse[GlossaryResponse]:
    """List glossaries with pagination and filters."""
    result = await service.list_glossaries(
        page=page,
        page_size=page_size,
        work_id=work_id,
        status=status,
    )
    return PaginatedResponse(
        items=[_glossary_to_response(g) for g in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get(
    "/{glossary_id}",
    response_model=GlossaryDetailResponse,
    summary="Get glossary by ID",
)
async def get_glossary(
    glossary_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryDetailResponse:
    """Get glossary by database ID with all entries."""
    # Note: For now using work_id as glossary_id since it's unique per work
    glossary = await service.get_glossary(glossary_id)
    return _glossary_to_detail_response(glossary)


@router.get(
    "/work/{work_id}",
    response_model=GlossaryDetailResponse,
    summary="Get glossary by work ID",
)
async def get_glossary_by_work(
    work_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryDetailResponse:
    """Get glossary by work ID."""
    glossary = await service.get_glossary(work_id)
    return _glossary_to_detail_response(glossary)


@router.patch(
    "/{glossary_id}",
    response_model=GlossaryResponse,
    summary="Update glossary",
)
async def update_glossary(
    glossary_id: int,
    update_data: GlossaryUpdate,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryResponse:
    """Update glossary metadata."""
    # TODO: Implement update in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.delete(
    "/{glossary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete glossary",
)
async def delete_glossary(
    glossary_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> None:
    """Delete a glossary."""
    # TODO: Implement delete in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


# =================== GLOSSARY ENTRY CRUD ===================

@router.post(
    "/{glossary_id}/entries",
    response_model=GlossaryEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create glossary entry",
)
async def create_glossary_entry(
    glossary_id: int,
    entry_data: GlossaryEntryCreate,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryEntryResponse:
    """Add a new entry to glossary."""
    # TODO: Implement in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get(
    "/{glossary_id}/entries",
    response_model=PaginatedResponse[GlossaryEntryResponse],
    summary="List glossary entries",
)
async def list_glossary_entries(
    glossary_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    service: GlossaryService = Depends(get_glossary_service),
) -> PaginatedResponse[GlossaryEntryResponse]:
    """List glossary entries with pagination and filters."""
    # TODO: Implement in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get(
    "/{glossary_id}/entries/{entry_id}",
    response_model=GlossaryEntryResponse,
    summary="Get glossary entry",
)
async def get_glossary_entry(
    glossary_id: int,
    entry_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryEntryResponse:
    """Get a specific glossary entry."""
    # TODO: Implement in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.patch(
    "/{glossary_id}/entries/{entry_id}",
    response_model=GlossaryEntryResponse,
    summary="Update glossary entry",
)
async def update_glossary_entry(
    glossary_id: int,
    entry_id: int,
    update_data: GlossaryEntryUpdate,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryEntryResponse:
    """Update a glossary entry."""
    command = UpdateGlossaryEntryCommand(
        entry_id=entry_id,
        translation=update_data.translation,
        is_verified=update_data.is_verified,
        confidence=update_data.confidence,
        entity_type=update_data.entity_type,
        is_proper_noun=update_data.is_proper_noun,
        do_not_translate=update_data.do_not_translate,
        context=update_data.context,
        notes=update_data.notes,
    )
    entry = await service.update_entry(command)
    return _entry_to_response(entry)


@router.delete(
    "/{glossary_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete glossary entry",
)
async def delete_glossary_entry(
    glossary_id: int,
    entry_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> None:
    """Delete a glossary entry."""
    # TODO: Implement in service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


# =================== SEARCH ===================

@router.get(
    "/{glossary_id}/search",
    response_model=PaginatedResponse[GlossaryEntryResponse],
    summary="Search glossary entries",
)
async def search_glossary(
    glossary_id: int,
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    service: GlossaryService = Depends(get_glossary_service),
) -> PaginatedResponse[GlossaryEntryResponse]:
    """Search glossary entries by term."""
    command = SearchGlossaryCommand(
        work_id=glossary_id,
        query=query,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        verified_only=verified_only,
    )
    result = await service.search_entries(command)
    return PaginatedResponse(
        items=[_entry_to_response(e) for e in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


# =================== PIPELINE OPERATIONS ===================

@router.post(
    "/build",
    response_model=GlossaryBuildResultResponse,
    summary="Build glossary from text",
)
async def build_glossary(
    request: BuildGlossaryRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> GlossaryBuildResultResponse:
    """
    Execute full glossary build pipeline.

    Stages:
    1. Extract entities from text (NLTK NER + patterns)
    2. Filter duplicates against existing glossary
    3. Validate entities with LLM
    4. Generate embeddings
    5. Suggest translations with LLM
    6. Save to glossary
    """
    command = BuildGlossaryCommand(
        work_id=request.work_id,
        volume_id=request.volume_id,
        text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        min_frequency=request.min_frequency,
        suggest_translations=request.suggest_translations,
        resume=request.resume,
        force_restart=request.force_restart,
    )
    result = await service.build_glossary(command)
    return GlossaryBuildResultResponse(**result.to_dict())


@router.get(
    "/pipelines",
    response_model=PaginatedResponse[BuildPipelineResponse],
    summary="List build pipelines",
)
async def list_pipelines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    work_id: Optional[int] = Query(None, gt=0),
    status: Optional[str] = Query(None),
    service: GlossaryService = Depends(get_glossary_service),
) -> PaginatedResponse[BuildPipelineResponse]:
    """List glossary build pipelines."""
    command = ListPipelinesCommand(
        page=page,
        page_size=page_size,
        work_id=work_id,
        status=status,
    )
    result = await service.list_pipelines(command)
    return PaginatedResponse(
        items=[_pipeline_to_response(p) for p in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get(
    "/pipelines/{work_id}/{volume_id}",
    response_model=BuildPipelineResponse,
    summary="Get pipeline status",
)
async def get_pipeline_status(
    work_id: int,
    volume_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> BuildPipelineResponse:
    """Get build pipeline status for a work/volume."""
    command = GetPipelineStatusCommand(work_id=work_id, volume_id=volume_id)
    pipeline = await service.get_pipeline_status(command)
    return _pipeline_to_response(pipeline)


@router.post(
    "/pipelines/{work_id}/{volume_id}/resume",
    response_model=BuildPipelineResponse,
    summary="Resume failed pipeline",
)
async def resume_pipeline(
    work_id: int,
    volume_id: int,
    service: GlossaryService = Depends(get_glossary_service),
) -> BuildPipelineResponse:
    """Resume a failed or partial pipeline."""
    command = ResumePipelineCommand(work_id=work_id, volume_id=volume_id)
    pipeline = await service.resume_pipeline(command)
    return _pipeline_to_response(pipeline)


# =================== INDIVIDUAL STAGE ENDPOINTS ===================

@router.post(
    "/pipelines/stages/extract",
    response_model=ExtractEntitiesResponse,
    summary="Stage 1: Extract entities from text",
)
async def extract_entities(
    request: ExtractEntitiesRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> ExtractEntitiesResponse:
    """
    Stage 1: Extract entities using NLTK NER + regex patterns.

    This endpoint can be called independently for testing/debugging.
    """
    entities = await service._uow.entity_extractor.extract(
        request.text,
        request.source_lang,
        request.min_frequency,
    )
    return ExtractEntitiesResponse(
        entities=[_to_entity_response(e) for e in entities],
        total=len(entities),
    )


@router.post(
    "/pipelines/stages/filter",
    response_model=FilterEntitiesResponse,
    summary="Stage 2: Filter entities against glossary",
)
async def filter_entities(
    request: FilterEntitiesRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> FilterEntitiesResponse:
    """
    Stage 2: Filter entities against existing glossary.

    Returns only new entities not already in the glossary.
    """
    entity_objects = [
        EntityCandidate(
            id=e.id,
            text=e.text,
            entity_type=e.entity_type,
            frequency=e.frequency,
            source_language=e.source_language,
            contexts=e.contexts,
            confidence=e.confidence,
            validated=e.validated,
            translation=e.translation,
        )
        for e in request.entities
    ]
    existing_terms = await service._uow.glossary_entries.get_existing_terms(
        request.work_id
    )
    new_entities = [e for e in entity_objects if e.key not in existing_terms]
    return FilterEntitiesResponse(
        new_entities=[_to_entity_response(e) for e in new_entities],
        skipped_count=len(entity_objects) - len(new_entities),
    )


@router.post(
    "/pipelines/stages/validate",
    response_model=ValidateEntitiesResponse,
    summary="Stage 3: Validate entities with LLM",
)
async def validate_entities(
    request: ValidateEntitiesRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> ValidateEntitiesResponse:
    """
    Stage 3: Validate entities with LLM.

    Classifies entities, filters false positives, suggests initial translations.
    """
    # Convert API entities to domain entities
    from ...domain.models.entity import EntityCandidate
    entity_objects = [
        EntityCandidate(
            id=e.id,
            text=e.text,
            entity_type=e.entity_type,
            frequency=e.frequency,
            source_language=e.source_language,
            contexts=e.contexts,
            confidence=e.confidence,
            validated=e.validated,
            translation=e.translation,
        )
        for e in request.entities
    ]

    from ...domain.services.commands import ValidateEntitiesCommand
    validated = await service.validate_entities(ValidateEntitiesCommand(
        entities=entity_objects,
        source_lang=request.source_lang,
        work_id=request.work_id,
        volume_id=request.volume_id,
        batch_size=request.batch_size,
    ))
    from .schemas import GlossaryBuildResultResponse
    return ValidateEntitiesResponse(
        validated_entities=[_to_entity_response(e) for e in validated],
        rejected_count=len(entity_objects) - len(validated),
    )


@router.post(
    "/pipelines/stages/embed",
    response_model=GenerateEmbeddingsResponse,
    summary="Stage 4: Generate embeddings",
)
async def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> GenerateEmbeddingsResponse:
    """
    Stage 4: Generate vector embeddings for entities.

    Used for semantic search and RAG during translation.
    """
    from ...domain.models.entity import EntityCandidate
    from ...domain.services.commands import GenerateEmbeddingsCommand

    entity_objects = [
        EntityCandidate(
            id=e.id,
            text=e.text,
            entity_type=e.entity_type,
            frequency=e.frequency,
            source_language=e.source_language,
            contexts=e.contexts,
            confidence=e.confidence,
            validated=e.validated,
            translation=e.translation,
        )
        for e in request.entities
    ]
    embedded = await service.generate_embeddings(GenerateEmbeddingsCommand(
        entities=entity_objects,
        model_name=request.model_name,
    ))
    return GenerateEmbeddingsResponse(
        entities_with_embeddings=[_to_entity_response(e) for e in embedded],
    )


@router.post(
    "/pipelines/stages/translate",
    response_model=SuggestTranslationsResponse,
    summary="Stage 5: Suggest translations",
)
async def suggest_translations(
    request: SuggestTranslationsRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> SuggestTranslationsResponse:
    """
    Stage 5: Suggest translations with LLM.

    Uses embeddings for context-aware translation suggestions.
    """
    from ...domain.models.entity import EntityCandidate
    from ...domain.services.commands import SuggestTranslationsCommand

    entity_objects = [
        EntityCandidate(
            id=e.id,
            text=e.text,
            entity_type=e.entity_type,
            frequency=e.frequency,
            source_language=e.source_language,
            contexts=e.contexts,
            confidence=e.confidence,
            validated=e.validated,
            translation=e.translation,
        )
        for e in request.entities
    ]
    translated = await service.suggest_translations(SuggestTranslationsCommand(
        entities=entity_objects,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        batch_size=request.batch_size,
    ))
    return SuggestTranslationsResponse(
        translated_entities=[_to_entity_response(e) for e in translated],
    )


@router.post(
    "/pipelines/stages/store",
    response_model=SaveEntitiesResponse,
    summary="Stage 6: Save entities to glossary",
)
async def save_entities(
    request: SaveEntitiesRequest,
    service: GlossaryService = Depends(get_glossary_service),
) -> SaveEntitiesResponse:
    """
    Stage 6: Save translated entities to glossary.

    Persists validated, translated entities to the database.
    """
    from ...domain.models.entity import EntityCandidate
    from ...domain.services.commands import SaveGlossaryEntriesCommand

    entity_objects = [
        EntityCandidate(
            id=e.id,
            text=e.text,
            entity_type=e.entity_type,
            frequency=e.frequency,
            source_language=e.source_language,
            contexts=e.contexts,
            confidence=e.confidence,
            validated=e.validated,
            translation=e.translation,
        )
        for e in request.entities
    ]
    saved = await service.save_glossary_entries(SaveGlossaryEntriesCommand(
        work_id=request.work_id,
        entities=entity_objects,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
    ))
    return SaveEntitiesResponse(saved_count=saved)


# =================== HELPERS ===================

def _glossary_to_response(glossary) -> GlossaryResponse:
    return GlossaryResponse(
        id=glossary.id,
        uuid=glossary.uuid,
        work_id=glossary.work_id,
        name=glossary.name,
        source_lang=glossary.source_lang,
        target_lang=glossary.target_lang,
        status=glossary.status,
        entry_count=glossary.entry_count,
        verified_count=glossary.verified_count,
        completion_percent=glossary.completion_percent,
        created_at=glossary.created_at,
        updated_at=glossary.updated_at,
    )


def _glossary_to_detail_response(glossary) -> GlossaryDetailResponse:
    base = _glossary_to_response(glossary)
    return GlossaryDetailResponse(
        **base.model_dump(),
        entries=[_entry_to_response(e) for e in glossary.entries.values()],
    )


def _entry_to_response(entry) -> GlossaryEntryResponse:
    return GlossaryEntryResponse(
        id=entry.id,
        uuid=entry.uuid,
        work_id=entry.work_id,
        term=entry.term,
        translation=entry.translation,
        entity_type=entry.entity_type,
        is_proper_noun=entry.is_proper_noun,
        do_not_translate=entry.do_not_translate,
        is_verified=entry.is_verified,
        confidence=entry.confidence,
        frequency=entry.frequency,
        context=entry.context,
        notes=entry.notes,
        source_lang=entry.source_lang,
        target_lang=entry.target_lang,
        effective_translation=entry.effective_translation,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _pipeline_to_response(pipeline) -> BuildPipelineResponse:
    return BuildPipelineResponse(
        id=pipeline.id,
        work_id=pipeline.work_id,
        volume_id=pipeline.volume_id,
        source_lang=pipeline.source_lang,
        target_lang=pipeline.target_lang,
        min_frequency=pipeline.min_frequency,
        dry_run=pipeline.dry_run,
        status=pipeline.status,
        progress_percent=pipeline.progress_percent,
        stages=[
            StageExecutionResponse(
                name=s.name,
                status=s.status,
                duration_seconds=s.duration_seconds,
                error=s.error_message,
                retry_count=s.retry_count,
            )
            for s in pipeline.stages
        ],
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


def _to_entity_response(entity) -> EntityCandidateResponse:
    return EntityCandidateResponse(
        id=entity.id,
        text=entity.text,
        entity_type=entity.entity_type,
        frequency=entity.frequency,
        source_language=entity.source_language,
        contexts=entity.contexts,
        confidence=entity.confidence,
        validated=entity.validated,
        translation=entity.translation,
    )