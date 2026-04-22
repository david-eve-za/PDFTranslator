# Glossary Build Resume System - Technical Design Document

**Date:** 2025-04-17
**Author:** OpenCode Assistant
**Status:** Approved

## Overview

This document describes the design for a resume/recovery system for the glossary build process. The system allows resuming from the last successful point when the process fails or is interrupted, preventing loss of expensive LLM operations.

## Problem Statement

The current glossary build process has these issues:

1. **Long processing time**: Each volume can take several minutes due to LLM validation and translation
2. **No recovery mechanism**: If the process fails midway, all work for that volume is lost
3. **Expensive LLM calls**: Re-processing from scratch wastes API tokens and time
4. **Failure points**: Failures can occur at:
   - Entity extraction (NLTK)
   - LLM validation (batch processing)
   - Embedding generation
   - LLM translation suggestion (batch processing)

### Current Flow

```
Volume → Extract entities → Filter duplicates → Validate (LLM batches) → 
Generate embeddings → Translate (LLM batches) → Save to glossary → Mark volume done
```

Problem: Volume is only marked as `glossary_built_at` at the end. If any step fails, everything is lost.

## Proposed Solution

Implement a checkpoint system at the entity level using a new `glossary_build_progress` table. The system saves progress after each phase and can resume from any point.

### Goals

1. ✅ Resume from exact failure point (entity-level granularity)
2. ✅ Automatic detection of resume point with `--resume` flag
3. ✅ Save progress in each pipeline phase
4. ✅ Compatible with existing duplicate filtering
5. ✅ Minimal performance overhead

## Architecture

### Phase-Based Pipeline

The pipeline is divided into phases that act as natural checkpoints:

```
Phase 1: EXTRACTED     → After NLTK entity extraction
Phase 2: VALIDATED     → After LLM validation (per batch)
Phase 3: TRANSLATED    → After LLM translation suggestion (per batch)
Phase 4: SAVED         → After saving to glossary_terms
```

### Data Flow

```
                    ┌─────────────────────┐
                    │   Start/Resume      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Check Progress     │
                    │  Table for resume   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌─────▼─────┐         ┌──────▼──────┐
   │Extract  │           │ Validate  │         │  Translate  │
   │(NLTK)   │           │ (LLM)     │         │   (LLM)     │
   └────┬────┘           └─────┬─────┘         └──────┬──────┘
        │                      │                      │
        │ Save to              │ Update               │ Update
        │ progress             │ phase                │ phase
        │                      │                      │
        └──────────────────────┴──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Save to Glossary   │
                    │  (glossary_terms)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Cleanup Progress   │
                    │  Mark volume done   │
                    └─────────────────────┘
```

## Database Schema

### New Table: `glossary_build_progress`

```sql
-- Migration: 015_glossary_build_progress.sql

CREATE TABLE glossary_build_progress (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,
    
    -- Phase tracking
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',
    -- Possible values: 'extracted', 'validated', 'translated', 'saved'
    
    -- Entity data
    entity_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    contexts TEXT[],
    translation VARCHAR(500),
    embedding vector(1536),
    
    -- Batch tracking for resume
    validation_batch INTEGER,
    translation_batch INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(work_id, volume_id, LOWER(entity_text))
);

-- Indexes for efficient resume queries
CREATE INDEX idx_progress_work_volume ON glossary_build_progress(work_id, volume_id);
CREATE INDEX idx_progress_phase ON glossary_build_progress(phase);
CREATE INDEX idx_progress_resume ON glossary_build_progress(work_id, volume_id, phase) 
    WHERE phase != 'saved';
CREATE INDEX idx_progress_pending ON glossary_build_progress(work_id, volume_id) 
    WHERE phase IN ('extracted', 'validated', 'translated');
```

### Extended Volumes Table

```sql
-- Add build status tracking
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_build_status VARCHAR(20) DEFAULT 'pending';
-- Possible values: 'pending', 'in_progress', 'completed', 'failed'

ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_error_message TEXT;
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_resume_phase VARCHAR(20);

CREATE INDEX idx_volumes_build_status ON volumes(glossary_build_status);
```

## Python Implementation

### Data Model

