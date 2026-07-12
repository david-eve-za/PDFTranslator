"""Volume repository for SQLite."""

from typing import Optional, List
from datetime import datetime

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import Volume


class VolumeRepository(BaseRepository[Volume]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from SQLite string format."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # SQLite uses "YYYY-MM-DD HH:MM:SS" format (space), not ISO "T" separator
            # Also handle potential "Z" suffix
            value_str = str(value).strip()
            # Replace space with T for ISO format parsing
            if " " in value_str and "T" not in value_str:
                value_str = value_str.replace(" ", "T")
            if value_str.endswith("Z"):
                value_str = value_str[:-1] + "+00:00"
            return datetime.fromisoformat(value_str)
        except (ValueError, AttributeError):
            return None

    def _row_to_volume(self, row) -> Volume:
        return Volume(
            id=row["id"],
            work_id=row["work_id"],
            volume_number=row["volume_number"],
            title=row["title"],
            full_text=row["full_text"],
            translated_text=row["translated_text"],
            glossary_built_at=self._parse_datetime(row["glossary_built_at"]) if "glossary_built_at" in row.keys() else None,
            created_at=self._parse_datetime(row["created_at"]) if "created_at" in row.keys() else None,
            glossary_build_status=row["glossary_build_status"] if "glossary_build_status" in row.keys() else "pending",
            glossary_error_message=row["glossary_error_message"] if "glossary_error_message" in row.keys() else None,
            glossary_resume_phase=row["glossary_resume_phase"] if "glossary_resume_phase" in row.keys() else None,
        )

    def get_by_id(self, id: int) -> Optional[Volume]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, work_id, volume_number, title, full_text, translated_text,
                       glossary_built_at, created_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes
                WHERE id = ?
                """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_volume(row)

    def get_all(self) -> List[Volume]:
        with self._pool.connection() as conn:
            cur = conn.execute(
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO volumes (work_id, volume_number, title, full_text, translated_text)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id, work_id, volume_number, title, full_text, translated_text,
                          glossary_built_at, created_at, glossary_build_status,
                          glossary_error_message, glossary_resume_phase
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE volumes
                SET work_id = ?, volume_number = ?, title = ?, full_text = ?, translated_text = ?
                WHERE id = ?
                RETURNING id, work_id, volume_number, title, full_text, translated_text,
                          glossary_built_at, created_at, glossary_build_status,
                          glossary_error_message, glossary_resume_phase
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
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM volumes WHERE id = ?", (id,))
            return cur.rowcount > 0

    def get_by_work_id(self, work_id: int) -> List[Volume]:
        """Get all volumes for a specific work."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, work_id, volume_number, title, full_text, translated_text,
                       glossary_built_at, created_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes
                WHERE work_id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, work_id, volume_number, title, full_text, translated_text,
                       glossary_built_at, created_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes
                WHERE work_id = ? AND volume_number = ?
                """,
                (work_id, volume_number),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_volume(row)

    def update_full_text(self, volume_id: int, text: str) -> bool:
        """Update only the full_text field of a volume."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE volumes
                SET full_text = ?
                WHERE id = ?
                """,
                (text, volume_id),
            )
            return cur.rowcount > 0

    def mark_glossary_built(self, volume_id: int) -> bool:
        """Mark a volume as having its glossary built."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE volumes
                SET glossary_built_at = CURRENT_TIMESTAMP
                WHERE id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE volumes
                SET glossary_build_status = ?,
                    glossary_error_message = ?,
                    glossary_resume_phase = ?
                WHERE id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, work_id, volume_number, title, full_text, translated_text,
                       glossary_built_at, created_at, glossary_build_status,
                       glossary_error_message, glossary_resume_phase
                FROM volumes
                WHERE work_id = ? AND glossary_build_status = ?
                ORDER BY volume_number
                """,
                (work_id, status),
            )
            rows = cur.fetchall()
            return [self._row_to_volume(row) for row in rows]