"""
Chapter API Routes.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...domain.services.catalog_service import CatalogService
from ...domain.repositories.exceptions import NotFoundError
from ..schemas.chapter import ChapterCreate, ChapterUpdate, ChapterResponse, ChapterListResponse
from ..dependencies import get_catalog_service


router = APIRouter(prefix="/volumes/{volume_id}/chapters", tags=["chapters"])


@router.get(
    "",
    response_model=ChapterListResponse,
    summary="List chapters for a volume",
)
async def list_chapters(
    volume_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> ChapterListResponse:
    """List all chapters for a volume with pagination."""
    try:
        await catalog_service.get_volume(volume_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volume not found")

    chapters = await catalog_service.get_chapters_for_volume(volume_id)

    start = (page - 1) * page_size
    end = start + page_size
    paginated = chapters[start:end]

    return ChapterListResponse(
        items=[_chapter_to_response(c) for c in paginated],
        total=len(chapters),
        page=page,
        page_size=page_size,
        total_pages=(len(chapters) + page_size - 1) // page_size,
    )


@router.get(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Get chapter by ID",
)
async def get_chapter(
    volume_id: int,
    chapter_id: int,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> ChapterResponse:
    """Get chapter details."""
    try:
        chapter = await catalog_service.get_chapter(chapter_id)
        if chapter.volume_id != volume_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found in this volume")
        return _chapter_to_response(chapter)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _chapter_to_response(chapter) -> ChapterResponse:
    return ChapterResponse(
        id=chapter.id,
        uuid=str(chapter.uuid),
        volume_id=chapter.volume_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        start_position=chapter.start_position,
        end_position=chapter.end_position,
        original_text=chapter.original_text,
        translated_text=chapter.translated_text,
        is_translated=chapter.is_translated,
        word_count_original=chapter.word_count_original,
        word_count_translated=chapter.word_count_translated,
        created_at=chapter.created_at,
        updated_at=chapter.updated_at,
    )