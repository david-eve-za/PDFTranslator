"""Repository for translation_jobs table."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository


_COLUMNS = (
    "id, work_id, scope, volume_id, chapter_id, "
    "source_lang, target_lang, skip_translated, dry_run, "
    "status, total_chapters, completed_chapters, "
    "success_count, failure_count, "
    "current_chapter_info, error_message, "
    "created_at, updated_at"
)


@dataclass
class TranslationJob:
    work_id: int = 0
    scope: str = ""
    volume_id: Optional[int] = None
    chapter_id: Optional[int] = None
    source_lang: str = "en"
    target_lang: str = "es"
    skip_translated: bool = True
    dry_run: bool = False
    status: str = "pending"
    total_chapters: int = 0
    completed_chapters: int = 0
    success_count: int = 0
    failure_count: int = 0
    current_chapter_info: Optional[str] = None
    error_message: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TranslationJobRepository(BaseRepository[TranslationJob]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_job(self, row) -> TranslationJob:
        return TranslationJob(
            id=row["id"],
            work_id=row["work_id"],
            scope=row["scope"],
            volume_id=row["volume_id"],
            chapter_id=row["chapter_id"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            skip_translated=row["skip_translated"],
            dry_run=row["dry_run"],
            status=row["status"],
            total_chapters=row["total_chapters"],
            completed_chapters=row["completed_chapters"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            current_chapter_info=row["current_chapter_info"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_id(self, id: int) -> Optional[TranslationJob]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"SELECT {_COLUMNS} FROM translation_jobs WHERE id = ?",
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_job(row)

    def get_all(self) -> List[TranslationJob]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"SELECT {_COLUMNS} FROM translation_jobs ORDER BY id DESC"
            )
            rows = cur.fetchall()
            return [self._row_to_job(row) for row in rows]

    def create(self, entity: TranslationJob) -> TranslationJob:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"""
                INSERT INTO translation_jobs (
                    work_id, scope, volume_id, chapter_id,
                    source_lang, target_lang, skip_translated, dry_run,
                    status, total_chapters, completed_chapters,
                    success_count, failure_count,
                    current_chapter_info, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING {_COLUMNS}
                """,
                (
                    entity.work_id,
                    entity.scope,
                    entity.volume_id,
                    entity.chapter_id,
                    entity.source_lang,
                    entity.target_lang,
                    entity.skip_translated,
                    entity.dry_run,
                    entity.status,
                    entity.total_chapters,
                    entity.completed_chapters,
                    entity.success_count,
                    entity.failure_count,
                    entity.current_chapter_info,
                    entity.error_message,
                ),
            )
            row = cur.fetchone()
            return self._row_to_job(row)

    def update(self, entity: TranslationJob) -> Optional[TranslationJob]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"""
                UPDATE translation_jobs
                SET status = ?, total_chapters = ?,
                    completed_chapters = ?, success_count = ?,
                    failure_count = ?, current_chapter_info = ?,
                    error_message = ?
                WHERE id = ?
                RETURNING {_COLUMNS}
                """,
                (
                    entity.status,
                    entity.total_chapters,
                    entity.completed_chapters,
                    entity.success_count,
                    entity.failure_count,
                    entity.current_chapter_info,
                    entity.error_message,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_job(row)

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM translation_jobs WHERE id = ?", (id,))
            return cur.rowcount > 0

    def list_by_work(self, work_id: int) -> List[TranslationJob]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"SELECT {_COLUMNS} FROM translation_jobs WHERE work_id = ? ORDER BY id DESC",
                (work_id,),
            )
            rows = cur.fetchall()
            return [self._row_to_job(row) for row in rows]