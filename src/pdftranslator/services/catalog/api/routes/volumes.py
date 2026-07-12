"""
Volume API Routes.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...domain.services.catalog_service import CatalogService
from ...domain.repositories.exceptions import NotFoundError
from ..schemas.volume import VolumeCreate, VolumeUpdate, VolumeResponse, VolumeListResponse
from ..dependencies import get_catalog_service


router = APIRouter(prefix="/works/{work_id}/volumes", tags=["volumes"])


@router.get(
    "",
    response_model=VolumeListResponse,
    summary="List volumes for a work",
)
async def list_volumes(
    work_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> VolumeListResponse:
    """List all volumes for a work."""
    # Verify work exists
    try:
        await catalog_service.get_work(work_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")

    volumes = await catalog_service.get_volumes_for_work(work_id)

    # Simple pagination (volumes per work typically small)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = volumes[start:end]

    return VolumeListResponse(
        items=[_volume_to_response(v) for v in paginated],
        total=len(volumes),
        page=page,
        page_size=page_size,
        total_pages=(len(volumes) + page_size - 1) // page_size,
    )


@router.get(
    "/{volume_id}",
    response_model=VolumeResponse,
    summary="Get volume by ID",
)
async def get_volume(
    work_id: int,
    volume_id: int,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> VolumeResponse:
    """Get volume with all chapters."""
    try:
        volume = await catalog_service.get_volume(volume_id)
        if volume.work_id != work_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volume not found in this work")
        return _volume_to_response(volume)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "",
    response_model=VolumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create volume",
)
async def create_volume(
    work_id: int,
    volume_data: VolumeCreate,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> VolumeResponse:
    """Add a new volume to a work."""
    try:
        work = await catalog_service.get_work(work_id)

        from ...domain.models.volume import Volume
        volume = Volume(
            work_id=work_id,
            volume_number=volume_data.volume_number,
            title=volume_data.title,
            full_text=volume_data.full_text,
            translated_text=volume_data.translated_text,
        )

        # Add to work aggregate (validates uniqueness)
        work.add_volume(volume)

        # Persist through unit of work (service handles this)
        # For now, simplification - in production use UoW
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Write operations require full UoW integration"
        )
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _volume_to_response(volume) -> VolumeResponse:
    """Convert domain Volume to API response."""
    chapters = [
        {
            "id": c.id,
            "chapter_number": c.chapter_number,
            "title": c.title,
            "is_translated": c.is_translated,
            "word_count_original": c.word_count_original,
            "word_count_translated": c.word_count_translated,
        }
        for c in volume.chapters
    ]

    return VolumeResponse(
        id=volume.id,
        uuid=str(volume.uuid),
        work_id=volume.work_id,
        volume_number=volume.volume_number,
        title=volume.title,
        full_text=volume.full_text,
        translated_text=volume.translated_text,
        chapters=chapters,
        chapter_count=volume.chapter_count,
        translated_chapters=volume.translated_chapters,
        translation_progress=volume.translation_progress,
        glossary_built_at=volume.glossary_built_at,
        glossary_build_status=volume.glossary_build_status,
        glossary_error_message=volume.glossary_error_message,
        glossary_resume_phase=volume.glossary_resume_phase,
        created_at=volume.created_at,
        updated_at=volume.updated_at,
    )