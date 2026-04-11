"""Glossary management routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


class GlossaryTerm(BaseModel):
    """Glossary term schema."""

    id: int
    source_lang: str
    target_lang: str
    term: str
    translation: Optional[str] = None
    context: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GlossaryCreateRequest(BaseModel):
    """Glossary create request schema."""

    source_lang: str
    target_lang: str
    term: str
    translation: Optional[str] = None
    context: Optional[str] = None


class GlossaryUpdateRequest(BaseModel):
    """Glossary update request schema."""

    term: Optional[str] = None
    translation: Optional[str] = None
    context: Optional[str] = None


_glossary_db: List[GlossaryTerm] = []
_id_counter = 0


@router.get("/", response_model=List[GlossaryTerm])
async def list_glossary(
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all glossary terms with optional filters."""
    results = _glossary_db
    if source_lang:
        results = [t for t in results if t.source_lang == source_lang]
    if target_lang:
        results = [t for t in results if t.target_lang == target_lang]
    if search:
        search_lower = search.lower()
        results = [
            t
            for t in results
            if search_lower in t.term.lower()
            or (t.translation and search_lower in t.translation.lower())
        ]
    return results


@router.post("/", response_model=GlossaryTerm)
async def create_glossary_term(data: GlossaryCreateRequest):
    """Create a new glossary term."""
    global _id_counter
    _id_counter += 1
    now = datetime.now()
    term = GlossaryTerm(
        id=_id_counter,
        source_lang=data.source_lang,
        target_lang=data.target_lang,
        term=data.term,
        translation=data.translation,
        context=data.context,
        created_at=now,
        updated_at=now,
    )
    _glossary_db.append(term)
    return term


@router.get("/{term_id}", response_model=GlossaryTerm)
async def get_glossary_term(term_id: int):
    """Get a glossary term by ID."""
    for term in _glossary_db:
        if term.id == term_id:
            return term
    raise HTTPException(status_code=404, detail="Glossary term not found")


@router.put("/{term_id}", response_model=GlossaryTerm)
async def update_glossary_term(term_id: int, data: GlossaryUpdateRequest):
    """Update a glossary term."""
    for term in _glossary_db:
        if term.id == term_id:
            if data.term is not None:
                term.term = data.term
            if data.translation is not None:
                term.translation = data.translation
            if data.context is not None:
                term.context = data.context
            term.updated_at = datetime.now()
            return term
    raise HTTPException(status_code=404, detail="Glossary term not found")


@router.delete("/{term_id}")
async def delete_glossary_term(term_id: int):
    """Delete a glossary term."""
    global _glossary_db
    for i, term in enumerate(_glossary_db):
        if term.id == term_id:
            _glossary_db.pop(i)
            return {"message": "Glossary term deleted"}
    raise HTTPException(status_code=404, detail="Glossary term not found")
