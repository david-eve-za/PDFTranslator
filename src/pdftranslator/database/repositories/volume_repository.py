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
        )

    def get_by_id(self, id: int) -> Optional[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text,
                           glossary_built_at, created_at
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
                           glossary_built_at, created_at
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
