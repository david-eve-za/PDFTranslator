from typing import Optional, Set

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import EntityBlacklist


class EntityBlacklistRepository(BaseRepository[EntityBlacklist]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_entity_blacklist(self, row: tuple) -> EntityBlacklist:
        return EntityBlacklist(
            id=row[0],
            term=row[1],
            reason=row[2] if len(row) > 2 else None,
        )

    def get_by_id(self, id: int) -> Optional[EntityBlacklist]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, reason FROM entity_blacklist WHERE id = %s",
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_entity_blacklist(row) if row else None

    def get_all(self) -> list[EntityBlacklist]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, reason FROM entity_blacklist ORDER BY term"
                )
                rows = cur.fetchall()
                return [self._row_to_entity_blacklist(row) for row in rows]

    def get_all_terms(self) -> Set[str]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT term FROM entity_blacklist")
                return {row[0].lower() for row in cur.fetchall()}

    def create(self, entity: EntityBlacklist) -> EntityBlacklist:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO entity_blacklist (term, reason)
                    VALUES (%s, %s)
                    RETURNING id, term, reason
                    """,
                    (entity.term.lower(), entity.reason),
                )
                row = cur.fetchone()
                return self._row_to_entity_blacklist(row)

    def add(self, term: str, reason: Optional[str] = None) -> EntityBlacklist:
        return self.create(EntityBlacklist(id=None, term=term, reason=reason))

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM entity_blacklist WHERE id = %s", (id,))
                return cur.rowcount > 0

    def remove(self, term: str) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM entity_blacklist WHERE LOWER(term) = LOWER(%s)",
                    (term,),
                )
                return cur.rowcount > 0

    def exists(self, term: str) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM entity_blacklist WHERE LOWER(term) = LOWER(%s)",
                    (term,),
                )
                return cur.fetchone() is not None

    def update(self, entity: EntityBlacklist) -> EntityBlacklist:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE entity_blacklist
                    SET term = %s, reason = %s
                    WHERE id = %s
                    RETURNING id, term, reason
                    """,
                    (entity.term.lower(), entity.reason, entity.id),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_entity_blacklist(row)
