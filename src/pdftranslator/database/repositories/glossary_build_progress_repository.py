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
                                  embedding, validation_batch, translation_batch,
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
                           embedding, validation_batch, translation_batch,
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

                phase_counts = {row[0]: (row[1], row[2], row[3]) for row in results}

                if "extracted" in phase_counts:
                    extracted_count, _, _ = phase_counts.get(
                        "extracted", (0, None, None)
                    )
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