```python
# src/pdftranslator/database/models.py

@dataclass
class GlossaryBuildProgress:
    id: int | None = None
    work_id: int = 0
    volume_id: int = 0
    entity_text: str = ""
    phase: str = "extracted"
    entity_type: str | None = None
    frequency: int = 1
    contexts: list[str] = field(default_factory=list)
    translation: str | None = None
    embedding: list[float] | None = None
    validation_batch: int | None = None
    translation_batch: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_complete(self) -> bool:
        return self.phase == "saved"

    def next_phase(self) -> str | None:
        phases = ["extracted", "validated", "translated", "saved"]
        if self.phase in phases:
            idx = phases.index(self.phase)
            return phases[idx + 1] if idx < len(phases) - 1 else None
        return None

    @classmethod
    def from_entity_candidate(
        cls, 
        entity: EntityCandidate, 
        work_id: int, 
        volume_id: int
    ) -> "GlossaryBuildProgress":
        return cls(
            work_id=work_id,
            volume_id=volume_id,
            entity_text=entity.text,
            entity_type=entity.entity_type,
            frequency=entity.frequency,
            contexts=entity.contexts,
            translation=entity.translation,
        )
```

### Repository

```python
# src/pdftranslator/database/repositories/glossary_build_progress_repository.py

class GlossaryBuildProgressRepository(BaseRepository[GlossaryBuildProgress]):
    def __init__(self, pool: DatabasePool | None = None):
        self._pool = pool or DatabasePool.get_instance()

    def save_extracted(
        self, 
        work_id: int, 
        volume_id: int, 
        entities: list[EntityCandidate]
    ) -> list[GlossaryBuildProgress]:
        """
        Save entities after extraction phase.
        Bulk insert for efficiency.
        """
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Use ON CONFLICT to handle duplicates
                for entity in entities:
                    cur.execute("""
                        INSERT INTO glossary_build_progress 
                            (work_id, volume_id, entity_text, phase, 
                             entity_type, frequency, contexts)
                        VALUES (%s, %s, %s, 'extracted', %s, %s, %s)
                        ON CONFLICT (work_id, volume_id, LOWER(entity_text)) 
                        DO UPDATE SET 
                            entity_type = EXCLUDED.entity_type,
                            frequency = EXCLUDED.frequency,
                            contexts = EXCLUDED.contexts,
                            phase = 'extracted',
                            updated_at = NOW()
                        RETURNING id, work_id, volume_id, entity_text, phase, 
                                  entity_type, frequency, contexts, translation,
                                  validation_batch, translation_batch, 
                                  created_at, updated_at
                    """, (work_id, volume_id, entity.text, 
                          entity.entity_type, entity.frequency, entity.contexts))
                # ... collect results
        return results

    def get_pending_for_phase(
        self, 
        work_id: int, 
        volume_id: int, 
        phase: str
    ) -> list[GlossaryBuildProgress]:
        """Get all entities in a specific phase (waiting to be processed)."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, work_id, volume_id, entity_text, phase,
                           entity_type, frequency, contexts, translation,
                           embedding, validation_batch, translation_batch,
                           created_at, updated_at
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s AND phase = %s
                    ORDER BY id
                """, (work_id, volume_id, phase))
                return [self._row_to_progress(row) for row in cur.fetchall()]

    def batch_update_phase(
        self, 
        ids: list[int], 
        phase: str,
        batch_number: int | None = None
    ) -> int:
        """Update phase for multiple progress records."""
        if not ids:
            return 0
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE glossary_build_progress
                    SET phase = %s, updated_at = NOW()
                        {batch_field}
                    WHERE id = ANY(%s)
                """.format(batch_field=f", {phase[:-1]}_batch = {batch_number}" 
                           if batch_number and phase in ('validated', 'translated') 
                           else ""), (phase, ids))
                return cur.rowcount

    def batch_update_embeddings(
        self, 
        updates: list[tuple[int, list[float]]]
    ) -> int:
        """Update embeddings for validated entities."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for progress_id, embedding in updates:
                    cur.execute("""
                        UPDATE glossary_build_progress
                        SET embedding = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (embedding, progress_id))
        return len(updates)

    def batch_update_translations(
        self, 
        updates: list[tuple[int, str]]
    ) -> int:
        """Update translations for entities."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for progress_id, translation in updates:
                    cur.execute("""
                        UPDATE glossary_build_progress
                        SET translation = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (translation, progress_id))
        return len(updates)

    def get_resume_point(
        self, 
        work_id: int, 
        volume_id: int
    ) -> tuple[str, int | None]:
        """
        Determine where to resume from.
        Returns (phase, batch_number).
        """
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get counts per phase
                cur.execute("""
                    SELECT phase, COUNT(*) as count,
                           MAX(validation_batch) as last_val_batch,
                           MAX(translation_batch) as last_trans_batch
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s
                    GROUP BY phase
                    ORDER BY phase
                """, (work_id, volume_id))
                results = cur.fetchall()
                
                if not results:
                    return ("extracted", None)
                
                phase_counts = {row[0]: (row[1], row[2], row[3]) for row in results}
                
                # Determine resume point based on phase counts
                if "extracted" in phase_counts:
                    extracted_count, _, _ = phase_counts.get("extracted", (0, None, None))
                    if extracted_count > 0:
                        return ("validated", None)  # Need to validate
                
                if "validated" in phase_counts:
                    validated_count, last_val_batch, _ = phase_counts.get("validated", (0, None, None))
                    if validated_count > 0:
                        return ("translated", last_val_batch)  # Need to translate
                
                return ("extracted", None)

    def get_statistics(self, work_id: int, volume_id: int) -> dict:
        """Get progress statistics for a volume."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT phase, COUNT(*) as count
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s
                    GROUP BY phase
                """, (work_id, volume_id))
                return {row[0]: row[1] for row in cur.fetchall()}

    def cleanup_completed(self, volume_id: int) -> int:
        """Remove progress records after successful completion."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM glossary_build_progress
                    WHERE volume_id = %s AND phase = 'saved'
                """, (volume_id,))
                deleted = cur.rowcount
                # Delete remaining records too (cleanup)
                cur.execute("DELETE FROM glossary_build_progress WHERE volume_id = %s", (volume_id,))
                return deleted

    def _row_to_progress(self, row: tuple) -> GlossaryBuildProgress:
        return GlossaryBuildProgress(
            id=row[0],
            work_id=row[1],
            volume_id=row[2],
            entity_text=row[3],
            phase=row[4],
            entity_type=row[5],
            frequency=row[6],
            contexts=row[7] if row[7] else [],
            translation=row[8],
            embedding=row[9] if row[9] else None,
            validation_batch=row[10],
            translation_batch=row[11],
            created_at=row[12],
            updated_at=row[13],
        )
```

