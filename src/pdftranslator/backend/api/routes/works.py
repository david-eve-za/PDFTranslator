"""Works management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import (
    WorkCreate,
    WorkListResponse,
    WorkResponse,
    WorkUpdate,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository

router = APIRouter(prefix="/api/works", tags=["works"])


def get_work_repository() -> BookRepository:
    """Get work repository instance."""
    return BookRepository(DatabasePool.get_instance())


@router.get("/", response_model=WorkListResponse)
async def list_works(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    repo: BookRepository = Depends(get_work_repository),
):
    """List all works with pagination."""
    works = repo.get_all()
    total = len(works)
    start = (page - 1) * page_size
    end = start + page_size
    items = [_work_to_response(w) for w in works[start:end]]
    return WorkListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{work_id}", response_model=WorkResponse)
async def get_work(work_id: int, repo: BookRepository = Depends(get_work_repository)):
    """Get a work by ID."""
    work = repo.get_by_id(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return _work_to_response(work, include_volumes=True)


@router.post("/", response_model=WorkResponse, status_code=201)
async def create_work(
    work_data: WorkCreate, repo: BookRepository = Depends(get_work_repository)
):
    """Create a new work."""
    from pdftranslator.core.models.work import Work

    work = Work(
        title=work_data.title,
        author=work_data.author,
        title_translated=work_data.title_translated,
        source_lang=work_data.source_lang,
        target_lang=work_data.target_lang,
    )
    created = repo.create(work)
    return _work_to_response(created)


@router.put("/{work_id}", response_model=WorkResponse)
async def update_work(
    work_id: int,
    work_data: WorkUpdate,
    repo: BookRepository = Depends(get_work_repository),
):
    """Update a work."""
    work = repo.get_by_id(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    if work_data.title is not None:
        work.title = work_data.title
    if work_data.title_translated is not None:
        work.title_translated = work_data.title_translated
    if work_data.author is not None:
        work.author = work_data.author
    if work_data.source_lang is not None:
        work.source_lang = work_data.source_lang
    if work_data.target_lang is not None:
        work.target_lang = work_data.target_lang

    updated = repo.update(work)
    if not updated:
        raise HTTPException(status_code=404, detail="Work not found")
    return _work_to_response(updated)


@router.delete("/{work_id}")
async def delete_work(
    work_id: int, repo: BookRepository = Depends(get_work_repository)
):
    """Delete a work."""
    deleted = repo.delete(work_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Work not found")
    return {"message": "Work deleted", "id": work_id}


def _work_to_response(work, include_volumes: bool = False) -> dict:
    """Convert work to response dict."""
    volume_repo = VolumeRepository(DatabasePool.get_instance())
    from pdftranslator.database.repositories.chapter_repository import ChapterRepository

    volumes = []
    total_chapters = 0
    translated_chapters = 0

    work_volumes = volume_repo.get_by_work_id(work.id)
    for v in work_volumes:
        chapter_repo = ChapterRepository(DatabasePool.get_instance())
        chapters = chapter_repo.get_by_volume(v.id)
        total_chapters += len(chapters)
        vol_translated = sum(1 for c in chapters if c.translated_text)
        translated_chapters += vol_translated

        volumes.append(
            {
                "id": v.id,
                "volume_number": v.volume_number,
                "total_chapters": len(chapters),
                "translated_chapters": vol_translated,
            }
        )

    return {
        "id": work.id,
        "title": work.title,
        "title_translated": work.title_translated,
        "author": work.author or "",
        "source_lang": work.source_lang or "en",
        "target_lang": work.target_lang or "es",
        "volumes": volumes,
        "total_volumes": len(volumes),
        "total_chapters": total_chapters,
        "translated_chapters": translated_chapters,
        "created_at": work.created_at.isoformat()
        if work.created_at
        else datetime.now().isoformat(),
        "updated_at": work.updated_at.isoformat()
        if work.updated_at
        else datetime.now().isoformat(),
    }
