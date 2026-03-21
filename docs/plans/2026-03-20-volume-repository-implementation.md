# Volume Repository Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Crear VolumeRepository con CRUD completo y refactorizar el código existente para eliminar métodos de Volume de BookRepository.

**Architecture:** Nuevo repositorio VolumeRepository siguiendo el patrón de ChapterRepository. Refactorizar split_text.py y add_to_database.py para usar VolumeRepository.

**Tech Stack:** Python, PostgreSQL via psycopg_pool, BaseRepository pattern

---

## Prerequisites
- Review `database/repositories/chapter_repository.py` for pattern
- Review `database/repositories/base.py` for interface
- Review design doc: `docs/plans/2026-03-20-volume-repository-design.md`

---

### Task 1: Create VolumeRepository with CRUD methods

**Files:**
- Create: `database/repositories/volume_repository.py`

**Step 1: Create the file with full implementation**

```python
from typing import Optional, List

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import Volume


class VolumeRepository(BaseRepository[Volume]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_volume(self, row: tuple) -> Volume:
        return Volume(
            id=row[0],
            work_id=row[1],
            volume_number=row[2],
            title=row[3],
            full_text=row[4],
            translated_text=row[5],
        )

    def get_by_id(self, id: int) -> Optional[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text
                    FROM volumes
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_volume(row)

    def get_all(self) -> List[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text
                    FROM volumes
                    ORDER BY work_id, volume_number
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]

    def create(self, entity: Volume) -> Volume:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO volumes (work_id, volume_number, title, full_text, translated_text)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, work_id, volume_number, title, full_text, translated_text
                    """,
                    (
                        entity.work_id,
                        entity.volume_number,
                        entity.title,
                        entity.full_text,
                        entity.translated_text,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_volume(row)

    def update(self, entity: Volume) -> Optional[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE volumes
                    SET work_id = %s, volume_number = %s, title = %s, 
                        full_text = %s, translated_text = %s
                    WHERE id = %s
                    RETURNING id, work_id, volume_number, title, full_text, translated_text
                    """,
                    (
                        entity.work_id,
                        entity.volume_number,
                        entity.title,
                        entity.full_text,
                        entity.translated_text,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_volume(row)

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM volumes WHERE id = %s", (id,))
                return cur.rowcount > 0

    def get_by_work_id(self, work_id: int) -> List[Volume]:
        """Get all volumes for a specific work."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text
                    FROM volumes
                    WHERE work_id = %s
                    ORDER BY volume_number
                    """,
                    (work_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]

    def find_by_volume_number(self, work_id: int, volume_number: int) -> Optional[Volume]:
        """Find a specific volume by work and volume number."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text
                    FROM volumes
                    WHERE work_id = %s AND volume_number = %s
                    """,
                    (work_id, volume_number),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_volume(row)

    def update_full_text(self, volume_id: int, text: str) -> bool:
        """Update only the full_text field of a volume."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE volumes
                    SET full_text = %s
                    WHERE id = %s
                    """,
                    (text, volume_id),
                )
                return cur.rowcount > 0
```

**Step 2: Commit**
```bash
git add database/repositories/volume_repository.py
git commit -m "feat: add VolumeRepository with CRUD methods"
```

---

### Task 2: Update __init__.py to export VolumeRepository

**Files:**
- Modify: `database/repositories/__init__.py`

**Step 1: Add VolumeRepository import**

Add to the exports:
```python
from database.repositories.volume_repository import VolumeRepository
```

**Step 2: Commit**
```bash
git add database/repositories/__init__.py
git commit -m "feat: export VolumeRepository from __init__.py"
```

---

### Task 3: Refactor split_text.py to use VolumeRepository

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add VolumeRepository import**

Add after existing imports:
```python
from database.repositories.volume_repository import VolumeRepository
```

**Step 2: Update select_volume_interactive function**

Replace:
```python
def select_volume_interactive(repo: BookRepository) -> Optional[Volume]:
    works = repo.find_all()
    # ...
    volumes = repo.get_volumes(selected_work.id)
```

With:
```python
def select_volume_interactive(
    work_repo: BookRepository, volume_repo: VolumeRepository
) -> Optional[Volume]:
    works = work_repo.find_all()
    # ...
    volumes = volume_repo.get_by_work_id(selected_work.id)
```

**Step 3: Update update_volume_text function**