### Modified GlossaryManager

```python
# src/pdftranslator/database/services/glossary_manager.py (modifications)

class GlossaryManager:
    def __init__(self, pool: DatabasePool | None = None):
        self._pool = pool or DatabasePool.get_instance()
        self._extractor = EntityExtractor(pool)
        self._glossary_repo = GlossaryRepository(pool)
        self._progress_repo = GlossaryBuildProgressRepository(pool)  # NEW
        self._vector_service = VectorStoreService()
        self._llm_client: NvidiaLLM | None = None

    def build_from_text(
        self,
        text: str,
        work_id: int,
        volume_id: int,  # NEW: required for progress tracking
        source_lang: str = "en",
        target_lang: str = "es",
        suggest_translations: bool = True,
        resume: bool = False,  # NEW
    ) -> BuildResult:
        """
        Build glossary from text with full pipeline.
        
        NEW: Supports resume from last checkpoint when resume=True.
        """
        entities_by_type: dict[str, int] = {}
        
        # Check for resume
        if resume:
            phase, batch_num = self._progress_repo.get_resume_point(work_id, volume_id)
            if phase != "extracted":
                logger.info(f"Resuming from phase '{phase}' (batch {batch_num})")
                return self._resume_from_phase(work_id, volume_id, phase, batch_num, 
                                               source_lang, target_lang, suggest_translations)

        # === PHASE 1: EXTRACT ===
        logger.info("Phase 1: Extracting entities...")
        candidates = self._extractor.extract(text, source_lang)
        
        # Track entities by type
        for c in candidates:
            entities_by_type[c.entity_type] = entities_by_type.get(c.entity_type, 0) + 1
        
        # Filter duplicates against existing glossary
        new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)
        
        if not new_entities:
            return BuildResult(
                extracted=len(candidates),
                new=0,
                skipped=len(candidates),
                entities_by_type=entities_by_type,
            )
        
        # NEW: Save extracted entities to progress table
        progress_records = self._progress_repo.save_extracted(
            work_id, volume_id, new_entities
        )
        logger.info(f"Saved {len(progress_records)} entities to progress table")
        
        # === PHASE 2: VALIDATE ===
        validated_entities = new_entities
        if suggest_translations:
            logger.info(f"Phase 2: Validating {len(new_entities)} entities with LLM...")
            validated_entities, validation_batches = self._validate_with_llm_tracked(
                new_entities, source_lang, work_id, volume_id
            )
        
        # Update entities_by_type with validated types
        entities_by_type = {}
        for e in validated_entities:
            entities_by_type[e.entity_type] = entities_by_type.get(e.entity_type, 0) + 1
        
        # === PHASE 3: EMBEDDINGS ===
        logger.info("Phase 3: Generating embeddings...")
        entity_embeddings = self._vector_service.embed_entities_for_glossary(
            validated_entities
        )
        
        # NEW: Update embeddings in progress table
        embedding_updates = []
        for entity, embedding in entity_embeddings:
            matching = [p for p in progress_records if p.entity_text == entity.text]
            if matching:
                embedding_updates.append((matching[0].id, embedding))
        if embedding_updates:
            self._progress_repo.batch_update_embeddings(embedding_updates)
        
        # === PHASE 4: TRANSLATE ===
        translations: dict[str, str] = {}
        if suggest_translations and entity_embeddings:
            logger.info("Phase 4: Translating entities...")
            translations, translation_batches = self._suggest_translations_tracked(
                validated_entities, source_lang, target_lang, work_id, volume_id
            )
            
            # NEW: Update translations in progress table
            translation_updates = []
            for entity in validated_entities:
                if entity.text in translations:
                    matching = [p for p in progress_records if p.entity_text == entity.text]
                    if matching:
                        translation_updates.append((matching[0].id, translations[entity.text]))
            if translation_updates:
                self._progress_repo.batch_update_translations(translation_updates)
        
        # === PHASE 5: SAVE ===
        logger.info("Phase 5: Saving to glossary...")
        saved = self._save_entities(
            entity_embeddings,
            translations,
            work_id,
            source_lang,
            target_lang,
        )
        
        # NEW: Mark as saved in progress table
        self._progress_repo.batch_update_phase(
            [p.id for p in progress_records], "saved"
        )
        
        # NEW: Cleanup progress records
        self._progress_repo.cleanup_completed(volume_id)
        
        return BuildResult(
            extracted=len(candidates),
            new=len(saved),
            skipped=len(candidates) - len(validated_entities),
            entities_by_type=entities_by_type,
        )

    def _validate_with_llm_tracked(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
        work_id: int,
        volume_id: int,
    ) -> tuple[list[EntityCandidate], int]:
        """
        Validate entities with LLM, tracking progress per batch.
        Returns (validated_entities, last_batch_number).
        """
        if not entities:
            return [], 0
        
        self._ensure_llm()
        batch_size = self._calculate_validation_batch_size()
        batches = self._split_into_batches(entities, batch_size)
        
        validated_entities = []
        for i, batch in enumerate(batches):
            logger.info(f"Validating batch {i + 1}/{len(batches)} ({len(batch)} entities)")
            batch_validated = self._validate_batch(batch, source_lang)
            validated_entities.extend(batch_validated)
            
            # NEW: Update progress after each batch
            batch_entity_texts = [e.text for e in batch_validated]
            matching_ids = [
                p.id for p in self._progress_repo.get_pending_for_phase(
                    work_id, volume_id, "extracted"
                ) if p.entity_text in batch_entity_texts
            ]
            self._progress_repo.batch_update_phase(matching_ids, "validated", i + 1)
        
        return validated_entities, len(batches)

    def _suggest_translations_tracked(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
        target_lang: str,
        work_id: int,
        volume_id: int,
    ) -> tuple[dict[str, str], int]:
        """
        Suggest translations with progress tracking.
        Returns (translations, last_batch_number).
        """
        if not entities:
            return {}, 0
        
        self._ensure_llm()
        
        # Check if entities already have translations from validation
        if all(e.translation for e in entities):
            logger.info("Using translations from LLM validation")
            return {e.text: e.translation for e in entities}, 0
        
        batch_size = self._calculate_translation_batch_size(len(entities))
        batches = self._split_into_batches(entities, batch_size)
        
        all_translations = {}
        for i, batch in enumerate(batches):
            logger.info(f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)")
            batch_translations = self._translate_batch(batch, source_lang, target_lang)
            all_translations.update(batch_translations)
            
            # NEW: Update progress after each batch
            batch_entity_texts = list(batch_translations.keys())
            matching_ids = [
                p.id for p in self._progress_repo.get_pending_for_phase(
                    work_id, volume_id, "validated"
                ) if p.entity_text in batch_entity_texts
            ]
            self._progress_repo.batch_update_phase(matching_ids, "translated", i + 1)
        
        return all_translations, len(batches)

    def _resume_from_phase(
        self,
        work_id: int,
        volume_id: int,
        phase: str,
        batch_num: int | None,
        source_lang: str,
        target_lang: str,
        suggest_translations: bool,
    ) -> BuildResult:
        """Resume pipeline from a specific phase."""
        if phase == "validated":
            # Resume from validation
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "extracted"
            )
            # Convert back to EntityCandidate
            entities = [
                EntityCandidate(
                    text=p.entity_text,
                    entity_type=p.entity_type or "other",
                    frequency=p.frequency,
                    contexts=p.contexts,
                ) for p in pending
            ]
            validated, _ = self._validate_with_llm_tracked(
                entities, source_lang, work_id, volume_id
            )
            # Continue pipeline...
            
        elif phase == "translated":
            # Resume from translation
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "validated"
            )
            # ... continue from translation phase
        
        # ... (implementation continues)
```

