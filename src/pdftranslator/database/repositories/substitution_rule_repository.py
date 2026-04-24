"""Substitution rule repository."""

from typing import Optional, List

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import SubstitutionRule


class SubstitutionRuleRepository(BaseRepository[SubstitutionRule]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_rule(self, row: tuple) -> SubstitutionRule:
        return SubstitutionRule(
            id=row[0],
            name=row[1],
            pattern=row[2],
            replacement=row[3],
            description=row[4] if len(row) > 4 and row[4] else None,
            is_active=row[5] if len(row) > 5 else True,
            apply_on_extract=row[6] if len(row) > 6 else True,
            created_at=row[7] if len(row) > 7 else None,
            updated_at=row[8] if len(row) > 8 else None,
        )

    def get_by_id(self, id: int) -> Optional[SubstitutionRule]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_rule(row) if row else None

    def get_all(self, active_only: bool = False) -> List[SubstitutionRule]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                """
                if active_only:
                    query += " WHERE is_active = TRUE"
                query += " ORDER BY name"
                cur.execute(query)
                rows = cur.fetchall()
                return [self._row_to_rule(row) for row in rows]

    def get_auto_apply_rules(self) -> List[SubstitutionRule]:
        """Get rules that should be applied on extraction."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                    WHERE is_active = TRUE AND apply_on_extract = TRUE
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_rule(row) for row in rows]

    def create(self, entity: SubstitutionRule) -> SubstitutionRule:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO text_substitution_rules
                        (name, pattern, replacement, description, is_active, apply_on_extract)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, pattern, replacement, description,
                              is_active, apply_on_extract, created_at, updated_at
                    """,
                    (
                        entity.name,
                        entity.pattern,
                        entity.replacement,
                        entity.description,
                        entity.is_active,
                        entity.apply_on_extract,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_rule(row)

    def update(self, entity: SubstitutionRule) -> SubstitutionRule:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE text_substitution_rules
                    SET name = %s, pattern = %s, replacement = %s,
                        description = %s, is_active = %s, apply_on_extract = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, pattern, replacement, description,
                              is_active, apply_on_extract, created_at, updated_at
                    """,
                    (
                        entity.name,
                        entity.pattern,
                        entity.replacement,
                        entity.description,
                        entity.is_active,
                        entity.apply_on_extract,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_rule(row) if row else None

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM text_substitution_rules WHERE id = %s", (id,))
                return cur.rowcount > 0
