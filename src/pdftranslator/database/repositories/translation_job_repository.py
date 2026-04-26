"""Repository for translation_jobs table."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

    def _row_to_job(self, row: tuple) -> TranslationJob:
        return TranslationJob(
            id=row[0],
            work_id=row[1],
            scope=row[2],
            volume_id=row[3],
            chapter_id=row[4],
            source_lang=row[5],
            target_lang=row[6],
            skip_translated=row[7],
            dry_run=row[8],
            status=row[9],
            total_chapters=row[10],
            completed_chapters=row[11],
            success_count=row[12],
            failure_count=row[13],
            current_chapter_info=row[14],
            error_message=row[15],
            created_at=row[16],
            updated_at=row[17],
        )

    def get_by_id(self, id: int) -> Optional[TranslationJob]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_COLUMNS} FROM translation_jobs WHERE id = %s",
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_job(row)

    def get_all(self) -> list[TranslationJob]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_COLUMNS} FROM translation_jobs ORDER BY id DESC"
                )
                rows = cur.fetchall()
                return [self._row_to_job(row) for row in rows]

    def create(self, entity: TranslationJob) -> TranslationJob:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO translation_jobs (
                        work_id, scope, volume_id, chapter_id,
                        source_lang, target_lang, skip_translated, dry_run,
                        status, total_chapters, completed_chapters,
                        success_count, failure_count,
                        current_chapter_info, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE translation_jobs
                    SET status = %s, total_chapters = %s,
                        completed_chapters = %s, success_count = %s,
                        failure_count = %s, current_chapter_info = %s,
                        error_message = %s
                    WHERE id = %s
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
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM translation_jobs WHERE id = %s", (id,))
                return cur.rowcount > 0

    def list_by_work(self, work_id: int) -> list[TranslationJob]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_COLUMNS} FROM translation_jobs WHERE work_id = %s ORDER BY id DESC",
                    (work_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_job(row) for row in rows]