### Modified VolumeRepository

```python
# src/pdftranslator/database/repositories/volume_repository.py (additions)

def update_build_status(
    self, 
    volume_id: int, 
    status: str,
    error_message: str | None = None,
    resume_phase: str | None = None
) -> bool:
    """Update the glossary build status of a volume."""
    pool = self._pool.get_sync_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE volumes
                SET glossary_build_status = %s,
                    glossary_error_message = %s,
                    glossary_resume_phase = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (status, error_message, resume_phase, volume_id))
            return cur.rowcount > 0

def get_volumes_by_status(
    self, 
    work_id: int, 
    status: str
) -> list[Volume]:
    """Get all volumes with a specific build status."""
    pool = self._pool.get_sync_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, work_id, volume_number, title, full_text, 
                       translated_text, glossary_built_at, created_at
                FROM volumes
                WHERE work_id = %s AND glossary_build_status = %s
                ORDER BY volume_number
            """, (work_id, status))
            return [self._row_to_volume(row) for row in cur.fetchall()]
```

## CLI and API Changes

### CLI Changes

```python
# src/pdftranslator/cli/commands/build_glossary.py

@app.command("build-glossary")
def build_glossary(
    min_frequency: int = typer.Option(2, "--min-frequency", "-m"),
    source_lang: str = typer.Option("en", "--source-lang", "-s"),
    target_lang: str = typer.Option("es", "--target-lang", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    resume: bool = typer.Option(
        False, 
        "--resume", 
        "-r", 
        help="Resume from last checkpoint if interrupted"
    ),
    force_restart: bool = typer.Option(
        False,
        "--force-restart",
        "-f",
        help="Ignore existing progress and start fresh"
    ),
):
    """
    Build glossary with resume support.
    
    Examples:
        pdftranslator build-glossary
        pdftranslator build-glossary --resume
        pdftranslator build-glossary --force-restart
    """
    setup_logging()
    
    # ... work selection ...
    
    if force_restart:
        # Clear any existing progress
        progress_repo = GlossaryBuildProgressRepository(pool)
        volume_repo.update_build_status(volume.id, "pending")
        # Clear progress table for this volume
        # ...
    
    # Check for failed/in-progress volumes when resume is True
    if resume:
        failed_volumes = volume_repo.get_volumes_by_status(work.id, "failed")
        in_progress_volumes = volume_repo.get_volumes_by_status(work.id, "in_progress")
        
        if failed_volumes:
            console.print(f"[yellow]Found {len(failed_volumes)} failed volumes to resume[/yellow]")
        if in_progress_volumes:
            console.print(f"[yellow]Found {len(in_progress_volumes)} in-progress volumes[/yellow]")
    
    # ... processing ...
    
    try:
        volume_repo.update_build_status(volume.id, "in_progress")
        
        result = manager.build_from_text(
            text=consolidated_text,
            work_id=work.id,
            volume_id=volume.id,
            source_lang=source_lang,
            target_lang=target_lang,
            suggest_translations=not dry_run,
            resume=resume,
        )
        
        volume_repo.update_build_status(volume.id, "completed")
        
    except Exception as e:
        volume_repo.update_build_status(
            volume.id, 
            "failed",
            error_message=str(e),
            resume_phase=determine_resume_phase(e)
        )
        raise
```

