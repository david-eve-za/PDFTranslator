from typing import Optional, Dict

from src.database.connection import DatabasePool
from src.database.repositories.base import BaseRepository
from src.database.models import FantasyTerm


class FantasyTermRepository(BaseRepository[FantasyTerm]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_fantasy_term(self, row: tuple) -> FantasyTerm:
        return FantasyTerm(
            id=row[0],
            term=row[1],
            entity_type=row[2],
            do_not_translate=row[3],
            context_hint=row[4] if len(row) > 4 else None,
        )

    def get_by_id(self, id: int) -> Optional[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms WHERE id = %s",
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def get_all(self) -> list[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms ORDER BY term"
                )
                rows = cur.fetchall()
                return [self._row_to_fantasy_term(row) for row in rows]

    def get_all_terms(self) -> Dict[str, FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms"
                )
                rows = cur.fetchall()
                return {row[1].lower(): self._row_to_fantasy_term(row) for row in rows}

    def get_by_term(self, term: str) -> Optional[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, term, entity_type, do_not_translate, context_hint
                    FROM fantasy_terms
                    WHERE LOWER(term) = LOWER(%s)
                    """,
                    (term,),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def create(self, entity: FantasyTerm) -> FantasyTerm:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, term, entity_type, do_not_translate, context_hint
                    """,
                    (
                        entity.term.lower(),
                        entity.entity_type,
                        entity.do_not_translate,
                        entity.context_hint,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row)

    def update(self, entity: FantasyTerm) -> FantasyTerm:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE fantasy_terms
                    SET entity_type = %s, do_not_translate = %s, context_hint = %s
                    WHERE id = %s
                    RETURNING id, term, entity_type, do_not_translate, context_hint
                    """,
                    (
                        entity.entity_type,
                        entity.do_not_translate,
                        entity.context_hint,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fantasy_terms WHERE id = %s", (id,))
                return cur.rowcount > 0
