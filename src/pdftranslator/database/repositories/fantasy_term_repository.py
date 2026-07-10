"""Fantasy term repository for SQLite."""

from typing import Optional, Dict

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import FantasyTerm


class FantasyTermRepository(BaseRepository[FantasyTerm]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_fantasy_term(self, row) -> FantasyTerm:
        return FantasyTerm(
            id=row["id"],
            term=row["term"],
            entity_type=row["entity_type"],
            do_not_translate=bool(row["do_not_translate"]),
            context_hint=row["context_hint"] if "context_hint" in row.keys() else None,
        )

    def get_by_id(self, id: int) -> Optional[FantasyTerm]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms WHERE id = ?",
                (id,),
            )
            row = cur.fetchone()
            return self._row_to_fantasy_term(row) if row else None

    def get_all(self) -> list[FantasyTerm]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms ORDER BY term"
            )
            rows = cur.fetchall()
            return [self._row_to_fantasy_term(row) for row in rows]

    def get_all_terms(self) -> Dict[str, FantasyTerm]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms"
            )
            rows = cur.fetchall()
            return {row["term"].lower(): self._row_to_fantasy_term(row) for row in rows}

    def get_by_term(self, term: str) -> Optional[FantasyTerm]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, term, entity_type, do_not_translate, context_hint
                FROM fantasy_terms
                WHERE LOWER(term) = LOWER(?)
                """,
                (term,),
            )
            row = cur.fetchone()
            return self._row_to_fantasy_term(row) if row else None

    def create(self, entity: FantasyTerm) -> FantasyTerm:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint)
                VALUES (?, ?, ?, ?)
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

    def update(self, entity: FantasyTerm) -> Optional[FantasyTerm]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE fantasy_terms
                SET entity_type = ?, do_not_translate = ?, context_hint = ?
                WHERE id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM fantasy_terms WHERE id = ?", (id,))
            return cur.rowcount > 0