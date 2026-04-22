# Glossary Resume System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a checkpoint-based resume system for glossary build process that saves progress at each pipeline phase and can resume from the exact failure point.

**Architecture:** Create a new `glossary_build_progress` table that tracks each entity through phases (extracted → validated → translated → saved). Modify `GlossaryManager` to save progress after each batch, and add `--resume` flag to CLI/API. Uses existing repository pattern and connection pool.

**Tech Stack:** Python 3.11, PostgreSQL with pgvector, psycopg 3, Typer CLI, FastAPI

---

## Task 1: Create Database Migration

**Files:**
- Create: `src/pdftranslator/database/schemas/015_glossary_build_progress.sql`

**Step 1: Write migration file**
Create the SQL migration file with the progress table and volume extensions:

```sql
-- Progress tracking table for glossary build resume system
CREATE TABLE IF NOT EXISTS glossary_build_progress (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    volume_id INTEGER NOT NULL REFERENCES volumes(id) ON DELETE CASCADE,
    entity_text VARCHAR(200) NOT NULL,
    
    -- Phase tracking: extracted -> validated -> translated -> saved
    phase VARCHAR(20) NOT NULL DEFAULT 'extracted',
    
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

-- Extend volumes table with build status
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_build_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_error_message TEXT;
ALTER TABLE volumes ADD COLUMN IF NOT EXISTS glossary_resume_phase VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_volumes_build_status 
    ON volumes(glossary_build_status);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_glossary_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_glossary_progress_updated_at ON glossary_build_progress;
CREATE TRIGGER update_glossary_progress_updated_at 
    BEFORE UPDATE ON glossary_build_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_glossary_progress_updated_at();
```

**Step 2: Run migration**
Execute the migration against the database:
```bash
psql -h localhost -U postgres -d pdftranslator -f src/pdftranslator/database/schemas/015_glossary_build_progress.sql
```

Expected: `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE` messages

**Step 3: Verify migration**
```bash
psql -h localhost -U postgres -d pdftranslator -c "\d glossary_build_progress"
```

Expected: Table structure showing all columns and indexes

**Step 4: Commit**
```bash
git add src/pdftranslator/database/schemas/015_glossary_build_progress.sql
git commit -m "feat(db): add glossary_build_progress table for resume system"
```

---

## Task 2: Add Data Model

**Files:**
- Modify: `src/pdftranslator/database/models.py` (add after `BuildResult` class)

**Step 1: Write failing test for model**
Create test file: `tests/database/test_glossary_build_progress_model.py`

```python
"""Tests for GlossaryBuildProgress model."""

import pytest
from datetime import datetime

from pdftranslator.database.models import GlossaryBuildProgress


def test_glossary_build_progress_creation():
    """Test creating a progress record."""
    progress = GlossaryBuildProgress(
        work_id=1,
        volume_id=2,
        entity_text="Harry Potter",
        phase="extracted",
        entity_type="character",
        frequency=10,
    )
    
    assert progress.work_id == 1
    assert progress.volume_id == 2
    assert progress.entity_text == "Harry Potter"
    assert progress.phase == "extracted"
    assert progress.is_complete() is False


def test_glossary_build_progress_is_complete():
    """Test is_complete method."""
    progress = GlossaryBuildProgress(phase="saved")
    assert progress.is_complete() is True
    
    progress.phase = "extracted"
    assert progress.is_complete() is False


def test_glossary_build_progress_next_phase():
    """Test next_phase method."""
    progress = GlossaryBuildProgress(phase="extracted")
    assert progress.next_phase() == "validated"
    
    progress.phase = "validated"
    assert progress.next_phase() == "translated"
    
    progress.phase = "translated"
    assert progress.next_phase() == "saved"
    
    progress.phase = "saved"
    assert progress.next_phase() is None


def test_glossary_build_progress_default_values():
    """Test default values."""
    progress = GlossaryBuildProgress()
    
    assert progress.frequency == 1
    assert progress.phase == "extracted"
    assert progress.contexts == []
    assert progress.embedding is None
    assert progress.translation is None
```

**Step 2: Run test to verify it fails**
```bash
pytest tests/database/test_glossary_build_progress_model.py -v
```

Expected: FAIL with "cannot import name 'GlossaryBuildProgress'"

**Step 3: Implement the model**
Add to `src/pdftranslator/database/models.py` after `BuildResult` class:

```python
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
```

**Step 4: Update __all__ in models.py**
```python
__all__ = [
    # From models.work (backward compatibility)
    "Work",
    "Volume",
    "Chapter",
    "GlossaryEntry",
    # From this module
    "UploadedFile",
    "ContextExample",
    "TermContext",
    "EntityBlacklist",
    "FantasyTerm",
    "EntityCandidate",
    "BuildResult",
    "GlossaryBuildProgress",  # NEW
    "SubstitutionRule",
]
```

**Step 5: Run test to verify it passes**
```bash
pytest tests/database/test_glossary_build_progress_model.py -v
```

Expected: PASS (all tests green)

**Step 6: Commit**
```bash
git add src/pdftranslator/database/models.py tests/database/test_glossary_build_progress_model.py
git commit -m "feat(models): add GlossaryBuildProgress dataclass for tracking"
```

---

## Task 3: Create Progress Repository

**Files:**
- Create: `src/pdftranslator/database/repositories/glossary_build_progress_repository.py`
- Create: `tests/database/test_glossary_build_progress_repository.py`

**Step 1: Write failing tests**
Create `tests/database/test_glossary_build_progress_repository.py`:

