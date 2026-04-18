"""Glossary management routes."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from pdftranslator.backend.api.models.schemas import (
    GlossaryCreate,
    GlossaryEntryResponse,
    GlossaryUpdateRequest,
    GlossaryBuildRequest,
    GlossaryBuildResponse,
    GlossaryBuildVolumeResult,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.services.glossary_manager import GlossaryManager

router = APIRouter(prefix="/api/glossary", tags=["glossary"])
logger = logging.getLogger(__name__)


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
        entity_type=data.entity_type,
        context=data.context,
        is_proper_noun=data.is_proper_noun,
        source_lang=data.source_lang,
        target_lang=data.target_lang,
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

    if data.term is not None:
        entry.term = data.term
    if data.translation is not None:
        entry.translation = data.translation
    if data.context is not None:
        entry.context = data.context
    if data.is_proper_noun is not None:
        entry.is_proper_noun = data.is_proper_noun
    if data.do_not_translate is not None:
        entry.do_not_translate = data.do_not_translate
    if data.is_verified is not None:
        entry.is_verified = data.is_verified

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
        "entity_type": entry.entity_type,
        "context": entry.context,
        "is_proper_noun": entry.is_proper_noun,
        "do_not_translate": getattr(entry, "do_not_translate", False),
        "is_verified": getattr(entry, "is_verified", False),
        "confidence": getattr(entry, "confidence", 0.0),
        "frequency": entry.frequency,
        "source_lang": entry.source_lang,
        "target_lang": entry.target_lang,
        "created_at": entry.created_at.isoformat()
        if entry.created_at
        else datetime.now().isoformat(),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


@router.post("/build", response_model=GlossaryBuildResponse)
async def build_glossary(
    data: GlossaryBuildRequest,
    resume: bool = Query(
        False, description="Reanudar desde el último punto guardado si se interrumpió"
    ),
    force_restart: bool = Query(
        False, description="Ignorar progreso existente y comenzar desde cero"
    ),
    background_tasks: BackgroundTasks = None,
):
    """
    Build glossary from work volumes using NER + LLM.

    Processes each volume that hasn't been analyzed yet, extracting entities
    and suggesting translations. Volumes with glossary_built_at set are skipped.

    NEW: Supports resume from last checkpoint with ?resume=true
    """
    pool = DatabasePool.get_instance()
    work_repo = BookRepository(pool)
    volume_repo = VolumeRepository(pool)
    chapter_repo = ChapterRepository(pool)

    work = work_repo.get_by_id(data.work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    volumes = volume_repo.get_by_work_id(data.work_id)
    if not volumes:
        raise HTTPException(status_code=404, detail="No volumes found for this work")

    source_lang = data.source_lang or work.source_lang or "en"
    target_lang = data.target_lang or work.target_lang or "es"

    manager = GlossaryManager(pool)

    total_extracted = 0
    total_new = 0
    total_skipped = 0
    volumes_processed = 0
    volumes_skipped = 0
    all_entities_by_type = {}
    volume_results = []

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        if volume.glossary_built_at:
            logger.info(
                f"Volume {volume.volume_number} already processed at {volume.glossary_built_at}, skipping"
            )
            volumes_skipped += 1
            volume_results.append(
                GlossaryBuildVolumeResult(
                    volume_id=volume.id,
                    volume_number=volume.volume_number,
                    extracted=0,
                    new=0,
                    skipped=0,
                    entities_by_type={},
                )
            )
            continue

        try:
            volume_repo.update_build_status(volume.id, "in_progress")

            chapters = chapter_repo.get_by_volume(volume.id)
            texts = [ch.original_text for ch in chapters if ch.original_text]

            if not texts:
                logger.info(
                    f"Volume {volume.volume_number} has no text content, skipping"
                )
                volumes_skipped += 1
                volume_repo.update_build_status(volume.id, "completed")
                volume_results.append(
                    GlossaryBuildVolumeResult(
                        volume_id=volume.id,
                        volume_number=volume.volume_number,
                        extracted=0,
                        new=0,
                        skipped=0,
                        entities_by_type={},
                    )
                )
                continue

            consolidated_text = "\n\n".join(texts)
            logger.info(
                f"Processing Volume {volume.volume_number} ({len(consolidated_text)} chars)"
            )

            result = manager.build_from_text(
                text=consolidated_text,
                work_id=data.work_id,
                volume_id=volume.id,
                source_lang=source_lang,
                target_lang=target_lang,
                suggest_translations=True,
                resume=resume,
            )

            volume_repo.mark_glossary_built(volume.id)
            volume_repo.update_build_status(volume.id, "completed")

            total_extracted += result.extracted
            total_new += result.new
            total_skipped += result.skipped
            volumes_processed += 1

            for etype, count in result.entities_by_type.items():
                all_entities_by_type[etype] = all_entities_by_type.get(etype, 0) + count

            volume_results.append(
                GlossaryBuildVolumeResult(
                    volume_id=volume.id,
                    volume_number=volume.volume_number,
                    extracted=result.extracted,
                    new=result.new,
                    skipped=result.skipped,
                    entities_by_type=result.entities_by_type,
                )
            )

        except Exception as e:
            volume_repo.update_build_status(
                volume.id,
                "failed",
                error_message=str(e),
            )
            logger.error(f"Volume {volume.volume_number} failed: {e}")
            volumes_skipped += 1
            volume_results.append(
                GlossaryBuildVolumeResult(
                    volume_id=volume.id,
                    volume_number=volume.volume_number,
                    extracted=0,
                    new=0,
                    skipped=0,
                    entities_by_type={},
                )
            )

    return GlossaryBuildResponse(
        total_extracted=total_extracted,
        total_new=total_new,
        total_skipped=total_skipped,
        volumes_processed=volumes_processed,
        volumes_skipped=volumes_skipped,
        entities_by_type=all_entities_by_type,
        volume_results=volume_results,
    )