### API Changes

```python
# src/pdftranslator/backend/api/routes/glossary.py

@router.post("/build", response_model=GlossaryBuildResponse)
async def build_glossary(
    data: GlossaryBuildRequest,
    resume: bool = Query(
        False, 
        description="Resume from last checkpoint if interrupted"
    ),
    force_restart: bool = Query(
        False,
        description="Ignore existing progress and start fresh"
    ),
    background_tasks: BackgroundTasks = None,
):
    """
    Build glossary from work volumes using NER + LLM.
    
    NEW: Supports resume from last checkpoint with ?resume=true
    """
    # ... validation ...
    
    for volume in sorted(volumes, key=lambda v: v.volume_number):
        if volume.glossary_built_at:
            # Already completed
            continue
            
        try:
            volume_repo.update_build_status(volume.id, "in_progress")
            
            result = manager.build_from_text(
                text=consolidated_text,
                work_id=data.work_id,
                volume_id=volume.id,
                source_lang=source_lang,
                target_lang=target_lang,
                suggest_translations=True,
                resume=resume,
            )
            
            volume_repo.update_build_status(volume.id, "completed")
            
        except Exception as e:
            volume_repo.update_build_status(
                volume.id,
                "failed",
                error_message=str(e)
            )
            logger.error(f"Volume {volume.volume_number} failed: {e}")
            # Continue with next volume or raise
```