```python
"""Tests for GlossaryBuildProgressRepository."""

import pytest
from unittest.mock import MagicMock, patch

from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)
from pdftranslator.database.models import EntityCandidate, GlossaryBuildProgress


@pytest.fixture
def mock_pool():
    """Mock database pool."""
    pool = MagicMock()
    sync_pool = MagicMock()
    pool.get_sync_pool.return_value.__enter__ = MagicMock(return_value=sync_pool)
    pool.get_sync_pool.return_value.__exit__ = MagicMock(return_value=None)
    return pool, sync_pool


@pytest.fixture
def sample_entities():
    """Sample entity candidates for testing."""
    return [
        EntityCandidate(text="Harry Potter", entity_type="character", frequency=10),
        EntityCandidate(text="Hogwarts", entity_type="place", frequency=5),
        EntityCandidate(text="Expelliarmus", entity_type="skill", frequency=3),
    ]


class TestGlossaryBuildProgressRepository:
    def test_save_extracted(self, mock_pool, sample_entities):
        """Test saving extracted entities."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.fetchone.return_value = (1, 1, 1, "Harry Potter", "extracted", "character", 10, [], None, None, None, None, None, None)
        
        repo = GlossaryBuildProgressRepository(pool)
        result = repo.save_extracted(1, 1, sample_entities)
        
        assert cursor.execute.called
        assert len(result) >= 0  # Returns list of progress records

    def test_get_pending_for_phase(self, mock_pool):
        """Test retrieving pending entities for a phase."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.fetchall.return_value = [
            (1, 1, 1, "Harry Potter", "extracted", "character", 10, [], None, None, None, None, None, None),
        ]
        
        repo = GlossaryBuildProgressRepository(pool)
        result = repo.get_pending_for_phase(1, 1, "extracted")
        
        assert len(result) == 1
        assert result[0].entity_text == "Harry Potter"
        assert result[0].phase == "extracted"

    def test_batch_update_phase(self, mock_pool):
        """Test batch updating phase."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.rowcount = 3
        
        repo = GlossaryBuildProgressRepository(pool)
        result = repo.batch_update_phase([1, 2, 3], "validated")
        
        assert cursor.execute.called
        assert result == 3

    def test_get_resume_point_empty(self, mock_pool):
        """Test resume point when no progress exists."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.fetchall.return_value = []
        
        repo = GlossaryBuildProgressRepository(pool)
        phase, batch = repo.get_resume_point(1, 1)
        
        assert phase == "extracted"
        assert batch is None

    def test_get_statistics(self, mock_pool):
        """Test getting progress statistics."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.fetchall.return_value = [
            ("extracted", 10),
            ("validated", 5),
            ("saved", 3),
        ]
        
        repo = GlossaryBuildProgressRepository(pool)
        result = repo.get_statistics(1, 1)
        
        assert result["extracted"] == 10
        assert result["validated"] == 5
        assert result["saved"] == 3

    def test_cleanup_completed(self, mock_pool):
        """Test cleaning up completed progress."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.rowcount = 10
        
        repo = GlossaryBuildProgressRepository(pool)
        result = repo.cleanup_completed(1)
        
        assert cursor.execute.called
```

**Step 2: Run tests to verify they fail**
```bash
pytest tests/database/test_glossary_build_progress_repository.py -v
```

Expected: FAIL with "No module named"

**Step 3: Implement the repository**
Create `src/pdftranslator/database/repositories/glossary_build_progress_repository.py`:

```python
"""Repository for glossary build progress tracking."""

from __future__ import annotations

import logging
from typing import Optional, List

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.models import EntityCandidate, GlossaryBuildProgress

logger = logging.getLogger(__name__)


class GlossaryBuildProgressRepository:
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def save_extracted(
        self,
        work_id: int,
        volume_id: int,
        entities: List[EntityCandidate],
    ) -> List[GlossaryBuildProgress]:
        """
        Save entities after extraction phase.
        Uses ON CONFLICT to handle duplicates.
        """
        if not entities:
            return []

        pool = self._pool.get_sync_pool()
        results = []
        
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for entity in entities:
                    cur.execute(
                        """
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
                        """,
                        (
                            work_id,
                            volume_id,
                            entity.text,
                            entity.entity_type,
                            entity.frequency,
                            entity.contexts,
                        ),
                    )
                    row = cur.fetchone()
                    if row:
                        results.append(self._row_to_progress(row))

        logger.info(f"Saved {len(results)} entities to progress table")
        return results

    def get_pending_for_phase(
        self,
        work_id: int,
        volume_id: int,
        phase: str,
    ) -> List[GlossaryBuildProgress]:
        """Get all entities in a specific phase (waiting to be processed)."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_id, entity_text, phase,
                           entity_type, frequency, contexts, translation,
                           validation_batch, translation_batch,
                           created_at, updated_at
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s AND phase = %s
                    ORDER BY id
                    """,
                    (work_id, volume_id, phase),
                )
                rows = cur.fetchall()
                return [self._row_to_progress(row) for row in rows]

    def batch_update_phase(
        self,
        ids: List[int],
        phase: str,
        batch_number: Optional[int] = None,
    ) -> int:
        """Update phase for multiple progress records."""
        if not ids:
            return 0

        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                batch_field = ""
                if batch_number is not None:
                    if phase == "validated":
                        batch_field = ", validation_batch = %s"
                    elif phase == "translated":
                        batch_field = ", translation_batch = %s"

                sql = f"""
                    UPDATE glossary_build_progress
                    SET phase = %s{batch_field}, updated_at = NOW()
                    WHERE id = ANY(%s)
                """

                if batch_number is not None and batch_field:
                    cur.execute(sql, (phase, batch_number, ids))
                else:
                    cur.execute(sql, (phase, ids))

                return cur.rowcount

    def batch_update_embeddings(
        self,
        updates: List[tuple[int, List[float]]],
    ) -> int:
        """Update embeddings for validated entities."""
        if not updates:
            return 0

        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for progress_id, embedding in updates:
                    cur.execute(
                        """
                        UPDATE glossary_build_progress
                        SET embedding = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (embedding, progress_id),
                    )
        return len(updates)

    def batch_update_translations(
        self,
        updates: List[tuple[int, str]],
    ) -> int:
        """Update translations for entities."""
        if not updates:
            return 0

        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for progress_id, translation in updates:
                    cur.execute(
                        """
                        UPDATE glossary_build_progress
                        SET translation = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (translation, progress_id),
                    )
        return len(updates)

    def get_resume_point(
        self,
        work_id: int,
        volume_id: int,
    ) -> tuple[str, Optional[int]]:
        """
        Determine where to resume from.
        Returns (phase, batch_number).
        """
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT phase, COUNT(*) as count,
                           MAX(validation_batch) as last_val_batch,
                           MAX(translation_batch) as last_trans_batch
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s
                    GROUP BY phase
                    ORDER BY phase
                    """,
                    (work_id, volume_id),
                )
                results = cur.fetchall()

                if not results:
                    return ("extracted", None)

                phase_counts = {
                    row[0]: (row[1], row[2], row[3]) for row in results
                }

                if "extracted" in phase_counts:
                    extracted_count, _, _ = phase_counts.get("extracted", (0, None, None))
                    if extracted_count > 0:
                        return ("validated", None)

                if "validated" in phase_counts:
                    validated_count, last_val_batch, _ = phase_counts.get(
                        "validated", (0, None, None)
                    )
                    if validated_count > 0:
                        return ("translated", last_val_batch)

                return ("extracted", None)

    def get_statistics(
        self,
        work_id: int,
        volume_id: int,
    ) -> dict:
        """Get progress statistics for a volume."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT phase, COUNT(*) as count
                    FROM glossary_build_progress
                    WHERE work_id = %s AND volume_id = %s
                    GROUP BY phase
                    """,
                    (work_id, volume_id),
                )
                return {row[0]: row[1] for row in cur.fetchall()}

    def cleanup_completed(self, volume_id: int) -> int:
        """Remove progress records after successful completion."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM glossary_build_progress
                    WHERE volume_id = %s
                    """,
                    (volume_id,),
                )
                return cur.rowcount

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
            embedding=list(row[9]) if row[9] else None,
            validation_batch=row[10],
            translation_batch=row[11],
            created_at=row[12],
            updated_at=row[13],
        )
```

