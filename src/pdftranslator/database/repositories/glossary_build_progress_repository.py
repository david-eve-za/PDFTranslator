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

    def _row_to_progress(self, row) -> GlossaryBuildProgress:
        return GlossaryBuildProgress(
            id=row["id"],
            work_id=row["work_id"],
            volume_id=row["volume_id"],
            entity_text=row["entity_text"],
            phase=row["phase"],
            entity_type=row["entity_type"],
            frequency=row["frequency"],
            contexts=row["contexts"] if row["contexts"] else [],
            translation=row["translation"],
            embedding=None,  # Embeddings not stored in SQLite
            validation_batch=row["validation_batch"],
            translation_batch=row["translation_batch"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

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

        results = []

        with self._pool.connection() as conn:
            for entity in entities:
                cur = conn.execute(
                    """
                    INSERT INTO glossary_build_progress
                        (work_id, volume_id, entity_text, phase,
                         entity_type, frequency, contexts)
                    VALUES (?, ?, ?, 'extracted', ?, ?, ?)
                    ON CONFLICT (work_id, volume_id, LOWER(entity_text))
                    DO UPDATE SET
                        entity_type = excluded.entity_type,
                        frequency = excluded.frequency,
                        contexts = excluded.contexts,
                        phase = 'extracted',
                        updated_at = CURRENT_TIMESTAMP
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, work_id, volume_id, entity_text, phase,
                       entity_type, frequency, contexts, translation,
                       validation_batch, translation_batch,
                       created_at, updated_at
                FROM glossary_build_progress
                WHERE work_id = ? AND volume_id = ? AND phase = ?
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

        placeholders = ",".join("?" * len(ids))
        batch_field = ""
        params = [phase]

        if batch_number is not None:
            if phase == "validated":
                batch_field = ", validation_batch = ?"
            elif phase == "translated":
                batch_field = ", translation_batch = ?"
            params.append(batch_number)

        params.extend(ids)

        with self._pool.connection() as conn:
            cur = conn.execute(
                f"""
                UPDATE glossary_build_progress
                SET phase = ?{batch_field}, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                """,
                params,
            )
            return cur.rowcount

    def batch_update_embeddings(
        self,
        updates: List[tuple[int, List[float]]],
    ) -> int:
        """Update embeddings for validated entities.

        Note: Embeddings not stored in SQLite, this is a no-op."""
        return len(updates)

    def batch_update_translations(
        self,
        updates: List[tuple[int, str]],
    ) -> int:
        """Update translations for entities."""
        if not updates:
            return 0

        with self._pool.connection() as conn:
            for progress_id, translation in updates:
                conn.execute(
                    """
                    UPDATE glossary_build_progress
                    SET translation = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT phase, COUNT(*) as count,
                       MAX(validation_batch) as last_val_batch,
                       MAX(translation_batch) as last_trans_batch
                FROM glossary_build_progress
                WHERE work_id = ? AND volume_id = ?
                GROUP BY phase
                ORDER BY phase
                """,
                (work_id, volume_id),
            )
            results = cur.fetchall()

            if not results:
                return ("extracted", None)

            phase_counts = {
                row["phase"]: (
                    row["count"],
                    row["last_val_batch"],
                    row["last_trans_batch"],
                )
                for row in results
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT phase, COUNT(*) as count
                FROM glossary_build_progress
                WHERE work_id = ? AND volume_id = ?
                GROUP BY phase
                """,
                (work_id, volume_id),
            )
            return {row["phase"]: row["count"] for row in cur.fetchall()}

    def cleanup_completed(self, volume_id: int) -> int:
        """Remove progress records after successful completion."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                DELETE FROM glossary_build_progress
                WHERE volume_id = ?
                """,
                (volume_id,),
            )
            return cur.rowcount