### New Response Schema

```python
# src/pdftranslator/backend/api/models/schemas.py

class GlossaryBuildVolumeResult(BaseModel):
    volume_id: int
    volume_number: int
    extracted: int
    new: int
    skipped: int
    entities_by_type: dict[str, int]
    
    # NEW: Resume information
    was_resumed: bool = False
    resume_phase: str | None = None
    progress_stats: dict[str, int] | None = None  # {"extracted": N, "validated": M, ...}

class GlossaryBuildResponse(BaseModel):
    total_extracted: int
    total_new: int
    total_skipped: int
    volumes_processed: int
    volumes_skipped: int
    entities_by_type: dict[str, int]
    volume_results: list[GlossaryBuildVolumeResult]
    
    # NEW: Overall resume stats
    resumed_volumes: int = 0
```

## Error Handling

### Error Detection and Resume Point

When an error occurs, the system determines the appropriate resume point:

```python
def determine_resume_phase(error: Exception) -> str:
    """Determine which phase to resume from based on error type."""
    error_str = str(error).lower()
    
    if "nltk" in error_str or "tokenize" in error_str:
        return "extracted"
    elif "validation" in error_str or "validate_batch" in error_str:
        return "extracted"  # Re-validate from start of phase
    elif "embedding" in error_str or "vector" in error_str:
        return "validated"
    elif "translation" in error_str or "translate_batch" in error_str:
        return "validated"  # Re-translate from start of phase
    else:
        return "extracted"  # Safe default
```

### Cleanup Strategy

Progress records are cleaned up in these scenarios:

1. **Successful completion**: All records deleted
2. **Manual restart with `--force-restart`**: All records deleted
3. **Work/Volume deletion**: Cascade delete via foreign key
4. **Old progress cleanup**: Scheduled job (optional) to clean up progress older than N days

```python
# Optional: Cleanup job for stale progress
def cleanup_stale_progress(days_old: int = 7) -> int:
    """Remove progress records older than N days."""
    pool = DatabasePool.get_instance().get_sync_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM glossary_build_progress
                WHERE created_at < NOW() - INTERVAL '%s days'
            """, (days_old,))
            return cur.rowcount
```

## Testing Strategy

### Unit Tests

