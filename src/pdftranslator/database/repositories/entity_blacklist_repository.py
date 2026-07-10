"""Entity Blacklist repository for SQLite."""

from typing import Optional, List

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import EntityBlacklist


class EntityBlacklistRepository(BaseRepository[EntityBlacklist]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_blacklist(self, row) -> EntityBlacklist:
        return EntityBlacklist(
            id=row["id"],
            term=row["term"],
            reason=row["reason"],
        )

    def get_by_id(self, id: int) -> Optional[EntityBlacklist]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, reason FROM entity_blacklist WHERE id = ?",
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_blacklist(row)

    def get_all(self) -> List[EntityBlacklist]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, reason FROM entity_blacklist ORDER BY term"
            )
            return [self._row_to_blacklist(row) for row in cur.fetchall()]

    def get_all_terms(self) -> List[str]:
        """Get all blacklisted terms as a list of strings."""
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT term FROM entity_blacklist")
            return [row["term"] for row in cur.fetchall()]

    def create(self, entity: EntityBlacklist) -> EntityBlacklist:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "INSERT INTO entity_blacklist (term, reason) VALUES (?, ?) RETURNING id, term, reason",
                (entity.term.lower(), entity.reason),
            )
            row = cur.fetchone()
            return self._row_to_blacklist(row)

    def add(self, term: str, reason: Optional[str] = None) -> EntityBlacklist:
        return self.create(EntityBlacklist(id=None, term=term, reason=reason))

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM entity_blacklist WHERE id = ?", (id,))
            return cur.rowcount > 0

    def remove(self, term: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "DELETE FROM entity_blacklist WHERE LOWER(term) = LOWER(?)",
                (term,),
            )
            return cur.rowcount > 0

    def exists(self, term: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT 1 FROM entity_blacklist WHERE LOWER(term) = LOWER(?)",
                (term,),
            )
            return cur.fetchone() is not None

    def update(self, entity: EntityBlacklist) -> Optional[EntityBlacklist]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE entity_blacklist
                SET term = ?, reason = ?
                WHERE id = ?
                RETURNING id, term, reason
                """,
                (entity.term.lower(), entity.reason, entity.id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_blacklist(row)

    def find_by_term(self, term: str) -> Optional[EntityBlacklist]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, term, reason FROM entity_blacklist WHERE term = ?",
                (term,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_blacklist(row)

    def is_blacklisted(self, term: str) -> bool:
        """Check if a term is in the blacklist."""
        return self.find_by_term(term) is not None