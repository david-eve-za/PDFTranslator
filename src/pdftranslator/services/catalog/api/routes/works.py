"""
Work API Routes - Read operations for Catalog Service.

CUPID Principle: Unix Philosophy
- Single responsibility: Work CRUD via HTTP
- Stateless, JSON in/out
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...domain.services.catalog_service import CatalogService, CreateWorkCommand, UpdateWorkCommand
from ...domain.repositories.protocols import PaginationParams
from ...domain.repositories.exceptions import NotFoundError, DomainError
from ..schemas.work import WorkCreate, WorkUpdate, WorkResponse, WorkListResponse
from ..dependencies import get_catalog_service


router = APIRouter(prefix="/works", tags=["works"])


@router.get(
    "",
    response_model=WorkListResponse,
    summary="List all works",
    description="Retrieve paginated list of works with volume summaries",
)
async def list_works(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> WorkListResponse:
    """List works with pagination."""
    pagination = PaginationParams(page=page, page_size=page_size)
    result = await catalog_service.list_works(pagination)

    return WorkListResponse(
        items=[_work_to_response(w) for w in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get(
    "/{work_id}",
    response_model=WorkResponse,
    summary="Get work by ID",
    description="Retrieve a single work with all volumes and chapter counts",
)
async def get_work(
    work_id: int,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> WorkResponse:
    """Get work by ID with full aggregate."""
    try:
        work = await catalog_service.get_work(work_id)
        return _work_to_response(work)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/uuid/{uuid}",
    response_model=WorkResponse,
    summary="Get work by UUID",
    description="Retrieve a single work by UUID",
)
async def get_work_by_uuid(
    uuid: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> WorkResponse:
    """Get work by UUID."""
    try:
        work = await catalog_service.get_work_by_uuid(uuid)
        return _work_to_response(work)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "",
    response_model=WorkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new work",
    description="Create a new literary work with metadata",
)
async def create_work(
    work_data: WorkCreate,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> WorkResponse:
    """Create a new work."""
    try:
        command = CreateWorkCommand(
            title=work_data.title,
            source_lang=work_data.source_lang,
            target_lang=work_data.target_lang,
            author=work_data.author,
            title_translated=work_data.title_translated,
        )
        work = await catalog_service.create_work(command)
        return _work_to_response(work)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{work_id}",
    response_model=WorkResponse,
    summary="Update work metadata",
    description="Update title, author, or translated title of a work",
)
async def update_work(
    work_id: int,
    work_data: WorkUpdate,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> WorkResponse:
    """Update work metadata."""
    try:
        command = UpdateWorkCommand(
            title=work_data.title,
            author=work_data.author,
            title_translated=work_data.title_translated,
        )
        work = await catalog_service.update_work(work_id, command)
        return _work_to_response(work)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{work_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete work",
    description="Delete a work and all its volumes/chapters",
)
async def delete_work(
    work_id: int,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> None:
    """Delete a work (cascades to volumes and chapters)."""
    try:
        deleted = await catalog_service.delete_work(work_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _work_to_response(work) -> WorkResponse:
    """Convert domain Work to API response."""
    volumes = [
        {
            "id": v.id,
            "volume_number": v.volume_number,
            "title": v.title,
            "total_chapters": v.chapter_count,
            "translated_chapters": v.translated_chapters,
        }
        for v in work.volumes
    ]

    return WorkResponse(
        id=work.id,
        uuid=str(work.uuid),
        title=work.title,
        title_translated=work.title_translated,
        author=work.author,
        source_lang=work.source_lang,
        target_lang=work.target_lang,
        volumes=volumes,
        total_volumes=work.volume_count,
        total_chapters=work.total_chapters,
        translated_chapters=work.translated_chapters,
        translation_progress=work.translation_progress,
        created_at=work.created_at,
        updated_at=work.updated_at,
    )