```python
# tests/database/test_glossary_build_progress_repository.py

def test_save_extracted_entities():
    """Test saving extracted entities to progress table."""
    
def test_get_pending_for_phase():
    """Test retrieving entities pending for a specific phase."""
    
def test_batch_update_phase():
    """Test updating phase for multiple entities."""
    
def test_get_resume_point():
    """Test determining resume point from progress state."""
    
def test_cleanup_completed():
    """Test cleanup of completed progress records."""
```

### Integration Tests

```python
# tests/database/test_glossary_manager_resume.py

def test_resume_from_validation_phase():
    """Test resuming from LLM validation phase."""
    
def test_resume_from_translation_phase():
    """Test resuming from translation phase."""
    
def test_resume_after_failure():
    """Test full cycle: start, fail, resume, complete."""
    
def test_force_restart_clears_progress():
    """Test that --force-restart clears existing progress."""
```

### E2E Tests

```bash
# Start glossary build
pdftranslator build-glossary --work-id 1

# Simulate failure (Ctrl+C or kill)

# Resume from checkpoint
pdftranslator build-glossary --work-id 1 --resume

# Verify results match expected
```

## Performance Considerations

### Overhead Analysis

| Operation | Overhead | Impact |
|-----------|----------|--------|
| Save extracted entities | 1 bulk INSERT | Low (milliseconds) |
| Update phase (per batch) | 1 UPDATE per batch | Very Low |
| Update embeddings | N UPDATEs | Medium (batched) |
| Update translations | N UPDATEs | Medium (batched) |
| Cleanup | 1 DELETE | Low |

**Total overhead**: < 5% of total processing time (LLM calls dominate)

### Optimization Opportunities

1. **Bulk operations**: Use COPY for initial insert
2. **Batch updates**: Single UPDATE with WHERE id = ANY(...)
3. **Partial indexes**: Index only pending phases
4. **Connection pooling**: Use existing pool (no extra connections)

## Migration Plan

### Step 1: Create Migration File

```sql
-- src/pdftranslator/database/schemas/015_glossary_build_progress.sql
-- (Full schema from Database Schema section)
```

### Step 2: Run Migration

```bash
psql -h localhost -U postgres -d pdftranslator \
  -f src/pdftranslator/database/schemas/015_glossary_build_progress.sql
```

### Step 3: Deploy Code Changes

1. Add `GlossaryBuildProgress` model
2. Add `GlossaryBuildProgressRepository`
3. Modify `GlossaryManager.build_from_text()`
4. Modify `VolumeRepository` with status methods
5. Update CLI and API endpoints

### Step 4: Test

```bash
pytest tests/database/test_glossary_build_progress_repository.py
pytest tests/database/test_glossary_manager_resume.py
```

## Future Enhancements

1. **Progress UI**: Add real-time progress display in frontend
2. **Batch retry**: Retry failed batches without restarting phase
3. **Parallel processing**: Process multiple volumes in parallel with progress tracking
4. **Progress export**: Export progress to JSON for debugging
5. **Auto-resume**: Automatically detect and prompt for resume on startup

## Appendix: Full Migration SQL

```sql
-- src/pdftranslator/database/schemas/015_glossary_build_progress.sql

-- Progress tracking table
CREATE TABLE IF NOT EXISTS glossary_build_progress (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,
    
    -- Phase tracking
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',
    
    -- Entity data
    entity_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    contexts TEXT[],
    translation VARCHAR(500),
    embedding vector(1536),
    
    -- Batch tracking
    validation_batch INTEGER,
    translation_batch INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(work_id, volume_id, LOWER(entity_text))
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_progress_work_volume 
    ON glossary_build_progress(work_id, volume_id);

CREATE INDEX IF NOT EXISTS idx_progress_phase 
    ON glossary_build_progress(phase);

CREATE INDEX IF NOT EXISTS idx_progress_resume 
    ON glossary_build_progress(work_id, volume_id, phase) 
    WHERE phase != 'saved';

CREATE INDEX IF NOT EXISTS idx_progress_pending 
    ON glossary_build_progress(work_id, volume_id) 
    WHERE phase IN ('extracted', 'validated', 'translated');

-- Extend volumes table
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_build_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_error_message TEXT;
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_resume_phase VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_volumes_build_status 
    ON volumes(glossary_build_status);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_glossary_progress_updated_at 
    BEFORE UPDATE ON glossary_build_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```