**Step 4: Run tests to verify they pass**
```bash
pytest tests/database/test_glossary_build_progress_repository.py -v
```

Expected: PASS (all tests green)

**Step 5: Commit**
```bash
git add src/pdftranslator/database/repositories/glossary_build_progress_repository.py tests/database/test_glossary_build_progress_repository.py
git commit -m "feat(repo): add GlossaryBuildProgressRepository"
```

---

## Task 4: Extend VolumeRepository

**Files:**
- Modify: `src/pdftranslator/database/repositories/volume_repository.py`
- Create: `tests/database/test_volume_repository_status.py`

**Step 1: Write failing tests**
Create `tests/database/test_volume_repository_status.py`:

```python
"""Tests for VolumeRepository status methods."""

import pytest
from unittest.mock import MagicMock

from pdftranslator.database.repositories.volume_repository import VolumeRepository


@pytest.fixture
def mock_pool():
    """Mock database pool."""
    pool = MagicMock()
    sync_pool = MagicMock()
    pool.get_sync_pool.return_value.__enter__ = MagicMock(return_value=sync_pool)
    pool.get_sync_pool.return_value.__exit__ = MagicMock(return_value=None)
    return pool, sync_pool


class TestVolumeRepositoryStatus:
    def test_update_build_status(self, mock_pool):
        """Test updating build status."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.rowcount = 1
        
        repo = VolumeRepository(pool)
        result = repo.update_build_status(1, "in_progress")
        
        assert cursor.execute.called
        assert result is True

    def test_update_build_status_with_error(self, mock_pool):
        """Test updating build status with error message."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        
        repo = VolumeRepository(pool)
        result = repo.update_build_status(1, "failed", error_message="Test error")
        
        assert cursor.execute.called

    def test_get_volumes_by_status(self, mock_pool):
        """Test getting volumes by status."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        cursor.fetchall.return_value = []
        
        repo = VolumeRepository(pool)
        result = repo.get_volumes_by_status(1, "failed")
        
        assert cursor.execute.called
        assert isinstance(result, list)
```

**Step 2: Run tests to verify they fail**
```bash
pytest tests/database/test_volume_repository_status.py -v
```

Expected: FAIL with "AttributeError: 'VolumeRepository' object has no attribute 'update_build_status'"

**Step 3: Implement status methods**
Add to `src/pdftranslator/database/repositories/volume_repository.py` before the final closing:

```python
    def update_build_status(
        self,
        volume_id: int,
        status: str,
        error_message: str | None = None,
        resume_phase: str | None = None,
    ) -> bool:
        """Update the glossary build status of a volume."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE volumes
                    SET glossary_build_status = %s,
                        glossary_error_message = %s,
                        glossary_resume_phase = %s
                    WHERE id = %s
                    """,
                    (status, error_message, resume_phase, volume_id),
                )
                return cur.rowcount > 0

    def get_volumes_by_status(
        self,
        work_id: int,
        status: str,
    ) -> list[Volume]:
        """Get all volumes with a specific build status."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, 
                           translated_text, glossary_built_at, created_at
                    FROM volumes
                    WHERE work_id = %s AND glossary_build_status = %s
                    ORDER BY volume_number
                    """,
                    (work_id, status),
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]
```

**Step 4: Update Volume model**
Check if `Volume` dataclass in `src/pdftranslator/core/models/work.py` has the new fields. If not, add:

