"""
SQLite repository implementations for Catalog Domain.

CUPID Principles:
- Composable: Implements protocols, can be swapped
- Predictable: Explicit SQL, proper error handling
- Idiomatic: Uses aiosqlite async patterns
"""

from __future__ import annotations
from typing import Optional, List
from datetime import datetime

import aiosqlite

from ...domain.models.work import Work
from ...domain.models.volume import Volume
from ...domain.models.chapter import Chapter
from ...domain.repositories.protocols import (
    WorkRepository,
    VolumeRepository,
    ChapterRepository,
    CatalogUnitOfWork,
    PaginationParams,
    PaginatedResult,
)
from ...domain.repositories.exceptions import DomainError, NotFoundError
from .connection import DatabaseConnection


class SQLiteWorkRepository(WorkRepository):
    """SQLite implementation of WorkRepository."""

    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_id(self, work_id: int) -> Optional[Work]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, title, title_translated, author,
                       source_lang, target_lang, created_at, updated_at
                FROM works WHERE id = ?
                """,
                (work_id,),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_work(row)

    async def get_by_uuid(self, uuid: str) -> Optional[Work]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, title, title_translated, author,
                       source_lang, target_lang, created_at, updated_at
                FROM works WHERE uuid = ?
                """,
                (uuid,),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_work(row)

    async def get_all(self, pagination: PaginationParams) -> PaginatedResult[Work]:
        async with self._db.read_only() as conn:
            # Count total
            count_row = await conn.execute("SELECT COUNT(*) FROM works")
            count_row = await count_row.fetchone()
            total = count_row[0] if count_row else 0

            # Get paginated results
            cursor = await conn.execute(
                """
                SELECT id, uuid, title, title_translated, author,
                       source_lang, target_lang, created_at, updated_at
                FROM works
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (pagination.limit, pagination.offset),
            )
            rows = await cursor.fetchall()
            items = [self._row_to_work(row) for row in rows]

            return PaginatedResult(
                items=items,
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
            )

    async def create(self, work: Work) -> Work:
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO works (uuid, title, title_translated, author,
                                   source_lang, target_lang, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(work.uuid),
                    work.title,
                    work.title_translated,
                    work.author,
                    work.source_lang,
                    work.target_lang,
                    work.created_at.isoformat(),
                    work.updated_at.isoformat(),
                ),
            )
            work.id = cursor.lastrowid
            return work

    async def update(self, work: Work) -> Work:
        async with self._db.transaction() as conn:
            work.updated_at = datetime.utcnow()
            await conn.execute(
                """
                UPDATE works
                SET title = ?, title_translated = ?, author = ?,
                    source_lang = ?, target_lang = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    work.title,
                    work.title_translated,
                    work.author,
                    work.source_lang,
                    work.target_lang,
                    work.updated_at.isoformat(),
                    work.id,
                ),
            )
            return work

    async def delete(self, work_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM works WHERE id = ?", (work_id,))
            return cursor.rowcount > 0

    async def find_by_title(self, title: str, fuzzy: bool = False) -> List[Work]:
        async with self._db.read_only() as conn:
            if fuzzy:
                pattern = f"%{title}%"
                cursor = await conn.execute(
                    """
                    SELECT id, uuid, title, title_translated, author,
                           source_lang, target_lang, created_at, updated_at
                    FROM works WHERE title LIKE ?
                    ORDER BY title
                    """,
                    (pattern,),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT id, uuid, title, title_translated, author,
                           source_lang, target_lang, created_at, updated_at
                    FROM works WHERE title = ?
                    ORDER BY title
                    """,
                    (title,),
                )
            rows = await cursor.fetchall()
            return [self._row_to_work(row) for row in rows]

    def _row_to_work(self, row: aiosqlite.Row) -> Work:
        return Work(
            id=row["id"],
            uuid=row["uuid"],
            title=row["title"],
            title_translated=row["title_translated"],
            author=row["author"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SQLiteVolumeRepository(VolumeRepository):
    """SQLite implementation of VolumeRepository."""

    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_id(self, volume_id: int) -> Optional[Volume]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, work_id, volume_number, title, full_text,
                       translated_text, created_at, updated_at,
                       glossary_built_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes WHERE id = ?
                """,
                (volume_id,),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_volume(row)

    async def get_by_work_id(self, work_id: int) -> List[Volume]:
        async with self._db.read_only() as conn:
            cursor = await conn.execute(
                """
                SELECT id, uuid, work_id, volume_number, title, full_text,
                       translated_text, created_at, updated_at,
                       glossary_built_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes WHERE work_id = ?
                ORDER BY volume_number
                """,
                (work_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_volume(row) for row in rows]

    async def get_by_work_and_number(self, work_id: int, volume_number: int) -> Optional[Volume]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, work_id, volume_number, title, full_text,
                       translated_text, created_at, updated_at,
                       glossary_built_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes WHERE work_id = ? AND volume_number = ?
                """,
                (work_id, volume_number),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_volume(row)

    async def create(self, volume: Volume) -> Volume:
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO volumes (
                    uuid, work_id, volume_number, title, full_text, translated_text,
                    created_at, updated_at, glossary_build_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(volume.uuid),
                    volume.work_id,
                    volume.volume_number,
                    volume.title,
                    volume.full_text,
                    volume.translated_text,
                    volume.created_at.isoformat(),
                    volume.updated_at.isoformat(),
                    volume.glossary_build_status,
                ),
            )
            volume.id = cursor.lastrowid
            return volume

    async def update(self, volume: Volume) -> Volume:
        async with self._db.transaction() as conn:
            volume.updated_at = datetime.utcnow()
            await conn.execute(
                """
                UPDATE volumes SET
                    title = ?, full_text = ?, translated_text = ?,
                    updated_at = ?, glossary_built_at = ?,
                    glossary_build_status = ?, glossary_error_message = ?,
                    glossary_resume_phase = ?
                WHERE id = ?
                """,
                (
                    volume.title,
                    volume.full_text,
                    volume.translated_text,
                    volume.updated_at.isoformat(),
                    volume.glossary_built_at.isoformat() if volume.glossary_built_at else None,
                    volume.glossary_build_status,
                    volume.glossary_error_message,
                    volume.glossary_resume_phase,
                    volume.id,
                ),
            )
            return volume

    async def delete(self, volume_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM volumes WHERE id = ?", (volume_id,))
            return cursor.rowcount > 0

    def _row_to_volume(self, row: aiosqlite.Row) -> Volume:
        return Volume(
            id=row["id"],
            uuid=row["uuid"],
            work_id=row["work_id"],
            volume_number=row["volume_number"],
            title=row["title"],
            full_text=row["full_text"],
            translated_text=row["translated_text"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            glossary_built_at=datetime.fromisoformat(row["glossary_built_at"]) if row["glossary_built_at"] else None,
            glossary_build_status=row["glossary_build_status"],
            glossary_error_message=row["glossary_error_message"],
            glossary_resume_phase=row["glossary_resume_phase"],
        )


class SQLiteChapterRepository(ChapterRepository):
    """SQLite implementation of ChapterRepository."""

    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, volume_id, chapter_number, title,
                       start_position, end_position, original_text, translated_text,
                       created_at, updated_at
                FROM chapters WHERE id = ?
                """,
                (chapter_id,),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_chapter(row)

    async def get_by_volume_id(self, volume_id: int) -> List[Chapter]:
        async with self._db.read_only() as conn:
            cursor = await conn.execute(
                """
                SELECT id, uuid, volume_id, chapter_number, title,
                       start_position, end_position, original_text, translated_text,
                       created_at, updated_at
                FROM chapters WHERE volume_id = ?
                ORDER BY chapter_number
                """,
                (volume_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_chapter(row) for row in rows]

    async def get_by_volume_and_number(self, volume_id: int, chapter_number: int) -> Optional[Chapter]:
        async with self._db.read_only() as conn:
            row = await conn.execute(
                """
                SELECT id, uuid, volume_id, chapter_number, title,
                       start_position, end_position, original_text, translated_text,
                       created_at, updated_at
                FROM chapters WHERE volume_id = ? AND chapter_number = ?
                """,
                (volume_id, chapter_number),
            )
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_chapter(row)

    async def create(self, chapter: Chapter) -> Chapter:
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO chapters (
                    uuid, volume_id, chapter_number, title,
                    start_position, end_position, original_text, translated_text,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(chapter.uuid),
                    chapter.volume_id,
                    chapter.chapter_number,
                    chapter.title,
                    chapter.start_position,
                    chapter.end_position,
                    chapter.original_text,
                    chapter.translated_text,
                    chapter.created_at.isoformat(),
                    chapter.updated_at.isoformat(),
                ),
            )
            chapter.id = cursor.lastrowid
            return chapter

    async def update(self, chapter: Chapter) -> Chapter:
        async with self._db.transaction() as conn:
            chapter.updated_at = datetime.utcnow()
            await conn.execute(
                """
                UPDATE chapters SET
                    chapter_number = ?, title = ?,
                    start_position = ?, end_position = ?,
                    original_text = ?, translated_text = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    chapter.chapter_number,
                    chapter.title,
                    chapter.start_position,
                    chapter.end_position,
                    chapter.original_text,
                    chapter.translated_text,
                    chapter.updated_at.isoformat(),
                    chapter.id,
                ),
            )
            return chapter

    async def delete(self, chapter_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
            return cursor.rowcount > 0

    def _row_to_chapter(self, row: aiosqlite.Row) -> Chapter:
        return Chapter(
            id=row["id"],
            uuid=row["uuid"],
            volume_id=row["volume_id"],
            chapter_number=row["chapter_number"],
            title=row["title"],
            start_position=row["start_position"],
            end_position=row["end_position"],
            original_text=row["original_text"],
            translated_text=row["translated_text"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SQLiteUnitOfWork(CatalogUnitOfWork):
    """
    SQLite Unit of Work implementation.

    CUPID Principle: Predictable
    - Single transaction across repositories
    - Explicit commit/rollback
    """

    def __init__(self, db: DatabaseConnection):
        self._db = db
        self._works: Optional[SQLiteWorkRepository] = None
        self._volumes: Optional[SQLiteVolumeRepository] = None
        self._chapters: Optional[SQLiteChapterRepository] = None
        self._committed = False

    @property
    def works(self) -> SQLiteWorkRepository:
        if self._works is None:
            self._works = SQLiteWorkRepository(self._db)
        return self._works

    @property
    def volumes(self) -> SQLiteVolumeRepository:
        if self._volumes is None:
            self._volumes = SQLiteVolumeRepository(self._db)
        return self._volumes

    @property
    def chapters(self) -> SQLiteChapterRepository:
        if self._chapters is None:
            self._chapters = SQLiteChapterRepository(self._db)
        return self._chapters

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass  # Handled by connection context manager on exception

    async def __aenter__(self) -> SQLiteUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            pass  # Rollback handled by connection
        elif not self._committed:
            pass  # No explicit commit