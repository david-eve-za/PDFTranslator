from typing import Optional, List

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import Work
from database.services.vector_store import VectorStoreService


class BookRepository(BaseRepository[Work]):
    def _row_to_work(self, row: tuple) -> Work:
        return Work(
            id=row[0],
            title=row[1],
            source_lang=row[2],
            target_lang=row[3],
        )

    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def get_by_id(self, id: int) -> Optional[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, source_lang, target_lang
                    FROM works
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_work(row)

    def get_all(self) -> List[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, source_lang, target_lang
                    FROM works
                    ORDER BY id
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_work(row) for row in rows]

    def create(self, entity: Work) -> Work:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO works (title, source_lang, target_lang)
                    VALUES (%s, %s, %s)
                    RETURNING id, title, source_lang, target_lang
                    """,
                    (
                        entity.title,
                        entity.source_lang,
                        entity.target_lang,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_work(row)

    def update(self, entity: Work) -> Optional[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE works
                    SET title = %s, source_lang = %s, target_lang = %s
                    WHERE id = %s
                    RETURNING id, title, source_lang, target_lang
                    """,
                    (
                        entity.title,
                        entity.source_lang,
                        entity.target_lang,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_work(row)

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM works WHERE id = %s", (id,))
                return cur.rowcount > 0

    def find_by_title(self, title: str, fuzzy: bool = False) -> List[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if fuzzy:
                    cur.execute(
                        """
                        SELECT id, title, source_lang, target_lang
                        FROM works
                        WHERE title % %s
                        ORDER BY similarity(title, %s) DESC
                        """,
                        (title, title),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, title, source_lang, target_lang
                        FROM works
                        WHERE title = %s
                        ORDER BY id
                        """,
                        (title,),
                    )
                rows = cur.fetchall()
                return [self._row_to_work(row) for row in rows]

    def find_similar_works(self, query: str, top_k: int = 5) -> List[Work]:
        """
        Busca obras similares usando embeddings semánticos.

        Args:
            query: Consulta de búsqueda
            top_k: Número máximo de resultados

        Returns:
            Lista de obras más similares
        """
        query_embedding = self._vector_service.embed_query(query)
        works = self.get_all()
        if not works:
            return []
        titles = [w.title for w in works]
        title_embeddings = self._vector_service.embed_documents(titles)
        indices = self._vector_service.find_most_similar(
            query_embedding, title_embeddings, top_k
        )
        return [works[i] for i in indices]

    def find_all(self) -> List[Work]:
        """Returns all works in the database."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, source_lang, target_lang FROM works")
                rows = cur.fetchall()
                return [self._row_to_work(row) for row in rows]
