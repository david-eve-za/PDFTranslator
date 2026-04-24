import warnings

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.services.vector_store import VectorStoreService
from pdftranslator.domain.models.work import Work


class BookRepository(BaseRepository[Work]):
    def _row_to_work(self, row: tuple) -> Work:
        return Work(
            id=row[0],
            title=row[1],
            title_translated=row[2],
            source_lang=row[3],
            target_lang=row[4],
            author=row[5] if len(row) > 5 else None,
        )

    def __init__(self, pool: DatabasePool | None = None, vector_service: VectorStoreService | None = None):
        if pool is None:
            warnings.warn(
                "Providing pool=None is deprecated. Inject a ConnectionPool explicitly.",
                DeprecationWarning,
                stacklevel=2,
            )
            pool = DatabasePool.get_instance()
        self._pool = pool
        if vector_service is None:
            warnings.warn(
                "Providing vector_service=None is deprecated. Inject a VectorStoreService explicitly.",
                DeprecationWarning,
                stacklevel=2,
            )
        self._vector_service = vector_service or VectorStoreService()

    def get_by_id(self, id: int) -> Work | None:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE id = %s
                    """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_work(row)

    def get_all(self) -> list[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    ORDER BY id
                    """
            )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]

    def create(self, entity: Work) -> Work:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO works (title, title_translated, source_lang, target_lang, author)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, title, title_translated, source_lang, target_lang, author
                """,
                (
                    entity.title,
                    entity.title_translated,
                    entity.source_lang,
                    entity.target_lang,
                    entity.author,
                ),
            )
            row = cur.fetchone()
            return self._row_to_work(row)

    def update(self, entity: Work) -> Work | None:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE works
                SET title = %s, title_translated = %s, source_lang = %s, target_lang = %s, author = %s
                WHERE id = %s
                RETURNING id, title, title_translated, source_lang, target_lang, author
                """,
                (
                    entity.title,
                    entity.title_translated,
                    entity.source_lang,
                    entity.target_lang,
                    entity.author,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_work(row)

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM works WHERE id = %s", (id,))
            return cur.rowcount > 0

    def find_by_title(self, title: str, fuzzy: bool = False) -> list[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            if fuzzy:
                cur.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE title % %s
                    ORDER BY similarity(title, %s) DESC
                    """,
                    (title, title),
                )
            else:
                cur.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE title = %s
                    ORDER BY id
                    """,
                    (title,),
                )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]

    def find_similar_works(self, query: str, top_k: int = 5) -> list[Work]:
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

    def find_all(self) -> list[Work]:
        """Returns all works in the database."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, title_translated, source_lang, target_lang, author FROM works"
            )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]
