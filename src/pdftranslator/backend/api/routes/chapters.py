"""Chapters management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import (
    ChapterListResponse,
    ChapterResponse,
    ChapterUpdate,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.chapter_repository import ChapterRepository

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def get_chapter_repository() -> ChapterRepository:
    """Get chapter repository instance."""
    return ChapterRepository(DatabasePool.get_instance())


@router.get("/", response_model=ChapterListResponse)
async def list_chapters(
    volume_id: int = Query(...),
    repo: ChapterRepository = Depends(get_chapter_repository),
):
    """List all chapters for a volume."""
    chapters = repo.get_by_volume(volume_id)
    items = [_chapter_to_response(c) for c in chapters]
    return ChapterListResponse(items=items, total=len(items))


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: int, repo: ChapterRepository = Depends(get_chapter_repository)
):
    """Get a chapter by ID."""
    chapter = repo.get_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_to_response(chapter)


@router.put("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    chapter_data: ChapterUpdate,
    repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Update a chapter."""
    chapter = repo.get_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if chapter_data.title is not None:
        chapter.title = chapter_data.title
    if chapter_data.translated_text is not None:
        chapter.translated_text = chapter_data.translated_text

    updated = repo.update(chapter)
    if not updated:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_to_response(updated)


def _chapter_to_response(chapter) -> dict:
    """Convert chapter to response dict."""
    return {
        "id": chapter.id,
        "volume_id": chapter.volume_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title or "",
        "original_text": chapter.original_text,
        "translated_text": chapter.translated_text,
        "is_translated": chapter.translated_text is not None
        and len(chapter.translated_text) > 0,
        "created_at": chapter.created_at.isoformat()
        if chapter.created_at
        else datetime.now().isoformat(),
        "updated_at": chapter.created_at.isoformat()
        if chapter.created_at
        else datetime.now().isoformat(),
    }