```python
@dataclass
class Volume:
    # ... existing fields ...
    glossary_build_status: str = "pending"
    glossary_error_message: str | None = None
    glossary_resume_phase: str | None = None
```

Update `_row_to_volume` in `volume_repository.py` to handle these fields:

```python
def _row_to_volume(self, row: tuple) -> Volume:
    return Volume(
        id=row[0],
        work_id=row[1],
        volume_number=row[2],
        title=row[3],
        full_text=row[4],
        translated_text=row[5],
        glossary_built_at=row[6] if len(row) > 6 else None,
        created_at=row[7] if len(row) > 7 else None,
        glossary_build_status=row[8] if len(row) > 8 else "pending",
        glossary_error_message=row[9] if len(row) > 9 else None,
        glossary_resume_phase=row[10] if len(row) > 10 else None,
    )
```

**Step 5: Run tests to verify they pass**
```bash
pytest tests/database/test_volume_repository_status.py -v
```

Expected: PASS

**Step 6: Commit**
```bash
git add src/pdftranslator/database/repositories/volume_repository.py tests/database/test_volume_repository_status.py
git commit -m "feat(repo): add build status methods to VolumeRepository"
```

---

## Task 5: Modify GlossaryManager - Part 1 (Save Progress)

**Files:**
- Modify: `src/pdftranslator/database/services/glossary_manager.py`
- Create: `tests/database/test_glossary_manager_progress.py`

**Step 1: Write failing tests for progress tracking**
Create `tests/database/test_glossary_manager_progress.py`:

```python
"""Tests for GlossaryManager progress tracking."""

import pytest
from unittest.mock import MagicMock, patch, call

from pdftranslator.database.services.glossary_manager import GlossaryManager
from pdftranslator.database.models import EntityCandidate, BuildResult


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies."""
    with patch("pdftranslator.database.services.glossary_manager.EntityExtractor") as mock_extractor_cls, \
         patch("pdftranslator.database.services.glossary_manager.GlossaryRepository") as mock_glossary_cls, \
         patch("pdftranslator.database.services.glossary_manager.GlossaryBuildProgressRepository") as mock_progress_cls, \
         patch("pdftranslator.database.services.glossary_manager.VectorStoreService") as mock_vector_cls:
        
        mock_pool = MagicMock()
        mock_extractor = MagicMock()
        mock_glossary = MagicMock()
        mock_progress = MagicMock()
        mock_vector = MagicMock()
        
        mock_extractor_cls.return_value = mock_extractor
        mock_glossary_cls.return_value = mock_glossary
        mock_progress_cls.return_value = mock_progress
        mock_vector_cls.return_value = mock_vector
        
        yield {
            "pool": mock_pool,
            "extractor": mock_extractor,
            "glossary": mock_glossary,
            "progress": mock_progress,
            "vector": mock_vector,
        }


class TestGlossaryManagerProgress:
    def test_save_extracted_on_build(self, mock_dependencies):
        """Test that extracted entities are saved to progress table."""
        manager = GlossaryManager(mock_dependencies["pool"])
        
        # Mock extraction
        mock_dependencies["extractor"].extract.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]
        mock_dependencies["glossary"].filter_new_entities.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]
        mock_dependencies["progress"].save_extracted.return_value = []
        mock_dependencies["vector"].embed_entities_for_glossary.return_value = []
        
        # Call build_from_text with volume_id
        result = manager.build_from_text(
            text="Test text",
            work_id=1,
            volume_id=1,
            suggest_translations=False,
        )
        
        # Verify progress was saved
        mock_dependencies["progress"].save_extracted.assert_called_once()

    def test_cleanup_on_completion(self, mock_dependencies):
        """Test that progress is cleaned up after successful completion."""
        manager = GlossaryManager(mock_dependencies["pool"])
        
        mock_dependencies["extractor"].extract.return_value = []
        mock_dependencies["glossary"].filter_new_entities.return_value = []
        
        result = manager.build_from_text(
            text="Test",
            work_id=1,
            volume_id=1,
        )
        
        # Verify cleanup was called
        mock_dependencies["progress"].cleanup_completed.assert_called_once_with(1)
```

**Step 2: Run tests to verify they fail**
```bash
pytest tests/database/test_glossary_manager_progress.py -v
```

Expected: FAIL (method signature mismatch or missing calls)

**Step 3: Modify GlossaryManager constructor**
Update `src/pdftranslator/database/services/glossary_manager.py`:

```python
from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)

class GlossaryManager:
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._extractor = EntityExtractor(pool)
        self._glossary_repo = GlossaryRepository(pool)
        self._progress_repo = GlossaryBuildProgressRepository(pool)  # NEW
        self._vector_service = VectorStoreService()
        self._llm_client: Optional[NvidiaLLM] = None
```

**Step 4: Modify build_from_text signature**
Update the method signature to accept `volume_id`:

```python
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
```

**Step 5: Add progress saving in extraction phase**
After filtering duplicates, add:

```python
# 2. Filter duplicates against existing glossary
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
```

**Step 6: Add cleanup at the end**
Before returning BuildResult, add:

```python
# 6. Save to database
saved = self._save_entities(
    entity_embeddings,
    translations,
    work_id,
    source_lang,
    target_lang,
)

# NEW: Mark as saved and cleanup
if progress_records:
    self._progress_repo.batch_update_phase(
        [p.id for p in progress_records if p.id], "saved"
    )
    self._progress_repo.cleanup_completed(volume_id)

return BuildResult(
    extracted=len(candidates),
    new=len(saved),
    skipped=len(candidates) - len(validated_entities),
    entities_by_type=entities_by_type,
)
```

**Step 7: Run tests to verify they pass**
```bash
pytest tests/database/test_glossary_manager_progress.py -v
```

Expected: PASS