Replace:
```python
def update_volume_text(repo: BookRepository, volume_id: int, text: str) -> bool:
    try:
        volume = repo.get_volume_by_id(volume_id)
        if not volume:
            logger.error(f"Volume with ID {volume_id} not found")
            return False
        volume.full_text = text
        repo.update(volume)
        return True
    except Exception as e:
        logger.error(f"Failed to update volume: {e}")
        return False
```

With:
```python
def update_volume_text(volume_repo: VolumeRepository, volume_id: int, text: str) -> bool:
    try:
        return volume_repo.update_full_text(volume_id, text)
    except Exception as e:
        logger.error(f"Failed to update volume: {e}")
        return False
```

**Step 4: Update split_text command**

Replace:
```python
repo = BookRepository()
chapter_repo = ChapterRepository()
selected_volume = select_volume_interactive(repo)
# ...
update_volume_text(repo, selected_volume.id, content_without_header)
```

With:
```python
work_repo = BookRepository()
volume_repo = VolumeRepository()
chapter_repo = ChapterRepository()
selected_volume = select_volume_interactive(work_repo, volume_repo)
# ...
update_volume_text(volume_repo, selected_volume.id, content_without_header)
```

**Step 5: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "refactor: use VolumeRepository in split_text command"
```

---

### Task 4: Refactor add_to_database.py to use VolumeRepository

**Files:**
- Modify: `cli/commands/add_to_database.py`

**Step 1: Add VolumeRepository import**

Add:
```python
from database.repositories.volume_repository import VolumeRepository
```

**Step 2: Update process_single_file function**

Replace:
```python
def process_single_file(
    file_path: Path, repo: BookRepository, extractor: TextExtractor
) -> ProcessingResult:
    # ...
    existing_volumes = repo.get_volumes(work.id)
    volume_numbers = [v.volume_number for v in existing_volumes]
    # ...
    repo.add_volume(volume)
```

With:
```python
def process_single_file(
    file_path: Path, 
    work_repo: BookRepository, 
    volume_repo: VolumeRepository,
    extractor: TextExtractor
) -> ProcessingResult:
    # ...
    existing_volumes = volume_repo.get_by_work_id(work.id)
    volume_numbers = [v.volume_number for v in existing_volumes]
    # ...
    volume_repo.create(volume)
```

**Step 3: Update process_files function**

Replace:
```python
def process_files(files: List[Path]) -> List[ProcessingResult]:
    results: List[ProcessingResult] = []
    repo = get_book_repository()
    extractor = TextExtractor()
    # ...
    result = process_single_file(file_path, repo, extractor)
```

With:
```python
def process_files(files: List[Path]) -> List[ProcessingResult]:
    results: List[ProcessingResult] = []
    work_repo = BookRepository()
    volume_repo = VolumeRepository()
    extractor = TextExtractor()
    # ...
    result = process_single_file(file_path, work_repo, volume_repo, extractor)
```

**Step 4: Remove get_book_repository function if no longer needed**

If `get_book_repository()` is only used in `process_files`, remove it.

**Step 5: Commit**
```bash
git add cli/commands/add_to_database.py
git commit -m "refactor: use VolumeRepository in add_to_database command"
```

---

### Task 5: Remove Volume methods from BookRepository

**Files:**
- Modify: `database/repositories/book_repository.py`

**Step 1: Remove Volume-related methods**

Remove these methods:
- `_row_to_volume`
- `get_volumes`
- `add_volume`
- `get_volume_by_id`

**Step 2: Remove Volume from imports**

Change:
```python
from database.models import Work, Volume
```

To:
```python
from database.models import Work
```

**Step 3: Commit**
```bash
git add database/repositories/book_repository.py
git commit -m "refactor: remove Volume methods from BookRepository"
```

---

### Task 6: Test the changes

**Step 1: Run the CLI to verify**
```bash
python -m cli split-text --help
python -m cli add-to-database --help
```

**Step 2: Test with actual data if available**

**Step 3: Commit if all working**
```bash
git status
```

---

### Task 7: Push to remote

**Step 1: Push all commits**
```bash
git push origin main
```

---

## Summary

This implementation:
1. Creates `VolumeRepository` with full CRUD + additional query methods
2. Refactors `split_text.py` to use `VolumeRepository`
3. Refactors `add_to_database.py` to use `VolumeRepository`
4. Removes Volume methods from `BookRepository` for clean separation
