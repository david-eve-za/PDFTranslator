"""Glossary management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import (
    GlossaryCreate,
    GlossaryEntryResponse,
    GlossaryUpdateRequest,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


def get_glossary_repository() -> GlossaryRepository:
    """Get glossary repository instance."""
    return GlossaryRepository(DatabasePool.get_instance())


@router.get("/", response_model=list[GlossaryEntryResponse])
async def list_glossary(
    work_id: int | None = None,
    search: str | None = None,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    """List all glossary terms with optional filters."""
    if work_id:
        entries = repo.get_by_work(work_id)
    else:
        entries = repo.get_all()

    if search:
        search_lower = search.lower()
        entries = [
            e
            for e in entries
            if search_lower in e.term.lower()
            or (e.translation and search_lower in e.translation.lower())
        ]

    return [_entry_to_response(e) for e in entries]


@router.post("/", response_model=GlossaryEntryResponse, status_code=201)
async def create_glossary_term(
    data: GlossaryCreate, repo: GlossaryRepository = Depends(get_glossary_repository)
):
    """Create a new glossary term."""
    from pdftranslator.core.models.work import GlossaryEntry

    entry = GlossaryEntry(
        work_id=data.work_id,
        term=data.term,
        translation=data.translation,
        notes=data.notes,
        is_proper_noun=data.is_proper_noun,
    )
    created = repo.create(entry)
    return _entry_to_response(created)


@router.get("/{term_id}", response_model=GlossaryEntryResponse)
async def get_glossary_term(
    term_id: int, repo: GlossaryRepository = Depends(get_glossary_repository)
):
    """Get a glossary term by ID."""
    entry = repo.get_by_id(term_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary term not found")
    return _entry_to_response(entry)


@router.put("/{term_id}", response_model=GlossaryEntryResponse)
async def update_glossary_term(
    term_id: int,
    data: GlossaryUpdateRequest,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    """Update a glossary term."""
    entry = repo.get_by_id(term_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary term not found")

    if data.translation is not None:
        entry.translation = data.translation
    if data.notes is not None:
        entry.notes = data.notes

    updated = repo.update(entry)
    if not updated:
        raise HTTPException(status_code=404, detail="Glossary term not found")
    return _entry_to_response(updated)


@router.delete("/{term_id}")
async def delete_glossary_term(
    term_id: int, repo: GlossaryRepository = Depends(get_glossary_repository)
):
    """Delete a glossary term."""
    deleted = repo.delete(term_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Glossary term not found")
    return {"message": "Glossary term deleted", "id": term_id}


def _entry_to_response(entry) -> dict:
    """Convert glossary entry to response dict."""
    return {
        "id": entry.id,
        "work_id": entry.work_id,
        "term": entry.term,
        "translation": entry.translation,
        "notes": entry.notes,
        "is_proper_noun": entry.is_proper_noun,
        "created_at": entry.created_at.isoformat()
        if entry.created_at
        else datetime.now().isoformat(),
    }