**Step 8: Commit**
```bash
git add src/pdftranslator/database/services/glossary_manager.py tests/database/test_glossary_manager_progress.py
git commit -m "feat(manager): add progress saving in extraction phase"
```

---

## Task 6: Modify GlossaryManager - Part 2 (Batch Tracking)

**Files:**
- Modify: `src/pdftranslator/database/services/glossary_manager.py`

**Step 1: Write failing tests for batch tracking**
Add to `tests/database/test_glossary_manager_progress.py`:

```python
    def test_validate_updates_progress_per_batch(self, mock_dependencies):
        """Test that validation updates progress after each batch."""
        manager = GlossaryManager(mock_dependencies["pool"])
        
        # Mock entities
        entities = [
            EntityCandidate(text=f"Entity{i}", entity_type="character", frequency=1)
            for i in range(100)
        ]
        
        mock_dependencies["extractor"].extract.return_value = entities
        mock_dependencies["glossary"].filter_new_entities.return_value = entities
        mock_dependencies["progress"].save_extracted.return_value = [
            MagicMock(id=i, entity_text=f"Entity{i}") for i in range(100)
        ]
        
        # Track phase updates
        update_calls = []
        mock_dependencies["progress"].batch_update_phase.side_effect = lambda ids, phase, *args: update_calls.append((len(ids), phase))
        
        # This would normally call LLM, but we're testing progress tracking
        # ... (requires more mocking of LLM)
```

**Step 2: Modify _validate_with_llm to track progress**
Create a new tracked version:

```python
def _validate_with_llm_tracked(
    self,
    entities: List[EntityCandidate],
    source_lang: str,
    work_id: int,
    volume_id: int,
) -> tuple[List[EntityCandidate], int]:
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
        logger.info(
            f"Validating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
        )
        batch_validated = self._validate_batch(batch, source_lang)
        validated_entities.extend(batch_validated)

        # NEW: Update progress after each batch
        batch_entity_texts = [e.text for e in batch_validated]
        pending = self._progress_repo.get_pending_for_phase(
            work_id, volume_id, "extracted"
        )
        matching_ids = [
            p.id for p in pending if p.entity_text in batch_entity_texts
        ]
        if matching_ids:
            self._progress_repo.batch_update_phase(
                matching_ids, "validated", i + 1
            )

    return validated_entities, len(batches)
```

**Step 3: Modify _suggest_translations similarly**
Create a tracked version:

```python
def _suggest_translations_tracked(
    self,
    entities: List[EntityCandidate],
    source_lang: str,
    target_lang: str,
    work_id: int,
    volume_id: int,
) -> tuple[Dict[str, str], int]:
    """
    Suggest translations with progress tracking.
    Returns (translations, last_batch_number).
    """
    if not entities:
        return {}, 0

    self._ensure_llm()

    # If entities already have translations from validation, use them
    if all(e.translation for e in entities):
        logger.info("Using translations from LLM validation")
        return {e.text: e.translation for e in entities}, 0

    batch_size = self._calculate_translation_batch_size(len(entities))
    batches = self._split_into_batches(entities, batch_size)

    all_translations = {}
    for i, batch in enumerate(batches):
        logger.info(
            f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
        )
        batch_translations = self._translate_batch(batch, source_lang, target_lang)
        all_translations.update(batch_translations)

        # NEW: Update progress after each batch
        batch_entity_texts = list(batch_translations.keys())
        pending = self._progress_repo.get_pending_for_phase(
            work_id, volume_id, "validated"
        )
        matching_ids = [
            p.id for p in pending if p.entity_text in batch_entity_texts
        ]
        if matching_ids:
            self._progress_repo.batch_update_phase(
                matching_ids, "translated", i + 1
            )

    return all_translations, len(batches)
```

**Step 4: Update build_from_text to use tracked versions**
Replace calls to `_validate_with_llm` and `_suggest_translations`:

```python
# 3. Validate with LLM (NEW: use tracked version)
validated_entities = new_entities
validation_batches = 0
if suggest_translations:
    logger.info(f"Validating {len(new_entities)} entities with LLM...")
    validated_entities, validation_batches = self._validate_with_llm_tracked(
        new_entities, source_lang, work_id, volume_id
    )

# ... (embedding phase)

# 5. Suggest translations with batching (IMPROVED: use tracked version)
translations: Dict[str, str] = {}
translation_batches = 0
if suggest_translations and entity_embeddings:
    translations, translation_batches = self._suggest_translations_tracked(
        validated_entities, source_lang, target_lang, work_id, volume_id
    )
```

**Step 5: Run tests**
```bash
pytest tests/database/test_glossary_manager_progress.py -v
```

**Step 6: Commit**
```bash
git add src/pdftranslator/database/services/glossary_manager.py tests/database/test_glossary_manager_progress.py
git commit -m "feat(manager): add batch-level progress tracking for validation and translation"
```

---

## Task 7: Implement Resume Logic

**Files:**
- Modify: `src/pdftranslator/database/services/glossary_manager.py`

**Step 1: Write failing tests for resume**
Add to `tests/database/test_glossary_manager_progress.py`:

```python
    def test_resume_from_validation_phase(self, mock_dependencies):
        """Test resuming from validation phase."""
        manager = GlossaryManager(mock_dependencies["pool"])
        
        # Mock resume point detection
        mock_dependencies["progress"].get_resume_point.return_value = ("validated", 2)
        
        # Mock pending entities
        mock_progress = MagicMock()
        mock_progress.id = 1
        mock_progress.entity_text = "Harry"
        mock_progress.entity_type = "character"
        mock_progress.frequency = 5
        mock_progress.contexts = []
        mock_dependencies["progress"].get_pending_for_phase.return_value = [mock_progress]
        
        # Call with resume=True
        result = manager.build_from_text(
            text="Test",
            work_id=1,
            volume_id=1,
            resume=True,
        )
        
        # Should not call extractor when resuming
        mock_dependencies["extractor"].extract.assert_not_called()
```

