"""Volumes management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import (
    VolumeCreate,
    VolumeListResponse,
    VolumeResponse,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository

router = APIRouter(prefix="/api/volumes", tags=["volumes"])


def get_volume_repository() -> VolumeRepository:
    """Get volume repository instance."""
    return VolumeRepository(DatabasePool.get_instance())


@router.get("/", response_model=VolumeListResponse)
async def list_volumes(
    work_id: int = Query(...), repo: VolumeRepository = Depends(get_volume_repository)
):
    """List all volumes for a work."""
    volumes = repo.get_by_work_id(work_id)
    items = [_volume_to_response(v) for v in volumes]
    return VolumeListResponse(items=items, total=len(items))


@router.get("/{volume_id}", response_model=VolumeResponse)
async def get_volume(
    volume_id: int, repo: VolumeRepository = Depends(get_volume_repository)
):
    """Get a volume by ID."""
    volume = repo.get_by_id(volume_id)
    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")
    return _volume_to_response(volume, include_chapters=True)


@router.post("/", response_model=VolumeResponse, status_code=201)
async def create_volume(
    volume_data: VolumeCreate, repo: VolumeRepository = Depends(get_volume_repository)
):
    """Create a new volume."""
    from pdftranslator.core.models.work import Volume

    volume = Volume(
        work_id=volume_data.work_id,
        volume_number=volume_data.volume_number,
        title=volume_data.title,
    )
    created = repo.create(volume)
    return _volume_to_response(created)


@router.delete("/{volume_id}")
async def delete_volume(
    volume_id: int, repo: VolumeRepository = Depends(get_volume_repository)
):
    """Delete a volume."""
    deleted = repo.delete(volume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Volume not found")
    return {"message": "Volume deleted", "id": volume_id}


def _volume_to_response(volume, include_chapters: bool = False) -> dict:
    """Convert volume to response dict."""
    chapter_repo = ChapterRepository(DatabasePool.get_instance())
    chapters = []
    if include_chapters:
        chapters = [
            {"id": c.id, "chapter_number": c.chapter_number, "title": c.title}
            for c in chapter_repo.get_by_volume(volume.id)
        ]
    return {
        "id": volume.id,
        "work_id": volume.work_id,
        "volume_number": volume.volume_number,
        "title": volume.title,
        "full_text": volume.full_text,
        "chapters": chapters,
        "created_at": volume.created_at.isoformat()
        if volume.created_at
        else datetime.now().isoformat(),
    }
