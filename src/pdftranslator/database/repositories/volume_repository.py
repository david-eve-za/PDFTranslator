from typing import Optional, List
from datetime import datetime
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import Volume


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
            glossary_built_at=row[6] if len(row) > 6 else None,
            created_at=row[7] if len(row) > 7 else None,
            glossary_build_status=row[8] if len(row) > 8 else "pending",
            glossary_error_message=row[9] if len(row) > 9 else None,
            glossary_resume_phase=row[10] if len(row) > 10 else None,
        )

    def get_by_id(self, id: int) -> Optional[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                    glossary_built_at, created_at, glossary_build_status,
                    glossary_error_message, glossary_resume_phase
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
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                    glossary_built_at, created_at, glossary_build_status,
                    glossary_error_message, glossary_resume_phase
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
                    SET work_id = %s, volume_number = %s, title = %s, full_text = %s, translated_text = %s
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
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                    glossary_built_at, created_at, glossary_build_status,
                    glossary_error_message, glossary_resume_phase
                    FROM volumes
                    WHERE work_id = %s
                    ORDER BY volume_number
                    """,
                    (work_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]

    def find_by_volume_number(
        self, work_id: int, volume_number: int
    ) -> Optional[Volume]:
        """Find a specific volume by work and volume number."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                    glossary_built_at, created_at, glossary_build_status,
                    glossary_error_message, glossary_resume_phase
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

    def mark_glossary_built(self, volume_id: int) -> bool:
        """Mark a volume as having its glossary built."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE volumes
                    SET glossary_built_at = NOW()
                    WHERE id = %s
                    """,
                    (volume_id,),
                )
                return cur.rowcount > 0

    def update_build_status(
        self,
        volume_id: int,
        status: str,
        error_message: str | None = None,
        resume_phase: str | None = None,
    ) -> bool:
        """Update the glossary build status of a volume.

        Args:
            volume_id: ID of the volume to update
            status: Build status (pending, in_progress, completed, failed)
            error_message: Optional error message for failed builds
            resume_phase: Optional phase to resume from after failure

        Returns:
            True if the volume was updated, False if no volume was found
        """
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
        """Get all volumes with a specific build status.

        Args:
            work_id: ID of the work to filter by
            status: Build status to filter by

        Returns:
            List of volumes matching the status, ordered by volume_number
        """
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                    glossary_built_at, created_at, glossary_build_status,
                    glossary_error_message, glossary_resume_phase
                    FROM volumes
                    WHERE work_id = %s AND glossary_build_status = %s
                    ORDER BY volume_number
                    """,
                    (work_id, status),
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]