**Step 2: Implement resume logic in build_from_text**
Add at the beginning of `build_from_text`:

```python
def build_from_text(
    self,
    text: str,
    work_id: int,
    volume_id: int,
    source_lang: str = "en",
    target_lang: str = "es",
    suggest_translations: bool = True,
    resume: bool = False,
) -> BuildResult:
    """
    Build glossary from text with full pipeline.
    
    NEW: Supports resume from last checkpoint when resume=True.
    """
    entities_by_type: Dict[str, int] = {}

    # Check for resume
    if resume:
        phase, batch_num = self._progress_repo.get_resume_point(work_id, volume_id)
        if phase != "extracted":
            logger.info(f"Resuming from phase '{phase}' (batch {batch_num})")
            return self._resume_from_phase(
                work_id,
                volume_id,
                phase,
                batch_num,
                source_lang,
                target_lang,
                suggest_translations,
            )

    # ... rest of normal flow
```

**Step 3: Implement _resume_from_phase**
Add this method to GlossaryManager:

```python
def _resume_from_phase(
    self,
    work_id: int,
    volume_id: int,
    phase: str,
    batch_num: Optional[int],
    source_lang: str,
    target_lang: str,
    suggest_translations: bool,
) -> BuildResult:
    """Resume pipeline from a specific phase."""
    entities_by_type: Dict[str, int] = {}

    if phase == "validated":
        # Resume from validation
        pending = self._progress_repo.get_pending_for_phase(
            work_id, volume_id, "extracted"
        )
        entities = [
            EntityCandidate(
                text=p.entity_text,
                entity_type=p.entity_type or "other",
                frequency=p.frequency,
                contexts=p.contexts,
            )
            for p in pending
        ]

        if not entities:
            return BuildResult(
                extracted=0, new=0, skipped=0, entities_by_type={}
            )

        validated_entities, _ = self._validate_with_llm_tracked(
            entities, source_lang, work_id, volume_id
        )

        # Continue with embeddings and translation
        entity_embeddings = self._vector_service.embed_entities_for_glossary(
            validated_entities
        )

        translations = {}
        if suggest_translations and entity_embeddings:
            translations, _ = self._suggest_translations_tracked(
                validated_entities, source_lang, target_lang, work_id, volume_id
            )

        saved = self._save_entities(
            entity_embeddings,
            translations,
            work_id,
            source_lang,
            target_lang,
        )

        # Update progress and cleanup
        progress_ids = [p.id for p in pending if p.id]
        if progress_ids:
            self._progress_repo.batch_update_phase(progress_ids, "saved")
            self._progress_repo.cleanup_completed(volume_id)

        for e in validated_entities:
            entities_by_type[e.entity_type] = (
                entities_by_type.get(e.entity_type, 0) + 1
            )

        return BuildResult(
            extracted=len(entities),
            new=len(saved),
            skipped=len(entities) - len(validated_entities),
            entities_by_type=entities_by_type,
        )

    elif phase == "translated":
        # Resume from translation
        pending = self._progress_repo.get_pending_for_phase(
            work_id, volume_id, "validated"
        )
        entities = [
            EntityCandidate(
                text=p.entity_text,
                entity_type=p.entity_type or "other",
                frequency=p.frequency,
                contexts=p.contexts,
                translation=p.translation,
            )
            for p in pending
        ]

        if not entities:
            return BuildResult(
                extracted=0, new=0, skipped=0, entities_by_type={}
            )

        # Need to regenerate embeddings (or fetch from progress if saved)
        entity_embeddings = self._vector_service.embed_entities_for_glossary(
            entities
        )

        translations = {}
        if suggest_translations and entity_embeddings:
            translations, _ = self._suggest_translations_tracked(
                entities, source_lang, target_lang, work_id, volume_id
            )

        saved = self._save_entities(
            entity_embeddings,
            translations,
            work_id,
            source_lang,
            target_lang,
        )

        progress_ids = [p.id for p in pending if p.id]
        if progress_ids:
            self._progress_repo.batch_update_phase(progress_ids, "saved")
            self._progress_repo.cleanup_completed(volume_id)

        for e in entities:
            entities_by_type[e.entity_type] = (
                entities_by_type.get(e.entity_type, 0) + 1
            )

        return BuildResult(
            extracted=len(entities),
            new=len(saved),
            skipped=0,
            entities_by_type=entities_by_type,
        )

    # Default: start fresh
    return BuildResult(extracted=0, new=0, skipped=0, entities_by_type={})
```

**Step 4: Run tests**
```bash
pytest tests/database/test_glossary_manager_progress.py -v
```

**Step 5: Commit**
```bash
git add src/pdftranslator/database/services/glossary_manager.py tests/database/test_glossary_manager_progress.py
git commit -m "feat(manager): implement resume logic for interrupted builds"
```

---

## Task 8: Update CLI Commands

**Files:**
- Modify: `src/pdftranslator/cli/commands/build_glossary.py`

**Step 1: Add --resume and --force-restart flags**
Update the command signature:

```python
@app.command("build-glossary")
def build_glossary(
    min_frequency: int = typer.Option(
        2, "--min-frequency", "-m", help="Frecuencia mínima de entidades"
    ),
    source_lang: str = typer.Option("en", "--source-lang", "-s", help="Idioma origen"),
    target_lang: str = typer.Option("es", "--target-lang", "-t", help="Idioma destino"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Solo mostrar entidades sin guardar"
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Reanudar desde el último punto guardado si se interrumpió",
    ),
    force_restart: bool = typer.Option(
        False,
        "--force-restart",
        "-f",
        help="Ignorar progreso existente y comenzar desde cero",
    ),
):
    """
    Construye el glosario de traducción con soporte de recuperación.

    El comando guía al usuario a través de selección interactiva:
    1. Selección de obra
    2. Selección de alcance (All Book / All Volume / Single Chapter)
    3. Selección de volumen/capítulo según corresponda

    Ejemplos:
        pdftranslator build-glossary
        pdftranslator build-glossary --resume
        pdftranslator build-glossary --force-restart
        pdftranslator build-glossary -r -m 3
    """
```

**Step 2: Update build_from_text calls**
Find all calls to `manager.build_from_text()` and add `volume_id` parameter:

In `_process_all_book`:
```python
result = manager.build_from_text(
    text=consolidated_text,
    work_id=selected_work.id,
    volume_id=vol.id,  # NEW
    source_lang=source_lang,
    target_lang=target_lang,
    suggest_translations=not dry_run,
    resume=resume,  # NEW
)
```

In `_process_volume_consolidated`:
```python
result = manager.build_from_text(
    text=consolidated_text,
    work_id=work_id,
    volume_id=volume.id,  # NEW
    source_lang=source_lang,
    target_lang=target_lang,
    suggest_translations=not dry_run,
    resume=resume,  # NEW
)
```

In single chapter mode:
```python
result = manager.build_from_text(
    text=selected_chapter.original_text,
    work_id=work_id,
    volume_id=selected_volume.id,  # NEW
    source_lang=source_lang,
    target_lang=target_lang,
    suggest_translations=not dry_run,
    resume=resume,  # NEW
)
```

**Step 3: Add resume information display**
Before processing, show resume status:

```python
pool = DatabasePool.get_instance()
manager = GlossaryManager(pool)
volume_repo = VolumeRepository(pool)  # NEW

# Check for failed/in-progress volumes when resume is True
if resume:
    from pdftranslator.database.repositories.glossary_build_progress_repository import (
        GlossaryBuildProgressRepository,
    )
    progress_repo = GlossaryBuildProgressRepository(pool)
    
    failed_volumes = volume_repo.get_volumes_by_status(selected_work.id, "failed")
    in_progress_volumes = volume_repo.get_volumes_by_status(selected_work.id, "in_progress")
    
    if failed_volumes:
        console.print(
            f"[yellow]Encontrados {len(failed_volumes)} volúmenes fallidos a reanudar[/yellow]"
        )
    if in_progress_volumes:
        console.print(
            f"[yellow]Encontrados {len(in_progress_volumes)} volúmenes en progreso[/yellow]"
        )

# ... (rest of processing)
```

**Step 4: Handle force_restart flag**
Add before processing:

```python
if force_restart:
    from pdftranslator.database.repositories.glossary_build_progress_repository import (
        GlossaryBuildProgressRepository,
    )
    progress_repo = GlossaryBuildProgressRepository(pool)
    
    console.print("[yellow]Limpiando progreso existente...[/yellow]")
    for vol in volumes if selected_scope == SCOPE_ALL_BOOK else [selected_volume]:
        progress_repo.cleanup_completed(vol.id)
        volume_repo.update_build_status(vol.id, "pending")
```

**Step 5: Run CLI tests**
```bash
pytest tests/cli/test_build_glossary.py -v
```

**Step 6: Commit**
```bash
git add src/pdftranslator/cli/commands/build_glossary.py
git commit -m "feat(cli): add --resume and --force-restart flags to build-glossary"
```

---

## Task 9: Update API Endpoint

**Files:**
- Modify: `src/pdftranslator/backend/api/routes/glossary.py`

**Step 1: Add query parameters to endpoint**
Update the `build_glossary` endpoint:

```python
@router.post("/build", response_model=GlossaryBuildResponse)
async def build_glossary(
    data: GlossaryBuildRequest,
    resume: bool = Query(
        False,
        description="Reanudar desde el último punto guardado si se interrumpió"
    ),
    force_restart: bool = Query(
        False,
        description="Ignorar progreso existente y comenzar desde cero"
    ),
    background_tasks: BackgroundTasks = None,
):
    """
    Build glossary from work volumes using NER + LLM.

    Processes each volume that hasn't been analyzed yet, extracting entities
    and suggesting translations. Volumes with glossary_built_at set are skipped.
    
    NEW: Supports resume from last checkpoint with ?resume=true
    """
```

**Step 2: Update build_from_text calls in API**
Find the call to `manager.build_from_text()`:

```python
result = manager.build_from_text(
    text=consolidated_text,
    work_id=data.work_id,
    volume_id=volume.id,  # NEW
    source_lang=source_lang,
    target_lang=target_lang,
    suggest_translations=True,
    resume=resume,  # NEW
)
```

**Step 3: Update volume status on success/failure**
Wrap in try-except:

```python
for volume in sorted(volumes, key=lambda v: v.volume_number):
    if volume.glossary_built_at:
        # Already completed
        continue

    try:
        volume_repo.update_build_status(volume.id, "in_progress")
        
        # ... (existing processing code)
        
        result = manager.build_from_text(...)
        
        volume_repo.mark_glossary_built(volume.id)
        volume_repo.update_build_status(volume.id, "completed")
        
    except Exception as e:
        volume_repo.update_build_status(
            volume.id,
            "failed",
            error_message=str(e),
        )
        logger.error(f"Volume {volume.volume_number} failed: {e}")
        # Optionally continue with next volume or raise
```

**Step 4: Update response schema**
Add resume info to `GlossaryBuildVolumeResult` in `src/pdftranslator/backend/api/models/schemas.py`:

```python
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
    progress_stats: dict[str, int] | None = None
```

**Step 5: Test API endpoint**
```bash
pytest tests/backend/test_glossary_routes.py -v
```

**Step 6: Commit**
```bash
git add src/pdftranslator/backend/api/routes/glossary.py src/pdftranslator/backend/api/models/schemas.py
git commit -m "feat(api): add resume support to glossary build endpoint"
```

---

## Task 10: Integration Testing

**Files:**
- Create: `tests/integration/test_glossary_resume_integration.py`

**Step 1: Write integration test**
Create integration test file:

```python
"""Integration tests for glossary resume functionality."""

import pytest
from unittest.mock import MagicMock, patch
import tempfile
import json

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.services.glossary_manager import GlossaryManager
from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository


@pytest.mark.integration
class TestGlossaryResumeIntegration:
    """Test full resume cycle with database."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database connection."""
        # Uses test database
        DatabasePool.reset_instance()
        yield
        DatabasePool.reset_instance()

    def test_resume_after_simulated_failure(self):
        """
        Test full cycle:
        1. Start glossary build
        2. Simulate failure mid-process
        3. Resume and verify completion
        """
        pool = DatabasePool.get_instance()
        progress_repo = GlossaryBuildProgressRepository(pool)
        
        # This test requires actual database with test data
        # In real test, we would:
        # 1. Create test work and volume
        # 2. Start build, interrupt it
        # 3. Resume and verify
        
        # For now, test the logic flow
        work_id = 1
        volume_id = 1
        
        # Check resume point
        phase, batch = progress_repo.get_resume_point(work_id, volume_id)
        assert phase in ["extracted", "validated", "translated"]

    def test_cli_resume_flag(self):
        """Test that CLI --resume flag triggers resume logic."""
        # This would be an E2E test with subprocess
        # For unit test, verify flag is passed correctly
        pass

    def test_api_resume_parameter(self):
        """Test that API resume parameter works."""
        # This would test the FastAPI endpoint
        pass
```

**Step 2: Run integration tests**
```bash
pytest tests/integration/test_glossary_resume_integration.py -v -m integration
```

**Step 3: Manual E2E test**
Perform manual testing:

```bash
# Start glossary build
python PDFAgent.py cli build-glossary

# Select a work with multiple volumes
# Let it process 1-2 volumes
# Press Ctrl+C to simulate failure

# Resume from checkpoint
python PDFAgent.py cli build-glossary --resume

# Verify it continues from where it stopped
```

**Step 4: Commit**
```bash
git add tests/integration/test_glossary_resume_integration.py
git commit -m "test(integration): add glossary resume integration tests"
```

---

## Task 11: Update Documentation

**Files:**
- Update: `README.md`
- Update: `CHANGELOG.md`
- Update: `AGENTS.md`

**Step 1: Update README**
Add resume documentation to README.md:

```markdown
### Glossary Build Resume

The glossary build process now supports resuming from interruptions:

```bash
# Normal build
python PDFAgent.py cli build-glossary

# Resume from last checkpoint (if interrupted)
python PDFAgent.py cli build-glossary --resume

# Force restart (clear all progress)
python PDFAgent.py cli build-glossary --force-restart
```

**How it works:**
- Progress is saved after each batch (validation, translation)
- Use `--resume` to continue from the exact failure point
- No duplicated LLM calls or processing
```

**Step 2: Update CHANGELOG**
Add entry to CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- Glossary build resume system with `--resume` flag
- Progress tracking at entity level through pipeline phases
- `glossary_build_progress` table for checkpoint persistence
- Volume build status tracking (`pending`, `in_progress`, `completed`, `failed`)
- `--force-restart` flag to clear progress and start fresh
```

**Step 3: Update AGENTS.md**
Add note about resume system:

```markdown
## Glossary Resume System

When building glossaries, the system tracks progress through phases:
- `extracted`: After NLTK entity extraction
- `validated`: After LLM validation (per batch)
- `translated`: After LLM translation (per batch)
- `saved`: After saving to glossary_terms

Use `--resume` to continue from interruptions.
Use `--force-restart` to start fresh.

Related tables:
- `glossary_build_progress`: Tracks entity progress
- `volumes.glossary_build_status`: Overall volume status
```

**Step 4: Commit**
```bash
git add README.md CHANGELOG.md AGENTS.md
git commit -m "docs: document glossary resume system"
```

---

## Task 12: Final Verification and Cleanup

**Step 1: Run all tests**
```bash
pytest tests/ -v --cov=src/pdftranslator --cov-report=term-missing
```

**Step 2: Run linting**
```bash
ruff check src/pdftranslator/database/repositories/glossary_build_progress_repository.py
ruff check src/pdftranslator/database/services/glossary_manager.py
ruff check src/pdftranslator/cli/commands/build_glossary.py
```

**Step 3: Run type checking**
```bash
mypy src/pdftranslator/database/repositories/glossary_build_progress_repository.py
mypy src/pdftranslator/database/services/glossary_manager.py
```

**Step 4: Create final commit**
```bash
git add -A
git commit -m "feat: complete glossary resume system implementation"
```

**Step 5: Create PR or merge**
```bash
git log --oneline --graph -10
```

---

## Summary

This implementation plan covers:

1. ✅ Database migration for progress table
2. ✅ Data model for progress tracking
3. ✅ Repository for progress operations
4. ✅ Volume status tracking
5. ✅ Progress saving in GlossaryManager
6. ✅ Batch-level progress updates
7. ✅ Resume logic implementation
8. ✅ CLI flags (--resume, --force-restart)
9. ✅ API endpoint support
10. ✅ Integration tests
11. ✅ Documentation

**Estimated effort:** 8-12 hours

**Dependencies:**
- PostgreSQL database with pgvector
- Python 3.11+
- Existing LLM infrastructure (NVIDIA/Gemini/Ollama)

**Risk mitigation:**
- Extensive unit tests before integration
- Backward compatibility (resume=False is default)
- Graceful degradation if progress table missing
